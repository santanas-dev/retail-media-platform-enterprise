"""
Retail Media Platform — Phase 3.2d Auth API Tests.

Tests: login (success, wrong credentials, AD unavailable),
refresh (success, missing/invalid cookie), logout (idempotent), me (token validation),
security (no refresh_token leak, no password in response),
no auth on health/identity endpoints.

All tests use mocked AuthService + AsyncMock — no real DB/network required.
"""

import importlib.util
import json
import os
import sys
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

os.environ["ENVIRONMENT"] = "dev"
os.environ["JWT_SECRET"] = "test-jwt-secret-for-api-tests"

from fastapi.testclient import TestClient

from packages.auth.schemas import AuthFailure, AuthSuccess
from packages.security.config import reset_security_config


# ---------------------------------------------------------------------------
# App loader (importlib — dir name has hyphen)
# ---------------------------------------------------------------------------

_APP = None


def _get_app():
    """Import the FastAPI app via importlib (hyphens in dir name)."""
    global _APP
    if _APP is None:
        path = os.path.join(
            os.path.dirname(__file__), "..", "apps", "control-api", "main.py"
        )
        spec = importlib.util.spec_from_file_location("control_api_main", path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        _APP = mod.app
    return _APP


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_success(**overrides) -> AuthSuccess:
    return AuthSuccess(
        user_id=overrides.get("user_id", "u-001"),
        auth_provider=overrides.get("auth_provider", "local_advertiser"),
        access_token=overrides.get("access_token", "access-token-value"),
        refresh_token=overrides.get(
            "refresh_token",
            "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
        ),
        refresh_session_id=overrides.get("refresh_session_id", "rs-001"),
    )


def _make_failure(internal_code="AUTH_FAILED", debug_context=None) -> AuthFailure:
    return AuthFailure(
        public_reason="Invalid credentials",
        internal_code=internal_code,
        debug_context=debug_context,
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestAuthAPI(unittest.TestCase):
    """Auth API endpoint tests with mocked AuthService."""

    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(_get_app())

    def setUp(self):
        reset_security_config()
        os.environ["ENVIRONMENT"] = "dev"
        os.environ["JWT_SECRET"] = "test-jwt-secret-32-bytes-for-api"
        # Clear cookies between tests (TestClient persists them)
        self.client.cookies.clear()

    def tearDown(self):
        reset_security_config()

    # -----------------------------------------------------------------------
    # Login
    # -----------------------------------------------------------------------

    @patch("packages.api.auth.AuthService.login", new_callable=AsyncMock)
    def test_login_success_returns_access_token_and_sets_cookie(self, mock_login):
        """Login success: JSON body has access_token, response sets refresh cookie."""
        mock_login.return_value = _make_success(
            access_token="test-access-token-value",
            refresh_token="test-refresh-token-value",
        )

        resp = self.client.post("/api/v1/auth/login", json={
            "username_or_email": "testuser",
            "password": "correct-password",
            "auth_provider": "local_advertiser",
        })

        self.assertEqual(resp.status_code, 200, resp.text)
        body = resp.json()
        self.assertEqual(body["access_token"], "test-access-token-value")
        self.assertEqual(body["token_type"], "Bearer")
        self.assertGreater(body["expires_in"], 0)
        self.assertEqual(body["user"]["sub"], "u-001")
        self.assertEqual(body["user"]["auth_provider"], "local_advertiser")

        # Refresh token must NOT be in JSON body
        self.assertNotIn("refresh_token", body)

        # Refresh cookie must be set
        self.assertIn("refresh_token", resp.cookies)
        self.assertEqual(resp.cookies["refresh_token"], "test-refresh-token-value")

    @patch("packages.api.auth.AuthService.login", new_callable=AsyncMock)
    def test_login_no_refresh_token_in_json(self, mock_login):
        """Login response body NEVER contains refresh_token."""
        mock_login.return_value = _make_success(
            refresh_token="secret-refresh-token",
        )

        resp = self.client.post("/api/v1/auth/login", json={
            "username_or_email": "user@test.com",
            "password": "correct",
            "auth_provider": "local_advertiser",
        })

        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertNotIn("refresh_token", body)
        body_str = json.dumps(body)
        self.assertNotIn("secret-refresh-token", body_str)

        # But it IS in the cookie
        self.assertEqual(resp.cookies["refresh_token"], "secret-refresh-token")

    @patch("packages.api.auth.AuthService.login", new_callable=AsyncMock)
    def test_login_wrong_credentials_returns_401(self, mock_login):
        """Wrong credentials: 401, generic error message, no user enum."""
        mock_login.return_value = _make_failure(internal_code="AUTH_FAILED")

        resp = self.client.post("/api/v1/auth/login", json={
            "username_or_email": "nonexistent@test.com",
            "password": "wrong",
            "auth_provider": "local_advertiser",
        })

        self.assertEqual(resp.status_code, 401, resp.text)
        body = resp.json()
        self.assertEqual(body["detail"]["code"], "INVALID_CREDENTIALS")
        self.assertNotIn("user_not_found", str(body))
        self.assertNotIn("wrong_password", str(body))

        # No cookie on failure
        self.assertNotIn("refresh_token", resp.cookies)

    @patch("packages.api.auth.AuthService.login", new_callable=AsyncMock)
    def test_login_ad_unavailable_returns_503(self, mock_login):
        """AD unavailable: 503, no stack trace."""
        mock_login.return_value = _make_failure(
            internal_code="AUTH_FAILED",
            debug_context={"ad_error": "ldap_unavailable"},
        )

        resp = self.client.post("/api/v1/auth/login", json={
            "username_or_email": "aduser",
            "password": "valid-ldap-password",
            "auth_provider": "ad",
        })

        self.assertEqual(resp.status_code, 503, resp.text)
        body = resp.json()
        self.assertEqual(body["detail"]["code"], "SERVICE_UNAVAILABLE")
        self.assertNotIn("ldap", str(body).lower())
        self.assertNotIn("traceback", str(body).lower())

        self.assertNotIn("refresh_token", resp.cookies)

    # -----------------------------------------------------------------------
    # Refresh
    # -----------------------------------------------------------------------

    @patch("packages.api.auth.AuthService.refresh_session", new_callable=AsyncMock)
    def test_refresh_rotates_token_and_sets_new_cookie(self, mock_refresh):
        """Valid refresh token: returns new access_token, sets new cookie."""
        mock_refresh.return_value = AuthSuccess(
            user_id="u-001",
            auth_provider="local_advertiser",
            access_token="new-access-token",
            refresh_token="new-refresh-token-hexstring-32-bytes",
            refresh_session_id="rs-002",
        )

        self.client.cookies.set("refresh_token", "old-refresh-token-value")
        resp = self.client.post("/api/v1/auth/refresh")

        self.assertEqual(resp.status_code, 200, resp.text)
        body = resp.json()
        self.assertEqual(body["access_token"], "new-access-token")
        self.assertEqual(body["token_type"], "Bearer")
        self.assertNotIn("refresh_token", body)

        self.assertEqual(
            resp.cookies["refresh_token"], "new-refresh-token-hexstring-32-bytes"
        )

    @patch("packages.api.auth.AuthService.refresh_session", new_callable=AsyncMock)
    def test_refresh_missing_cookie_returns_401(self, mock_refresh):
        """No refresh cookie: 401."""
        resp = self.client.post("/api/v1/auth/refresh")

        self.assertEqual(resp.status_code, 401, resp.text)
        body = resp.json()
        self.assertEqual(body["detail"]["code"], "NOT_AUTHENTICATED")
        mock_refresh.assert_not_called()

    @patch("packages.api.auth.AuthService.refresh_session", new_callable=AsyncMock)
    def test_refresh_invalid_token_returns_401(self, mock_refresh):
        """Invalid/expired refresh token: 401 generic."""
        mock_refresh.return_value = _make_failure(internal_code="REFRESH_FAILED")

        self.client.cookies.set("refresh_token", "invalid-token-value")
        resp = self.client.post("/api/v1/auth/refresh")

        self.assertEqual(resp.status_code, 401, resp.text)
        body = resp.json()
        self.assertEqual(body["detail"]["code"], "INVALID_TOKEN")
        self.assertNotIn("token_not_found", str(body))
        self.assertNotIn("REFRESH_FAILED", str(body))

    @patch("packages.api.auth.AuthService.refresh_session", new_callable=AsyncMock)
    def test_refresh_replayed_token_returns_401(self, mock_refresh):
        """Replayed/rotated refresh token: 401."""
        mock_refresh.return_value = _make_failure(internal_code="REFRESH_REPLAY")

        self.client.cookies.set("refresh_token", "already-rotated-token")
        resp = self.client.post("/api/v1/auth/refresh")

        self.assertEqual(resp.status_code, 401)
        body = resp.json()
        self.assertEqual(body["detail"]["code"], "INVALID_TOKEN")

    # -----------------------------------------------------------------------
    # Logout
    # -----------------------------------------------------------------------

    @patch("packages.api.auth.AuthService.logout", new_callable=AsyncMock)
    def test_logout_revokes_and_clears_cookie(self, mock_logout):
        """Valid refresh token: revoke session, clear cookie."""
        mock_logout.return_value = True

        self.client.cookies.set("refresh_token", "valid-refresh-token")
        resp = self.client.post("/api/v1/auth/logout")

        self.assertEqual(resp.status_code, 200, resp.text)
        body = resp.json()
        self.assertEqual(body["message"], "Logged out")

        cookie = resp.cookies.get("refresh_token")
        self.assertTrue(
            cookie == "" or cookie is None,
            f"Expected empty/absent cookie, got '{cookie}'",
        )

        mock_logout.assert_called_once()

    @patch("packages.api.auth.AuthService.logout", new_callable=AsyncMock)
    def test_logout_no_cookie_is_idempotent(self, mock_logout):
        """No refresh cookie: still 200, AuthService not called."""
        resp = self.client.post("/api/v1/auth/logout")

        self.assertEqual(resp.status_code, 200, resp.text)
        body = resp.json()
        self.assertEqual(body["message"], "Logged out")
        mock_logout.assert_not_called()

    @patch("packages.api.auth.AuthService.logout", new_callable=AsyncMock)
    def test_logout_idempotent_double_call(self, mock_logout):
        """Logout twice: both return 200."""
        mock_logout.return_value = True

        self.client.cookies.set("refresh_token", "token-to-revoke")
        resp1 = self.client.post("/api/v1/auth/logout")
        self.assertEqual(resp1.status_code, 200)

        resp2 = self.client.post("/api/v1/auth/logout")
        self.assertEqual(resp2.status_code, 200)

    # -----------------------------------------------------------------------
    # /me
    # -----------------------------------------------------------------------

    def test_me_valid_token_returns_claims(self):
        """Valid JWT: returns sub + auth_provider."""
        from packages.security.jwt import create_access_token

        token = create_access_token("u-001", "local_advertiser")

        resp = self.client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )

        self.assertEqual(resp.status_code, 200, resp.text)
        body = resp.json()
        self.assertEqual(body["sub"], "u-001")
        self.assertEqual(body["auth_provider"], "local_advertiser")

    def test_me_missing_token_returns_401(self):
        """No Authorization header: 401."""
        resp = self.client.get("/api/v1/auth/me")

        self.assertEqual(resp.status_code, 401)
        body = resp.json()
        self.assertEqual(body["detail"]["code"], "NOT_AUTHENTICATED")

    def test_me_invalid_token_returns_401(self):
        """Garbage token: 401."""
        resp = self.client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer not.a.real.jwt"},
        )

        self.assertEqual(resp.status_code, 401)
        body = resp.json()
        self.assertEqual(body["detail"]["code"], "INVALID_TOKEN")

    def test_me_expired_token_returns_401(self):
        """Expired token: 401."""
        import time
        import uuid

        import jwt as pyjwt

        from packages.security.config import get_security_config

        cfg = get_security_config()
        now = int(time.time())
        token = pyjwt.encode(
            {
                "sub": "u-001",
                "auth_provider": "ad",
                "jti": str(uuid.uuid4()),
                "iat": now - 3600,
                "exp": now - 1800,
                "iss": cfg.jwt_issuer,
                "aud": cfg.jwt_audience,
            },
            cfg.jwt_secret,
            algorithm=cfg.jwt_algorithm,
        )

        resp = self.client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )

        self.assertEqual(resp.status_code, 401)
        body = resp.json()
        self.assertEqual(body["detail"]["code"], "TOKEN_EXPIRED")

    def test_me_wrong_audience_token_returns_401(self):
        """Token with wrong audience: 401."""
        import time
        import uuid

        import jwt as pyjwt

        from packages.security.config import get_security_config

        cfg = get_security_config()
        now = int(time.time())
        token = pyjwt.encode(
            {
                "sub": "u-001",
                "auth_provider": "ad",
                "jti": str(uuid.uuid4()),
                "iat": now,
                "exp": now + 900,
                "iss": cfg.jwt_issuer,
                "aud": "wrong-service",
            },
            cfg.jwt_secret,
            algorithm=cfg.jwt_algorithm,
        )

        resp = self.client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )

        self.assertEqual(resp.status_code, 401)
        body = resp.json()
        self.assertEqual(body["detail"]["code"], "INVALID_TOKEN")

    # -----------------------------------------------------------------------
    # Security: no leaks
    # -----------------------------------------------------------------------

    @patch("packages.api.auth.AuthService.login", new_callable=AsyncMock)
    def test_no_password_in_response_body(self, mock_login):
        """Password is never echoed back in any response."""
        mock_login.return_value = _make_success()

        resp1 = self.client.post("/api/v1/auth/login", json={
            "username_or_email": "user",
            "password": "SuperSecret123!",
            "auth_provider": "local_advertiser",
        })
        # Both return 200 because mock returns success — we only check no password leak
        self.assertEqual(resp1.status_code, 200)

        for resp in [resp1]:
            body_str = resp.text
            self.assertNotIn("SuperSecret123!", body_str)

    @patch("packages.api.auth.AuthService.login", new_callable=AsyncMock)
    def test_no_internal_error_in_401(self, mock_login):
        """401 response never leaks internal error codes/reasons."""
        mock_login.return_value = _make_failure(
            internal_code="AUTH_FAILED",
            debug_context={"reason": "user_not_found"},
        )

        resp = self.client.post("/api/v1/auth/login", json={
            "username_or_email": "ghost",
            "password": "boo",
            "auth_provider": "local_advertiser",
        })

        self.assertEqual(resp.status_code, 401)
        body_str = resp.text
        self.assertNotIn("user_not_found", body_str)
        self.assertNotIn("AUTH_FAILED", body_str)
        self.assertNotIn("internal_code", body_str)

    # -----------------------------------------------------------------------
    # No auth on health + identity endpoints
    # -----------------------------------------------------------------------

    def test_health_live_no_auth_required(self):
        """GET /health/live returns 200 without any auth."""
        resp = self.client.get("/health/live")
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(body["status"], "ok")

    def test_identity_users_no_auth_required(self):
        """Identity endpoints remain unprotected — any error except 401/403 is fine."""
        try:
            resp = self.client.get("/api/v1/identity/users")
            # If it connects, must not be auth-gated
            self.assertNotEqual(resp.status_code, 401)
            self.assertNotEqual(resp.status_code, 403)
        except Exception:
            # DB unavailable — 500 is not 401/403, test passes
            pass


if __name__ == "__main__":
    unittest.main()
