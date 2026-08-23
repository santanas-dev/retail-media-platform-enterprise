# Pilot Deployment Packaging — 001B (Production-like + Immutable Identity)

| **Created:** 2026-08-22 |
| **Task:** PILOT-DEPLOYMENT-READINESS-001B |
| **Status:** IMPLEMENTED (packaging only — NO deploy, NO tag, NO main merge) |
| **Release baseline:** tag `v0.11.0-pilot-control-plane` (main SHA `e130207`) — **immutable, NOT reused/moved** |

> 001B подготавливает deployable packaging. Он **не выполняет** deploy и **не
> создаёт** новый release/tag. Любые 001B-изменения находятся после R4 и
> потребуют отдельного patch release после 001C (restore drill) перед 001D/001E.

## 1. Что упаковано

### Pilot compose (`infra/compose/docker-compose.pilot.yml`)

Отдельный production-like overlay, НЕ ломающий `phase1.yml` (dev).

| Service | Включён | Тип |
|---------|:------:|-----|
| postgres 16.4-alpine | ✅ | infra (persistent `pg_data`) |
| redis 7.4-alpine | ✅ | infra (disposable) |
| minio (pinned RELEASE tag) | ✅ | infra (persistent `minio_data`) |
| nats 2.10-alpine | ✅ | infra (persistent `nats_jetstream`) |
| db-migrate (one-shot) | ✅ | migration+seed (owner credential) |
| control-api | ✅ | runtime |
| device-gateway | ✅ | runtime |
| orchestrator-worker | ✅ | runtime |
| admin-web | ✅ | static frontend |
| advertiser-web | ✅ | static frontend |

**Исключены:** clickhouse (deferred), pop-ingestor (не использует ClickHouse,
skeleton; нет доказанной pilot-функции), mock-adapter (dev-only).

### Свойства pilot compose (проверены тестами)

- нет `build:` — только `image:` (иммутабельные refs через `${VAR}`);
- нет source bind mounts (`.dockerignore` + тест);
- нет `latest`/mutable tags;
- `restart: unless-stopped` на runtime; migration job — `restart: "no"`;
- healthchecks на всех;
- `depends_on` через `service_healthy` / `service_completed_successfully`;
- app runtime под `retail_media_app` (NOBYPASSRLS); migration под owner;
- `SEED_DEV_CREDENTIALS=false`, `LICENSE_DEV_INGEST_ENABLED=false`.

## 2. Immutable image references

- Lock manifest: `infra/deploy/images.lock.example.json` (service, repository,
  version, git_sha, image_digest, build_timestamp, source_tag).
- Validator: `scripts/deploy/validate-image-lock.py` — блокирует latest,
  пустой digest, mutable tag без digest, несоответствие service list,
  смешение git SHA, R4/e130207 identity для post-R4 кода.
- `.example` + генератор после реальной сборки/push (`build-images.sh --push`).
- **Никакие digest не выдуманы** — example содержит только `REPLACE_WITH_*`.

## 3. Version identity

- Backend: `GET /version` на control-api, device-gateway, orchestrator-worker,
  pop-ingestor — возвращает `{service, version, git_sha, build_time,
  schema_head, environment}`.
- Значения инжектятся env (`RMP_VERSION`, `RMP_GIT_SHA`, `RMP_BUILD_TIME`,
  `RMP_SCHEMA_HEAD`) через `packages/version.py`; runtime не вызывает git и не
  читает рабочую директорию; не возвращает secrets/host paths/env dump.
- **Fail-closed:** в pilot/production/staging отсутствие RMP_VERSION/GIT_SHA/
  BUILD_TIME → 503 (RuntimeError). Dev/test → честный fallback `dev`/`unknown`.
- Frontend: `build-info.json` в `dist/` (через `scripts/write-build-info.mjs`),
  раздаётся nginx по `/build-info.json` для deployment verification.

## 4. Secrets / config

- `infra/deploy/.env.pilot.example` — только пример, без реальных значений.
- `scripts/deploy/validate-pilot-env.py` — отвергает: minioadmin,
  retail_media_owner_pass, dev JWT/manifest ключи, SEED_DEV_CREDENTIALS=true,
  LICENSE_DEV_INGEST_ENABLED=true, пустые/короткие/placeholder секреты,
  localhost DB URL, CORS localhost/wildcard.

## 5. Build (reproducible)

- `scripts/deploy/build-images.sh` — принимает version + git SHA, требует
  clean tree, собирает все app images, OCI labels (revision/version/source/
  created), выводит image IDs; `--push` → digest + lock manifest. Без явного
  `--push`/credentials ничего не пушит. Нет `latest`.

## 6. CI / verification

- CI job `packaging` (в `release-gate`): compose config, lock validator,
  env validator, frontend production images (build + healthz + build-info.json
  + SPA fallback), version/packaging tests.
- 41 новых тестов: `tests/test_version_identity.py`,
  `tests/test_pilot_packaging.py`.

## 7. Migration / release truth

- R4 `e130207` **неизменен** — тег не создавался, не перемещался.
- 001B имеет новый substantive SHA (см. PROJECT_STATE).
- Pilot deploy потребует нового patch release после 001C.
- Deployed SHA = UNKNOWN/NOT TRACKED. Production = NO-GO.

## 8. Remaining owner inputs / next

- Owner inputs (001A) всё ещё открыты: host/IP, DNS, TLS, firewall, SMTP/AD,
  backup/monitoring destination, secret storage, оператор, реальное КСО.
- Next → **PILOT-DEPLOYMENT-READINESS-001C** (restore drill).
- После 001C — отдельный packaging patch release до 001D/001E.
- `backup.restore` остаётся blocked (без реального restore drill).
