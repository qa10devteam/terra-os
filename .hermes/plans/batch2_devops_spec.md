# Terra.OS — Batch 2: DevOps / Infra Full Spec
**Autor:** Senior Developer 💲 — Agency Agents  
**Data:** 2026-07-07  
**Stack:** Python 3.12 · FastAPI · Next.js 16 · PostgreSQL · Redis · GitHub Actions  

---

## 0. Audyt Infrastruktury (Stan Obecny)

### Znalezione pliki
| Plik | Status |
|------|--------|
| `.github/workflows/ci.yml` | ✅ Istnieje — básic (lint+test), brak typecheck, brak mypy |
| `docker-compose.dev.yml` | ✅ Istnieje — tylko db+ollama, brak api/ui |
| `Makefile` | ❌ Brak |
| `Dockerfile.*` | ❌ Brak |
| `docker-compose.prod.yml` | ❌ Brak |
| Prometheus/Grafana config | ❌ Brak |
| LangGraph pipeline | ❌ Brak |
| Flutter mobile app | ❌ Brak |

### Wnioski z audytu
- Istniejące CI uruchamia pytest ale **nie ma ruff, black, mypy** (tylko `npm lint`)
- Brak cache'owania pip — każdy run instaluje od nowa (slow)
- Brak Docker images — deploy jest ad-hoc via `systemd + pip install`
- `main.py` ma 234 linie, 30+ routerów — duże ryzyko bez typecheckingu
- `pyproject.toml` definiuje ruff/black/mypy strict — nie są egzekwowane w CI

---

## 1. CI/CD SPEC — GitHub Actions Workflows

### 1.1 `.github/workflows/ci.yml` — Lint + Typecheck + Tests

```yaml
# .github/workflows/ci.yml
# Trigger: push + PR do każdego brancha
# Cel: szybki feedback loop (<5 min) — linting, types, unit tests offline

name: CI — Lint · Types · Tests

on:
  push:
    branches: ["**"]
  pull_request:
    types: [opened, synchronize, reopened]

concurrency:
  group: ci-${{ github.ref }}
  cancel-in-progress: true

env:
  PYTHON_VERSION: "3.12"
  NODE_VERSION: "20"
  PIP_CACHE_DIR: ~/.cache/pip

jobs:
  # ─────────────────────────────────────────────────────
  # JOB 1: Python Lint (ruff + black --check)
  # ─────────────────────────────────────────────────────
  python-lint:
    name: "🐍 Python Lint (ruff + black)"
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Setup Python ${{ env.PYTHON_VERSION }}
        uses: actions/setup-python@v5
        with:
          python-version: ${{ env.PYTHON_VERSION }}
          cache: "pip"

      - name: Install lint tools
        run: pip install ruff black

      - name: Ruff — lint
        run: ruff check . --output-format=github

      - name: Black — format check
        run: black --check .

  # ─────────────────────────────────────────────────────
  # JOB 2: Mypy strict typecheck
  # ─────────────────────────────────────────────────────
  python-typecheck:
    name: "🔬 Mypy Typecheck (strict)"
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Setup Python ${{ env.PYTHON_VERSION }}
        uses: actions/setup-python@v5
        with:
          python-version: ${{ env.PYTHON_VERSION }}
          cache: "pip"

      - name: Install packages
        run: |
          pip install mypy types-all
          pip install -e packages/shared -e packages/db -e services/api
          pip install fastapi uvicorn pydantic pydantic-settings sqlalchemy alembic httpx

      - name: Mypy — strict typecheck
        run: mypy services/ packages/ --ignore-missing-imports

  # ─────────────────────────────────────────────────────
  # JOB 3: Pytest — unit tests (zero network)
  # ─────────────────────────────────────────────────────
  python-tests:
    name: "🧪 Pytest (offline unit tests)"
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Setup Python ${{ env.PYTHON_VERSION }}
        uses: actions/setup-python@v5
        with:
          python-version: ${{ env.PYTHON_VERSION }}
          cache: "pip"

      - name: Install dependencies
        run: |
          pip install fastapi uvicorn pydantic pydantic-settings sqlalchemy alembic \
                      psycopg2-binary httpx pytest pytest-asyncio pytest-cov
          pip install -e packages/shared -e packages/db -e services/api

      - name: Run unit tests with coverage
        env:
          ENVIRONMENT: test
          DATABASE_URL: sqlite+aiosqlite:///./test.db
        run: |
          pytest tests/ -q \
            --cov=services --cov=packages \
            --cov-report=xml \
            --cov-report=term-missing \
            --tb=short

      - name: Upload coverage to Codecov
        uses: codecov/codecov-action@v4
        with:
          files: ./coverage.xml
          fail_ci_if_error: false

  # ─────────────────────────────────────────────────────
  # JOB 4: Next.js — TypeScript + ESLint + Build
  # ─────────────────────────────────────────────────────
  ui-checks:
    name: "⚡ Next.js (lint + tsc + build)"
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: apps/ui
    steps:
      - uses: actions/checkout@v4

      - name: Setup Node ${{ env.NODE_VERSION }}
        uses: actions/setup-node@v4
        with:
          node-version: ${{ env.NODE_VERSION }}
          cache: "npm"
          cache-dependency-path: apps/ui/package-lock.json

      - name: Install
        run: npm ci

      - name: ESLint
        run: npm run lint

      - name: TypeScript check
        run: npx tsc --noEmit

      - name: Build (standalone output)
        run: npm run build
        env:
          NEXT_PUBLIC_API_URL: http://localhost:8000

  # ─────────────────────────────────────────────────────
  # JOB 5: Security scan
  # ─────────────────────────────────────────────────────
  security:
    name: "🔐 Security Scan (bandit + safety)"
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: ${{ env.PYTHON_VERSION }}
          cache: "pip"

      - name: Install
        run: pip install bandit safety

      - name: Bandit — SAST
        run: bandit -r services/ packages/ -ll -x tests/

      - name: Safety — dependency CVE check
        run: safety check --bare
        continue-on-error: true  # advisory only

  # ─────────────────────────────────────────────────────
  # Final gate — all checks must pass
  # ─────────────────────────────────────────────────────
  ci-gate:
    name: "✅ CI Gate"
    needs: [python-lint, python-typecheck, python-tests, ui-checks, security]
    runs-on: ubuntu-latest
    if: always()
    steps:
      - name: Check all jobs passed
        run: |
          if [[ "${{ needs.python-lint.result }}" != "success" ]] || \
             [[ "${{ needs.python-typecheck.result }}" != "success" ]] || \
             [[ "${{ needs.python-tests.result }}" != "success" ]] || \
             [[ "${{ needs.ui-checks.result }}" != "success" ]]; then
            echo "❌ One or more required checks failed"
            exit 1
          fi
          echo "✅ All checks passed"
```

---

### 1.2 `.github/workflows/build.yml` — Docker Multi-Stage Build

```yaml
# .github/workflows/build.yml
# Trigger: push do main (po merged PR)
# Cel: zbuduj i opublikuj Docker images API + UI

name: Build — Docker Images

on:
  push:
    branches: [main]
  workflow_dispatch:
    inputs:
      tag:
        description: "Custom image tag (default: git SHA)"
        required: false

env:
  REGISTRY: ghcr.io
  IMAGE_API: ${{ github.repository }}/terra-api
  IMAGE_UI: ${{ github.repository }}/terra-ui

jobs:
  build-api:
    name: "🐳 Build API Image"
    runs-on: ubuntu-latest
    permissions:
      contents: read
      packages: write

    outputs:
      image-tag: ${{ steps.meta.outputs.tags }}
      digest: ${{ steps.build.outputs.digest }}

    steps:
      - uses: actions/checkout@v4

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3

      - name: Login to GitHub Container Registry
        uses: docker/login-action@v3
        with:
          registry: ${{ env.REGISTRY }}
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - name: Extract metadata
        id: meta
        uses: docker/metadata-action@v5
        with:
          images: ${{ env.REGISTRY }}/${{ env.IMAGE_API }}
          tags: |
            type=sha,prefix=sha-,format=short
            type=ref,event=branch
            type=raw,value=latest,enable={{is_default_branch}}

      - name: Build and push API image
        id: build
        uses: docker/build-push-action@v5
        with:
          context: .
          file: Dockerfile.api
          push: true
          tags: ${{ steps.meta.outputs.tags }}
          labels: ${{ steps.meta.outputs.labels }}
          cache-from: type=gha
          cache-to: type=gha,mode=max
          platforms: linux/amd64,linux/arm64

  build-ui:
    name: "⚡ Build UI Image"
    runs-on: ubuntu-latest
    permissions:
      contents: read
      packages: write

    outputs:
      image-tag: ${{ steps.meta.outputs.tags }}
      digest: ${{ steps.build.outputs.digest }}

    steps:
      - uses: actions/checkout@v4

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3

      - name: Login to GitHub Container Registry
        uses: docker/login-action@v3
        with:
          registry: ${{ env.REGISTRY }}
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - name: Extract metadata
        id: meta
        uses: docker/metadata-action@v5
        with:
          images: ${{ env.REGISTRY }}/${{ env.IMAGE_UI }}
          tags: |
            type=sha,prefix=sha-,format=short
            type=ref,event=branch
            type=raw,value=latest,enable={{is_default_branch}}

      - name: Build and push UI image
        id: build
        uses: docker/build-push-action@v5
        with:
          context: apps/ui
          file: apps/ui/Dockerfile.ui
          push: true
          tags: ${{ steps.meta.outputs.tags }}
          labels: ${{ steps.meta.outputs.labels }}
          cache-from: type=gha
          cache-to: type=gha,mode=max
          platforms: linux/amd64,linux/arm64
          build-args: |
            NEXT_PUBLIC_API_URL=${{ vars.NEXT_PUBLIC_API_URL }}

  image-scan:
    name: "🔍 Trivy Image Scan"
    needs: [build-api, build-ui]
    runs-on: ubuntu-latest
    steps:
      - name: Scan API image
        uses: aquasecurity/trivy-action@master
        with:
          image-ref: ${{ env.REGISTRY }}/${{ env.IMAGE_API }}:latest
          format: sarif
          output: trivy-api.sarif
          severity: CRITICAL,HIGH

      - name: Upload scan results
        uses: github/codeql-action/upload-sarif@v3
        with:
          sarif_file: trivy-api.sarif
        continue-on-error: true
```

---

### 1.3 `.github/workflows/deploy-staging.yml` — Auto Deploy to Staging

```yaml
# .github/workflows/deploy-staging.yml
# Trigger: po pomyślnym build.yml na main
# Cel: automatyczny deploy na staging server

name: Deploy — Staging

on:
  workflow_run:
    workflows: ["Build — Docker Images"]
    types: [completed]
    branches: [main]

  workflow_dispatch:
    inputs:
      image_tag:
        description: "Image tag to deploy"
        required: false
        default: "latest"

jobs:
  deploy-staging:
    name: "🚀 Deploy to Staging"
    runs-on: ubuntu-latest
    if: ${{ github.event.workflow_run.conclusion == 'success' || github.event_name == 'workflow_dispatch' }}
    environment:
      name: staging
      url: https://staging.terra-os.pl

    steps:
      - uses: actions/checkout@v4

      - name: Determine image tag
        id: tag
        run: |
          if [[ "${{ github.event_name }}" == "workflow_dispatch" ]]; then
            echo "tag=${{ inputs.image_tag }}" >> $GITHUB_OUTPUT
          else
            echo "tag=sha-$(echo ${{ github.sha }} | cut -c1-7)" >> $GITHUB_OUTPUT
          fi

      - name: Deploy to staging via SSH
        uses: appleboy/ssh-action@v1
        with:
          host: ${{ secrets.STAGING_HOST }}
          username: ${{ secrets.STAGING_USER }}
          key: ${{ secrets.STAGING_SSH_KEY }}
          envs: TAG
          script: |
            export TAG=${{ steps.tag.outputs.tag }}
            cd /opt/terra-os
            
            # Pull latest images
            docker compose -f docker-compose.prod.yml pull
            
            # Blue-green: bring up new containers
            docker compose -f docker-compose.prod.yml up -d --no-deps api ui
            
            # Health check (retry 30s)
            for i in {1..15}; do
              if curl -sf http://localhost:8000/health; then
                echo "✅ API healthy"
                break
              fi
              sleep 2
            done
            
            # Remove old images
            docker image prune -f

      - name: Smoke tests
        run: |
          sleep 5
          curl -sf https://staging.terra-os.pl/health || exit 1
          curl -sf https://staging.terra-os.pl/api/tenders?limit=1 || exit 1
          echo "✅ Smoke tests passed"

      - name: Notify Slack on failure
        if: failure()
        uses: slackapi/slack-github-action@v1
        with:
          payload: |
            {
              "text": "❌ Staging deploy FAILED: ${{ github.sha }}\n${{ github.server_url }}/${{ github.repository }}/actions/runs/${{ github.run_id }}"
            }
        env:
          SLACK_WEBHOOK_URL: ${{ secrets.SLACK_WEBHOOK_URL }}
```

---

### 1.4 `.github/workflows/deploy-prod.yml` — Manual Approval + Rollback

```yaml
# .github/workflows/deploy-prod.yml
# Trigger: manual_dispatch LUB release tag
# Cel: produkcyjny deploy z approvem + rollback strategy

name: Deploy — Production

on:
  push:
    tags:
      - "v[0-9]+.[0-9]+.[0-9]+"
  workflow_dispatch:
    inputs:
      image_tag:
        description: "Image tag to deploy (e.g. sha-a1b2c3d)"
        required: true
      skip_approval:
        description: "Skip approval gate (emergency only)"
        type: boolean
        default: false

jobs:
  # ─────────────────────────────────────────────────────
  # Gate: Pre-deploy checks
  # ─────────────────────────────────────────────────────
  pre-deploy-checks:
    name: "🔎 Pre-Deploy Checks"
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Verify image exists in registry
        run: |
          docker manifest inspect \
            ghcr.io/${{ github.repository }}/terra-api:${{ inputs.image_tag || github.ref_name }} \
            > /dev/null 2>&1 || (echo "❌ Image not found in registry" && exit 1)

      - name: Check staging health before prod deploy
        run: |
          STATUS=$(curl -sf -o /dev/null -w "%{http_code}" https://staging.terra-os.pl/health)
          if [[ "$STATUS" != "200" ]]; then
            echo "❌ Staging is unhealthy ($STATUS) — blocking prod deploy"
            exit 1
          fi
          echo "✅ Staging healthy, proceeding"

  # ─────────────────────────────────────────────────────
  # Manual approval gate
  # ─────────────────────────────────────────────────────
  approval-gate:
    name: "👥 Manual Approval Required"
    needs: [pre-deploy-checks]
    runs-on: ubuntu-latest
    if: ${{ !inputs.skip_approval }}
    environment:
      name: production-approval  # Configure in GitHub Environments with required reviewers

    steps:
      - name: Awaiting approval
        run: echo "✅ Approved — proceeding to production deploy"

  # ─────────────────────────────────────────────────────
  # Deploy to production
  # ─────────────────────────────────────────────────────
  deploy-production:
    name: "🏭 Deploy to Production"
    needs: [approval-gate]
    runs-on: ubuntu-latest
    environment:
      name: production
      url: https://terra-os.pl

    steps:
      - uses: actions/checkout@v4

      - name: Determine tag
        id: tag
        run: |
          if [[ "${{ github.event_name }}" == "push" ]]; then
            echo "tag=${{ github.ref_name }}" >> $GITHUB_OUTPUT
          else
            echo "tag=${{ inputs.image_tag }}" >> $GITHUB_OUTPUT
          fi

      - name: Deploy to production via SSH
        id: deploy
        uses: appleboy/ssh-action@v1
        with:
          host: ${{ secrets.PROD_HOST }}
          username: ${{ secrets.PROD_USER }}
          key: ${{ secrets.PROD_SSH_KEY }}
          script: |
            set -e
            cd /opt/terra-os
            
            # ── Capture current state for rollback ──────────
            CURRENT_API=$(docker compose -f docker-compose.prod.yml images -q api)
            CURRENT_UI=$(docker compose -f docker-compose.prod.yml images -q ui)
            echo "$CURRENT_API $CURRENT_UI" > /tmp/terra-os-rollback-state
            
            # ── Pull new images ──────────────────────────────
            export IMAGE_TAG=${{ steps.tag.outputs.tag }}
            docker compose -f docker-compose.prod.yml pull api ui
            
            # ── Database migration (non-destructive only) ────
            docker compose -f docker-compose.prod.yml run --rm api \
              alembic upgrade head
            
            # ── Rolling restart (zero-downtime) ─────────────
            # Scale up new, then scale down old
            docker compose -f docker-compose.prod.yml up -d --no-deps \
              --scale api=2 api
            sleep 15
            
            # Health check new instances
            for i in {1..20}; do
              if curl -sf http://localhost:8000/health; then
                echo "✅ New instance healthy"
                break
              fi
              if [[ $i -eq 20 ]]; then
                echo "❌ Health check failed — triggering rollback"
                exit 1
              fi
              sleep 3
            done
            
            # Scale back to 1 (removes old container)
            docker compose -f docker-compose.prod.yml up -d --no-deps \
              --scale api=1 api
            
            # Reload nginx/caddy without downtime
            docker compose -f docker-compose.prod.yml kill -s HUP caddy
            
            echo "✅ Production deploy complete: $IMAGE_TAG"

      - name: Post-deploy smoke tests
        run: |
          sleep 10
          curl -sf https://terra-os.pl/health || exit 1
          curl -sf https://terra-os.pl/api/tenders?limit=1 || exit 1
          echo "✅ Production smoke tests passed"

  # ─────────────────────────────────────────────────────
  # Rollback job (manual trigger on failure)
  # ─────────────────────────────────────────────────────
  rollback:
    name: "⏪ Rollback Production"
    needs: [deploy-production]
    runs-on: ubuntu-latest
    if: failure()
    environment:
      name: production-rollback

    steps:
      - name: Rollback via SSH
        uses: appleboy/ssh-action@v1
        with:
          host: ${{ secrets.PROD_HOST }}
          username: ${{ secrets.PROD_USER }}
          key: ${{ secrets.PROD_SSH_KEY }}
          script: |
            cd /opt/terra-os
            
            # Read saved image IDs
            if [[ -f /tmp/terra-os-rollback-state ]]; then
              read PREV_API PREV_UI < /tmp/terra-os-rollback-state
              
              # Tag prev images as rollback
              docker tag $PREV_API ghcr.io/${{ github.repository }}/terra-api:rollback
              docker tag $PREV_UI ghcr.io/${{ github.repository }}/terra-ui:rollback
              
              # Redeploy with rollback images
              IMAGE_TAG=rollback docker compose -f docker-compose.prod.yml up -d api ui
              
              echo "⏪ Rollback complete"
            else
              echo "❌ No rollback state found"
              exit 1
            fi

      - name: Notify team of rollback
        uses: slackapi/slack-github-action@v1
        with:
          payload: |
            {
              "text": "⏪ PRODUCTION ROLLBACK executed\nRun: ${{ github.server_url }}/${{ github.repository }}/actions/runs/${{ github.run_id }}"
            }
        env:
          SLACK_WEBHOOK_URL: ${{ secrets.SLACK_WEBHOOK_URL }}
```

---

## 2. DOCKER SETUP

### 2.1 `Dockerfile.api` — Python 3.12 Multi-Stage (<200MB)

```dockerfile
# Dockerfile.api
# Multi-stage build: builder → runtime
# Target: <200MB, non-root user, security hardened

# ─── Stage 1: Builder ─────────────────────────────────────────────────────────
FROM python:3.12-slim AS builder

WORKDIR /build

# System deps for C extensions (psycopg2, etc.)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency specs first (cache layer)
COPY packages/shared/pyproject.toml packages/shared/
COPY packages/db/pyproject.toml packages/db/
COPY services/api/pyproject.toml services/api/

# Install all packages into /build/venv
RUN python -m venv /build/venv
ENV PATH="/build/venv/bin:$PATH"

# Install packages
COPY packages/ packages/
COPY services/api/ services/api/
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir \
        fastapi>=0.111 \
        uvicorn[standard]>=0.30 \
        pydantic>=2.7 \
        pydantic-settings>=2.3 \
        sqlalchemy>=2.0 \
        alembic>=1.13 \
        psycopg2-binary \
        httpx \
        slowapi \
        python-multipart \
        prometheus-fastapi-instrumentator>=6.1 \
        sentry-sdk[fastapi]>=1.40 && \
    pip install --no-cache-dir -e packages/shared -e packages/db -e services/api

# ─── Stage 2: Runtime ─────────────────────────────────────────────────────────
FROM python:3.12-slim AS runtime

# Security: non-root user
RUN groupadd --gid 1001 terra && \
    useradd --uid 1001 --gid terra --shell /bin/false --no-create-home terra

# Only runtime system deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy venv from builder
COPY --from=builder /build/venv /app/venv
ENV PATH="/app/venv/bin:$PATH"

# Copy application source
COPY --chown=terra:terra packages/ packages/
COPY --chown=terra:terra services/api/ services/api/

# Alembic migrations
COPY --chown=terra:terra alembic.ini* ./
COPY --chown=terra:terra migrations/ migrations/ 2>/dev/null || true

USER terra

EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -sf http://localhost:8000/health || exit 1

# Start command
CMD ["uvicorn", "services.api.main:app", \
     "--host", "0.0.0.0", \
     "--port", "8000", \
     "--workers", "4", \
     "--log-config", "/app/services/api/logging.json"]
```

### 2.2 `apps/ui/Dockerfile.ui` — Next.js Standalone (<100MB)

```dockerfile
# apps/ui/Dockerfile.ui
# Next.js standalone output — minimal runtime image

# ─── Stage 1: Dependencies ────────────────────────────────────────────────────
FROM node:20-alpine AS deps

WORKDIR /app

COPY package.json package-lock.json* ./
RUN npm ci --only=production && npm cache clean --force

# ─── Stage 2: Builder ─────────────────────────────────────────────────────────
FROM node:20-alpine AS builder

WORKDIR /app

COPY package.json package-lock.json* ./
RUN npm ci

COPY . .

# Enable standalone output in next.config.js (add output: 'standalone')
ENV NEXT_TELEMETRY_DISABLED=1
ARG NEXT_PUBLIC_API_URL=http://terra-api:8000
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL

RUN npm run build

# ─── Stage 3: Runtime ─────────────────────────────────────────────────────────
FROM node:20-alpine AS runtime

# Security: non-root
RUN addgroup --system --gid 1001 nodejs && \
    adduser --system --uid 1001 nextjs

WORKDIR /app

ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1
ENV PORT=3000

# Standalone output (only what's needed)
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static
COPY --from=builder --chown=nextjs:nodejs /app/public ./public

USER nextjs

EXPOSE 3000

HEALTHCHECK --interval=30s --timeout=10s --start-period=20s --retries=3 \
    CMD wget -qO- http://localhost:3000/api/health || exit 1

CMD ["node", "server.js"]
```

> ⚠️ **Wymagana zmiana w `next.config.js`:**
> ```js
> // apps/ui/next.config.js
> const nextConfig = {
>   output: 'standalone',
>   // ... rest of config
> }
> module.exports = nextConfig
> ```

### 2.3 `docker-compose.prod.yml` — Full Production Stack

```yaml
# docker-compose.prod.yml
# Production stack: api + ui + nginx + redis + postgres + celery worker

x-logging: &default-logging
  driver: "json-file"
  options:
    max-size: "10m"
    max-file: "3"
    labels: "service"
    tag: "{{.ImageName}}|{{.Name}}"

x-healthcheck-defaults: &hc-defaults
  interval: 30s
  timeout: 10s
  retries: 3
  start_period: 30s

services:
  # ─── PostgreSQL ─────────────────────────────────────────────────────────────
  db:
    image: pgvector/pgvector:pg16
    restart: unless-stopped
    environment:
      POSTGRES_DB: ${POSTGRES_DB:-terraos}
      POSTGRES_USER: ${POSTGRES_USER:-terraos}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:?POSTGRES_PASSWORD required}
    volumes:
      - terraos_pg:/var/lib/postgresql/data
      - ./infra/postgres/postgresql.conf:/etc/postgresql/postgresql.conf:ro
    command: postgres -c config_file=/etc/postgresql/postgresql.conf
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER:-terraos} -d ${POSTGRES_DB:-terraos}"]
      <<: *hc-defaults
    networks: [terra-net]
    logging: *default-logging
    deploy:
      resources:
        limits:
          memory: 512M

  # ─── Redis ──────────────────────────────────────────────────────────────────
  redis:
    image: redis:7-alpine
    restart: unless-stopped
    command: redis-server --maxmemory 256mb --maxmemory-policy allkeys-lru --save ""
    volumes:
      - terraos_redis:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      <<: *hc-defaults
    networks: [terra-net]
    logging: *default-logging
    deploy:
      resources:
        limits:
          memory: 256M

  # ─── API (FastAPI) ──────────────────────────────────────────────────────────
  api:
    image: ${REGISTRY:-ghcr.io}/${IMAGE_REPO}/terra-api:${IMAGE_TAG:-latest}
    restart: unless-stopped
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_healthy
    environment:
      ENVIRONMENT: production
      DATABASE_URL: postgresql+asyncpg://${POSTGRES_USER:-terraos}:${POSTGRES_PASSWORD}@db:5432/${POSTGRES_DB:-terraos}
      REDIS_URL: redis://redis:6379/0
      SECRET_KEY: ${SECRET_KEY:?SECRET_KEY required}
      SENTRY_DSN: ${SENTRY_DSN:-}
      PROMETHEUS_ENABLED: "true"
      LOG_LEVEL: INFO
      CORS_ORIGINS: ${CORS_ORIGINS:-https://terra-os.pl}
    healthcheck:
      test: ["CMD", "curl", "-sf", "http://localhost:8000/health"]
      <<: *hc-defaults
    networks: [terra-net]
    logging: *default-logging
    labels:
      - "prometheus.scrape=true"
      - "prometheus.port=8000"
      - "prometheus.path=/metrics"
    deploy:
      resources:
        limits:
          memory: 512M
      replicas: 2
      update_config:
        parallelism: 1
        delay: 15s
        failure_action: rollback

  # ─── Celery Worker ──────────────────────────────────────────────────────────
  worker:
    image: ${REGISTRY:-ghcr.io}/${IMAGE_REPO}/terra-api:${IMAGE_TAG:-latest}
    restart: unless-stopped
    command: celery -A services.api.tasks worker --loglevel=info --concurrency=4
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_healthy
    environment:
      ENVIRONMENT: production
      DATABASE_URL: postgresql+asyncpg://${POSTGRES_USER:-terraos}:${POSTGRES_PASSWORD}@db:5432/${POSTGRES_DB:-terraos}
      REDIS_URL: redis://redis:6379/0
      SECRET_KEY: ${SECRET_KEY}
    healthcheck:
      test: ["CMD", "celery", "-A", "services.api.tasks", "inspect", "ping"]
      interval: 60s
      timeout: 30s
      retries: 3
      start_period: 60s
    networks: [terra-net]
    logging: *default-logging

  # ─── UI (Next.js) ───────────────────────────────────────────────────────────
  ui:
    image: ${REGISTRY:-ghcr.io}/${IMAGE_REPO}/terra-ui:${IMAGE_TAG:-latest}
    restart: unless-stopped
    environment:
      NEXT_PUBLIC_API_URL: ${NEXT_PUBLIC_API_URL:-https://terra-os.pl/api}
    healthcheck:
      test: ["CMD", "wget", "-qO-", "http://localhost:3000/"]
      <<: *hc-defaults
    networks: [terra-net]
    logging: *default-logging

  # ─── Nginx (reverse proxy) ──────────────────────────────────────────────────
  nginx:
    image: nginx:alpine
    restart: unless-stopped
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./infra/nginx/nginx.conf:/etc/nginx/nginx.conf:ro
      - ./infra/nginx/conf.d:/etc/nginx/conf.d:ro
      - terraos_certs:/etc/nginx/certs:ro
      - terraos_nginx_logs:/var/log/nginx
    depends_on:
      - api
      - ui
    healthcheck:
      test: ["CMD", "nginx", "-t"]
      <<: *hc-defaults
    networks: [terra-net]
    logging: *default-logging

  # ─── Prometheus ─────────────────────────────────────────────────────────────
  prometheus:
    image: prom/prometheus:v2.51.0
    restart: unless-stopped
    command:
      - "--config.file=/etc/prometheus/prometheus.yml"
      - "--storage.tsdb.path=/prometheus"
      - "--storage.tsdb.retention.time=30d"
      - "--web.enable-lifecycle"
    volumes:
      - ./infra/prometheus:/etc/prometheus:ro
      - terraos_prometheus:/prometheus
    ports:
      - "127.0.0.1:9090:9090"  # local only
    networks: [terra-net]
    logging: *default-logging

  # ─── Grafana ────────────────────────────────────────────────────────────────
  grafana:
    image: grafana/grafana:10.4.0
    restart: unless-stopped
    environment:
      GF_SECURITY_ADMIN_PASSWORD: ${GRAFANA_PASSWORD:?required}
      GF_USERS_ALLOW_SIGN_UP: "false"
      GF_SERVER_ROOT_URL: ${GRAFANA_URL:-https://terra-os.pl/grafana}
    volumes:
      - terraos_grafana:/var/lib/grafana
      - ./infra/grafana/provisioning:/etc/grafana/provisioning:ro
      - ./infra/grafana/dashboards:/var/lib/grafana/dashboards:ro
    ports:
      - "127.0.0.1:3001:3000"  # local only
    networks: [terra-net]
    logging: *default-logging

  # ─── Loki (log aggregation) ─────────────────────────────────────────────────
  loki:
    image: grafana/loki:2.9.6
    restart: unless-stopped
    command: -config.file=/etc/loki/config.yml
    volumes:
      - ./infra/loki/config.yml:/etc/loki/config.yml:ro
      - terraos_loki:/loki
    ports:
      - "127.0.0.1:3100:3100"
    networks: [terra-net]

  # ─── Promtail (log shipper) ─────────────────────────────────────────────────
  promtail:
    image: grafana/promtail:2.9.6
    restart: unless-stopped
    volumes:
      - /var/log:/var/log:ro
      - /var/lib/docker/containers:/var/lib/docker/containers:ro
      - ./infra/promtail/config.yml:/etc/promtail/config.yml:ro
    command: -config.file=/etc/promtail/config.yml
    networks: [terra-net]

volumes:
  terraos_pg:
  terraos_redis:
  terraos_prometheus:
  terraos_grafana:
  terraos_loki:
  terraos_certs:
  terraos_nginx_logs:

networks:
  terra-net:
    driver: bridge
    ipam:
      config:
        - subnet: 172.20.0.0/16
```

### 2.4 `.dockerignore` (API i UI)

**`.dockerignore` (root — dla Dockerfile.api):**
```
.git
.github
.gitignore
**/__pycache__
**/*.pyc
**/*.pyo
**/*.pyd
.pytest_cache
.mypy_cache
.ruff_cache
**/*.egg-info
dist/
build/
*.egg
.env
.env.*
!.env.example
node_modules
apps/ui/.next
apps/ui/node_modules
apps/desktop
apps/mobile
docs/
*.md
tests/
infra/
docker-compose.dev.yml
```

**`apps/ui/.dockerignore` (dla Dockerfile.ui):**
```
node_modules
.next
.git
*.md
.env.local
.env.development
Dockerfile*
.dockerignore
```

### 2.5 Health Check Commands

```bash
# Healthchecks per service (dla manual/CI use)

# API
curl -sf http://localhost:8000/health
# Expected: {"status":"ok","version":"0.1.0","db":"ok"}

# UI
wget -qO- http://localhost:3000/ | grep -q 'Terra'

# PostgreSQL
docker exec terra-db pg_isready -U terraos -d terraos

# Redis
docker exec terra-redis redis-cli ping
# Expected: PONG

# Celery worker
docker exec terra-worker celery -A services.api.tasks inspect ping

# Full stack health script
docker compose -f docker-compose.prod.yml ps --format json | \
  jq '.[] | select(.Health != "healthy") | .Name'
```

---

## 3. MONITORING STACK SPEC

### 3.1 Prometheus Metrics dla FastAPI

**Instalacja i konfiguracja:**
```python
# services/api/metrics.py
"""Prometheus metrics — Terra.OS API instrumentation."""
from __future__ import annotations

from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
from prometheus_fastapi_instrumentator import Instrumentator
from fastapi import FastAPI, Response

# ─── Custom business metrics ──────────────────────────────────────────────────

TENDER_INGESTED = Counter(
    "terra_tender_ingested_total",
    "Total tenders ingested from BZP/TED",
    ["source", "status"],
)

TENDER_ANALYZED = Counter(
    "terra_tender_analyzed_total",
    "Total tenders processed by AI pipeline",
    ["model", "result"],
)

ESTIMATE_GENERATED = Counter(
    "terra_estimate_generated_total",
    "Total cost estimates generated",
    ["confidence_tier"],  # low/medium/high
)

PIPELINE_DURATION = Histogram(
    "terra_pipeline_duration_seconds",
    "LangGraph pipeline execution duration",
    ["pipeline_type", "status"],
    buckets=[0.5, 1, 2.5, 5, 10, 30, 60, 120],
)

ACTIVE_SESSIONS = Gauge(
    "terra_active_sessions",
    "Number of active user sessions",
)

DB_CONNECTIONS = Gauge(
    "terra_db_connections_active",
    "Active PostgreSQL connections",
)

AI_TOKENS_USED = Counter(
    "terra_ai_tokens_total",
    "Total LLM tokens consumed",
    ["model", "type"],  # type: prompt/completion
)

# ─── Standard HTTP instrumentation ───────────────────────────────────────────

def setup_metrics(app: FastAPI) -> None:
    """Attach Prometheus instrumentation to FastAPI app."""
    instrumentator = Instrumentator(
        should_group_status_codes=True,
        should_ignore_untemplated=True,
        should_respect_env_var=True,
        should_instrument_requests_inprogress=True,
        excluded_handlers=["/metrics", "/health", "/docs"],
        env_var_name="PROMETHEUS_ENABLED",
        inprogress_name="terra_inprogress_requests",
        inprogress_labels=True,
    )

    instrumentator.instrument(app).expose(
        app,
        endpoint="/metrics",
        include_in_schema=False,
        tags=["monitoring"],
    )

    # Custom metrics endpoint (raw)
    @app.get("/metrics/raw", include_in_schema=False)
    def metrics_raw() -> Response:
        return Response(
            content=generate_latest(),
            media_type=CONTENT_TYPE_LATEST,
        )
```

**Dodaj do `main.py`:**
```python
# W lifespan lub po inicjalizacji app:
from .metrics import setup_metrics
setup_metrics(app)
```

**`infra/prometheus/prometheus.yml`:**
```yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s
  external_labels:
    cluster: terra-prod
    environment: production

rule_files:
  - /etc/prometheus/rules/*.yml

alerting:
  alertmanagers:
    - static_configs:
        - targets: ["alertmanager:9093"]

scrape_configs:
  # API metrics
  - job_name: terra-api
    static_configs:
      - targets: ["api:8000"]
    metrics_path: /metrics
    relabel_configs:
      - source_labels: [__address__]
        target_label: instance
        replacement: terra-api

  # PostgreSQL exporter
  - job_name: postgres
    static_configs:
      - targets: ["postgres-exporter:9187"]

  # Redis exporter
  - job_name: redis
    static_configs:
      - targets: ["redis-exporter:9121"]

  # Node exporter (system metrics)
  - job_name: node
    static_configs:
      - targets: ["node-exporter:9100"]

  # Nginx exporter
  - job_name: nginx
    static_configs:
      - targets: ["nginx-exporter:9113"]
```

---

### 3.2 Grafana Dashboard JSON

```json
{
  "__inputs": [
    {
      "name": "DS_PROMETHEUS",
      "label": "Prometheus",
      "type": "datasource",
      "pluginId": "prometheus"
    }
  ],
  "title": "Terra.OS — API Health & Business Metrics",
  "uid": "terra-os-main",
  "tags": ["terra-os", "api", "production"],
  "schemaVersion": 38,
  "version": 1,
  "refresh": "30s",
  "time": { "from": "now-3h", "to": "now" },
  "panels": [
    {
      "id": 1,
      "title": "🟢 API Status",
      "type": "stat",
      "gridPos": {"h": 4, "w": 4, "x": 0, "y": 0},
      "targets": [{
        "datasource": {"type": "prometheus"},
        "expr": "up{job=\"terra-api\"}",
        "legendFormat": "API"
      }],
      "options": {
        "colorMode": "background",
        "thresholds": {
          "steps": [
            {"color": "red", "value": 0},
            {"color": "green", "value": 1}
          ]
        }
      }
    },
    {
      "id": 2,
      "title": "📊 Request Rate (req/s)",
      "type": "timeseries",
      "gridPos": {"h": 8, "w": 12, "x": 0, "y": 4},
      "targets": [{
        "expr": "sum(rate(http_requests_total{job=\"terra-api\"}[2m])) by (handler)",
        "legendFormat": "{{handler}}"
      }]
    },
    {
      "id": 3,
      "title": "⏱️ Latency p50/p95/p99",
      "type": "timeseries",
      "gridPos": {"h": 8, "w": 12, "x": 12, "y": 4},
      "targets": [
        {
          "expr": "histogram_quantile(0.50, sum(rate(http_request_duration_seconds_bucket{job=\"terra-api\"}[5m])) by (le))",
          "legendFormat": "p50"
        },
        {
          "expr": "histogram_quantile(0.95, sum(rate(http_request_duration_seconds_bucket{job=\"terra-api\"}[5m])) by (le))",
          "legendFormat": "p95"
        },
        {
          "expr": "histogram_quantile(0.99, sum(rate(http_request_duration_seconds_bucket{job=\"terra-api\"}[5m])) by (le))",
          "legendFormat": "p99"
        }
      ]
    },
    {
      "id": 4,
      "title": "❌ Error Rate (%)",
      "type": "gauge",
      "gridPos": {"h": 4, "w": 6, "x": 0, "y": 12},
      "targets": [{
        "expr": "100 * sum(rate(http_requests_total{job=\"terra-api\", status=~\"5..\"}[5m])) / sum(rate(http_requests_total{job=\"terra-api\"}[5m]))",
        "legendFormat": "Error %"
      }],
      "options": {
        "thresholds": {
          "steps": [
            {"color": "green", "value": 0},
            {"color": "yellow", "value": 0.5},
            {"color": "red", "value": 1}
          ]
        }
      }
    },
    {
      "id": 5,
      "title": "🗄️ DB Connections",
      "type": "gauge",
      "gridPos": {"h": 4, "w": 6, "x": 6, "y": 12},
      "targets": [{
        "expr": "terra_db_connections_active",
        "legendFormat": "Active"
      }],
      "options": {
        "thresholds": {
          "steps": [
            {"color": "green", "value": 0},
            {"color": "yellow", "value": 60},
            {"color": "red", "value": 80}
          ]
        },
        "max": 100
      }
    },
    {
      "id": 6,
      "title": "📋 Tenders Ingested (24h)",
      "type": "stat",
      "gridPos": {"h": 4, "w": 6, "x": 12, "y": 12},
      "targets": [{
        "expr": "increase(terra_tender_ingested_total[24h])",
        "legendFormat": "Tenders"
      }]
    },
    {
      "id": 7,
      "title": "🤖 AI Pipeline Throughput",
      "type": "timeseries",
      "gridPos": {"h": 8, "w": 12, "x": 0, "y": 16},
      "targets": [
        {
          "expr": "rate(terra_tender_analyzed_total[5m])",
          "legendFormat": "Analyzed/s — {{model}}"
        },
        {
          "expr": "rate(terra_estimate_generated_total[5m])",
          "legendFormat": "Estimates/s — {{confidence_tier}}"
        }
      ]
    },
    {
      "id": 8,
      "title": "🧠 LLM Token Usage",
      "type": "timeseries",
      "gridPos": {"h": 8, "w": 12, "x": 12, "y": 16},
      "targets": [{
        "expr": "rate(terra_ai_tokens_total[5m])",
        "legendFormat": "{{model}} — {{type}}"
      }]
    },
    {
      "id": 9,
      "title": "💾 Redis Memory",
      "type": "timeseries",
      "gridPos": {"h": 6, "w": 8, "x": 0, "y": 24},
      "targets": [{
        "expr": "redis_memory_used_bytes / 1024 / 1024",
        "legendFormat": "Used MB"
      }]
    }
  ]
}
```

**`infra/grafana/provisioning/datasources/prometheus.yml`:**
```yaml
apiVersion: 1
datasources:
  - name: Prometheus
    type: prometheus
    url: http://prometheus:9090
    access: proxy
    isDefault: true
    editable: false

  - name: Loki
    type: loki
    url: http://loki:3100
    access: proxy
    editable: false
```

---

### 3.3 AlertManager Rules

**`infra/prometheus/rules/terra-os.yml`:**
```yaml
groups:
  - name: terra-os-api
    interval: 1m
    rules:
      # ─── Latency: p99 > 1s ────────────────────────────────────────────────
      - alert: HighLatencyP99
        expr: |
          histogram_quantile(0.99,
            sum(rate(http_request_duration_seconds_bucket{job="terra-api"}[5m])) by (le, handler)
          ) > 1.0
        for: 3m
        labels:
          severity: warning
          team: backend
        annotations:
          summary: "High p99 latency on {{ $labels.handler }}"
          description: "p99 latency is {{ $value | humanizeDuration }} (threshold: 1s) on handler {{ $labels.handler }}"
          runbook: "https://wiki.terra-os.pl/runbooks/high-latency"

      # ─── Error rate > 1% ──────────────────────────────────────────────────
      - alert: HighErrorRate
        expr: |
          100 * (
            sum(rate(http_requests_total{job="terra-api", status=~"5.."}[5m]))
            /
            sum(rate(http_requests_total{job="terra-api"}[5m]))
          ) > 1.0
        for: 2m
        labels:
          severity: critical
          team: backend
        annotations:
          summary: "High 5xx error rate: {{ $value | humanize }}%"
          description: "API error rate exceeds 1% (current: {{ $value | humanize }}%)"
          runbook: "https://wiki.terra-os.pl/runbooks/high-error-rate"

      # ─── DB connections > 80% ─────────────────────────────────────────────
      - alert: DatabaseConnectionsHigh
        expr: terra_db_connections_active > 80
        for: 5m
        labels:
          severity: warning
          team: backend
        annotations:
          summary: "DB connections saturated: {{ $value }}/100"
          description: "Active DB connections {{ $value }} exceeds 80% threshold"
          runbook: "https://wiki.terra-os.pl/runbooks/db-connections"

      # ─── API down ─────────────────────────────────────────────────────────
      - alert: APIDown
        expr: up{job="terra-api"} == 0
        for: 1m
        labels:
          severity: critical
          team: on-call
        annotations:
          summary: "Terra API is DOWN"
          description: "API instance {{ $labels.instance }} has been unreachable for 1 minute"

      # ─── High inprogress requests (overload) ─────────────────────────────
      - alert: RequestQueueHigh
        expr: terra_inprogress_requests > 50
        for: 2m
        labels:
          severity: warning
        annotations:
          summary: "High number of in-flight requests: {{ $value }}"

  - name: terra-os-business
    rules:
      # ─── Pipeline stalled ─────────────────────────────────────────────────
      - alert: PipelineStalled
        expr: |
          increase(terra_tender_analyzed_total[30m]) == 0
          AND on() hour() >= 8
          AND on() hour() <= 20
        for: 15m
        labels:
          severity: warning
          team: ai
        annotations:
          summary: "AI pipeline stalled — no tenders analyzed in 30m"

      # ─── Token cost spike ─────────────────────────────────────────────────
      - alert: TokenCostSpike
        expr: rate(terra_ai_tokens_total[5m]) > 10000
        for: 5m
        labels:
          severity: warning
          team: ai
        annotations:
          summary: "Abnormally high LLM token usage: {{ $value | humanize }} tok/s"
```

**`infra/prometheus/alertmanager.yml`:**
```yaml
global:
  resolve_timeout: 5m
  slack_api_url: "${SLACK_WEBHOOK_URL}"

route:
  group_by: [alertname, team]
  group_wait: 30s
  group_interval: 5m
  repeat_interval: 4h
  receiver: slack-default

  routes:
    - matchers: [severity=critical]
      receiver: pagerduty-critical
      group_wait: 10s
      repeat_interval: 1h

    - matchers: [team=on-call]
      receiver: pagerduty-critical

receivers:
  - name: slack-default
    slack_configs:
      - channel: "#terra-alerts"
        title: '[{{ .Status | toUpper }}] {{ .GroupLabels.alertname }}'
        text: |
          {{ range .Alerts }}
          *Summary:* {{ .Annotations.summary }}
          *Description:* {{ .Annotations.description }}
          *Runbook:* {{ .Annotations.runbook }}
          {{ end }}
        send_resolved: true

  - name: pagerduty-critical
    pagerduty_configs:
      - service_key: "${PAGERDUTY_KEY}"
        severity: critical

inhibit_rules:
  - source_matchers: [alertname=APIDown]
    target_matchers: [job=terra-api]
    equal: [instance]
```

---

### 3.4 Loki Log Aggregation

**Konfiguracja strukturalnego JSON logging dla FastAPI:**
```python
# services/api/logging.json
{
  "version": 1,
  "disable_existing_loggers": false,
  "formatters": {
    "json": {
      "()": "pythonjsonlogger.jsonlogger.JsonFormatter",
      "format": "%(asctime)s %(name)s %(levelname)s %(message)s",
      "rename_fields": {
        "asctime": "timestamp",
        "levelname": "level",
        "name": "logger"
      }
    }
  },
  "handlers": {
    "console": {
      "class": "logging.StreamHandler",
      "formatter": "json",
      "stream": "ext://sys.stdout"
    }
  },
  "root": {
    "level": "INFO",
    "handlers": ["console"]
  },
  "loggers": {
    "uvicorn.access": {
      "handlers": ["console"],
      "level": "INFO",
      "propagate": false
    },
    "terra": {
      "handlers": ["console"],
      "level": "DEBUG",
      "propagate": false
    }
  }
}
```

**Structured logging helper:**
```python
# services/api/log.py
import logging
import structlog

structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer(),
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

log = structlog.get_logger("terra")
```

**`infra/loki/config.yml`:**
```yaml
auth_enabled: false

server:
  http_listen_port: 3100
  grpc_listen_port: 9096

ingester:
  lifecycler:
    address: 127.0.0.1
    ring:
      kvstore:
        store: inmemory
      replication_factor: 1
    final_sleep: 0s
  chunk_idle_period: 5m
  max_chunk_age: 1h
  chunk_retain_period: 30s

schema_config:
  configs:
    - from: 2024-01-01
      store: boltdb-shipper
      object_store: filesystem
      schema: v11
      index:
        prefix: index_
        period: 24h

storage_config:
  boltdb_shipper:
    active_index_directory: /loki/index
    cache_location: /loki/cache
    shared_store: filesystem
  filesystem:
    directory: /loki/chunks

limits_config:
  retention_period: 30d
  ingestion_rate_mb: 16
  max_streams_per_user: 10000
```

**`infra/promtail/config.yml`:**
```yaml
server:
  http_listen_port: 9080

positions:
  filename: /tmp/positions.yaml

clients:
  - url: http://loki:3100/loki/api/v1/push

scrape_configs:
  - job_name: docker
    docker_sd_configs:
      - host: unix:///var/run/docker.sock
        refresh_interval: 5s
    relabel_configs:
      - source_labels: [__meta_docker_container_name]
        target_label: container
      - source_labels: [__meta_docker_container_label_com_docker_compose_service]
        target_label: service
    pipeline_stages:
      - json:
          expressions:
            level: level
            timestamp: timestamp
            message: message
      - labels:
          level:
          service:
      - timestamp:
          source: timestamp
          format: RFC3339
```

---

### 3.5 Sentry Integration

```python
# services/api/sentry.py
"""Sentry SDK integration for Terra.OS API."""
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
from sentry_sdk.integrations.redis import RedisIntegration
from sentry_sdk.integrations.logging import LoggingIntegration
import logging

def setup_sentry(dsn: str, environment: str, release: str) -> None:
    """Initialize Sentry with FastAPI, SQLAlchemy, Redis integrations."""
    sentry_sdk.init(
        dsn=dsn,
        environment=environment,
        release=release,
        # Performance monitoring
        traces_sample_rate=0.1,         # 10% of transactions
        profiles_sample_rate=0.1,        # 10% CPU profiling
        # Error filtering
        sample_rate=1.0,                 # 100% errors
        # Integrations
        integrations=[
            FastApiIntegration(
                transaction_style="endpoint",
            ),
            SqlalchemyIntegration(),
            RedisIntegration(),
            LoggingIntegration(
                level=logging.WARNING,
                event_level=logging.ERROR,
            ),
        ],
        # PII scrubbing
        send_default_pii=False,
        # Custom fingerprinting
        before_send=_scrub_sensitive_data,
    )

def _scrub_sensitive_data(event, hint):
    """Remove PII from Sentry events."""
    if "request" in event:
        headers = event["request"].get("headers", {})
        for sensitive in ["authorization", "x-api-key", "cookie"]:
            if sensitive in headers:
                headers[sensitive] = "[Filtered]"
    return event
```

**Frontend Sentry (`apps/ui/lib/sentry.ts`):**
```typescript
// apps/ui/lib/sentry.ts
import * as Sentry from "@sentry/nextjs";

Sentry.init({
  dsn: process.env.NEXT_PUBLIC_SENTRY_DSN,
  environment: process.env.NODE_ENV,
  release: process.env.NEXT_PUBLIC_BUILD_SHA,

  // Performance
  tracesSampleRate: 0.1,
  replaysSessionSampleRate: 0.05,
  replaysOnErrorSampleRate: 1.0,

  integrations: [
    Sentry.replayIntegration({
      maskAllText: true,
      blockAllMedia: true,
    }),
  ],

  // Filter noisy errors
  ignoreErrors: [
    "ResizeObserver loop limit exceeded",
    "Non-Error exception captured",
    /ChunkLoadError/,
  ],
});
```

---

## 4. M9 LANGGRAPH ORCHESTRATION SPEC

### 4.1 Pipeline State Schema

```python
# services/pipeline/state.py
"""TenderPipeline — LangGraph state schema."""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Annotated, Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field
from typing_extensions import TypedDict
from langgraph.graph import add_messages


class PipelineStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    AWAITING_HUMAN = "awaiting_human"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TenderSource(str, Enum):
    BZP = "bzp"
    TED = "ted"
    MANUAL = "manual"
    EMAIL = "email"


class ConfidenceTier(str, Enum):
    LOW = "low"        # < 0.6
    MEDIUM = "medium"  # 0.6-0.85
    HIGH = "high"      # > 0.85


class AnalysisResult(BaseModel):
    category: str
    subcategory: str
    cpv_codes: list[str]
    keywords: list[str]
    estimated_value_pln: float | None = None
    deadline_days: int | None = None
    complexity_score: float  # 0.0-1.0
    confidence: float        # 0.0-1.0
    model_used: str


class CostEstimate(BaseModel):
    labor_cost_pln: float
    materials_cost_pln: float
    equipment_cost_pln: float
    overhead_pln: float
    total_pln: float
    margin_pct: float
    confidence: ConfidenceTier
    comparable_projects: list[str]  # IDs of similar past projects


class EngineDecision(BaseModel):
    recommendation: str  # "bid" | "skip" | "escalate"
    score: float         # 0.0-1.0
    reasoning: str
    risk_factors: list[str]
    opportunity_factors: list[str]


class HumanDecision(BaseModel):
    decided_by: str          # user_id
    decided_at: datetime
    action: str              # "approve" | "reject" | "modify"
    override_reason: str | None = None
    modified_estimate: CostEstimate | None = None


class LearnRecord(BaseModel):
    outcome: str             # "won" | "lost" | "withdrawn"
    actual_cost_pln: float | None = None
    variance_pct: float | None = None
    lessons: list[str]


class TenderPipeline(TypedDict):
    """LangGraph state — flows through all 6 nodes."""

    # ─── Metadata ─────────────────────────────────────────────────────────────
    pipeline_id: str
    tender_id: str
    source: TenderSource
    status: PipelineStatus
    created_at: str          # ISO datetime
    updated_at: str

    # ─── Raw input ────────────────────────────────────────────────────────────
    raw_document: str        # raw text/HTML from BZP/TED
    document_url: str | None
    attachments: list[str]   # s3:// or local paths

    # ─── Node outputs ─────────────────────────────────────────────────────────
    ingested_text: str | None         # cleaned text (IngestNode)
    analysis: AnalysisResult | None   # (AnalysisNode)
    estimate: CostEstimate | None     # (EstimateNode)
    engine_decision: EngineDecision | None  # (EngineNode)
    human_decision: HumanDecision | None    # (DecisionNode — human-in-loop)
    learn_record: LearnRecord | None        # (LearnNode)

    # ─── Control flow ─────────────────────────────────────────────────────────
    retry_count: int
    max_retries: int
    error_log: list[str]
    skip_human_gate: bool    # for low-value tenders

    # ─── Tracing ──────────────────────────────────────────────────────────────
    langsmith_run_id: str | None
    trace_url: str | None

    # ─── Messages (for chat/debug) ────────────────────────────────────────────
    messages: Annotated[list, add_messages]
```

---

### 4.2 LangGraph Nodes — 6 Pipeline Stages

```python
# services/pipeline/nodes.py
"""LangGraph pipeline nodes — Terra.OS tender processing."""
from __future__ import annotations

import asyncio
import re
from datetime import datetime, timezone
from typing import Any

from langchain_core.messages import HumanMessage, AIMessage
from langchain_openai import ChatOpenAI
from langgraph.types import interrupt

from .state import (
    TenderPipeline, PipelineStatus, AnalysisResult,
    CostEstimate, ConfidenceTier, EngineDecision, LearnRecord
)
from ..metrics import TENDER_ANALYZED, ESTIMATE_GENERATED, PIPELINE_DURATION


# ─── Shared LLM client ────────────────────────────────────────────────────────

llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
llm_heavy = ChatOpenAI(model="gpt-4o", temperature=0)


# ═══════════════════════════════════════════════════════════════════════════════
# NODE 1: IngestNode — document cleaning + extraction
# ═══════════════════════════════════════════════════════════════════════════════

async def ingest_node(state: TenderPipeline) -> TenderPipeline:
    """
    Clean raw document, extract structured fields.
    Input: state.raw_document
    Output: state.ingested_text
    """
    raw = state["raw_document"]

    # Strip HTML/XML
    text = re.sub(r"<[^>]+>", " ", raw)
    text = re.sub(r"\s+", " ", text).strip()

    # Truncate to 32K chars (LLM context limit)
    if len(text) > 32_000:
        text = text[:32_000] + "\n[TRUNCATED]"

    return {
        **state,
        "ingested_text": text,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "status": PipelineStatus.RUNNING,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# NODE 2: AnalysisNode — AI classification + extraction
# ═══════════════════════════════════════════════════════════════════════════════

async def analysis_node(state: TenderPipeline) -> TenderPipeline:
    """
    Use LLM to classify tender: category, CPV, keywords, complexity.
    Input: state.ingested_text
    Output: state.analysis
    """
    text = state["ingested_text"] or ""

    prompt = f"""Analyze this Polish public procurement tender. 
Return JSON with fields: category, subcategory, cpv_codes (list), keywords (list), 
estimated_value_pln (number or null), deadline_days (int or null), 
complexity_score (0.0-1.0), confidence (0.0-1.0).

TENDER:
{text[:8000]}

Respond ONLY with valid JSON."""

    response = await llm.ainvoke([HumanMessage(content=prompt)])
    import json

    try:
        data = json.loads(response.content)
        analysis = AnalysisResult(
            **data,
            model_used=llm.model_name,
        )
        TENDER_ANALYZED.labels(model=llm.model_name, result="success").inc()
    except Exception as e:
        TENDER_ANALYZED.labels(model=llm.model_name, result="error").inc()
        raise

    return {
        **state,
        "analysis": analysis,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }


# ═══════════════════════════════════════════════════════════════════════════════
# NODE 3: EstimateNode — cost estimation
# ═══════════════════════════════════════════════════════════════════════════════

async def estimate_node(state: TenderPipeline) -> TenderPipeline:
    """
    Generate cost estimate based on analysis + historical data.
    Input: state.analysis
    Output: state.estimate
    """
    from packages.db.models import get_comparable_projects  # lazy import

    analysis = state["analysis"]
    comparable = await get_comparable_projects(
        cpv_codes=analysis.cpv_codes,
        value_range=(
            (analysis.estimated_value_pln or 0) * 0.5,
            (analysis.estimated_value_pln or 0) * 2.0,
        ),
        limit=5,
    )

    prompt = f"""You are a construction cost estimator for Polish infrastructure projects.
Based on tender analysis and comparable projects, estimate costs.

ANALYSIS: {analysis.model_dump_json()}
COMPARABLE PROJECTS: {comparable}

Return JSON: labor_cost_pln, materials_cost_pln, equipment_cost_pln, 
overhead_pln, total_pln, margin_pct (0-30), confidence_tier (low/medium/high),
comparable_projects (list of IDs used)."""

    response = await llm_heavy.ainvoke([HumanMessage(content=prompt)])
    import json
    data = json.loads(response.content)
    estimate = CostEstimate(**data)

    ESTIMATE_GENERATED.labels(confidence_tier=estimate.confidence).inc()

    return {
        **state,
        "estimate": estimate,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }


# ═══════════════════════════════════════════════════════════════════════════════
# NODE 4: EngineNode — bid/no-bid decision engine
# ═══════════════════════════════════════════════════════════════════════════════

async def engine_node(state: TenderPipeline) -> TenderPipeline:
    """
    Apply business rules + ML scoring to recommend bid/skip/escalate.
    Input: state.analysis + state.estimate
    Output: state.engine_decision
    """
    analysis = state["analysis"]
    estimate = state["estimate"]

    # Business rules scoring
    score = 0.0
    risk_factors: list[str] = []
    opportunity_factors: list[str] = []

    # Rule: margin viability
    if estimate.margin_pct >= 15:
        score += 0.3
        opportunity_factors.append(f"Good margin: {estimate.margin_pct:.1f}%")
    elif estimate.margin_pct < 8:
        score -= 0.3
        risk_factors.append(f"Low margin: {estimate.margin_pct:.1f}%")

    # Rule: confidence tier
    if estimate.confidence == ConfidenceTier.HIGH:
        score += 0.2
        opportunity_factors.append("High estimate confidence")
    elif estimate.confidence == ConfidenceTier.LOW:
        score -= 0.2
        risk_factors.append("Low estimate confidence")

    # Rule: timeline
    if analysis.deadline_days and analysis.deadline_days < 14:
        score -= 0.2
        risk_factors.append(f"Very short deadline: {analysis.deadline_days} days")

    # Rule: complexity
    if analysis.complexity_score > 0.8:
        risk_factors.append(f"High complexity: {analysis.complexity_score:.2f}")
        score -= 0.1

    # Normalize
    score = max(0.0, min(1.0, score + 0.5))

    recommendation = (
        "bid" if score >= 0.65
        else "escalate" if 0.4 <= score < 0.65
        else "skip"
    )

    decision = EngineDecision(
        recommendation=recommendation,
        score=score,
        reasoning=f"Score: {score:.2f} based on {len(opportunity_factors)} opportunities, {len(risk_factors)} risks",
        risk_factors=risk_factors,
        opportunity_factors=opportunity_factors,
    )

    return {
        **state,
        "engine_decision": decision,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }


# ═══════════════════════════════════════════════════════════════════════════════
# NODE 5: DecisionNode — Human-in-the-Loop gate
# ═══════════════════════════════════════════════════════════════════════════════

async def decision_node(state: TenderPipeline) -> TenderPipeline:
    """
    Human approval gate. Pauses execution and waits for human input.
    Low-value + high-confidence tenders skip this gate.
    Uses LangGraph interrupt() for persistent pause.
    """
    engine = state["engine_decision"]
    estimate = state["estimate"]

    # Auto-approve conditions:
    # 1. Recommendation is "skip" — no human needed
    # 2. Very low value AND high confidence — auto
    auto_skip = (
        state.get("skip_human_gate", False)
        or engine.recommendation == "skip"
        or (
            estimate.total_pln < 50_000
            and estimate.confidence == ConfidenceTier.HIGH
            and engine.score > 0.75
        )
    )

    if auto_skip:
        from .state import HumanDecision
        auto_decision = HumanDecision(
            decided_by="system",
            decided_at=datetime.now(timezone.utc),
            action="approve" if engine.recommendation == "bid" else "reject",
            override_reason="Auto-approved by system rules",
        )
        return {
            **state,
            "human_decision": auto_decision,
            "status": PipelineStatus.RUNNING,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }

    # ── Interrupt: pause for human input ─────────────────────────────────────
    # This persists state to SQLite checkpointer and suspends execution
    human_input = interrupt({
        "type": "human_decision_required",
        "tender_id": state["tender_id"],
        "pipeline_id": state["pipeline_id"],
        "engine_recommendation": engine.recommendation,
        "engine_score": engine.score,
        "estimated_cost_pln": estimate.total_pln,
        "margin_pct": estimate.margin_pct,
        "risk_factors": engine.risk_factors,
        "opportunity_factors": engine.opportunity_factors,
        "resume_endpoint": f"/pipeline/{state['pipeline_id']}/resume",
    })

    # ── Resumed: process human decision ──────────────────────────────────────
    from .state import HumanDecision
    h_decision = HumanDecision(
        decided_by=human_input["user_id"],
        decided_at=datetime.now(timezone.utc),
        action=human_input["action"],
        override_reason=human_input.get("reason"),
        modified_estimate=human_input.get("modified_estimate"),
    )

    return {
        **state,
        "human_decision": h_decision,
        "status": PipelineStatus.RUNNING,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }


# ═══════════════════════════════════════════════════════════════════════════════
# NODE 6: LearnNode — feedback loop + model improvement
# ═══════════════════════════════════════════════════════════════════════════════

async def learn_node(state: TenderPipeline) -> TenderPipeline:
    """
    Record pipeline outcome. Update comparable project index.
    Fires async — does not block pipeline completion.
    """
    from packages.db.repository import save_pipeline_result

    human = state["human_decision"]
    estimate = state["estimate"]

    outcome = (
        "bid_submitted" if human.action == "approve"
        else "skipped"
    )

    record = LearnRecord(
        outcome=outcome,
        actual_cost_pln=None,  # filled later when project closes
        variance_pct=None,
        lessons=[
            f"Engine score: {state['engine_decision'].score:.2f}",
            f"Human decision: {human.action}",
            f"Confidence: {estimate.confidence}",
        ],
    )

    # Persist to DB (async fire-and-forget)
    asyncio.create_task(save_pipeline_result(state, record))

    return {
        **state,
        "learn_record": record,
        "status": PipelineStatus.COMPLETED,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
```

---

### 4.3 LangGraph Graph Definition + Checkpointing

```python
# services/pipeline/graph.py
"""LangGraph graph — TenderPipeline with SQLite checkpointing."""
from __future__ import annotations

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from .state import TenderPipeline, PipelineStatus
from .nodes import (
    ingest_node, analysis_node, estimate_node,
    engine_node, decision_node, learn_node,
)


# ─── Conditional routing ──────────────────────────────────────────────────────

def route_after_engine(state: TenderPipeline) -> str:
    """After engine: go to human gate OR skip directly to learn."""
    decision = state.get("engine_decision")
    if decision and decision.recommendation == "skip":
        return "learn"  # skip human gate for clear rejects
    return "decision"


def route_after_decision(state: TenderPipeline) -> str:
    """After human: if rejected, still learn (for ML training)."""
    human = state.get("human_decision")
    return "learn"  # always learn regardless of outcome


# ─── Error handling wrapper ───────────────────────────────────────────────────

def with_retry(node_fn, max_retries: int = 3):
    """Wrap node with retry logic for transient failures."""
    import asyncio

    async def wrapped(state: TenderPipeline) -> TenderPipeline:
        retry_count = state.get("retry_count", 0)
        try:
            result = await node_fn(state)
            return {**result, "retry_count": 0}  # reset on success
        except (ConnectionError, TimeoutError, OSError) as e:
            # Transient error — retry
            if retry_count < max_retries:
                await asyncio.sleep(2 ** retry_count)  # exponential backoff
                return {
                    **state,
                    "retry_count": retry_count + 1,
                    "error_log": state.get("error_log", []) + [f"Retry {retry_count + 1}: {str(e)}"],
                }
            else:
                return {
                    **state,
                    "status": PipelineStatus.FAILED,
                    "error_log": state.get("error_log", []) + [f"Max retries exceeded: {str(e)}"],
                }
        except Exception as e:
            # Non-transient — fail immediately
            return {
                **state,
                "status": PipelineStatus.FAILED,
                "error_log": state.get("error_log", []) + [f"Fatal error: {str(e)}"],
            }

    return wrapped


def should_continue(state: TenderPipeline) -> str:
    """Check if pipeline failed — short-circuit to END."""
    if state.get("status") == PipelineStatus.FAILED:
        return END
    return "continue"


# ─── Build graph ──────────────────────────────────────────────────────────────

def build_pipeline_graph(checkpointer_path: str = "/var/lib/terra/pipeline.db"):
    """Build and compile the TenderPipeline LangGraph."""

    workflow = StateGraph(TenderPipeline)

    # Add nodes (with retry wrappers)
    workflow.add_node("ingest",   with_retry(ingest_node))
    workflow.add_node("analysis", with_retry(analysis_node, max_retries=3))
    workflow.add_node("estimate", with_retry(estimate_node, max_retries=3))
    workflow.add_node("engine",   with_retry(engine_node))
    workflow.add_node("decision", decision_node)  # no retry — human gate
    workflow.add_node("learn",    learn_node)

    # Entry point
    workflow.set_entry_point("ingest")

    # Edges
    workflow.add_edge("ingest", "analysis")
    workflow.add_edge("analysis", "estimate")
    workflow.add_edge("estimate", "engine")
    workflow.add_conditional_edges(
        "engine",
        route_after_engine,
        {"decision": "decision", "learn": "learn"},
    )
    workflow.add_conditional_edges(
        "decision",
        route_after_decision,
        {"learn": "learn"},
    )
    workflow.add_edge("learn", END)

    return workflow


async def get_compiled_graph(db_path: str = "/var/lib/terra/pipeline.db"):
    """Get compiled graph with async SQLite checkpointer."""
    workflow = build_pipeline_graph(db_path)

    async with AsyncSqliteSaver.from_conn_string(db_path) as checkpointer:
        graph = workflow.compile(
            checkpointer=checkpointer,
            interrupt_before=["decision"],  # pause before human gate
        )
        return graph, checkpointer
```

---

### 4.4 Pipeline API Endpoints

```python
# services/api/routers/pipeline.py
"""LangGraph pipeline REST endpoints."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel

from services.pipeline.state import TenderPipeline, PipelineStatus, TenderSource
from services.pipeline.graph import get_compiled_graph

router = APIRouter(prefix="/pipeline", tags=["pipeline"])


class RunPipelineRequest(BaseModel):
    tender_id: str
    source: TenderSource
    raw_document: str
    document_url: str | None = None
    skip_human_gate: bool = False


class PipelineStatusResponse(BaseModel):
    pipeline_id: str
    tender_id: str
    status: PipelineStatus
    current_node: str | None
    created_at: str
    updated_at: str
    error_log: list[str]
    result: dict[str, Any] | None = None
    interrupt_data: dict[str, Any] | None = None  # set when awaiting human


class ResumeRequest(BaseModel):
    user_id: str
    action: str  # "approve" | "reject" | "modify"
    reason: str | None = None
    modified_estimate: dict | None = None


# In-memory store (replace with Redis/DB in production)
_pipeline_registry: dict[str, dict] = {}


@router.post("/run", response_model=PipelineStatusResponse, status_code=202)
async def run_pipeline(
    req: RunPipelineRequest,
    background_tasks: BackgroundTasks,
) -> PipelineStatusResponse:
    """
    Start a new tender pipeline run.
    Returns immediately with pipeline_id; execution is async.
    """
    pipeline_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()

    initial_state: TenderPipeline = {
        "pipeline_id": pipeline_id,
        "tender_id": req.tender_id,
        "source": req.source,
        "status": PipelineStatus.PENDING,
        "created_at": now,
        "updated_at": now,
        "raw_document": req.raw_document,
        "document_url": req.document_url,
        "attachments": [],
        "ingested_text": None,
        "analysis": None,
        "estimate": None,
        "engine_decision": None,
        "human_decision": None,
        "learn_record": None,
        "retry_count": 0,
        "max_retries": 3,
        "error_log": [],
        "skip_human_gate": req.skip_human_gate,
        "langsmith_run_id": None,
        "trace_url": None,
        "messages": [],
    }

    _pipeline_registry[pipeline_id] = {
        "state": initial_state,
        "status": PipelineStatus.PENDING,
    }

    # Run in background
    background_tasks.add_task(_run_pipeline_async, pipeline_id, initial_state)

    return PipelineStatusResponse(
        pipeline_id=pipeline_id,
        tender_id=req.tender_id,
        status=PipelineStatus.PENDING,
        current_node=None,
        created_at=now,
        updated_at=now,
        error_log=[],
    )


@router.get("/{pipeline_id}/status", response_model=PipelineStatusResponse)
async def get_pipeline_status(pipeline_id: str) -> PipelineStatusResponse:
    """Get current pipeline status + interrupt data if awaiting human."""
    if pipeline_id not in _pipeline_registry:
        raise HTTPException(status_code=404, detail="Pipeline not found")

    entry = _pipeline_registry[pipeline_id]
    state = entry["state"]

    return PipelineStatusResponse(
        pipeline_id=pipeline_id,
        tender_id=state["tender_id"],
        status=state["status"],
        current_node=entry.get("current_node"),
        created_at=state["created_at"],
        updated_at=state["updated_at"],
        error_log=state.get("error_log", []),
        interrupt_data=entry.get("interrupt_data"),
        result=_extract_result(state) if state["status"] == PipelineStatus.COMPLETED else None,
    )


@router.post("/{pipeline_id}/resume", response_model=PipelineStatusResponse)
async def resume_pipeline(
    pipeline_id: str,
    decision: ResumeRequest,
    background_tasks: BackgroundTasks,
) -> PipelineStatusResponse:
    """
    Resume a paused pipeline with human decision.
    Called after human reviews interrupt_data and makes a decision.
    """
    if pipeline_id not in _pipeline_registry:
        raise HTTPException(status_code=404, detail="Pipeline not found")

    entry = _pipeline_registry[pipeline_id]
    if entry["state"]["status"] != PipelineStatus.AWAITING_HUMAN:
        raise HTTPException(
            status_code=400,
            detail=f"Pipeline is not awaiting human input (status: {entry['state']['status']})"
        )

    # Store human decision for resume
    entry["human_resume_input"] = {
        "user_id": decision.user_id,
        "action": decision.action,
        "reason": decision.reason,
        "modified_estimate": decision.modified_estimate,
    }
    entry["state"]["status"] = PipelineStatus.RUNNING

    # Resume background execution
    background_tasks.add_task(_resume_pipeline_async, pipeline_id)

    return PipelineStatusResponse(
        pipeline_id=pipeline_id,
        tender_id=entry["state"]["tender_id"],
        status=PipelineStatus.RUNNING,
        current_node="decision",
        created_at=entry["state"]["created_at"],
        updated_at=datetime.now(timezone.utc).isoformat(),
        error_log=entry["state"].get("error_log", []),
    )


@router.delete("/{pipeline_id}")
async def cancel_pipeline(pipeline_id: str) -> dict:
    """Cancel a running or paused pipeline."""
    if pipeline_id not in _pipeline_registry:
        raise HTTPException(status_code=404, detail="Pipeline not found")

    _pipeline_registry[pipeline_id]["state"]["status"] = PipelineStatus.CANCELLED
    return {"pipeline_id": pipeline_id, "status": "cancelled"}


# ─── Internal helpers ─────────────────────────────────────────────────────────

async def _run_pipeline_async(pipeline_id: str, initial_state: TenderPipeline) -> None:
    """Execute pipeline in background with LangSmith tracing."""
    from langsmith import traceable

    graph, _ = await get_compiled_graph()
    config = {
        "configurable": {"thread_id": pipeline_id},
        "run_name": f"tender-pipeline-{pipeline_id[:8]}",
    }

    try:
        _pipeline_registry[pipeline_id]["state"]["status"] = PipelineStatus.RUNNING

        async for chunk in graph.astream(initial_state, config=config):
            node_name = list(chunk.keys())[0] if chunk else None
            _pipeline_registry[pipeline_id]["current_node"] = node_name

            # Check for interrupt (human gate)
            if "__interrupt__" in chunk:
                _pipeline_registry[pipeline_id]["state"]["status"] = PipelineStatus.AWAITING_HUMAN
                _pipeline_registry[pipeline_id]["interrupt_data"] = chunk["__interrupt__"]
                return  # pause here

            # Update state
            if node_name and node_name in chunk:
                _pipeline_registry[pipeline_id]["state"].update(chunk[node_name])

    except Exception as e:
        _pipeline_registry[pipeline_id]["state"]["status"] = PipelineStatus.FAILED
        _pipeline_registry[pipeline_id]["state"]["error_log"].append(str(e))


async def _resume_pipeline_async(pipeline_id: str) -> None:
    """Resume pipeline after human decision."""
    graph, _ = await get_compiled_graph()
    entry = _pipeline_registry[pipeline_id]
    config = {"configurable": {"thread_id": pipeline_id}}

    await graph.aupdate_state(
        config,
        entry["human_resume_input"],
        as_node="decision",
    )

    async for chunk in graph.astream(None, config=config):
        node_name = list(chunk.keys())[0] if chunk else None
        if node_name and node_name in chunk:
            entry["state"].update(chunk[node_name])

    entry["state"]["status"] = PipelineStatus.COMPLETED


def _extract_result(state: TenderPipeline) -> dict:
    return {
        "analysis": state.get("analysis"),
        "estimate": state.get("estimate"),
        "engine_decision": state.get("engine_decision"),
        "human_decision": state.get("human_decision"),
        "learn_record": state.get("learn_record"),
    }
```

---

### 4.5 LangSmith Tracing

```python
# services/pipeline/tracing.py
"""LangSmith tracing configuration."""
import os

def setup_langsmith() -> None:
    """Configure LangSmith tracing via environment variables."""
    # Set these in .env / GitHub secrets:
    # LANGCHAIN_TRACING_V2=true
    # LANGCHAIN_API_KEY=ls__...
    # LANGCHAIN_PROJECT=terra-os-prod
    # LANGCHAIN_ENDPOINT=https://api.smith.langchain.com
    pass  # env vars configure automatically

# Usage in nodes:
# @traceable(run_type="chain", name="TenderAnalysis")
# async def analysis_node(state): ...
```

**Wymagane env vars:**
```bash
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=ls__your_key_here
LANGCHAIN_PROJECT=terra-os-prod
LANGCHAIN_ENDPOINT=https://api.smith.langchain.com
```

---

## 5. M8 FLUTTER MOBILE SPEC

### 5.1 Struktura Projektu

```
terra-os/
└── apps/
    └── mobile/                    # terra_mobile Flutter app
        ├── pubspec.yaml
        ├── lib/
        │   ├── main.dart
        │   ├── app.dart            # MaterialApp + router
        │   ├── core/
        │   │   ├── api/
        │   │   │   ├── client.dart        # Dio HTTP client
        │   │   │   └── endpoints.dart
        │   │   ├── auth/
        │   │   │   ├── auth_service.dart  # JWT + secure storage
        │   │   │   └── auth_state.dart    # Riverpod provider
        │   │   ├── db/
        │   │   │   ├── database.dart      # Drift SQLite
        │   │   │   ├── tables.dart
        │   │   │   └── sync_queue.dart    # offline queue
        │   │   ├── notifications/
        │   │   │   └── push_service.dart  # FCM + APNs
        │   │   └── theme/
        │   │       └── theme.dart
        │   ├── features/
        │   │   ├── plan_list/
        │   │   │   ├── plan_list_screen.dart
        │   │   │   └── plan_list_provider.dart
        │   │   ├── plan_detail/
        │   │   │   ├── plan_detail_screen.dart
        │   │   │   └── plan_detail_provider.dart
        │   │   ├── map_view/
        │   │   │   ├── map_view_screen.dart
        │   │   │   └── map_provider.dart
        │   │   ├── photo_capture/
        │   │   │   ├── photo_capture_screen.dart
        │   │   │   └── photo_provider.dart
        │   │   └── field_status/
        │   │       ├── field_status_screen.dart
        │   │       └── field_status_provider.dart
        │   └── shared/
        │       ├── widgets/
        │       └── models/          # Freezed data classes
        ├── android/
        ├── ios/
        └── test/
```

---

### 5.2 `pubspec.yaml`

```yaml
name: terra_mobile
description: Terra.OS — Field mobile app for construction tender management
publish_to: none
version: 1.0.0+1

environment:
  sdk: ">=3.3.0 <4.0.0"
  flutter: ">=3.22.0"

dependencies:
  flutter:
    sdk: flutter

  # ─── State Management ────────────────────────────────────
  flutter_riverpod: ^2.5.1
  riverpod_annotation: ^2.3.5

  # ─── Navigation ──────────────────────────────────────────
  go_router: ^14.2.7

  # ─── HTTP + API ───────────────────────────────────────────
  dio: ^5.4.3
  retrofit: ^4.1.0

  # ─── Auth ─────────────────────────────────────────────────
  flutter_secure_storage: ^9.0.0
  jwt_decoder: ^2.0.1

  # ─── Local DB (offline) ───────────────────────────────────
  drift: ^2.18.0
  sqlite3_flutter_libs: ^0.5.22
  path_provider: ^2.1.3
  path: ^1.9.0

  # ─── Maps ─────────────────────────────────────────────────
  flutter_map: ^7.0.1
  latlong2: ^0.9.0

  # ─── Camera / Photo ───────────────────────────────────────
  camera: ^0.11.0
  image_picker: ^1.1.2
  image: ^4.1.7
  photo_view: ^0.15.0

  # ─── Push Notifications ───────────────────────────────────
  firebase_core: ^3.3.0
  firebase_messaging: ^15.1.0
  flutter_local_notifications: ^17.2.2

  # ─── Utilities ────────────────────────────────────────────
  freezed_annotation: ^2.4.4
  json_annotation: ^4.9.0
  connectivity_plus: ^6.0.3
  permission_handler: ^11.3.1
  intl: ^0.19.0
  cached_network_image: ^3.3.1

  # ─── Monitoring ───────────────────────────────────────────
  sentry_flutter: ^8.3.0

dev_dependencies:
  flutter_test:
    sdk: flutter
  flutter_lints: ^4.0.0
  build_runner: ^2.4.11
  drift_dev: ^2.18.0
  freezed: ^2.5.7
  json_serializable: ^6.8.0
  retrofit_generator: ^8.1.0
  riverpod_generator: ^2.4.0
  mocktail: ^1.0.4
```

---

### 5.3 Key Screens

#### Screen 1: `plan_list_screen.dart`
```dart
// lib/features/plan_list/plan_list_screen.dart
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'plan_list_provider.dart';
import '../../shared/widgets/offline_banner.dart';

class PlanListScreen extends ConsumerWidget {
  const PlanListScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final plansAsync = ref.watch(planListProvider);
    final isOnline = ref.watch(connectivityProvider);

    return Scaffold(
      appBar: AppBar(
        title: const Text('Terra.OS — Przetargi'),
        actions: [
          IconButton(
            icon: const Icon(Icons.filter_list),
            onPressed: () => _showFilterSheet(context, ref),
          ),
          IconButton(
            icon: const Icon(Icons.sync),
            onPressed: isOnline ? () => ref.refresh(planListProvider) : null,
          ),
        ],
      ),
      body: Column(
        children: [
          if (!isOnline) const OfflineBanner(),
          Expanded(
            child: plansAsync.when(
              loading: () => const Center(child: CircularProgressIndicator()),
              error: (err, _) => _ErrorView(error: err.toString()),
              data: (plans) => RefreshIndicator(
                onRefresh: () => ref.refresh(planListProvider.future),
                child: ListView.builder(
                  itemCount: plans.length,
                  itemBuilder: (ctx, i) => _PlanCard(
                    plan: plans[i],
                    onTap: () => context.go('/plans/${plans[i].id}'),
                  ),
                ),
              ),
            ),
          ),
        ],
      ),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: () => context.go('/plans/new'),
        icon: const Icon(Icons.add),
        label: const Text('Nowy przetarg'),
      ),
    );
  }

  void _showFilterSheet(BuildContext context, WidgetRef ref) {
    showModalBottomSheet(
      context: context,
      builder: (_) => const _FilterSheet(),
    );
  }
}

class _PlanCard extends StatelessWidget {
  final dynamic plan;
  final VoidCallback onTap;

  const _PlanCard({required this.plan, required this.onTap});

  @override
  Widget build(BuildContext context) {
    return Card(
      margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 6),
      child: ListTile(
        leading: CircleAvatar(
          backgroundColor: _statusColor(plan.status),
          child: Icon(_statusIcon(plan.status), color: Colors.white, size: 18),
        ),
        title: Text(plan.title, maxLines: 2, overflow: TextOverflow.ellipsis),
        subtitle: Text('${plan.estimatedValuePln?.toStringAsFixed(0) ?? "—"} PLN • ${plan.deadline}'),
        trailing: const Icon(Icons.chevron_right),
        onTap: onTap,
      ),
    );
  }

  Color _statusColor(String status) => switch (status) {
    'active' => Colors.green,
    'pending' => Colors.orange,
    'closed' => Colors.grey,
    _ => Colors.blue,
  };

  IconData _statusIcon(String status) => switch (status) {
    'active' => Icons.play_arrow,
    'pending' => Icons.schedule,
    'closed' => Icons.check_circle,
    _ => Icons.info,
  };
}
```

#### Screen 2: `map_view_screen.dart`
```dart
// lib/features/map_view/map_view_screen.dart
import 'package:flutter/material.dart';
import 'package:flutter_map/flutter_map.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:latlong2/latlong.dart';
import 'map_provider.dart';

class MapViewScreen extends ConsumerStatefulWidget {
  const MapViewScreen({super.key});

  @override
  ConsumerState<MapViewScreen> createState() => _MapViewScreenState();
}

class _MapViewScreenState extends ConsumerState<MapViewScreen> {
  final _mapController = MapController();

  @override
  Widget build(BuildContext context) {
    final locationsAsync = ref.watch(tenderLocationsProvider);

    return Scaffold(
      appBar: AppBar(title: const Text('Mapa przetargów')),
      body: locationsAsync.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (e, _) => Center(child: Text('Błąd: $e')),
        data: (locations) => FlutterMap(
          mapController: _mapController,
          options: MapOptions(
            initialCenter: const LatLng(52.2297, 21.0122),  // Warsaw
            initialZoom: 6.0,
          ),
          children: [
            TileLayer(
              urlTemplate: 'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
              userAgentPackageName: 'pl.terraos.mobile',
            ),
            MarkerLayer(
              markers: locations.map((loc) => Marker(
                point: LatLng(loc.lat, loc.lng),
                child: GestureDetector(
                  onTap: () => _showTenderPopup(context, loc),
                  child: Container(
                    decoration: BoxDecoration(
                      color: _markerColor(loc.status),
                      shape: BoxShape.circle,
                      border: Border.all(color: Colors.white, width: 2),
                    ),
                    width: 24,
                    height: 24,
                  ),
                ),
              )).toList(),
            ),
          ],
        ),
      ),
    );
  }

  Color _markerColor(String status) => switch (status) {
    'active' => Colors.green,
    'pending' => Colors.orange,
    _ => Colors.grey,
  };

  void _showTenderPopup(BuildContext context, dynamic location) {
    showDialog(
      context: context,
      builder: (_) => AlertDialog(
        title: Text(location.title),
        content: Text('Status: ${location.status}\nWartość: ${location.value} PLN'),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('Zamknij'),
          ),
        ],
      ),
    );
  }
}
```

#### Screen 3: `photo_capture_screen.dart`
```dart
// lib/features/photo_capture/photo_capture_screen.dart
import 'dart:io';
import 'package:camera/camera.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'photo_provider.dart';

class PhotoCaptureScreen extends ConsumerStatefulWidget {
  final String tenderId;
  const PhotoCaptureScreen({super.key, required this.tenderId});

  @override
  ConsumerState<PhotoCaptureScreen> createState() => _PhotoCaptureScreenState();
}

class _PhotoCaptureScreenState extends ConsumerState<PhotoCaptureScreen> {
  CameraController? _controller;
  bool _isCapturing = false;
  File? _preview;

  @override
  void initState() {
    super.initState();
    _initCamera();
  }

  Future<void> _initCamera() async {
    final cameras = await availableCameras();
    if (cameras.isEmpty) return;

    _controller = CameraController(
      cameras.first,
      ResolutionPreset.high,
      imageFormatGroup: ImageFormatGroup.jpeg,
    );
    await _controller!.initialize();
    if (mounted) setState(() {});
  }

  Future<void> _capturePhoto() async {
    if (_controller == null || !_controller!.value.isInitialized) return;

    setState(() => _isCapturing = true);
    try {
      final xFile = await _controller!.takePicture();
      setState(() => _preview = File(xFile.path));

      // Queue for upload (works offline)
      await ref.read(photoUploadQueueProvider.notifier).enqueue(
        tenderId: widget.tenderId,
        filePath: xFile.path,
        metadata: {
          'timestamp': DateTime.now().toIso8601String(),
          'lat': 0.0,  // GPS integration TODO
          'lng': 0.0,
        },
      );

      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('📸 Zdjęcie zapisane — zostanie wysłane po połączeniu')),
        );
      }
    } finally {
      setState(() => _isCapturing = false);
    }
  }

  @override
  void dispose() {
    _controller?.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    if (_controller == null || !_controller!.value.isInitialized) {
      return const Scaffold(body: Center(child: CircularProgressIndicator()));
    }

    return Scaffold(
      backgroundColor: Colors.black,
      body: Stack(
        children: [
          Positioned.fill(child: CameraPreview(_controller!)),
          if (_preview != null)
            Positioned(
              bottom: 100, right: 16,
              child: Container(
                width: 80, height: 80,
                decoration: BoxDecoration(
                  border: Border.all(color: Colors.white, width: 2),
                  borderRadius: BorderRadius.circular(8),
                  image: DecorationImage(
                    image: FileImage(_preview!),
                    fit: BoxFit.cover,
                  ),
                ),
              ),
            ),
          Positioned(
            bottom: 24, left: 0, right: 0,
            child: Center(
              child: GestureDetector(
                onTap: _isCapturing ? null : _capturePhoto,
                child: Container(
                  width: 72, height: 72,
                  decoration: BoxDecoration(
                    shape: BoxShape.circle,
                    color: _isCapturing ? Colors.grey : Colors.white,
                    border: Border.all(color: Colors.white, width: 4),
                  ),
                  child: _isCapturing
                      ? const CircularProgressIndicator()
                      : const Icon(Icons.camera_alt, size: 32, color: Colors.black),
                ),
              ),
            ),
          ),
          Positioned(
            top: 48, left: 16,
            child: IconButton(
              icon: const Icon(Icons.arrow_back, color: Colors.white),
              onPressed: () => Navigator.pop(context),
            ),
          ),
        ],
      ),
    );
  }
}
```

---

### 5.4 Offline Strategy — Drift SQLite + Sync Queue

```dart
// lib/core/db/tables.dart
import 'package:drift/drift.dart';

// ─── Tables ───────────────────────────────────────────────────────────────────

class TendersTable extends Table {
  IntColumn get id => integer().autoIncrement()();
  TextColumn get remoteId => text().unique()();
  TextColumn get title => text()();
  TextColumn get status => text().withDefault(const Constant('pending'))();
  RealColumn get estimatedValuePln => real().nullable()();
  TextColumn get deadline => text().nullable()();
  TextColumn get rawJson => text()();
  DateTimeColumn get syncedAt => dateTime().nullable()();
  DateTimeColumn get updatedAt => dateTime().withDefault(currentDateAndTime)();
}

class PhotosTable extends Table {
  IntColumn get id => integer().autoIncrement()();
  TextColumn get tenderId => text()();
  TextColumn get localPath => text()();
  TextColumn get remoteUrl => text().nullable()();
  TextColumn get metadata => text().withDefault(const Constant('{}'))();
  BoolColumn get uploaded => boolean().withDefault(const Constant(false))();
  DateTimeColumn get capturedAt => dateTime().withDefault(currentDateAndTime)();
}

class SyncQueueTable extends Table {
  IntColumn get id => integer().autoIncrement()();
  TextColumn get operation => text()();    // CREATE | UPDATE | DELETE | UPLOAD
  TextColumn get entityType => text()();   // tender | photo | status
  TextColumn get entityId => text()();
  TextColumn get payload => text()();      // JSON
  IntColumn get retries => integer().withDefault(const Constant(0))();
  BoolColumn get processed => boolean().withDefault(const Constant(false))();
  DateTimeColumn get createdAt => dateTime().withDefault(currentDateAndTime)();
}
```

```dart
// lib/core/db/sync_queue.dart
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:connectivity_plus/connectivity_plus.dart';
import 'database.dart';
import '../api/client.dart';

/// Drains the offline sync queue when connectivity is restored.
class SyncQueueService {
  final AppDatabase _db;
  final ApiClient _api;

  SyncQueueService(this._db, this._api);

  /// Call this on app resume or connectivity change.
  Future<void> drain() async {
    final connectivity = await Connectivity().checkConnectivity();
    if (connectivity == ConnectivityResult.none) return;

    final pending = await _db.getPendingQueueItems(limit: 50);

    for (final item in pending) {
      try {
        await _processQueueItem(item);
        await _db.markQueueItemProcessed(item.id);
      } catch (e) {
        await _db.incrementRetries(item.id);
        // Give up after 5 retries
        if (item.retries >= 5) {
          await _db.markQueueItemFailed(item.id);
        }
      }
    }
  }

  Future<void> _processQueueItem(dynamic item) async {
    switch (item.operation) {
      case 'UPLOAD':
        if (item.entityType == 'photo') {
          await _api.uploadPhoto(item.entityId, item.payload);
        }
      case 'UPDATE':
        if (item.entityType == 'status') {
          await _api.updateFieldStatus(item.entityId, item.payload);
        }
      case 'CREATE':
        await _api.createEntity(item.entityType, item.payload);
    }
  }
}

/// Auto-drain on connectivity restore
final syncServiceProvider = Provider((ref) {
  final db = ref.watch(databaseProvider);
  final api = ref.watch(apiClientProvider);
  return SyncQueueService(db, api);
});
```

---

### 5.5 Auth Flow — JWT + flutter_secure_storage

```dart
// lib/core/auth/auth_service.dart
import 'dart:convert';
import 'package:dio/dio.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:jwt_decoder/jwt_decoder.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

class AuthService {
  static const _accessKey = 'terra_access_token';
  static const _refreshKey = 'terra_refresh_token';

  final FlutterSecureStorage _storage;
  final Dio _dio;

  AuthService(this._storage, this._dio);

  Future<bool> login(String email, String password) async {
    try {
      final response = await _dio.post('/auth/login', data: {
        'email': email,
        'password': password,
      });

      final access = response.data['access_token'] as String;
      final refresh = response.data['refresh_token'] as String;

      await _storage.write(key: _accessKey, value: access);
      await _storage.write(key: _refreshKey, value: refresh);

      return true;
    } on DioException {
      return false;
    }
  }

  Future<String?> getValidToken() async {
    final access = await _storage.read(key: _accessKey);
    if (access == null) return null;

    // Check expiry with 60s buffer
    if (!JwtDecoder.isExpired(access)) {
      return access;
    }

    // Refresh
    return _refreshToken();
  }

  Future<String?> _refreshToken() async {
    final refresh = await _storage.read(key: _refreshKey);
    if (refresh == null || JwtDecoder.isExpired(refresh)) {
      await logout();
      return null;
    }

    try {
      final response = await _dio.post('/auth/refresh', data: {
        'refresh_token': refresh,
      });

      final newAccess = response.data['access_token'] as String;
      await _storage.write(key: _accessKey, value: newAccess);
      return newAccess;
    } on DioException {
      await logout();
      return null;
    }
  }

  Future<void> logout() async {
    await _storage.delete(key: _accessKey);
    await _storage.delete(key: _refreshKey);
  }

  Future<bool> get isLoggedIn async {
    final token = await getValidToken();
    return token != null;
  }
}

// Dio interceptor for auto token refresh
class AuthInterceptor extends Interceptor {
  final AuthService _auth;

  AuthInterceptor(this._auth);

  @override
  Future<void> onRequest(
    RequestOptions options,
    RequestInterceptorHandler handler,
  ) async {
    final token = await _auth.getValidToken();
    if (token != null) {
      options.headers['Authorization'] = 'Bearer $token';
    }
    handler.next(options);
  }

  @override
  void onError(DioException err, ErrorInterceptorHandler handler) {
    if (err.response?.statusCode == 401) {
      // Force logout on 401
      _auth.logout();
    }
    handler.next(err);
  }
}
```

---

### 5.6 Push Notifications — FCM + APNs

```dart
// lib/core/notifications/push_service.dart
import 'package:firebase_messaging/firebase_messaging.dart';
import 'package:flutter_local_notifications/flutter_local_notifications.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

// Background handler (top-level function required by FCM)
@pragma('vm:entry-point')
Future<void> _firebaseMessagingBackgroundHandler(RemoteMessage message) async {
  await _showLocalNotification(message);
}

Future<void> _showLocalNotification(RemoteMessage message) async {
  final localNotif = FlutterLocalNotificationsPlugin();
  await localNotif.show(
    message.hashCode,
    message.notification?.title ?? 'Terra.OS',
    message.notification?.body ?? '',
    const NotificationDetails(
      android: AndroidNotificationDetails(
        'terra_channel',
        'Terra.OS Notifications',
        importance: Importance.high,
        priority: Priority.high,
      ),
      iOS: DarwinNotificationDetails(
        categoryIdentifier: 'terra_notification',
      ),
    ),
    payload: message.data['tender_id'],
  );
}

class PushNotificationService {
  final FirebaseMessaging _fcm;
  final FlutterLocalNotificationsPlugin _localNotif;

  PushNotificationService(this._fcm, this._localNotif);

  Future<void> initialize({
    required Function(String tenderId) onTenderNotification,
  }) async {
    // Request permission
    final settings = await _fcm.requestPermission(
      alert: true,
      badge: true,
      sound: true,
    );

    if (settings.authorizationStatus == AuthorizationStatus.denied) return;

    // Background handler
    FirebaseMessaging.onBackgroundMessage(_firebaseMessagingBackgroundHandler);

    // Foreground handling
    FirebaseMessaging.onMessage.listen((message) {
      _showLocalNotification(message);

      // Navigate to tender if app is in foreground
      final tenderId = message.data['tender_id'];
      if (tenderId != null) {
        onTenderNotification(tenderId);
      }
    });

    // App opened from notification
    FirebaseMessaging.onMessageOpenedApp.listen((message) {
      final tenderId = message.data['tender_id'];
      if (tenderId != null) {
        onTenderNotification(tenderId);
      }
    });

    // APNs token (iOS)
    await _fcm.setForegroundNotificationPresentationOptions(
      alert: true,
      badge: true,
      sound: true,
    );

    // Get and register FCM token with backend
    final token = await _fcm.getToken();
    if (token != null) {
      await _registerTokenWithBackend(token);
    }

    // Token refresh
    _fcm.onTokenRefresh.listen(_registerTokenWithBackend);
  }

  Future<void> _registerTokenWithBackend(String token) async {
    // POST /notifications/register-device { fcm_token: token, platform: 'android'|'ios' }
    // Implementation in ApiClient
  }
}

// Notification types:
// - NEW_TENDER: nowy przetarg z BZP pasujący do profilu
// - DEADLINE_REMINDER: przetarg kończy się za 3 dni
// - PIPELINE_DECISION: pipeline czeka na decyzję
// - ESTIMATE_READY: kosztorys gotowy
// - FIELD_STATUS_UPDATE: zmiana statusu pola przez inny device
```

---

### 5.7 Flutter CI Workflow

```yaml
# .github/workflows/flutter.yml
# Trigger: push/PR z zmianami w apps/mobile/

name: Flutter Mobile CI

on:
  push:
    paths:
      - "apps/mobile/**"
    branches: ["**"]
  pull_request:
    paths:
      - "apps/mobile/**"

env:
  FLUTTER_VERSION: "3.22.0"

defaults:
  run:
    working-directory: apps/mobile

jobs:
  # ─────────────────────────────────────────────────────
  # Analyze + Test
  # ─────────────────────────────────────────────────────
  analyze-test:
    name: "🎯 Flutter Analyze + Test"
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4

      - name: Setup Flutter
        uses: subosito/flutter-action@v2
        with:
          flutter-version: ${{ env.FLUTTER_VERSION }}
          channel: stable
          cache: true

      - name: Get dependencies
        run: flutter pub get

      - name: Generate code (Drift, Freezed, Retrofit)
        run: dart run build_runner build --delete-conflicting-outputs

      - name: Analyze (flutter analyze)
        run: flutter analyze --fatal-infos

      - name: Run unit tests
        run: flutter test --coverage

      - name: Upload coverage
        uses: codecov/codecov-action@v4
        with:
          files: coverage/lcov.info
          flags: flutter
        continue-on-error: true

  # ─────────────────────────────────────────────────────
  # Build APK (Android)
  # ─────────────────────────────────────────────────────
  build-android:
    name: "🤖 Build Android APK"
    runs-on: ubuntu-latest
    needs: [analyze-test]
    if: github.ref == 'refs/heads/main'

    steps:
      - uses: actions/checkout@v4

      - name: Setup Java 17
        uses: actions/setup-java@v4
        with:
          java-version: "17"
          distribution: "temurin"

      - name: Setup Flutter
        uses: subosito/flutter-action@v2
        with:
          flutter-version: ${{ env.FLUTTER_VERSION }}
          channel: stable
          cache: true

      - name: Get dependencies
        run: flutter pub get

      - name: Generate code
        run: dart run build_runner build --delete-conflicting-outputs

      - name: Build APK (release)
        run: |
          flutter build apk --release \
            --dart-define=API_URL=${{ vars.MOBILE_API_URL }}

      - name: Upload APK artifact
        uses: actions/upload-artifact@v4
        with:
          name: terra-os-android-${{ github.sha }}
          path: apps/mobile/build/app/outputs/flutter-apk/app-release.apk
          retention-days: 30

  # ─────────────────────────────────────────────────────
  # Build iOS (optional — requires macOS runner)
  # ─────────────────────────────────────────────────────
  build-ios:
    name: "🍎 Build iOS (no-codesign)"
    runs-on: macos-latest
    needs: [analyze-test]
    if: github.ref == 'refs/heads/main'

    steps:
      - uses: actions/checkout@v4

      - name: Setup Flutter
        uses: subosito/flutter-action@v2
        with:
          flutter-version: ${{ env.FLUTTER_VERSION }}
          channel: stable
          cache: true

      - name: Get dependencies
        run: flutter pub get

      - name: Generate code
        run: dart run build_runner build --delete-conflicting-outputs

      - name: Build iOS (no-codesign)
        run: flutter build ios --release --no-codesign

      - name: Upload iOS artifact
        uses: actions/upload-artifact@v4
        with:
          name: terra-os-ios-${{ github.sha }}
          path: apps/mobile/build/ios/iphoneos/Runner.app
          retention-days: 30
```

---

## Podsumowanie implementacji — Priorytety

| # | Zadanie | Effort | Impact | Priority |
|---|---------|--------|--------|----------|
| 1 | Upgrade CI: dodaj ruff+black+mypy do `.github/workflows/ci.yml` | S | HIGH | 🔴 P0 |
| 2 | Stwórz `Dockerfile.api` i `Dockerfile.ui` | M | HIGH | 🔴 P0 |
| 3 | Stwórz `docker-compose.prod.yml` | M | HIGH | 🔴 P0 |
| 4 | Dodaj `prometheus-fastapi-instrumentator` do API | S | HIGH | 🟡 P1 |
| 5 | Stwórz `build.yml` + `deploy-staging.yml` | M | HIGH | 🟡 P1 |
| 6 | Setup Grafana + Prometheus stack | L | MEDIUM | 🟡 P1 |
| 7 | LangGraph pipeline: `services/pipeline/` | XL | HIGH | 🟡 P1 |
| 8 | Flutter app: `apps/mobile/` | XL | MEDIUM | 🟢 P2 |
| 9 | AlertManager + Loki setup | M | MEDIUM | 🟢 P2 |
| 10 | `deploy-prod.yml` z approval gate | M | HIGH | 🟢 P2 |

---

## Wymagane GitHub Secrets

```
# Deployment
STAGING_HOST          # IP lub hostname serwera staging
STAGING_USER          # SSH user
STAGING_SSH_KEY       # Private SSH key
PROD_HOST             # IP lub hostname serwera prod
PROD_USER             # SSH user  
PROD_SSH_KEY          # Private SSH key

# Notifications
SLACK_WEBHOOK_URL     # Slack incoming webhook

# Services
SENTRY_DSN            # Sentry project DSN
LANGCHAIN_API_KEY     # LangSmith tracing key
PAGERDUTY_KEY         # PagerDuty service key

# App config
GRAFANA_PASSWORD      # Grafana admin password
```

---

*Specyfikacja wygenerowana przez Agency Agents Senior Developer 💲 | Terra.OS Batch 2 | 2026-07-07*
