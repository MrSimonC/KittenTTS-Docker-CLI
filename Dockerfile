FROM python:3.12-slim AS builder

ARG KITTENTTS_MODEL=KittenML/kitten-tts-mini-0.8
ENV KITTENTTS_MODEL=${KITTENTTS_MODEL}
ENV PYTHONDONTWRITEBYTECODE=1
ENV PIP_NO_CACHE_DIR=1

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        espeak-ng && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir --no-compile -r requirements.txt

RUN pip install --no-cache-dir --no-compile --no-deps \
    "kittentts @ https://github.com/KittenML/KittenTTS/releases/download/0.8.1/kittentts-0.8.1-py3-none-any.whl"

# Skip an unused import that would otherwise pull heavier transitive dependencies.
RUN sed -i 's/^from misaki import en, espeak$/# removed: from misaki import en, espeak/' \
    /usr/local/lib/python3.12/site-packages/kittentts/onnx_model.py

COPY download_model.py .
RUN python download_model.py
RUN printf '%s\n' "${KITTENTTS_MODEL}" > /app/baked-model.txt
RUN find /usr/local/lib/python3.12/site-packages \
    \( -type d -name __pycache__ -o -type d -name tests -o -type d -name test \) \
    -prune -exec rm -rf {} + && \
    find /usr/local/lib/python3.12/site-packages \
    \( -type f -name '*.pyc' -o -type f -name '*.pyo' \) \
    -delete


FROM python:3.12-slim

ARG KITTENTTS_MODEL=KittenML/kitten-tts-mini-0.8
ENV KITTENTTS_HOST=0.0.0.0
ENV KITTENTTS_PORT=8000
ENV PYTHONDONTWRITEBYTECODE=1

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        espeak-ng \
        libsndfile1 && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /root/.cache/huggingface /root/.cache/huggingface
COPY --from=builder /app/baked-model.txt /app/baked-model.txt

COPY server.py .

EXPOSE 8000

ENTRYPOINT ["python", "server.py"]
