# Release Notes — v0.11.1-pilot-packaging (Prerelease)

> **Status: PRERELEASE** — source/packaging release. **НЕ deployment.**
> Подготовлено в PILOT-PACKAGING-RELEASE-001.

**Version/tag:** `v0.11.1-pilot-packaging`

**Release SHA (main):** `__MAIN_SHA__` (заполняется после merge; см. SCOPE D)

---

## Что это

Source/packaging release поверх R4 `v0.11.0-pilot-control-plane` (main `e130207`).
Объединяет три workstream'а читаемости к развёртыванию pilot:

- **PILOT-DEPLOYMENT-READINESS-001A** — target discovery + deployment design.
- **PILOT-DEPLOYMENT-READINESS-001B** — deployment packaging.
- **PILOT-DEPLOYMENT-READINESS-001C (+FU)** — quiesced backup + isolated restore drill.

R4 tag `v0.11.0-pilot-control-plane` **не изменён**.

## Что вошло

### 001B — deployment packaging

- Отдельный pilot compose (`infra/compose/docker-compose.pilot.yml`, 10 сервисов):
  без `build`/source-mount/`latest`; `restart: unless-stopped`; healthchecks;
  `service_healthy`/`service_completed_successfully`.
- Backend identity: `GET /version` на control-api, device-gateway,
  orchestrator-worker, pop-ingestor (env-injected, fail-closed 503 в pilot/prod,
  dev fallback `dev`/`unknown`).
- Production frontend containers: multi-stage node→nginx Dockerfiles для
  admin-web и advertiser-web, SPA fallback, `/healthz` + `/build-info.json`.
- Image-lock + валидаторы: `images.lock.example.json`, `validate-image-lock.py`
  (latest/empty-digest/mutable-tag/mixed-SHA/service-mismatch rejected),
  `validate-pilot-env.py` (minioadmin/слабые ключи/dev JWT/SEED_DEV_CREDENTIALS
  rejected), `build-images.sh` (clean-tree, OCI labels, digest+lock, no latest).

### 001C — quiesced backup + isolated restore drill

- `scripts/backup/quiesced_backup.py` — quiesced PostgreSQL+MinIO backup:
  **fail-closed** без доказанного maintenance/quiesce режима (production/pilot
  вызов без quiescence evidence отклоняется **до** создания backup).
- `scripts/backup/backup_manifest.py` — unified manifest (schema v1.0, SHA-256,
  row counts, checksums, Alembic head, consistency mode, encryption state, RPO,
  пообъектная классификация stateful-компонентов, запрет секретов при
  сериализации).
- `scripts/restore/isolated_restore.py` — isolated restore (safety guard
  source≠target, отказ при непустом target, manifest/checksum verify, alembic
  head check).
- `infra/compose/docker-compose.restore-drill.yml` — отдельный disposable контур
  (src/tgt postgres+minio, раздельные volumes/network/ports 15432/15433/19000/19001).
- `scripts/ci/backup-restore-drill.sh` — migrate+seed → backup → isolated restore
  → app-role NOBYPASSRLS → control-api → verify; cleanup по точному project name
  через `trap`; артефакты только во временной директории, не публикуются.

### Классификация stateful-компонентов

- **NATS/JetStream** — `excluded_replayable`. JetStream включён (`-js`), durable
  stream `RMP` + consumer `rmp-campaign-consumer` создаются идемпотентно
  (`NATS_AUTO_PROVISION=true`), но авторитетный источник истины — PostgreSQL
  `outbox_events` (пишется первым, публикуется с `Nats-Msg-Id=event_id` dedup).
  Полное восстановление через provisioning + outbox replay.
- **Redis** — `excluded_disposable` (cache).
- **PostgreSQL + MinIO** — `backup_full` (полный backup/restore).

### CI / gates

- Новые blocking-джобы в release-gate: `packaging` и `backup-restore-drill`.
- **Feature registry:** 58 total / 53 reachable / 5 blocked (`backup.restore`
  стал reachable после реального изолированного restore drill).

## Честные ограничения

- **Pilot deployment NOT PERFORMED.**
- **Production deployment NO-GO.**
- **Deployed SHA UNKNOWN/NOT TRACKED.**
- **Image registry/digest lock — `IMAGE-REGISTRY-OWNER-INPUT`:** утверждённый
  container registry отсутствует; real immutable images не опубликованы.
  `images.lock.example.json` содержит только `REPLACE_WITH_*` placeholders.
  Никакого утверждения о deployable image bundle без реальных digest.
- TLS/DNS/host/secrets/monitoring — owner inputs не закрыты.
- Реальный KSO environment отсутствует.
- License Layer 2 (signed `.lic` / view / upload) — blocked.
- Operator walkthrough для infra release — **N/A**.

## Deployment truth

> This release has not been deployed to production.
> Production deployed SHA remains UNKNOWN/NOT TRACKED.
> Pilot deployment NOT PERFORMED.
> Image bundle NOT BUILT (no approved registry).
