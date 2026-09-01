# Build the React/Vite demo separately from the Python runtime.
FROM node:22-alpine AS web-build
WORKDIR /frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY frontend/index.html ./index.html
COPY frontend/vite.config.js ./vite.config.js
COPY frontend/src ./src
RUN npm run build

FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    DEVICE=cpu

RUN apt-get update && apt-get install -y --no-install-recommends \
    libglib2.0-0 libgomp1 libgl1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
# The default image is ONNX-only so it stays small and CPU friendly.
# Use an ONNX export for both detector and recognizer in this profile.
RUN pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir "paddlepaddle>=3,<4"

COPY app ./app
COPY --from=web-build /web ./web
RUN mkdir -p /var/log/wbrain /var/lib/wbrain/images

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/v1/health')"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
