FROM python:3.10-slim

WORKDIR /app/analyzer

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
        ffmpeg \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./requirements.txt

RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir essentia \
    && pip install --no-cache-dir -r requirements.txt

COPY src ./src
RUN mkdir -p ./temp_files

# Keep the container alive for interactive/debug workflows
# until it is explicitly stopped.
CMD ["tail", "-f", "/dev/null"]
