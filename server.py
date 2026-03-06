"""KittenTTS server with lightweight HTTP endpoints."""

import io
import itertools
import os
import sys
import threading
from pathlib import Path

import soundfile as sf
import uvicorn
from kittentts import KittenTTS
from starlette.applications import Starlette
from starlette.middleware.cors import CORSMiddleware
from starlette.requests import Request
from starlette.responses import FileResponse
from starlette.responses import JSONResponse
from starlette.routing import Route


DEFAULT_MODEL = "KittenML/kitten-tts-mini-0.8"
DEFAULT_VOICE = "Bruno"
VALID_VOICES = ["Bella", "Jasper", "Luna", "Bruno", "Rosie", "Hugo", "Kiki", "Leo"]
BAKED_MODEL_PATH = "/app/baked-model.txt"
AUDIO_OUTPUT_DIR = Path(os.environ.get("KITTENTTS_AUDIO_DIR", "/tmp/kittentts"))
MAX_AUDIO_FILES = 20
_audio_slot_lock = threading.Lock()
_audio_slot_counter = itertools.count()

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


def _ensure_audio_output_dir() -> None:
    AUDIO_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


MODEL_NAME = _load_baked_model_name()
_ensure_audio_output_dir()
_old_stdout = sys.stdout
sys.stdout = io.StringIO()
tts_model = KittenTTS(MODEL_NAME)
sys.stdout = _old_stdout


def synthesize_wav_bytes(text: str, voice: str = DEFAULT_VOICE, speed: float = 1.0) -> bytes:
    if voice not in VALID_VOICES:
        raise ValueError(f"Invalid voice '{voice}'. Choose from: {', '.join(VALID_VOICES)}")
    if not text or not text.strip():
        raise ValueError("Text must not be empty.")

    audio = tts_model.generate(text, voice=voice, speed=speed, clean_text=True)
    buffer = io.BytesIO()
    sf.write(buffer, audio, 24000, format="WAV")
    buffer.seek(0)
    return buffer.read()


def _allocate_audio_file() -> tuple[str, Path]:
    with _audio_slot_lock:
        slot = next(_audio_slot_counter) % MAX_AUDIO_FILES
    filename = f"audio-{slot:02d}.wav"
    return filename, AUDIO_OUTPUT_DIR / filename


def synthesize_wav_file(text: str, voice: str = DEFAULT_VOICE, speed: float = 1.0) -> dict[str, str | float | int]:
    wav_bytes = synthesize_wav_bytes(text=text, voice=voice, speed=speed)
    filename, file_path = _allocate_audio_file()
    file_path.write_bytes(wav_bytes)
    return {
        "filename": filename,
        "content_type": "audio/wav",
        "size_bytes": len(wav_bytes),
        "sample_rate": 24000,
        "voice": voice,
        "speed": float(speed),
    }


async def healthz(_request: Request) -> JSONResponse:
    return JSONResponse({"ok": True, "model": MODEL_NAME, "voices": VALID_VOICES})


async def voices(_request: Request) -> JSONResponse:
    return JSONResponse({"voices": VALID_VOICES})


async def audio_file(request: Request):
    filename = request.path_params["filename"]
    if "/" in filename or "\\" in filename:
        return JSONResponse({"ok": False, "error": "Invalid audio filename."}, status_code=400)

    file_path = AUDIO_OUTPUT_DIR / filename
    if not file_path.is_file():
        return JSONResponse({"ok": False, "error": "Audio file not found."}, status_code=404)

    return FileResponse(file_path, media_type="audio/wav", filename=filename)


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
        result = synthesize_wav_file(text=text, voice=voice, speed=float(speed))
    except Exception as exc:  # noqa: BLE001
        return JSONResponse({"ok": False, "error": str(exc)}, status_code=400)

    audio_url = str(request.url_for("audio_file", filename=result["filename"]))
    return JSONResponse({"ok": True, **result, "url": audio_url})


def build_http_app() -> Starlette:
    app = Starlette(
        routes=[
            Route("/healthz", healthz, methods=["GET"]),
            Route("/voices", voices, methods=["GET"]),
            Route("/tts", tts, methods=["POST"]),
            Route("/audio/{filename:str}", audio_file, methods=["GET"], name="audio_file"),
        ],
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )
    return app


if __name__ == "__main__":
    host = os.environ.get("KITTENTTS_HOST", "0.0.0.0")
    port = int(os.environ.get("KITTENTTS_PORT", "8000"))
    uvicorn.run(build_http_app(), host=host, port=port, log_level="warning")
