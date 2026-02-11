FROM nvidia/cuda:12.1.1-cudnn8-runtime-ubuntu22.04 AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    VENV_PATH=/opt/venv \
    PATH="/opt/venv/bin:${PATH}" \
    PIP_EXTRA_INDEX_URL=https://download.pytorch.org/whl/cu121 \
    DEBIAN_FRONTEND=noninteractive \
    HOME=/app \
    TORCH_HOME=/app/.cache/torch \
    HF_HOME=/app/.cache/hf \
    NUMBA_CACHE_DIR=/app/.cache/numba \
    NUMBA_DISABLE_JIT=1 \
    MPLCONFIGDIR=/app/.cache/matplotlib

# system deps for audio processing + Python runtime
RUN apt-get update && \
    apt-get install -y --no-install-recommends python3 python3-venv python3-pip ffmpeg libsndfile1 && \
    rm -rf /var/lib/apt/lists/*

RUN mkdir -p /app/.cache/torch /app/.cache/numba /app/.cache/matplotlib /app/.cache/hf /app/temp_files && \
    chmod -R 777 /app/.cache /app/temp_files

RUN python3 -m venv $VENV_PATH

WORKDIR /app

FROM base AS deps
WORKDIR /deps
COPY requirements.txt ./

# pre-install pinned requirements so rebuild only reruns when this list changes
RUN pip install --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r requirements.txt

FROM base AS final
WORKDIR /app
COPY --from=deps $VENV_PATH $VENV_PATH

COPY pyproject.toml requirements.txt ./
COPY song_analyzer ./song_analyzer
COPY main.py ./main.py
COPY split_stems.py ./split_stems.py

# install the actual analyzer package without re-resolving dependencies
RUN pip install --no-cache-dir --no-deps .

# User creation removed; container will run as root
ENTRYPOINT ["python", "-m", "song_analyzer.cli"]
CMD ["--help"]
