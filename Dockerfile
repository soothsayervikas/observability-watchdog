# Stage 1 — build dashboard
FROM node:20-slim AS dashboard-build
WORKDIR /dashboard
COPY dashboard/package.json dashboard/package-lock.json ./
RUN npm ci
COPY dashboard/ ./
ARG VITE_API_BASE=
ARG VITE_API_KEY=
ENV VITE_API_BASE=${VITE_API_BASE}
ENV VITE_API_KEY=${VITE_API_KEY}
RUN npm run build

# Stage 2 — API + static dashboard
FROM python:3.11-slim

WORKDIR /app

RUN useradd --create-home --uid 1000 appuser

COPY pyproject.toml README.md alembic.ini ./
COPY app ./app
COPY alembic ./alembic
COPY scripts ./scripts
COPY data ./data
COPY --from=dashboard-build /dashboard/dist ./dashboard/dist

RUN pip install --no-cache-dir . \
    && chown -R appuser:appuser /app

USER appuser

ENV SERVE_DASHBOARD=true

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/v1/health/ready')"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
