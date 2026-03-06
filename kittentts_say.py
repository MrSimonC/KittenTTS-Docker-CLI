#!/usr/bin/env python3
"""Local CLI wrapper for the Dockerized KittenTTS server."""

from __future__ import annotations

import argparse
import json
import os
import platform
import shutil
import subprocess
import sys
import tempfile
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path


DEFAULT_BASE_URL = os.environ.get("KITTENTTS_BASE_URL", "http://127.0.0.1:59151").rstrip("/")
DEFAULT_VOICE = os.environ.get("KITTENTTS_VOICE", "Bruno")
DEFAULT_SPEED = float(os.environ.get("KITTENTTS_SPEED", "1.0"))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate and play speech using the local Dockerized KittenTTS server."
    )
    parser.add_argument("text", nargs="*", help="Text to speak.")
    parser.add_argument("--voice", default=DEFAULT_VOICE, help="Voice name to use.")
    parser.add_argument("--speed", type=float, default=DEFAULT_SPEED, help="Speech speed.")
    parser.add_argument(
        "--base-url",
        default=DEFAULT_BASE_URL,
        help="Base URL for the KittenTTS server.",
    )
    parser.add_argument(
        "--list-voices",
        action="store_true",
        help="List available voices and exit.",
    )
    parser.add_argument(
        "--text",
        dest="text_value",
        help="Explicit text to speak. Overrides positional text.",
    )
    parser.add_argument(
        "--print-url",
        action="store_true",
        help="Print the generated audio URL.",
    )
    parser.add_argument(
        "--print-path",
        action="store_true",
        help="Print the downloaded local WAV path.",
    )
    parser.add_argument(
        "--no-play",
        action="store_true",
        help="Generate and download the WAV without playing it.",
    )
    parser.add_argument(
        "--output",
        help="Optional output WAV path on the host. Defaults to a temporary file.",
    )
    return parser


def request_json(url: str, payload: dict | None = None) -> dict:
    data = None
    headers = {}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"

    request = urllib.request.Request(url, data=data, headers=headers)
    try:
        with urllib.request.urlopen(request) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise SystemExit(f"Request failed: {exc.code} {exc.reason}\n{body}") from exc
    except urllib.error.URLError as exc:
        raise SystemExit(f"Could not reach KittenTTS server at {url}: {exc.reason}") from exc


def list_voices(base_url: str) -> None:
    response = request_json(f"{base_url}/voices")
    for voice in response.get("voices", []):
        print(voice)


def synthesize(base_url: str, text: str, voice: str, speed: float) -> dict:
    response = request_json(
        f"{base_url}/tts",
        payload={"text": text, "voice": voice, "speed": speed},
    )
    if not response.get("ok"):
        raise SystemExit(response.get("error", "Unknown synthesis error."))
    return response


def download_file(url: str, output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with urllib.request.urlopen(url) as response, output_path.open("wb") as handle:
            handle.write(response.read())
    except urllib.error.URLError as exc:
        raise SystemExit(f"Could not download audio from {url}: {exc.reason}") from exc
    return output_path


def is_wsl() -> bool:
    if os.environ.get("WSL_DISTRO_NAME"):
        return True
    try:
        return "microsoft" in Path("/proc/version").read_text(encoding="utf-8").lower()
    except OSError:
        return False


def convert_to_windows_path(path: Path) -> str:
    result = subprocess.run(
        ["wslpath", "-w", str(path)],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def play_audio(path: Path) -> str:
    system = platform.system()

    if is_wsl():
        windows_path = convert_to_windows_path(path)
        command = [
            "powershell.exe",
            "-NoProfile",
            "-Command",
            f"(New-Object Media.SoundPlayer '{windows_path}').PlaySync()",
        ]
        subprocess.run(command, check=True)
        return "powershell.exe"

    if system == "Windows":
        command = [
            "powershell",
            "-NoProfile",
            "-Command",
            f"(New-Object Media.SoundPlayer '{path}').PlaySync()",
        ]
        subprocess.run(command, check=True)
        return "powershell"

    if system == "Darwin":
        subprocess.run(["afplay", str(path)], check=True)
        return "afplay"

    for player in (
        ["paplay", str(path)],
        ["aplay", str(path)],
        ["ffplay", "-nodisp", "-autoexit", "-loglevel", "error", str(path)],
        ["play", "-q", str(path)],
    ):
        if shutil.which(player[0]):
            subprocess.run(player, check=True)
            return player[0]

    raise SystemExit(
        "No supported audio player was found on this host. "
        "Use --no-play, or install a player such as afplay, paplay, aplay, ffplay, or play."
    )


def resolve_text(args: argparse.Namespace) -> str | None:
    if args.text_value is not None:
        return args.text_value
    if args.text:
        return " ".join(args.text).strip()
    return None


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    base_url = args.base_url.rstrip("/")

    if args.list_voices:
        list_voices(base_url)
        return 0

    text = resolve_text(args)
    if not text:
        parser.error("text is required unless --list-voices is used")

    response = synthesize(base_url, text=text, voice=args.voice, speed=args.speed)

    output_path = Path(args.output) if args.output else Path(tempfile.gettempdir()) / response["filename"]
    download_file(response["url"], output_path)

    if args.print_url:
        print(response["url"])
    if args.print_path:
        print(output_path)

    if not args.no_play:
        player = play_audio(output_path)
        if not args.print_url and not args.print_path:
            print(f"Played via {player}: {output_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
