---
name: kitten-tts
description: Speak short messages aloud with the bundled `./scripts/kittentts_say.py` wrapper. Use when the user asks to say, speak, announce, read aloud, play a spoken status update, or generate quick local text-to-speech through the KittenTTS Docker CLI wrapper.
---

# Kitten TTS

Use the bundled wrapper at `./scripts/kittentts_say.py` to generate and play speech locally.

## Workflow

1. Run `./scripts/kittentts_say.py` (or `python3 ./scripts/kittentts_say.py`) from the skill directory.
2. If the user specified a voice, use it. Otherwise default to `Bruno`.
3. Prefer `--text` for the spoken message so punctuation and spacing stay intact.
4. Run the command directly instead of rewriting or explaining it unless the user asked for the command only.
5. If the bundled script is missing, direct the user to this repository's `skills/kitten-tts` folder.

## Command Pattern

Use:

```bash
./scripts/kittentts_say.py --voice <Voice> --text "<Message>"
```

Example:

```bash
./scripts/kittentts_say.py --voice Bruno --text "Hello, I am Bruno, your AI assistant. How can I help you today?"
```

## Guidance

- Keep spoken messages short unless the user explicitly wants longer narration.
- Preserve the user's wording unless they ask you to rewrite it.
- If the user asks what voices are available, run `./scripts/kittentts_say.py --list-voices`.
- If the user wants the file generated without playback, add `--no-play`.
- If the user wants a saved WAV path, add `--output <path>`.
