# MinIO Backup / Restore Runbook — Retail Media Platform Enterprise

| **Created:** 2026-07-13 |
| **S-049** — MinIO object storage backup/restore drill |
| **Status:** pilot-ready |

## 1. Overview

MinIO stores creative media objects (images, videos) uploaded by advertisers. Without
object storage backups, a PostgreSQL restore leaves campaigns referencing media that
no longer exists — broken creatives, missing PoP proof-of-play media.

This runbook covers **full-bucket backup and restore** using Python MinIO SDK.
No external tools (`mc`, `rclone`) required at the script level.

## 2. RPO / RTO

| Метрика | Pilot Target | Production Target |
|---------|-------------|-------------------|
| **RPO** | 24 часа (aligns with PostgreSQL backup) | 1 час |
| **RTO** | 1 час | 30 мин |

## 3. Backup

### 3.1 Manual backup

```bash
cd /opt/retail-media-platform

MINIO_ENDPOINT=localhost:9000 \
MINIO_ACCESS_KEY=... \
MINIO_SECRET_KEY=*** \
MINIO_BUCKET=retail-media-creatives \
BACKUP_DIR=/backups/minio \
KEEP_LAST=7 \
python scripts/backup/minio_backup.py
```

### 3.2 Via cron (daily, 04:00 UTC — after PostgreSQL backup at 03:00)

```cron
0 4 * * * cd /opt/retail-media-platform && \
  MINIO_ENDPOINT=minio:9000 \
  MINIO_ACCESS_KEY=... \
  MINIO_SECRET_KEY=... \
  MINIO_BUCKET=retail-media-creatives \
  BACKUP_DIR=/backups/minio \
  KEEP_LAST=7 \
  /usr/bin/python3 scripts/backup/minio_backup.py >> /var/log/rmp-minio-backup.log 2>&1
```

### 3.3 Parameters

| Переменная | Назначение | Default |
|------------|-----------|---------|
| `MINIO_ENDPOINT` | MinIO host:port | **обязательна** |
| `MINIO_ACCESS_KEY` | Access key | **обязательна** |
| `MINIO_SECRET_KEY` | Secret key | **обязательна** |
| `MINIO_BUCKET` | Source bucket name | **обязательна** |
| `BACKUP_DIR` | Directory for backups | `./backups/minio` |
| `KEEP_LAST` | Keep N most recent backups | без ограничения |
| `KEEP_OLDER_THAN_DAYS` | Remove backups older than D days | без ограничения |

### 3.4 Backup directory structure

```
/backups/minio/20260113T040000Z/
├── manifest.json
└── data/
    ├── org-uuid-1/asset-uuid-1/banner.png
    ├── org-uuid-2/asset-uuid-2/video.mp4
    └── ...
```

### 3.5 Manifest format

```json
{
  "bucket": "retail-media-creatives",
  "generated_at": "2026-01-13T04:00:00+00:00",
  "backup_timestamp": "20260113T040000Z",
  "object_count": 1432,
  "total_size_bytes": 524288000,
  "objects": [
    {
      "key": "org-uuid-1/asset-uuid-1/banner.png",
      "size": 245760,
      "sha256": "a1b2c3d4e5f6...",
      "last_modified": "2026-01-12T10:30:00+00:00",
      "etag": "abc123..."
    }
  ]
}
```

### 3.6 Security

- Secret key and access key are **never printed** — redacted to `mi***in` in summary
- Backup files stored with default permissions of the parent process
- No object content inspected or logged — binary-safe streaming download

## 4. Restore

### 4.1 Check mode — validate backup integrity

```bash
python scripts/restore/minio_restore.py /backups/minio/20260113T040000Z --check
```

Verifies:
- `manifest.json` exists and is valid JSON
- All `objects[]` entries have corresponding `data/` files
- All SHA-256 checksums in manifest match actual file content

Output: `=== Check Mode: VALID ===` or `=== Check Mode: INVALID ===`.

### 4.2 Dry-run — preview without writing

```bash
MINIO_ENDPOINT=localhost:9000 \
MINIO_ACCESS_KEY=... \
MINIO_SECRET_KEY=*** \
MINIO_BUCKET=retail-media-creatives \
python scripts/restore/minio_restore.py /backups/minio/20260113T040000Z --dry-run --verbose
```

Shows what would be uploaded/skipped. No writes to MinIO.

### 4.3 Restore — execute

```bash
MINIO_ENDPOINT=localhost:9000 \
MINIO_ACCESS_KEY=... \
MINIO_SECRET_KEY=*** \
MINIO_BUCKET=retail-media-creatives \
REQUIRE_RESTORE_CONFIRMATION=yes \
python scripts/restore/minio_restore.py /backups/minio/20260113T040000Z
```

### 4.4 Restore to a different bucket (drill target)

```bash
MINIO_ENDPOINT=localhost:9000 \
MINIO_ACCESS_KEY=... \
MINIO_SECRET_KEY=*** \
TARGET_MINIO_BUCKET=rmp-restore-target \
REQUIRE_RESTORE_CONFIRMATION=yes \
python scripts/restore/minio_restore.py /backups/minio/20260113T040000Z
```

### 4.5 Options

| Flag | Effect |
|------|--------|
| `--check` | Validate only, no restore |
| `--dry-run` | Simulate, print plan, no writes |
| `--overwrite` | Overwrite existing objects (default: skip) |
| `--verbose` | Per-object progress output |

### 4.6 Safety gates

- **`REQUIRE_RESTORE_CONFIRMATION=yes`** — mandatory; without it the script exits with error
- **Default: skip existing objects** — no accidental overwrite without `--overwrite`
- **Post-restore verification** — every restored object is re-read from MinIO and SHA-256 verified against manifest
- **Local integrity check** — before uploading, the local file's SHA-256 is verified against manifest

## 5. Restore drill procedure

Выполняется ежемесячно или после значительных изменений схемы хранения.

### 5.1 Automated (opt-in test)

```bash
cd /opt/retail-media-platform

RUN_MINIO_INTEGRATION_TESTS=1 \
python -m pytest tests/integration/test_minio_backup_restore.py -v
```

Tests upload → backup → restore → verify in isolated test buckets.

### 5.2 Manual drill

1. Create a backup from production MinIO: `scripts/backup/minio_backup.py`
2. Validate backup: `scripts/restore/minio_restore.py ... --check`
3. Restore to a separate test bucket: `TARGET_MINIO_BUCKET=rmp-drill-target REQUIRE_RESTORE_CONFIRMATION=yes scripts/restore/minio_restore.py ...`
4. Verify: object count, SHA-256 spot-checks on test bucket
5. Document result in drill journal
6. Clean up: remove `rmp-drill-target` bucket

## 6. Full disaster recovery order

При полном восстановлении после сбоя:

1. **Restore PostgreSQL** (см. `backup-restore-dr.md`)
2. **Restore MinIO objects** (этот runbook)
3. **Run consistency checks:**
   ```sql
   -- Creatives with missing MinIO objects
   SELECT ca.id, ca.storage_key
   FROM creative_assets ca
   WHERE ca.status = 'ready'
   ORDER BY ca.created_at;
   ```
   Spot-verify SHA-256 of a sample of ready assets against MinIO.
4. **Restart services** — control-api, device-gateway, orchestrator-worker
5. **Verify health:** `curl http://localhost:8000/health/ready`

## 7. Known limitations and deferred

| Элемент | Статус |
|---------|--------|
| Offsite encrypted backup | Deferred — local backup only |
| Lifecycle / retention policies | Deferred — manual KEEP_LAST |
| Object lock (immutable backups) | Deferred |
| Multi-site replication (active-passive) | Deferred |
| Scheduled cron backup | Deferred — script ready, deployment needed |
| Backup monitoring / alerting | Deferred — integration with Prometheus AlertManager |
| Incremental backup (changed objects only) | Deferred — always full backup |
| Large-object parallel download | Deferred — sequential download only |

## 8. References

- Скрипты: `scripts/backup/minio_backup.py`, `scripts/restore/minio_restore.py`
- Интеграционный тест: `tests/integration/test_minio_backup_restore.py`
- PostgreSQL backup runbook: `docs/runbook/backup-restore-dr.md`
- Media upload runbook: `docs/runbook/media-upload.md`
- Production gaps: `docs/product/production-gaps-triage.md`
- Стабилизационный трекер: `docs/architecture/stabilization-tracker.md`
