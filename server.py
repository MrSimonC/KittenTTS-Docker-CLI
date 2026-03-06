"""KittenTTS server with MCP and lightweight HTTP endpoints."""

import base64
import contextlib
import io
import os
import sys

import soundfile as sf
import uvicorn
from kittentts import KittenTTS
from mcp.server.fastmcp import FastMCP
from starlette.applications import Starlette
from starlette.middleware.cors import CORSMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Mount, Route


DEFAULT_MODEL = "KittenML/kitten-tts-mini-0.8"
DEFAULT_VOICE = "Bruno"
VALID_VOICES = ["Bella", "Jasper", "Luna", "Bruno", "Rosie", "Hugo", "Kiki", "Leo"]
BAKED_MODEL_PATH = "/app/baked-model.txt"

_original_generate = KittenTTS.generate


def _quiet_generate(self, text, voice="expr-voice-5-m", speed=1.0, clean_text=False):
    old_stdout = sys.stdout
    sys.stdout = io.StringIO()
    try:
        return _original_generate(
            self,
            text,
            voice=voice,
            speed=speed,
            clean_text=clean_text,
        )
    finally:
        sys.stdout = old_stdout


KittenTTS.generate = _quiet_generate


def _load_baked_model_name() -> str:
    try:
        with open(BAKED_MODEL_PATH, "r", encoding="utf-8") as handle:
            model_name = handle.read().strip()
            if model_name:
                return model_name
    except OSError:
        pass
    return DEFAULT_MODEL


MODEL_NAME = _load_baked_model_name()
_old_stdout = sys.stdout
sys.stdout = io.StringIO()
tts_model = KittenTTS(MODEL_NAME)
sys.stdout = _old_stdout

mcp = FastMCP(
    "KittenTTS",
    instructions="Text-to-speech server using KittenTTS. Generates WAV audio from text.",
    stateless_http=True,
    json_response=True,
    streamable_http_path="/mcp",
)


def synthesize_wav_b64(text: str, voice: str = DEFAULT_VOICE, speed: float = 1.0) -> str:
    if voice not in VALID_VOICES:
        raise ValueError(f"Invalid voice '{voice}'. Choose from: {', '.join(VALID_VOICES)}")
    if not text or not text.strip():
        raise ValueError("Text must not be empty.")

    audio = tts_model.generate(text, voice=voice, speed=speed, clean_text=True)
    buffer = io.BytesIO()
    sf.write(buffer, audio, 24000, format="WAV")
    buffer.seek(0)
    return base64.b64encode(buffer.read()).decode("utf-8")


@mcp.tool()
def text_to_speech(text: str, voice: str = DEFAULT_VOICE, speed: float = 1.0) -> str:
    """Convert text to speech and return base64-encoded WAV audio."""
    return synthesize_wav_b64(text=text, voice=voice, speed=speed)


@mcp.tool()
def list_voices() -> list[str]:
    """List available voice names for text-to-speech."""
    return VALID_VOICES


async def healthz(_request: Request) -> JSONResponse:
    return JSONResponse({"ok": True, "model": MODEL_NAME, "voices": VALID_VOICES})


async def voices(_request: Request) -> JSONResponse:
    return JSONResponse({"voices": VALID_VOICES})


async def tts(request: Request) -> JSONResponse:
    try:
        payload = await request.json()
    except Exception as exc:  # noqa: BLE001
        return JSONResponse({"ok": False, "error": f"Invalid JSON body: {exc}"}, status_code=400)

    if not isinstance(payload, dict):
        return JSONResponse({"ok": False, "error": "JSON body must be an object."}, status_code=400)

    text = payload.get("text")
    voice = payload.get("voice", DEFAULT_VOICE)
    speed = payload.get("speed", 1.0)

    if not isinstance(text, str) or not text.strip():
        return JSONResponse({"ok": False, "error": "Text must be a non-empty string."}, status_code=400)
    if not isinstance(voice, str) or not voice:
        return JSONResponse({"ok": False, "error": "Voice must be a non-empty string."}, status_code=400)
    if not isinstance(speed, (int, float)):
        return JSONResponse({"ok": False, "error": "Speed must be numeric."}, status_code=400)

    try:
        wav_b64 = synthesize_wav_b64(text=text, voice=voice, speed=float(speed))
    except Exception as exc:  # noqa: BLE001
        return JSONResponse({"ok": False, "error": str(exc)}, status_code=400)

    return JSONResponse({"ok": True, "wav_b64": wav_b64, "voice": voice, "speed": float(speed)})


def build_http_app() -> Starlette:
    app = Starlette(
        routes=[
            Route("/healthz", healthz, methods=["GET"]),
            Route("/voices", voices, methods=["GET"]),
            Route("/tts", tts, methods=["POST"]),
            Mount("/", app=mcp.streamable_http_app()),
        ],
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )
    return app


@contextlib.asynccontextmanager
async def lifespan(_app: Starlette):
    async with mcp.session_manager.run():
        yield


if __name__ == "__main__":
    transport = os.environ.get("MCP_TRANSPORT", "stdio").lower()
    host = os.environ.get("FASTMCP_HOST", "0.0.0.0")
    port = int(os.environ.get("FASTMCP_PORT", "8000"))

    if transport in {"streamable-http", "http"}:
        uvicorn.run(build_http_app(), host=host, port=port, log_level="warning")
    elif transport == "sse":
        mcp.run(transport="sse", host=host, port=port)
    else:
        mcp.run(transport="stdio")
