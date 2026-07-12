# CollabForge AI backend — AWS App Runner
FROM python:3.11-slim

WORKDIR /app

# ffmpeg is required by the Reel Builder for real MP4 composition.
RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ ./

# No secrets in the image — runtime env comes from App Runner configuration.
ENV APP_ENV=production
EXPOSE 8080

# App Runner injects PORT; default to 8080.
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8080}"]
