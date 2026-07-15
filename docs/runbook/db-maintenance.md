# Database Maintenance Runbook

Scheduled and on-demand maintenance operations for PostgreSQL tables.

## Delivery Manifests Cleanup (S-068)

Delivery manifests accumulate per-device over time. Only the latest
manifest per device is actively polled; older versions are historical.

### Retention Script

`scripts/maintenance/cleanup_delivery_manifests.py`

```bash
# Dry-run (safe, no deletes)
DATABASE_URL=postgresql+asyncpg://... \
RUN_MAINTENANCE=1 \
python scripts/maintenance/cleanup_delivery_manifests.py

# Actual delete
DRY_RUN=0 RUN_MAINTENANCE=1 \
MANIFEST_RETENTION_COUNT=5 \
MANIFEST_RETENTION_DAYS=90 \
DATABASE_URL=postgresql+asyncpg://... \
python scripts/maintenance/cleanup_delivery_manifests.py
```

**Safety gates:**
- `DRY_RUN=1` by default — previews candidates, deletes nothing
- `RUN_MAINTENANCE=1` required — script refuses to run otherwise
- Never deletes the latest manifest per device
- Only targets `status='generated'` manifests older than retention threshold
- Batched in 10 000-row chunks to avoid long-running transactions

**Recommended schedule:** weekly, during low-traffic windows.

## PoP Events Retention (S-068)

`pop_events_raw` stores every proof-of-playback event. Without a retention
strategy this table grows unboundedly, degrading query performance.

### Current State
No automatic retention is active. Manual archival/deletion is the
recommended approach until ClickHouse migration.

### Retention Policy
- **Keep:** last 90 days of events by default
- **Archive:** events older than 90 days should be exported (CSV/Parquet)
  to object storage before deletion
- **Billing impact:** PoP data is needed for billing reconciliation —
  ensure archived data is accessible before deleting

### Future Partitioning (planned, not implemented)
When/if PostgreSQL remains the PoP store:
```sql
-- Partition by rendered_at range (monthly)
CREATE TABLE pop_events_raw_partitioned (
    LIKE pop_events_raw INCLUDING ALL
) PARTITION BY RANGE (rendered_at);

CREATE TABLE pop_events_raw_2026_07
    PARTITION OF pop_events_raw_partitioned
    FOR VALUES FROM ('2026-07-01') TO ('2026-08-01');
```

Use `CREATE INDEX CONCURRENTLY` on large tables to avoid locking.

## Indexes

### delivery_manifests lookup index (S-068)

Migration `014_delivery_manifests_lookup_index.py` adds:
```
ix_delivery_manifests_device_status_generated
ON delivery_manifests (physical_device_id, status, generated_at)
```

This index directly supports the fast ETag manifest lookup introduced in
S-067 (`get_latest_manifest_metadata`), reducing the query from a
sequential scan to an index-only scan.

### Adding indexes to large tables
For production tables with existing data, use `CONCURRENTLY`:
```sql
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_name
    ON table_name (col1, col2);
```
This avoids locking the table during index creation.

## DB Pool Configuration (S-068)

Connection pool is configurable via environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `DB_POOL_SIZE` | 5 | Maximum number of persistent connections |
| `DB_MAX_OVERFLOW` | 10 | Additional connections beyond pool_size |
| `DB_POOL_TIMEOUT` | 30 | Seconds to wait for a connection |
| `DB_POOL_RECYCLE_SECONDS` | 1800 | Connection recycle interval |

**Production recommendation for 40K-device fleet:**
```
DB_POOL_SIZE=20
DB_MAX_OVERFLOW=30
DB_POOL_TIMEOUT=30
DB_POOL_RECYCLE_SECONDS=1800
```

These values provide ~50 concurrent connections at peak, sufficient for
~1333 req/sec manifest polling with S-067 ETag fast path.
