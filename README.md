# KittenTTS Docker HTTP Server

This repository packages a self-contained Docker image for running a persistent KittenTTS HTTP server on a fixed local port.

It is intentionally limited to the Docker runtime plus a lightweight local wrapper script for host playback. The heavy TTS runtime stays inside Docker.

The default baked model is `KittenML/kitten-tts-mini-0.8`.
The running container reads the baked model from the image itself, so changing `.env` only takes effect after a rebuild.

## Supported Baked Models

Set `KITTENTTS_MODEL` at build time to bake exactly one model into the image:

- `KittenML/kitten-tts-mini-0.8`
- `KittenML/kitten-tts-micro-0.8`
- `KittenML/kitten-tts-nano-0.8`
- `KittenML/kitten-tts-nano-0.8-int8`

The upstream project notes minor issues with the int8 nano model. Treat `KittenML/kitten-tts-nano-0.8-int8` as supported with caveats rather than the safest default.

## Requirements

- Docker
- Docker Compose

## Start The Default Server

```bash
docker compose up -d --build
```

This builds the image with the default `kitten-tts-mini-0.8` model and starts a persistent container named `kittentts-http`.

## Use A Local CLI Notifier

If your main goal is "say something aloud when the AI finishes its turn", use the local wrapper command.

Typical flow:

1. Start the Docker service with `docker compose up -d --build`
2. Confirm the server is up with `curl http://127.0.0.1:59151/healthz`
3. List available voices with `python3 kittentts_say.py --list-voices`
4. Speak text with `python3 kittentts_say.py --voice Bella "Finished on one"`

List voices:

```bash
python3 kittentts_say.py --list-voices
```

Speak custom text with a chosen voice:

```bash
python3 kittentts_say.py --voice Bella "Finished on one"
```

Print the generated URL without playing it:

```bash
python3 kittentts_say.py --voice Bruno --no-play --print-url "Finished on two"
```

Save the WAV to a chosen host path:

```bash
python3 kittentts_say.py --voice Luna --output ./finished.wav "Job completed"
```

Generate the file without playback and print the downloaded path:

```bash
python3 kittentts_say.py --no-play --print-path "Background task finished"
```

This wrapper talks to the Docker server over `http://127.0.0.1:59151`, downloads the generated WAV to a local temp file, and plays it with native host tooling. No host bind mount is required.

Useful options:

- `--voice <name>` chooses the voice
- `--list-voices` queries the server for available voices
- `--speed <value>` changes speech speed
- `--output <path>` saves the WAV to a specific host path
- `--no-play` generates the WAV without starting playback

For an agents-file pattern, tell the assistant to run a command such as:

```bash
python3 /path/to/kittentts-http/kittentts_say.py --voice Bella "Finished on one"
```

This is the recommended integration point for AI CLI agents: ask the assistant to run the wrapper command at the end of its turn with the text you want spoken.

## Rebuild With A Different Baked Model

Option 1: use an environment variable for a one-off build.

```bash
KITTENTTS_MODEL=KittenML/kitten-tts-micro-0.8 docker compose up -d --build
```

Option 2: copy `.env.example` to `.env` and change `KITTENTTS_MODEL` before building.

```bash
cp .env.example .env
docker compose up -d --build
```

If you change `KITTENTTS_MODEL` later, rebuild the image again before restarting the container.

## Verify The Server

Health check:

```bash
curl http://127.0.0.1:59151/healthz
```

List voices:

```bash
curl http://127.0.0.1:59151/voices
```

Generate speech:

```bash
curl \
  -X POST http://127.0.0.1:59151/tts \
  -H "Content-Type: application/json" \
  -d '{"text":"Hello from KittenTTS Docker HTTP","voice":"Bruno","speed":1.0}'
```

That response includes metadata plus a `url` field that points to a downloadable WAV file under `/audio/...`.

## Operate The Container

View logs:

```bash
docker compose logs -f
```

Restart:

```bash
docker compose restart
```

Stop:

```bash
docker compose stop
```

Remove the container:

```bash
docker compose down
```

Rebuild from scratch after changing models:

```bash
docker compose build --no-cache
docker compose up -d
```

## Notes

- The image pre-downloads the selected Hugging Face model during `docker build` so the container can start without fetching model files at runtime.
- The runtime is CPU-oriented by default.
- The server exposes lightweight JSON endpoints for health, voices, and synthesis metadata, plus WAV files under `/audio/...`.

## Default Runtime Contract

- Host port: `59151`
- Health endpoint: `http://127.0.0.1:59151/healthz`
- Voices endpoint: `http://127.0.0.1:59151/voices`
- Direct TTS endpoint: `http://127.0.0.1:59151/tts`
- Generated audio endpoint: `http://127.0.0.1:59151/audio/<id>.wav`
- Container behavior: `restart: unless-stopped`
