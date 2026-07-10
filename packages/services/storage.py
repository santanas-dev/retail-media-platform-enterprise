"""
Retail Media Platform — Creative Storage Service (S-017).

MinIO/S3-backed presigned URL upload flow.
Never trusts client-provided checksum or file size.
No presigned URLs or storage keys exposed outside upload-intent response.
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse

from minio import Minio
from minio.error import S3Error

from packages.security.config import get_security_config


def _now() -> datetime:
    return datetime.now(timezone.utc)


class StorageService:
    """MinIO client wrapper for creative asset presigned-URL upload."""

    def __init__(self) -> None:
        cfg = get_security_config()
        self._bucket = cfg.creative_storage_bucket
        self._ttl = cfg.creative_upload_url_ttl_seconds
        self._internal = Minio(
            cfg.minio_internal_endpoint,
            access_key=cfg.minio_access_key,
            secret_key=cfg.minio_secret_key,
            secure=False,  # pilot: HTTP; production: HTTPS
        )
        self._public_endpoint = cfg.minio_public_endpoint

    # ------------------------------------------------------------------
    # Bucket
    # ------------------------------------------------------------------

    def ensure_bucket(self) -> None:
        """Create the creative storage bucket if it does not exist.

        Idempotent — no-op if bucket already exists.
        Raises RuntimeError on connectivity/permission failure.
        """
        try:
            found = self._internal.bucket_exists(self._bucket)
            if not found:
                self._internal.make_bucket(self._bucket)
        except S3Error as exc:
            raise RuntimeError(
                f"MinIO bucket check failed for '{self._bucket}': {exc}"
            ) from exc

    # ------------------------------------------------------------------
    # Presigned upload URL
    # ------------------------------------------------------------------

    def _rewrite_to_public(self, url: str) -> str:
        """Replace the scheme+netloc of a presigned URL with the public endpoint.

        Uses urlparse/unparse — never does blind substring replacement.
        Preserves path, query, and signature exactly.
        """
        if not self._public_endpoint:
            return url
        cfg = get_security_config()
        internal = cfg.minio_internal_endpoint
        if not internal:
            return url
        parsed_internal = urlparse(f"http://{internal}" if "://" not in internal else internal)
        parsed_url = urlparse(url)
        # Only rewrite if scheme and netloc both match the internal endpoint
        if not (
            parsed_url.scheme == parsed_internal.scheme
            and parsed_url.netloc == parsed_internal.netloc
        ):
            return url
        # Parse public endpoint to extract scheme+netloc
        parsed_public = urlparse(
            self._public_endpoint
            if "://" in self._public_endpoint
            else f"http://{self._public_endpoint}"
        )
        rebuilt = parsed_url._replace(
            scheme=parsed_public.scheme,
            netloc=parsed_public.netloc,
        )
        return rebuilt.geturl()

    def generate_presigned_put(
        self,
        storage_key: str,
        content_type: str,
    ) -> tuple[str, datetime]:
        """Generate a presigned PUT URL for browser upload.

        Returns (url, expires_at).  URL uses the public endpoint so the
        browser can reach MinIO directly.  TTL from config.
        """
        url = self._internal.presigned_put_object(
            self._bucket,
            storage_key,
            expires=timedelta(seconds=self._ttl),
        )
        url = self._rewrite_to_public(url)
        expires_at = _now() + timedelta(seconds=self._ttl)
        return url, expires_at

    # ------------------------------------------------------------------
    # Object existence / size
    # ------------------------------------------------------------------

    def object_exists(self, storage_key: str) -> bool:
        """Check whether an object exists in the bucket."""
        try:
            self._internal.stat_object(self._bucket, storage_key)
            return True
        except S3Error:
            return False

    def get_object_size(self, storage_key: str) -> int | None:
        """Return object size in bytes, or None if not found."""
        try:
            stat = self._internal.stat_object(self._bucket, storage_key)
            return stat.size
        except S3Error:
            return None

    # ------------------------------------------------------------------
    # Streaming SHA-256
    # ------------------------------------------------------------------

    def compute_sha256(self, storage_key: str) -> str | None:
        """Compute SHA-256 hex digest of an object via streaming read.

        Reads the object in 128 KB chunks — never loads the full file
        into memory.  Returns lowercase hex string (64 chars) or None
        if the object does not exist.

        Never trusts client-provided checksum — always server-computed.
        """
        try:
            response = self._internal.get_object(self._bucket, storage_key)
        except S3Error:
            return None
        try:
            h = hashlib.sha256()
            while True:
                chunk = response.read(131_072)  # 128 KB
                if not chunk:
                    break
                h.update(chunk)
            return h.hexdigest()
        finally:
            response.close()
            response.release_conn()


# Singleton — created at app startup
_storage: StorageService | None = None


def get_storage_service() -> StorageService:
    """Return the singleton StorageService."""
    global _storage
    if _storage is None:
        _storage = StorageService()
    return _storage


def reset_storage_service() -> None:
    """Reset singleton — for tests."""
    global _storage
    _storage = None
