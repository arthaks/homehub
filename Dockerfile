FROM node:22-alpine AS frontend-build
WORKDIR /build/frontend
RUN corepack enable && corepack prepare pnpm@10.15.0 --activate
COPY frontend/package.json frontend/pnpm-lock.yaml ./
RUN HUSKY=0 pnpm install --frozen-lockfile
COPY frontend/ ./
RUN pnpm build

FROM python:3.12-slim AS runtime
ARG HOMEHUB_VERSION=0.1.0
ARG HOMEHUB_COMMIT_SHA=development
ARG HOMEHUB_BUILD_TIME=unknown
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HOMEHUB_VERSION=${HOMEHUB_VERSION} \
    HOMEHUB_COMMIT_SHA=${HOMEHUB_COMMIT_SHA} \
    HOMEHUB_BUILD_TIME=${HOMEHUB_BUILD_TIME} \
    HOMEHUB_STATIC_DIR=/app/static
WORKDIR /app
RUN groupadd --system --gid 10001 homehub \
    && useradd --system --uid 10001 --gid homehub --home-dir /nonexistent --shell /usr/sbin/nologin homehub
COPY backend/pyproject.toml /tmp/pyproject.toml
RUN python - <<'PY'
import tomllib
from pathlib import Path
project = tomllib.loads(Path('/tmp/pyproject.toml').read_text())['project']
Path('/tmp/requirements.txt').write_text('\n'.join(project['dependencies']) + '\n')
PY
RUN pip install --no-cache-dir -r /tmp/requirements.txt && rm -f /tmp/requirements.txt /tmp/pyproject.toml
COPY backend/app /app/app
COPY --from=frontend-build /build/frontend/dist /app/static
USER 10001:10001
EXPOSE 8080
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080", "--no-access-log"]
