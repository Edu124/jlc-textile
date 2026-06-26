# ── Stage 1: build the React frontend ───────────────────────────────────────
FROM node:20-bookworm-slim AS frontend
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm install
COPY frontend/ ./
RUN npm run build

# ── Stage 2: Python backend that also serves the built frontend ──────────────
FROM python:3.11-slim-bookworm
WORKDIR /app

# DejaVu fonts give the ₹ symbol + clean PDF text on Linux.
RUN apt-get update && apt-get install -y --no-install-recommends \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ ./
# Built SPA is served by FastAPI from /app/static
COPY --from=frontend /app/frontend/dist ./static

ENV PORT=8000
EXPOSE 8000
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]
