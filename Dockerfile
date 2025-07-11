# Stage 1: Build the frontend
FROM node:18 AS frontend
WORKDIR /app

# Copy only package.json and package-lock.json for caching npm install
COPY frontend/package.json frontend/package-lock.json ./
RUN npm install

# Copy the rest of the frontend code and build
COPY frontend/ .
RUN npm run build

# Stage 2: Serve frontend + Flask backend
FROM python:3.10-slim AS backend
RUN apt-get update && apt-get install -y \
    libfftw3-dev \
    libsamplerate0-dev \
    libtag1-dev \
    libyaml-cpp-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Core Python dependencies
RUN pip install --upgrade pip
RUN pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu128

# Copy only requirements.txt for caching pip install
COPY backend/requirements.txt ./
RUN pip install -r requirements.txt

# Copy the rest of the backend code
COPY backend/ ./backend/

# Copy static frontend files
COPY --from=frontend /app/dist ./static/

EXPOSE 5000
ENV PYTHONUNBUFFERED=1
CMD ["uvicorn", "backend.app:app", "--host", "0.0.0.0", "--port", "5500"]