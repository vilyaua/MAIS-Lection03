# --- Build stage: install deps with gcc, then discard build tools ---
FROM python:3.12-slim AS builder

RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# --- Runtime stage: clean image, no gcc, no build artifacts ---
FROM python:3.12-slim

WORKDIR /app

ARG APP_VERSION=dev

COPY --from=builder /install /usr/local

COPY . .

RUN echo "${APP_VERSION}" > VERSION && mkdir -p output logs

EXPOSE 8000

HEALTHCHECK CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/info')" || exit 1

ENTRYPOINT ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
