# Admin Web — production static container (PILOT-DEPLOYMENT-READINESS-001B).
#
# Multi-stage: node build → nginx static serve.
# No Vite dev/HMR, no source bind mounts, no `latest` base (pinned below).
#
# Build (from repo root):
#   docker build -f apps/admin-web/Dockerfile \
#     --build-arg RMP_VERSION=v0.11.0-pilot-control-plane \
#     --build-arg RMP_GIT_SHA=e130207 \
#     --build-arg RMP_BUILD_TIME=$(date -u +%Y-%m-%dT%H:%M:%SZ) \
#     -t rmp-admin-web:<sha> .

# ---------------------------------------------------------------------------
# Stage 1: build the static bundle
# ---------------------------------------------------------------------------
FROM node:22-alpine AS build

ARG RMP_VERSION
ARG RMP_GIT_SHA
ARG RMP_BUILD_TIME

ENV RMP_VERSION=${RMP_VERSION:-dev}
ENV RMP_GIT_SHA=${RMP_GIT_SHA:-unknown}
ENV RMP_BUILD_TIME=${RMP_BUILD_TIME:-unknown}

WORKDIR /app

# Install deps first (cache layer) — exact lockfile.
COPY apps/admin-web/package.json apps/admin-web/package-lock.json ./
RUN npm ci

# Build the production bundle.
COPY apps/admin-web/ ./
RUN npm run build

# Emit immutable build metadata for deployment verification.
COPY scripts/write-build-info.mjs /tmp/write-build-info.mjs
RUN node /tmp/write-build-info.mjs /app/dist

# ---------------------------------------------------------------------------
# Stage 2: static serve + SPA fallback + healthcheck
# ---------------------------------------------------------------------------
FROM nginx:1.27-alpine

# SPA fallback: any non-asset route → index.html. /healthz → 200 for probes.
COPY apps/admin-web/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 3000
