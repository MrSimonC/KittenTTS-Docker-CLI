"""Build-time script to pre-cache the configured Hugging Face model."""

import os

from kittentts import KittenTTS


def main() -> None:
    model_name = os.environ.get("KITTENTTS_MODEL", "KittenML/kitten-tts-mini-0.8")
    print(f"Downloading and caching KittenTTS model: {model_name}")
    KittenTTS(model_name)
    print("Model cached successfully.")


if __name__ == "__main__":
    main()
