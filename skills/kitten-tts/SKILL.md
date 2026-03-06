---
name: kitten-tts
description: Instruct Codex to speak short messages aloud with the local `kittentts_say.py` command. Use when the user asks to say, speak, announce, read aloud, play a spoken status update, or generate quick local text-to-speech through the KittenTTS Docker CLI wrapper.
---

# Kitten TTS

Use `kittentts_say.py` from `PATH` to generate and play speech locally.

## Workflow

1. Confirm the command is available by running `command -v kittentts_say.py`.
2. If the command is missing, tell the user to set it up from [MrSimonC/KittenTTS-Docker-CLI](https://github.com/MrSimonC/KittenTTS-Docker-CLI) and stop.
3. If the user specified a voice, use it. Otherwise default to `Bruno`.
4. Prefer `--text` for the spoken message so punctuation and spacing stay intact.
5. Run the command directly instead of rewriting or explaining it unless the user asked for the command only.

## Command Pattern

Use:

```bash
kittentts_say.py --voice <Voice> --text "<Message>"
```

Example:

```bash
kittentts_say.py --voice Bruno --text "Hello, I am Bruno, your AI assistant. How can I help you today?"
```

## Guidance

- Keep spoken messages short unless the user explicitly wants longer narration.
- Preserve the user's wording unless they ask you to rewrite it.
- If the user asks what voices are available, run `kittentts_say.py --list-voices`.
- If the user wants the file generated without playback, add `--no-play`.
- If the user wants a saved WAV path, add `--output <path>`.
