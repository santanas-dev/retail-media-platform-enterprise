# Pilot Deployment Readiness — 001A (Target Discovery + Deployment Design)

| **Created:** 2026-08-22 |
| **Task:** PILOT-DEPLOYMENT-READINESS-001A |
| **Status:** DESIGN (audit/docs only — no deploy, no server contact) |
| **Release baseline:** tag `v0.11.0-pilot-control-plane`, main SHA `e130207` |

> Этот документ — план и audit. Ни один шаг здесь **не выполнялся** против
> реального сервера. Deploy не производился. Production deployed SHA остаётся
> UNKNOWN/NOT TRACKED.

---

## 1. Verdict

**NEEDS OWNER INPUT.**

Код и конфигурация достаточны для начала упаковки (packaging), но целевой
pilot host, DNS/TLS и секреты отсутствуют — без них нельзя ни спроектировать
конкретный deploy manifest, ни выполнить preflight. Три обязательных
предусловия (owner inputs, restore drill, operator walkthrough) не выполнены.

Следующий конкретный шаг: **001B (deployment packaging + version endpoint +
image pinning)** — он не зависит от owner inputs и может быть выполнен сразу.

---

## 2. SCOPE A — Inventory существующего deployment

### 2.1 Файлы конфигурации

| Файл | Назначение |
|------|-----------|
| `infra/compose/docker-compose.phase1.yml` | Базовый стек (infra + app-сервисы). Dev-значения в env. |
| `infra/compose/docker-compose.observability.yml` | Prometheus + Grafana (профиль-оверлей). |
| `infra/compose/docker-compose.preview.yml` | LAN-preview override (не для pilot/prod). |
| `infra/compose/Dockerfile.service` | Единый shared Dockerfile для всех Python-сервисов (build-args). |
| `infra/compose/init-db.sql` | Создание `retail_media_app` (NOBYPASSRLS) при bootstrap БД. |
| `infra/compose/grant-app-role.py` | Grant table/sequence privileges после migrations+seed. |
| `scripts/backup/postgres_backup.py` | `pg_dump` custom-format + retention. |
| `scripts/restore/postgres_restore.py` | `pg_restore --clean --if-exists` + confirmation gate + check/dry-run. |
| `scripts/backup/minio_backup.py` | Full-bucket download + SHA-256 manifest. |
| `scripts/restore/minio_restore.py` | MinIO restore (см. runbook). |
| `infra/observability/prometheus.yml` | Scrape config (control-api:8000, device-gateway:8001). |
| `infra/observability/alerts.yml` | 8 alert rules (ServiceDown, DBUnhealthy, NATSUnhealthy, …). |
| `infra/observability/grafana/**` | RMP Overview dashboard + provisioning. |

### 2.2 Runtime services — включение в pilot

| Service | В pilot | Image/build | Зависимости | Persistent data | Health | Restart |
|---------|:------:|-------------|-------------|-----------------|--------|---------|
| **postgres** 16 | ✅ | `postgres:16-alpine` | — | `pg_data` (VOLUME) | `pg_isready` | НЕ задан |
| **redis** 7 | ✅ | `redis:7-alpine` | — | **нет** (disposable) | `redis-cli ping` | НЕ задан |
| **nats** 2 | ✅ | `nats:2-alpine` (JetStream) | — | `nats_jetstream` | `nats server check` | НЕ задан |
| **minio** | ✅ | `minio/minio:latest` ⚠️ | — | `minio_data` (VOLUME) | `/minio/health/live` | НЕ задан |
| **clickhouse** 24 | ❌ **исключён** | `clickhouse/clickhouse-server:24-alpine` | — | `ch_data` | (deferred) | НЕ задан |
| **control-api** | ✅ | `Dockerfile.service` (build) | postgres, redis | — | `/health/live`, `/health/ready`, `/metrics` | НЕ задан |
| **device-gateway** | ✅ | `Dockerfile.service` (build) | postgres, redis, nats | — | `/health/live` | НЕ задан |
| **orchestrator-worker** | ✅ | `Dockerfile.service` (build) | postgres, nats | — | `/health/live` (http.server) | НЕ задан |
| **pop-ingestor** | ⚠️ **спорно** | `Dockerfile.service` (build) | nats, clickhouse(неиспользуем) | — | `/health/live` | НЕ задан |
| **mock-adapter** | ⚠️ **исключить** | `Dockerfile.service` (build) | nats | — | `/health/live` | НЕ задан |
| **admin-web** | ✅ (но frontend-профиль) | `node:22-alpine` + volume mount ⚠️ | control-api | — | нет | НЕ задан |
| **advertiser-web** | ❌ **НЕ в compose** | — | control-api | — | — | — |
| **db-setup** (one-shot) | ✅ (профиль `setup`) | shares control-api image | postgres | — | — | one-shot |
| **prometheus** | ✅ (оверлей) | `prom/prometheus:v3.6.0` | — | `prometheus_data` | — | unless-stopped |
| **grafana** | ✅ (оверлей) | `grafana/grafana:11.8.1` | prometheus | `grafana_data` | — | unless-stopped |

### 2.3 Ключевые findings (gaps, влияющие на deploy)

1. **Нет image pinning.** Все app-сервисы — `build:` (no tag/digest). `minio/minio:latest`
   — плавающий тег. Нет ни одного `image: <digest>`. Это blocker для immutable identity
   (SCOPE C) → задача 001B.
2. **Нет version endpoint.** `/health/live` возвращает только `{status, service}`.
   `/metrics` имеет `rmp_service_info{service=…}` без tag/SHA. Приложение не отображает
   `v0.11.0-pilot-control-plane` / `e130207`. → 001B.
3. **Нет reverse proxy / TLS.** В репозитории нет nginx/traefik/caddy-конфигурации.
   ADR-001 упоминает reverse proxy как целевой слой, но файла нет. TLS termination —
   целиком owner input. → 001D.
4. **Нет restart policy** ни у одного runtime-сервиса в `phase1.yml` (только
   observability имеет `unless-stopped`). Для pilot нужен `restart: unless-stopped`
   на stateless-сервисах и явный policy для stateful. → 001B.
5. **pop-ingestor не использует ClickHouse** (skeleton, `"clickhouse": "not_configured"`),
   но `depends_on: clickhouse: service_healthy`. ClickHouse исключён из pilot → pop-ingestor
   либо исключить, либо убрать зависимость. → решение в 001E.
6. **advertiser-web отсутствует в compose.** Есть только admin-web (через `frontend`
   профиль + volume mount на host `dist/` — dev-паттерн, не production). Оба web —
   static-артефакты, требуют static-сервера/nginx в pilot. → 001B.
7. **Dev-credentials в compose.** `retail_media_owner_pass`, `minioadmin`, `dev-secret-…`,
   `JWT dev secret` зашиты в `phase1.yml`. Production config gate (S-030) это отклоняет,
   но отдельного production compose-файла нет. → 001B (env-file + secrets).
8. **Seed dev-credentials** (`advertiser-dev-only` / `break-glass-dev-only`) гейтятся
   `SEED_DEV_CREDENTIALS`; в production config gate запрещены. Pilot требует реальные
   admin/advertiser пароли через env-provided hash. → owner input + 001E.

### 2.4 Ports / networking (ADR-001)

| Service | Port | Exposure |
|---------|------|----------|
| postgres | 5432 | internal only |
| redis | 6379 | internal only |
| nats | 4222 (client), 8222 (mon) | internal only |
| minio | 9000 (API), 9001 (console) | API internal; public endpoint через proxy |
| control-api | 8000 | internal/VPN |
| device-gateway | 8001 | corporate network |
| pop-ingestor | 8002 | internal |
| orchestrator-worker | 8003 | internal |
| mock-adapter | 8100 | internal (исключить) |
| admin-web | 3000 | internal/VPN |
| advertiser-web | 3001 | VPN/public |
| prometheus | 9090 | internal |
| grafana | 3002 | internal |

---

## 3. SCOPE B — Обязательные owner inputs

Точный список. **Ничего не выдумано** — каждое поле пустое до получения от владельца.

### Хост и платформа
- [ ] Pilot host IP / hostname: `________`
- [ ] OS + версия (Ubuntu/Debian/Rocky…): `________`
- [ ] CPU / RAM / storage: `________`
- [ ] Docker Engine + Docker Compose версии: `________`

### Сеть и DNS
- [ ] DNS-имена для admin-web / advertiser-web / control-api / device-gateway: `________`
- [ ] TLS termination: где (cloud LB / nginx / нет)? Сертификаты: `________`
- [ ] Firewall/VPN правила: какие порты открыты, кому доступен control-api: `________`
- [ ] Outbound (AD/LDAPS, SMTP, внешние API): `________`

### Внешние зависимости
- [ ] SMTP (для приглашений/сброса пароля) — или подтвердить «не нужен»: `________`
- [ ] AD/LDAPS (реальный AD или только local credentials в pilot): `________`
- [ ] MinIO — внутренний или внешний S3-совместимый: `________`

### Безопасность и секреты
- [ ] Способ хранения секретов (docker secrets / .env / vault / host env): `________`
- [ ] Источник значений: JWT_SECRET, MANIFEST_SIGNING_KEY, METRICS_AUTH_TOKEN,
      MINIO keys, DATABASE_URL, admin/advertiser seed passwords: `________`

### Данные и восстановление
- [ ] Backup destination (локальный диск / NAS / S3): `________`
- [ ] Мониторинг destination (локальный Prometheus/Grafana или внешний): `________`

### Эксплуатация
- [ ] Maintenance window (для миграций и deploy): `________`
- [ ] Ответственный оператор (кто делает walkthrough + ведёт pilot): `________`

### КСО
- [ ] Доступно ли настоящее КСО (реальный player/hardware) на pilot? Да/Нет: `________`
  (если Нет — KSO-ENV-001 остаётся отдельной трассой; pilot = control-plane only.)

---

## 4. SCOPE C — Immutable deployment identity (дизайн)

Целевое состояние (реализуется в 001B):

1. **Image pinning.** Каждый образ помечается тегом `v0.11.0-pilot-control-plane`
   и `e130207` (short) при сборке. Запрещены `latest` и плавающие теги. Deploy manifest
   содержит **image digests** (`image@sha256:…`), не только теги.
2. **Version endpoint.** Добавить `GET /health/version` (или расширить `/health/live`)
   возвращающий `{tag, sha, service, build_time}` из env/build-args
   (`RMP_VERSION`, `RMP_SHA`, `RMP_BUILD_TIME`), проброшенных в Dockerfile.
3. **UI отображает версию.** admin-web/advertiser-web показывают tag/SHA в футере/настройках
   (build-time inject через `build-marker.txt` — механизм уже есть в CI, строка 365-372
   phase1-ci.yml).
4. **Deploy record.** После каждого реального deploy создаётся каноническая запись
   (файл в `docs/deployments/` или append в PROJECT_STATE):
   ```
   environment, host, deployed SHA, image digests (на сервис),
   migration head, timestamp, operator
   ```
5. **Не записывать SHA до proof.** Production/pilot deployed SHA пишется **только** после
   реального `docker inspect`/`curl /health/version` proof на живом хосте. До этого —
   UNKNOWN/NOT TRACKED.

---

## 5. SCOPE D — Data safety (обязательный порядок)

Порядок, который **обязателен** перед и во время pilot deploy (001C + 001E):

1. **PostgreSQL backup** (`scripts/backup/postgres_backup.py`) — custom-format dump.
2. **MinIO backup/versioning proof** (`scripts/backup/minio_backup.py`) — full bucket +
   SHA-256 manifest.
3. **Redis** — disposable (кэш/сессии/rate-limit/short locks). Не бэкапится. После
   сброса сервисы пересоздают кэш; refresh-сессии потеряются (пользователи
   перелогинятся) — допустимо для pilot.
4. **Alembic current/head** — `alembic current` и `alembic heads` = `034` до миграции.
5. **Restore drill** на отдельной БД/хосте (`scripts/restore/postgres_restore.py`
   + `minio_restore.py`) — обязателен, иначе `backup.restore` остаётся blocked.
6. **Migration rehearsal** 028→034 на копии перед prod/pilot.
7. **Rollback:**
   - application rollback → R3 binary (работает на schema 034);
   - schema downgrade 034→028 — **lossy** (удалит commerce/license данные) → не primary;
   - **restore-from-backup — основной DB rollback.**

> `backup.restore` НЕ переводится в reachable без реального restore test (drill).

---

## 6. SCOPE E — Pilot topology / runbook (draft)

### 6.1 Topology (один Docker host)

```
[reverse proxy / TLS terminator (owner-provided)]
        │
        ├── admin-web (static)      :3000
        ├── advertiser-web (static) :3001
        ├── control-api             :8000  (internal)
        └── device-gateway          :8001  (corporate)
                │
        ┌───────┴────────────────────────────┐
        │  postgres:5432  redis:6379          │
        │  nats:4222      minio:9000          │
        │  orchestrator-worker (no port)      │
        │  [prometheus:9090  grafana:3002]    │
        └─────────────────────────────────────┘
   (clickhouse / pop-ingestor / mock-adapter — ИСКЛЮЧЕНЫ из pilot)
```

### 6.2 Runbook steps (draft)

1. **Preflight** — host OS/Docker версии, дисковое место, DNS, firewall, TLS certs.
2. **Secrets installation** — env-file/secrets для JWT, MANIFEST, METRICS, MINIO, DB,
   seed passwords. Валидация через production config gate (`ENVIRONMENT=production`).
3. **Image acquisition/build** — build из `e130207` → тег `v0.11.0-pilot-control-plane`
   + push → pin digests в manifest.
4. **Backup** — PG + MinIO (см. §5).
5. **Migration** — `alembic upgrade head` → verify `034`.
6. **Service startup order** — postgres → redis/nats/minio → control-api →
   device-gateway → orchestrator-worker → web static → observability.
7. **Health verification** — `/health/live` + `/health/ready` на каждом.
8. **UI login** — admin-web + advertiser-web реальными учётками.
9. **Smoke subset** — P0 UI-smoke против живого хоста (не CI).
10. **Rollback trigger** — любой красный health/readiness или smoke → стоп.
11. **Rollback steps** — application → R3; DB → restore-from-backup.
12. **Evidence collection** — digests, health JSON, smoke output, версия endpoint.
13. **Shutdown/recovery** — порядок остановки, повторный запуск с теми же volumes.

### 6.3 Pilot acceptance (после будущего deploy)

- exact tag/SHA/digests зафиксированы;
- migration head = `034`;
- healthchecks green на всех включённых сервисах;
- admin + advertiser UI доступны;
- smoke green против pilot host;
- backup + restore proof (drill) выполнены;
- logs/metrics доступны (Prometheus/Grafana);
- operator walkthrough человеком — OK (не агент);
- **no production-ready claim** (явно).

---

## 7. SCOPE F — Gaps and slicing

| Task | Содержание | Блокируется |
|------|-----------|-------------|
| **001B** | Packaging: version endpoint, image pinning (tag+digest), restart policy, advertiser-web/admin-web static build, prod env-file шаблон, deploy-record шаблон | ничем (можно сразу) |
| **001C** | Backup + restore drill на отдельной БД/хосте (PG + MinIO) | target host/DB (owner) |
| **001D** | Pilot host preflight (OS, Docker, DNS, firewall, TLS) | owner inputs |
| **001E** | Controlled pilot deployment (по runbook §6) | 001B+001C+001D |
| **KSO-ENV-001** | Только с реальным КСО (player/hardware) | owner: доступно ли КСО |

---

## 8. SCOPE G — Canon (обновляется в PROJECT_STATE)

См. коммит canon в PROJECT_STATE.md:
- R4 software release complete ✅;
- Pilot deployment NOT PERFORMED;
- Production NO-GO;
- deployed SHA UNKNOWN/NOT TRACKED;
- blockers: owner inputs (host/DNS/TLS/secrets), restore drill, operator walkthrough;
- owner inputs list (§3);
- Next → **001B** (packaging, не зависит от owner) затем owner-input blocker.

Feature statuses НЕ меняются. Guard = 0, CI green, tree clean.
