# Media Upload Runbook — Retail Media Platform Enterprise

| **Created:** 2026-07-10 |
| **S-017** — Creative Media Upload via Presigned URL (MinIO/S3) |
| **Status:** backend complete, frontend admin-web upload UI shipped |

## Overview

Creative asset upload uses a **presigned-URL** flow backed by MinIO (S3-compatible).

**Flow:**
1. Frontend calls `POST /creative-assets/{id}/upload-intent` — backend generates an upload session + presigned PUT URL
2. Frontend PUTs the file directly to the presigned URL (no backend pass-through)
3. Frontend calls `POST /creative-assets/{id}/complete-upload` — backend verifies the object exists in MinIO, computes SHA-256 server-side, and transitions the asset from `metadata_only` to `ready`

**Never trusted:**
- Client-provided `sha256_checksum` — always ignored; server computes from MinIO object
- Client-told `file_size_bytes` — server reads actual object size from MinIO
- `e3b0c442...` empty-object checksum — rejected by delivery checksum gate

**Security:**
- Presigned URL uses the upload session's TTL (default 5 minutes)
- `storage_bucket` and `storage_key` are never exposed in normal API responses
- Cross-org upload blocked via advertiser scope checks
- Upload session validates: belongs to asset, not expired, not already completed
- Production rejects `minioadmin/minioadmin` credentials

## Environment Variables

| Variable | Dev Default | Purpose |
|----------|------------|---------|
| `MINIO_INTERNAL_ENDPOINT` | `minio:9000` (compose) | MinIO endpoint for backend SDK |
| `MINIO_PUBLIC_ENDPOINT` | `localhost:9000` (compose) | URL host:port for presigned URLs seen by browser |
| `MINIO_ACCESS_KEY` | `minioadmin` (dev only) | MinIO access key |
| `MINIO_SECRET_KEY` | `minioadmin` (dev only) | MinIO secret key |
| `CREATIVE_STORAGE_BUCKET` | `retail-media-creatives` | S3 bucket for creative files |
| `CREATIVE_MAX_FILE_SIZE_BYTES` | `10485760` (10 MB) | Max upload size |
| `CREATIVE_ALLOWED_MIME_TYPES` | `image/png,image/jpeg,image/webp,image/gif,video/mp4` | Allowed content types |
| `CREATIVE_UPLOAD_URL_TTL_SECONDS` | `300` (5 min) | Presigned URL lifetime |
| `CREATIVE_AUTO_APPROVE_UPLOADS` | `true` (dev) | Auto-approve moderation on complete-upload |

## API Endpoints

### POST /api/v1/identity/creative-assets/{asset_id}/upload-intent

**Request:**
```json
{
  "filename": "hero-banner.png",
  "content_type": "image/png",
  "content_length": 245760
}
```

**Response (200):**
```json
{
  "upload_id": "uuid",
  "upload_url": "http://localhost:9000/retail-media-creatives/org-id/asset-id/hero-banner.png?X-Amz-...",
  "method": "PUT",
  "headers": {"Content-Type": "image/png"},
  "expires_at": "2026-07-10T12:05:00Z"
}
```

**Errors:** 404 (asset not found), 409 (already uploaded), 422 (unsupported type / too large), 403 (cross-org)

### PUT {upload_url}

Direct browser-to-MinIO upload. Use the exact `upload_url` from the intent response.
- **Do NOT send `Authorization` header** — the URL is self-signing
- Send `Content-Type` matching the intent
- File body as raw bytes

### POST /api/v1/identity/creative-assets/{asset_id}/complete-upload

**Request:**
```json
{
  "upload_id": "uuid-from-intent"
}
```

**Response (200):**
```json
{
  "asset_id": "uuid",
  "sha256_checksum": "a1b2c3...",
  "file_size_bytes": 245760,
  "status": "ready",
  "moderation_status": "approved"
}
```

**Errors:** 404 (session / object not found), 409 (already completed), 410 (expired), 422 (size mismatch)

## Storage Key Format

```
{advertiser_organization_id}/{asset_id}/{original_filename}
```

Example: `00000000-0000-0000-0000-000000000200/abc123def/hero-banner.png`

Per-org isolation via key prefix. No flat namespace.

## Approval Gate

After upload, a creative asset becomes eligible for campaign approval only when ALL of:

1. `status == "ready"`
2. `moderation_status == "approved"`
3. `file_size_bytes > 0`
4. `storage_key` is non-empty
5. `sha256_checksum` is a valid 64-char hex (not `e3b0c442...`)

`metadata_only` assets block approval with a clear message.

## Frontend Upload UI

Located in `apps/admin-web/src/pages/CampaignDetailPage.tsx` — Creatives tab.

**Flow states:** `idle → requesting_url → uploading → finalizing → done/error`

- Hidden `<input type="file">` accepts: `.png, .jpg, .jpeg, .webp, .gif, .mp4`
- "Загрузить файл" button appears for each `metadata_only` asset
- Progress bar shows upload percentage
- Error block with "Сбросить" button on failure
- Storage fields never rendered in UI

## Testing

### Unit tests
```bash
cd tests && python -m pytest test_storage_service.py test_phase3_security.py -v
```

### Behavioral tests (requires PostgreSQL)
```bash
cd tests/behavioral && RUN_BEHAVIORAL_TESTS=1 python -m pytest test_creative_assets.py -v
```

### Admin-web tests
```bash
cd apps/admin-web && npx vitest run
```

### Integration test (requires MinIO + PostgreSQL)
```bash
RUN_MINIO_INTEGRATION_TESTS=1 python -m pytest tests/integration/test_minio_upload.py -v
```

Requires:
- MinIO running at `MINIO_INTERNAL_ENDPOINT`
- PostgreSQL with migrations + seed
- `MINIO_ACCESS_KEY` / `MINIO_SECRET_KEY` set
- `CREATIVE_STORAGE_BUCKET` exists (test auto-creates if missing)

Skips silently without `RUN_MINIO_INTEGRATION_TESTS=1`.

## Pilot Auto-Approve Rule

When `CREATIVE_AUTO_APPROVE_UPLOADS=true` (dev default), successful complete-upload automatically sets `moderation_status = "approved"`. In production, set to `false` for manual moderation workflow.

## Deferred

The following capabilities are intentionally deferred:
- **Antivirus / malware scanning** — no file scanning before acceptance
- **Manual moderation workflow** — pilot uses auto-approve; production needs review queue, reject/reupload flow
- **Image/video transcoding and renditions** — original file stored as-is; no thumbnails, web-optimized variants, or adaptive bitrate versions
- **CDN / edge caching** — direct MinIO access only; no CDN distribution
- **Orphan object cleanup** — uploaded objects with no matching `complete-upload` call are not automatically garbage-collected
- **Large multipart upload** — single PUT only; files must fit in memory/network buffer (~10 MB pilot limit)

## Rollback

To revert creative upload (code-only, no schema downgrade needed):

```bash
git revert <s-017-commits>
```

To remove upload session table:
```bash
alembic downgrade -1  # drops creative_upload_sessions (lossy)
```

MinIO objects persist after downgrade — manual cleanup via `mc rm` if needed.
