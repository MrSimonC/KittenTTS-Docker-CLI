FROM python:3.12-slim AS builder

ARG KITTENTTS_MODEL=KittenML/kitten-tts-mini-0.8
ENV KITTENTTS_MODEL=${KITTENTTS_MODEL}

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        espeak-ng \
        libespeak-ng1 \
        libsndfile1 && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

RUN pip install --no-cache-dir --no-deps \
    "kittentts @ https://github.com/KittenML/KittenTTS/releases/download/0.8.1/kittentts-0.8.1-py3-none-any.whl"

# Skip an unused import that would otherwise pull heavier transitive dependencies.
RUN sed -i 's/^from misaki import en, espeak$/# removed: from misaki import en, espeak/' \
    /usr/local/lib/python3.12/site-packages/kittentts/onnx_model.py

COPY download_model.py .
RUN python download_model.py
RUN printf '%s\n' "${KITTENTTS_MODEL}" > /app/baked-model.txt


FROM python:3.12-slim

ARG KITTENTTS_MODEL=KittenML/kitten-tts-mini-0.8
ENV KITTENTTS_HOST=0.0.0.0
ENV KITTENTTS_PORT=8000

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        espeak-ng \
        libespeak-ng1 \
        libsndfile1 && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin
COPY --from=builder /root/.cache/huggingface /root/.cache/huggingface
COPY --from=builder /app/baked-model.txt /app/baked-model.txt

COPY server.py .

EXPOSE 8000

ENTRYPOINT ["python", "server.py"]
