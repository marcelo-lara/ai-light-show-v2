FROM python:3.11-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV VENV_PATH=/opt/venv
ENV PATH="/opt/venv/bin:${PATH}"

# system deps for audio processing
RUN apt-get update && \
    apt-get install -y --no-install-recommends ffmpeg libsndfile1 && \
    rm -rf /var/lib/apt/lists/*

RUN python -m venv $VENV_PATH

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

COPY pyproject.toml requirements.txt README.md implementation_backlog.md ./
COPY song_analyzer ./song_analyzer
COPY main.py ./main.py
COPY split_stems.py ./split_stems.py

# install the actual analyzer package without re-resolving dependencies
RUN pip install --no-cache-dir --no-deps .
ARG BUILD_UID=1000
ARG BUILD_GID=1000

# Create dedicated non-root user and set ownership for application directories
RUN groupadd -g ${BUILD_GID} appuser && \
    useradd -m -u ${BUILD_UID} -g appuser -s /bin/bash appuser && \
    chown -R appuser:appuser /app /opt/venv

USER appuser

ENTRYPOINT ["python", "-m", "song_analyzer.cli"]
CMD ["--help"]
