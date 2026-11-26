FROM python:3.11-slim

WORKDIR /app

# Install minimal system dependencies for Pillow
RUN apt-get update && apt-get install -y --no-install-recommends \
    libjpeg62-turbo-dev zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ ./backend/
COPY frontend/ ./frontend/
COPY run.py ./run.py

# Ensure runtime data and media directories exist and are writable (compatible with Hugging Face UID 1000 & Render)
RUN mkdir -p /app/backend/data/media && chmod -R 777 /app/backend/data

ENV CLOUD_DEPLOY=1
ENV PORT=7860
EXPOSE 7860

CMD ["sh", "-c", "uvicorn backend.app.main:app --host 0.0.0.0 --port ${PORT:-7860}"]
