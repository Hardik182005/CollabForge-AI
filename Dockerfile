# CollabForge AI backend — AWS App Runner
FROM python:3.11-slim

WORKDIR /app

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ ./

# No secrets in the image — runtime env comes from App Runner configuration.
ENV APP_ENV=production
EXPOSE 8080

# App Runner injects PORT; default to 8080.
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8080}"]
