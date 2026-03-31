# KittenTTS LLM Skill + Docker Service

![KittenTTS Docker CLI hero image](./assets/kitten-tts-docker-cli-hero.png)

This repository packages KittenTTS as both:

- a reusable `skills/kitten-tts` folder for LLM tooling
- a Docker image that exposes a local HTTP service

Use it when you want an agent to finish work and say something out loud without installing the full TTS runtime on the host.

The default baked model is `KittenML/kitten-tts-mini-0.8`.

## Quick start

### 1. Pull and run the published image

```bash
docker pull ghcr.io/mrsimonc/kittentts-docker-cli:latest
docker run -d \
  --name kittentts-http \
  --restart unless-stopped \
  -p 59151:8000 \
  ghcr.io/mrsimonc/kittentts-docker-cli:latest
```

Verify the service:

```bash
curl http://127.0.0.1:59151/healthz
```

### 2. Copy the skill into your agent

```bash
mkdir -p ~/.agents/skills
cp -R ./skills/kitten-tts ~/.agents/skills/kitten-tts
```

Other common skill locations:

```text
~/.copilot/skills/kitten-tts
~/.claude/skills/kitten-tts
```

### 3. Test it

List voices:

```bash
python3 ./skills/kitten-tts/scripts/kittentts_say.py --list-voices
```

Speak a short message:

```bash
python3 ./skills/kitten-tts/scripts/kittentts_say.py --voice Bella --text "Finished on one"
```

The wrapper talks to `http://127.0.0.1:59151`, downloads the generated WAV to a temp file, and plays it with native host tooling.

## Published image

GitHub Actions publishes the container image to:

```text
ghcr.io/mrsimonc/kittentts-docker-cli:latest
```

The workflow runs on pushes to `main`, and also on the repo's current `master` branch until the default branch is renamed.

GitHub Container Registry packages are commonly created as private on first publish. If the image is not publicly pullable after the first workflow run, open the package settings in GitHub once and change visibility to **Public**.

## Build locally with a different baked model

If you want a different baked-in model than the published default image, build locally instead.

One-off build:

```bash
KITTENTTS_MODEL=KittenML/kitten-tts-micro-0.8 docker compose up -d --build
```

Or use `.env`:

```bash
cp .env.example .env
docker compose up -d --build
```

Supported baked models:

- `KittenML/kitten-tts-mini-0.8`
- `KittenML/kitten-tts-micro-0.8`
- `KittenML/kitten-tts-nano-0.8`
- `KittenML/kitten-tts-nano-0.8-int8`

If you change `KITTENTTS_MODEL`, rebuild the image before restarting the container.

## API quick check

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

That response includes metadata plus a `url` field pointing to `/audio/...`.

## Operate the container

View logs:

```bash
docker logs -f kittentts-http
```

Restart:

```bash
docker restart kittentts-http
```

Stop:

```bash
docker stop kittentts-http
```

Remove:

```bash
docker rm -f kittentts-http
```

## Default runtime contract

- Host port: `59151`
- Health endpoint: `http://127.0.0.1:59151/healthz`
- Voices endpoint: `http://127.0.0.1:59151/voices`
- Direct TTS endpoint: `http://127.0.0.1:59151/tts`
- Generated audio endpoint: `http://127.0.0.1:59151/audio/<id>.wav`
- Container behavior: `restart: unless-stopped`
