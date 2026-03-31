FROM python:3.10-slim

WORKDIR /app/analyzer
ENV ESSENTIA_MODEL_DIR=/opt/essentia-models

# Install system deps for Essentia
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        cmake \
        libeigen3-dev \
        libyaml-dev \
        libfftw3-dev \
        libavcodec-dev \
        libavformat-dev \
        libavutil-dev \
        libswresample-dev \
        libsamplerate0-dev \
        libtag1-dev \
        libchromaprint-dev \
        python3-dev \
        python3-numpy-dev \
        python3-yaml \
        ca-certificates \
        ffmpeg \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./requirements.txt

RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir essentia-tensorflow \
    && pip install --no-cache-dir -r requirements.txt

RUN mkdir -p "$ESSENTIA_MODEL_DIR" \
    && python - <<'PY'
import os
import time
import urllib.request
from pathlib import Path

model_dir = Path(os.environ["ESSENTIA_MODEL_DIR"])
assets = {
    "audioset-yamnet-1.pb": "https://essentia.upf.edu/models/audio-event-recognition/yamnet/audioset-yamnet-1.pb",
    "audioset-yamnet-1.json": "https://essentia.upf.edu/models/audio-event-recognition/yamnet/audioset-yamnet-1.json",
    "discogs-effnet-bs64-1.pb": "https://essentia.upf.edu/models/feature-extractors/discogs-effnet/discogs-effnet-bs64-1.pb",
    "discogs-effnet-bs64-1.json": "https://essentia.upf.edu/models/feature-extractors/discogs-effnet/discogs-effnet-bs64-1.json",
    "nsynth_instrument-discogs-effnet-1.pb": "https://essentia.upf.edu/models/classification-heads/nsynth_instrument/nsynth_instrument-discogs-effnet-1.pb",
    "nsynth_instrument-discogs-effnet-1.json": "https://essentia.upf.edu/models/classification-heads/nsynth_instrument/nsynth_instrument-discogs-effnet-1.json",
}

for name, url in assets.items():
    destination = model_dir / name
    for attempt in range(5):
        try:
            urllib.request.urlretrieve(url, destination)
            break
        except Exception:
            if attempt == 4:
                raise
            time.sleep(5)
PY

COPY src ./src
RUN mkdir -p ./temp_files

CMD ["uvicorn", "src.http_api:app", "--host", "0.0.0.0", "--port", "8100"]
