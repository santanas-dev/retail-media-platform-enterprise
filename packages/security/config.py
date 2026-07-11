"""
Retail Media Platform — Auth Security Configuration.

Phase 3.2b: Environment-based settings for auth, no hardcoded production secrets.
"""

import os
from dataclasses import dataclass, field


def _bool_env(name: str, default: bool = False) -> bool:
    val = os.environ.get(name, "").lower()
    if val in ("1", "true", "yes"):
        return True
    if val in ("0", "false", "no"):
        return False
    return default


def _is_dev() -> bool:
    """Heuristic: dev environment if common dev indicators are present."""
    env = os.environ.get("ENVIRONMENT", "").lower()
    if env in ("dev", "development", "local"):
        return True
    if env in ("prod", "production", "staging"):
        return False
    return os.environ.get("PYTEST_CURRENT_TEST") is not None


# ---------------------------------------------------------------------------
# SecurityConfig
# ---------------------------------------------------------------------------


@dataclass
class SecurityConfig:
    """Auth security configuration — loaded from environment.

    Sensitive values (JWT_SECRET, etc.) are validated at load time.
    Dev/test mode allows relaxed validation.
    """

    # Environment
    dev_mode: bool = field(default_factory=_is_dev)

    # JWT
    jwt_secret: str = ""
    jwt_algorithm: str = "HS256"
    jwt_access_token_ttl_minutes: int = 15
    jwt_clock_skew_seconds: int = 30
    jwt_issuer: str = "rmp-control-api"
    jwt_audience: str = ""

    # Refresh sessions
    refresh_session_ttl_hours: int = 8
    refresh_token_bytes: int = 32
    max_sessions_per_user: int = 5

    # Login rate limiting
    login_rate_limit_max_attempts: int = 5
    login_rate_limit_window_minutes: int = 15

    # Password policy (local credentials)
    password_min_length: int = 8
    password_bcrypt_rounds: int = 12

    # Cookie (refresh token)
    refresh_token_cookie_name: str = "refresh_token"
    refresh_token_cookie_secure: bool = True  # overridden to False in dev
    refresh_token_cookie_samesite: str = "strict"
    refresh_token_cookie_path: str = "/api/v1/auth"

    # Audit
    audit_correlation_id_header: str = "X-Correlation-ID"

    # CORS
    cors_allowed_origins: list[str] = field(default_factory=list)
    cors_allow_credentials: bool = False
    cors_allowed_methods: list[str] = field(default_factory=lambda: [
        "GET", "POST", "PUT", "DELETE", "OPTIONS",
    ])
    cors_allowed_headers: list[str] = field(default_factory=lambda: [
        "Authorization", "Content-Type",
    ])

    # MinIO / Creative Storage (S-017)
    creative_storage_bucket: str = "retail-media-creatives"
    creative_max_file_size_bytes: int = 10_485_760  # 10 MB
    creative_allowed_mime_types: frozenset[str] = frozenset({
        "image/png", "image/jpeg", "image/webp", "video/mp4", "image/gif",
    })
    creative_upload_url_ttl_seconds: int = 300  # 5 minutes
    creative_auto_approve_uploads: bool = True  # pilot: auto-approve on upload
    minio_internal_endpoint: str = ""
    minio_public_endpoint: str = ""
    minio_access_key: str = ""
    minio_secret_key: str = ""

    # Manifest signing (S-021)
    manifest_signing_key: str = ""

    def __post_init__(self) -> None:
        # Load JWT_SECRET from env if not provided
        if not self.jwt_secret:
            self.jwt_secret = os.environ.get("JWT_SECRET", "")
        # Load JWT_AUDIENCE from env if not provided
        if not self.jwt_audience:
            self.jwt_audience = os.environ.get("JWT_AUDIENCE", "")
        # Load CORS origins from env
        if not self.cors_allowed_origins:
            cors_env = os.environ.get("CORS_ALLOWED_ORIGINS", "").strip()
            if cors_env:
                self.cors_allowed_origins = [
                    o.strip() for o in cors_env.split(",") if o.strip()
                ]
        if not self.cors_allow_credentials:
            cred_env = os.environ.get("CORS_ALLOW_CREDENTIALS", "").strip()
            self.cors_allow_credentials = cred_env.lower() in ("true", "1", "yes")
        # Load MinIO/creative storage from env (S-017)
        self.minio_internal_endpoint = os.environ.get("MINIO_INTERNAL_ENDPOINT", self.minio_internal_endpoint)
        self.minio_public_endpoint = os.environ.get("MINIO_PUBLIC_ENDPOINT", self.minio_public_endpoint)
        self.minio_access_key = os.environ.get("MINIO_ACCESS_KEY", self.minio_access_key)
        self.minio_secret_key = os.environ.get("MINIO_SECRET_KEY", self.minio_secret_key)
        self.creative_storage_bucket = os.environ.get("CREATIVE_STORAGE_BUCKET", self.creative_storage_bucket)
        max_size_env = os.environ.get("CREATIVE_MAX_FILE_SIZE_BYTES", "")
        if max_size_env:
            self.creative_max_file_size_bytes = int(max_size_env)
        auto_approve_env = os.environ.get("CREATIVE_AUTO_APPROVE_UPLOADS", "")
        if auto_approve_env.lower() in ("false", "0", "no"):
            self.creative_auto_approve_uploads = False
        ttl_env = os.environ.get("CREATIVE_UPLOAD_URL_TTL_SECONDS", "")
        if ttl_env:
            self.creative_upload_url_ttl_seconds = int(ttl_env)
        # Load manifest signing key from env (S-021)
        self.manifest_signing_key = os.environ.get("MANIFEST_SIGNING_KEY", self.manifest_signing_key)
        self._validate()

    def _validate(self) -> None:
        if self.dev_mode:
            self._validate_dev()
        else:
            self._validate_production()

    def _validate_dev(self) -> None:
        """Dev mode: allow default weak secret but warn."""
        if not self.jwt_secret or self.jwt_secret == "CHANGE_ME":
            self.jwt_secret = "dev-secret-do-not-use-in-production"
        if len(self.jwt_secret) < 16:
            self.jwt_secret = "dev-secret-do-not-use-in-production"
        if not self.jwt_audience:
            self.jwt_audience = self.jwt_issuer  # default: issuer = audience
        # In dev mode, allow non-HTTPS cookies
        if self.dev_mode:
            self.refresh_token_cookie_secure = False
        # CORS dev defaults: allow localhost Vite dev server
        if not self.cors_allowed_origins:
            self.cors_allowed_origins = [
                "http://localhost:5173",
                "http://127.0.0.1:5173",
            ]
        self._validate_cors()

    def _validate_production(self) -> None:
        """Production mode: require strong JWT secret, explicit CORS, and non-default MinIO credentials."""
        if not self.jwt_secret or self.jwt_secret == "CHANGE_ME":
            raise ValueError(
                "JWT_SECRET must be set to a strong random value in production"
            )
        if len(self.jwt_secret) < 32:
            raise ValueError(
                f"JWT_SECRET must be at least 32 characters in production "
                f"(got {len(self.jwt_secret)})"
            )
        weak = {"secret", "changeme", "password", "test", "jwt_secret"}
        if self.jwt_secret.lower().strip() in weak:
            raise ValueError(
                "JWT_SECRET must not be a common weak value in production"
            )
        self._validate_cors()
        # S-017 P2: reject default MinIO credentials in production
        self._validate_minio_production()

    def _validate_cors(self) -> None:
        """Validate CORS configuration — safe defaults, no wildcard+credentials."""
        # Reject wildcard origins with credentials (browser blocks this anyway,
        # but we fail early to catch misconfiguration).
        if self.cors_allow_credentials and "*" in self.cors_allowed_origins:
            raise ValueError(
                "CORS: allow_origins=['*'] is incompatible with "
                "allow_credentials=True. Use explicit origins."
            )
        # In production, require explicit origins
        if not self.dev_mode and not self.cors_allowed_origins:
            raise ValueError(
                "CORS_ALLOWED_ORIGINS must be set to an explicit list in production"
            )

    def _validate_minio_production(self) -> None:
        """S-017 P2: reject default/weak MinIO credentials in production."""
        if self.minio_access_key == "minioadmin":
            raise ValueError(
                "MINIO_ACCESS_KEY must not be 'minioadmin' in production. "
                "Set a strong access key via MINIO_ACCESS_KEY env var."
            )
        if self.minio_secret_key == "minioadmin":
            raise ValueError(
                "MINIO_SECRET_KEY must not be 'minioadmin' in production. "
                "Set a strong secret key via MINIO_SECRET_KEY env var."
            )

    def __repr__(self) -> str:
        """Safe repr — never expose secret values."""
        return (
            f"SecurityConfig(dev_mode={self.dev_mode}, "
            f"jwt_secret='***', "
            f"jwt_algorithm={self.jwt_algorithm}, "
            f"jwt_access_token_ttl_minutes={self.jwt_access_token_ttl_minutes}, "
            f"refresh_session_ttl_hours={self.refresh_session_ttl_hours})"
        )


# Singleton — loaded once at import time
_config: SecurityConfig | None = None


def get_security_config() -> SecurityConfig:
    """Return the singleton SecurityConfig, creating it on first call."""
    global _config
    if _config is None:
        _config = SecurityConfig()
    return _config


def reset_security_config() -> None:
    """Reset singleton — useful for tests that modify env."""
    global _config
    _config = None
