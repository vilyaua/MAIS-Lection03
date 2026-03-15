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

EXPOSE 8501

HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health || exit 1

ENTRYPOINT ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
