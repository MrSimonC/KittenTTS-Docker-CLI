# KittenTTS Docker MCP

This repository packages a self-contained Docker image for running a persistent KittenTTS MCP server on a fixed local port.

It is intentionally limited to the Docker runtime and its documentation. It does not include the higher-level local skill wrapper or desktop playback helpers.

## Default Runtime Contract

- Host port: `59151`
- MCP endpoint: `http://127.0.0.1:59151/mcp`
- Health endpoint: `http://127.0.0.1:59151/healthz`
- Voices endpoint: `http://127.0.0.1:59151/voices`
- Direct TTS endpoint: `http://127.0.0.1:59151/tts`
- Container behavior: `restart: unless-stopped`

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

This builds the image with the default `kitten-tts-mini-0.8` model and starts a persistent container named `kittentts-mcp`.

## Add The MCP Server To CLI Clients

Once the container is running, add the local MCP endpoint to your CLI client.

Claude Code:

```bash
claude mcp add --transport http --scope user kittentts http://127.0.0.1:59151/mcp
claude mcp get kittentts
```

Codex CLI:

```bash
codex mcp add kittentts --url http://127.0.0.1:59151/mcp
codex mcp list
```

If you prefer a repo-local Claude Code configuration instead of a user-level one, replace `--scope user` with `--scope project`.

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
  -d '{"text":"Hello from KittenTTS Docker MCP","voice":"Bruno","speed":1.0}'
```

Probe the MCP endpoint:

```bash
curl -sS -o /dev/null -w '%{http_code}\n' http://127.0.0.1:59151/mcp
```

A `406` response is expected for this simple probe because the endpoint is live but the request is not performing an MCP handshake.

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
- The server exposes Streamable HTTP MCP on `/mcp` and lightweight JSON endpoints for health and direct synthesis.
