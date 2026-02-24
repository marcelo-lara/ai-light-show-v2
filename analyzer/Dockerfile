FROM python:3.10-slim

WORKDIR /app/analyzer

# Minimal system packages frequently needed by audio tooling.
RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./requirements.txt

RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

COPY src ./src
RUN mkdir -p ./temp_files

# Keep the container alive for interactive/debug workflows
# until it is explicitly stopped.
CMD ["tail", "-f", "/dev/null"]
