FROM python:3.11-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends build-essential curl \
    && rm -rf /var/lib/apt/lists/*
COPY requirements.txt requirements-ml.txt ./
ARG WITH_ML=false
RUN pip install --no-cache-dir -r requirements.txt \
    && if [ "$WITH_ML" = "true" ]; then pip install --no-cache-dir -r requirements-ml.txt; fi
COPY app app
COPY config config
EXPOSE 8000
HEALTHCHECK CMD curl -fs http://localhost:8000/health || exit 1
# --proxy-headers: behind nginx/Render, rate limits use the real client IP from X-Forwarded-For
# $PORT: Render injects its own port; default to 8000 for local/Docker Compose use.
CMD ["sh", "-c", "uvicorn app.api.main:app --host 0.0.0.0 --port ${PORT:-8000} --proxy-headers --forwarded-allow-ips '*'"]
