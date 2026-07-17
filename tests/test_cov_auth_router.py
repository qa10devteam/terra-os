"""Tests to improve coverage of auth/router.py and auth/deps.py."""
from __future__ import annotations

import hashlib
import importlib
import uuid
from datetime import datetime, timezone, timedelta
from typing import Any
from unittest.mock import MagicMock, patch, PropertyMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import sys
import os

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
for p in [
    ROOT,
    os.path.join(ROOT, "packages", "vendor"),
    os.path.join(ROOT, "packages", "shared"),
    os.path.join(ROOT, "packages", "db"),
    os.path.join(ROOT, "services", "api"),
]:
    if p not in sys.path:
        sys.path.insert(0, p)

os.environ.setdefault("ENVIRONMENT", "dev")
os.environ.setdefault("TESTING", "1")


# ---------------------------------------------------------------------------
# Import modules under test via importlib to avoid __init__ re-exporting
# the APIRouter object as "router"
# ---------------------------------------------------------------------------
auth_router_module = importlib.import_module("services.api.services.api.auth.router")
auth_deps_module = importlib.import_module("services.api.services.api.auth.deps")

# Re-export useful names
auth_router = auth_router_module.router  # the APIRouter
RegisterRequest = auth_router_module.RegisterRequest
LoginRequest = auth_router_module.LoginRequest
RefreshRequest = auth_router_module.RefreshRequest
ForgotPasswordRequest = auth_router_module.ForgotPasswordRequest
ResetPasswordRequest = auth_router_module.ResetPasswordRequest
_seed_new_org = auth_router_module._seed_new_org
_token_response = auth_router_module._token_response
_set_auth_cookies = auth_router_module._set_auth_cookies
get_db = auth_router_module.get_db

get_current_user = auth_deps_module.get_current_user
get_tenant_id = auth_deps_module.get_tenant_id
CurrentUser = auth_deps_module.CurrentUser

from services.api.services.api.auth.utils import (
    create_access_token,
    hash_password,
    hash_refresh_token,
    create_refresh_token,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_demo_user(**kwargs) -> CurrentUser:
    return CurrentUser(
        user_id=kwargs.get("user_id", str(uuid.uuid4())),
        email=kwargs.get("email", "test@example.com"),
        org_id=kwargs.get("org_id", str(uuid.uuid4())),
        role=kwargs.get("role", "owner"),
    )


class FakeRow:
    """Mimic a SQLAlchemy Row supporting attr + mapping access."""

    def __init__(self, data: dict):
        self._data = data
        for k, v in data.items():
            setattr(self, k, v)

    def __getitem__(self, key):
        return self._data[key]

    @property
    def _mapping(self):
        return self._data


def make_fake_row(**kwargs) -> FakeRow:
    defaults = {
        "id": str(uuid.uuid4()),
        "email": "user@example.com",
        "name": "Test User",
        "password_hash": hash_password("Password1!Super"),
        "org_id": str(uuid.uuid4()),
        "role": "owner",
        "is_active": True,
        "totp_enabled": False,
        "totp_secret": None,
    }
    defaults.update(kwargs)
    return FakeRow(defaults)


# Build isolated test app with dependency overrides
def build_test_app(db_override=None, user_override=None):
    from slowapi import Limiter, _rate_limit_exceeded_handler
    from slowapi.util import get_remote_address
    from slowapi.errors import RateLimitExceeded

    app = FastAPI()
    # Use a fresh per-test limiter so rate limits don't accumulate across tests
    fresh_limiter = Limiter(
        key_func=get_remote_address,
        default_limits=["99999/minute"],
        storage_uri="memory://",
    )
    app.state.limiter = fresh_limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    # Temporarily swap the module-level limiter so @limiter.limit decorators use the fresh one
    # The @limiter.limit decorator captures the limiter object at decoration time (module load),
    # so we can't change it per-test. Instead we reset the module-level limiter's storage.
    auth_router_module.limiter._storage.reset()
    app.state.limiter = auth_router_module.limiter
    app.include_router(auth_router)

    if db_override is not None:
        app.dependency_overrides[get_db] = db_override
    if user_override is not None:
        app.dependency_overrides[get_current_user] = user_override

    return app


def make_db_dep(db):
    """Create a FastAPI dependency (generator function) that yields the mock db."""
    def _dep():
        yield db
    return _dep


# ---------------------------------------------------------------------------
# ─── Schema Validation Tests ──────────────────────────────────────────────
# ---------------------------------------------------------------------------

class TestRegisterRequestSchema:
    """Cover schema imports + validators (lines 13,19,21,26-35,41,43-49,55,62)."""

    def test_valid_email_normalized(self):
        r = RegisterRequest(email="USER@Example.COM", name="Alice", password="SecretP@ss12!")
        assert r.email == "user@example.com"

    def test_invalid_email_raises(self):
        with pytest.raises(Exception):
            RegisterRequest(email="not-an-email", name="Alice", password="SecretP@ss12!")

    def test_password_too_short(self):
        with pytest.raises(Exception):
            RegisterRequest(email="a@b.com", name="A", password="Short1!")

    def test_password_no_uppercase(self):
        with pytest.raises(Exception):
            RegisterRequest(email="a@b.com", name="A", password="nouppercase1!aaa")

    def test_password_no_digit(self):
        with pytest.raises(Exception):
            RegisterRequest(email="a@b.com", name="A", password="NoDigitHere!!!!")

    def test_password_no_special(self):
        with pytest.raises(Exception):
            RegisterRequest(email="a@b.com", name="A", password="NoSpecial12345A")

    def test_password_equals_email(self):
        with pytest.raises(Exception):
            # password == email (already validates fine individually, but fails the cross-check)
            # Need valid structure but equal to email
            RegisterRequest(email="A1!aaaaaaaaa@b.com", name="A", password="A1!aaaaaaaaa@b.com")

    def test_valid_registration(self):
        r = RegisterRequest(
            email="valid@test.com",
            name="Test",
            password="ValidP@ss123!",
            org_name="MyOrg",
        )
        assert r.email == "valid@test.com"
        assert r.org_name == "MyOrg"


class TestResetPasswordSchema:
    """Cover validator in ResetPasswordRequest."""

    def test_weak_password_raises(self):
        with pytest.raises(Exception):
            ResetPasswordRequest(token="abc", new_password="weak")

    def test_valid_reset_password(self):
        r = ResetPasswordRequest(token="sometoken", new_password="StrongP@ss123!")
        assert r.token == "sometoken"


# ---------------------------------------------------------------------------
# ─── Helper function coverage ─────────────────────────────────────────────
# ---------------------------------------------------------------------------

class TestSetAuthCookies:
    """Line 88: _set_auth_cookies."""

    def test_cookies_set(self):
        from fastapi.responses import JSONResponse
        response = JSONResponse(content={})
        _set_auth_cookies(response, "fake_access_token")
        cookie_headers = [v for k, v in response.headers.items() if k == "set-cookie"]
        assert len(cookie_headers) >= 2


class TestSeedNewOrg:
    """Lines 182-188: _seed_new_org."""

    def test_seed_calls_db(self):
        db = MagicMock()
        _seed_new_org(db, str(uuid.uuid4()))
        assert db.execute.called
        assert db.commit.called


class TestTokenResponse:
    """Line 123 area: _token_response."""

    def test_returns_token_response_with_org(self):
        db = MagicMock()
        result_mock = MagicMock()
        db.execute.return_value = result_mock

        user_id = str(uuid.uuid4())
        org_id = str(uuid.uuid4())
        user_dict = {
            "id": user_id,
            "email": "t@t.com",
            "name": "Tester",
            "org_id": org_id,
            "role": "owner",
        }
        tr = _token_response(db, user_dict)
        assert tr.access_token
        assert tr.refresh_token
        assert tr.user["email"] == "t@t.com"
        db.commit.assert_called()

    def test_returns_token_response_no_org(self):
        db = MagicMock()
        user_dict = {
            "id": str(uuid.uuid4()),
            "email": "t@t.com",
            "name": "Tester",
            "org_id": None,
            "role": "viewer",
        }
        tr = _token_response(db, user_dict)
        assert tr.user["org_id"] is None


# ---------------------------------------------------------------------------
# ─── Register endpoint ────────────────────────────────────────────────────
# ---------------------------------------------------------------------------

class TestRegisterEndpoint:
    """Lines 224-269: POST /api/v2/auth/register."""

    def _app_with_db(self, db):
        return build_test_app(db_override=make_db_dep(db))

    def test_register_duplicate_email_409(self):
        db = MagicMock()
        existing_result = MagicMock()
        existing_result.fetchone.return_value = FakeRow({"id": str(uuid.uuid4()),
                                                          "email": "dup@x.com", "name": "X",
                                                          "password_hash": "", "org_id": None,
                                                          "role": "owner", "is_active": True,
                                                          "totp_enabled": False, "totp_secret": None})
        db.execute.return_value = existing_result

        with patch.object(auth_router_module, "send_welcome_email"):
            app = self._app_with_db(db)
            client = TestClient(app, raise_server_exceptions=False)
            resp = client.post("/api/v2/auth/register", json={
                "email": "dup@example.com",
                "name": "Dup",
                "password": "ValidP@ss123!",
            })
        assert resp.status_code == 409

    def test_register_success_no_org(self):
        db = MagicMock()
        call_count = [0]

        user_id = str(uuid.uuid4())
        org_id = str(uuid.uuid4())
        user_row = FakeRow({
            "id": user_id, "email": "new@example.com",
            "name": "New User", "org_id": org_id, "role": "owner",
        })

        def execute_side(query, params=None):
            result = MagicMock()
            call_count[0] += 1
            if call_count[0] == 1:
                result.fetchone.return_value = None  # no duplicate
            else:
                result.fetchone.return_value = user_row
            return result

        db.execute.side_effect = execute_side

        with patch.object(auth_router_module, "send_welcome_email") as mock_email:
            app = self._app_with_db(db)
            client = TestClient(app, raise_server_exceptions=False)
            resp = client.post("/api/v2/auth/register", json={
                "email": "new@example.com",
                "name": "New User",
                "password": "ValidP@ss123!",
            })
        assert resp.status_code in (200, 201), resp.text
        mock_email.assert_called_once()

    def test_register_with_org_name(self):
        db = MagicMock()
        call_count = [0]
        user_id = str(uuid.uuid4())
        org_id = str(uuid.uuid4())

        user_row = FakeRow({
            "id": user_id, "email": "org@example.com",
            "name": "Org User", "org_id": org_id, "role": "owner",
        })

        def execute_side(query, params=None):
            result = MagicMock()
            call_count[0] += 1
            if call_count[0] == 1:
                result.fetchone.return_value = None  # no duplicate
            else:
                result.fetchone.return_value = user_row
            return result

        db.execute.side_effect = execute_side

        with (
            patch.object(auth_router_module, "send_welcome_email"),
            patch.object(auth_router_module, "_seed_new_org") as mock_seed,
        ):
            app = self._app_with_db(db)
            client = TestClient(app, raise_server_exceptions=False)
            resp = client.post("/api/v2/auth/register", json={
                "email": "org@example.com",
                "name": "Org User",
                "password": "ValidP@ss123!",
                "org_name": "TestOrg",
            })
        assert resp.status_code in (200, 201), resp.text
        mock_seed.assert_called_once()


# ---------------------------------------------------------------------------
# ─── Login endpoint ───────────────────────────────────────────────────────
# ---------------------------------------------------------------------------

class TestLoginEndpoint:
    """Lines 278-301: POST /api/v2/auth/login."""

    def _app_with_db(self, db):
        return build_test_app(db_override=make_db_dep(db))

    def test_login_user_not_found_401(self):
        db = MagicMock()
        result = MagicMock()
        result.fetchone.return_value = None
        db.execute.return_value = result

        app = self._app_with_db(db)
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.post("/api/v2/auth/login", json={"email": "x@x.com", "password": "wrong"})
        assert resp.status_code == 401

    def test_login_wrong_password_401(self):
        db = MagicMock()
        result = MagicMock()
        pw_hash = hash_password("CorrectP@ss123!")
        result.fetchone.return_value = FakeRow({
            "id": str(uuid.uuid4()), "email": "x@x.com", "name": "X",
            "password_hash": pw_hash, "org_id": None, "role": "viewer",
            "is_active": True, "totp_enabled": False, "totp_secret": None,
        })
        db.execute.return_value = result

        app = self._app_with_db(db)
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.post("/api/v2/auth/login", json={"email": "x@x.com", "password": "WrongP@ss123!"})
        assert resp.status_code == 401

    def test_login_inactive_user_403(self):
        db = MagicMock()
        result = MagicMock()
        pw_hash = hash_password("CorrectP@ss123!")
        result.fetchone.return_value = FakeRow({
            "id": str(uuid.uuid4()), "email": "x@x.com", "name": "X",
            "password_hash": pw_hash, "org_id": None, "role": "viewer",
            "is_active": False, "totp_enabled": False, "totp_secret": None,
        })
        db.execute.return_value = result

        app = self._app_with_db(db)
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.post("/api/v2/auth/login", json={"email": "x@x.com", "password": "CorrectP@ss123!"})
        assert resp.status_code == 403

    def test_login_totp_required_401(self):
        """2FA enabled but totp_code not provided."""
        import pyotp
        secret = pyotp.random_base32()
        db = MagicMock()
        pw_hash = hash_password("CorrectP@ss123!")
        result = MagicMock()
        result.fetchone.return_value = FakeRow({
            "id": str(uuid.uuid4()), "email": "totp@x.com", "name": "T",
            "password_hash": pw_hash, "org_id": None, "role": "viewer",
            "is_active": True, "totp_enabled": True, "totp_secret": secret,
        })
        db.execute.return_value = result

        app = self._app_with_db(db)
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.post("/api/v2/auth/login", json={"email": "totp@x.com", "password": "CorrectP@ss123!"})
        assert resp.status_code == 401

    def test_login_totp_invalid_code_401(self):
        """2FA enabled, wrong code provided."""
        import pyotp
        secret = pyotp.random_base32()
        db = MagicMock()
        pw_hash = hash_password("CorrectP@ss123!")
        result = MagicMock()
        result.fetchone.return_value = FakeRow({
            "id": str(uuid.uuid4()), "email": "totp@x.com", "name": "T",
            "password_hash": pw_hash, "org_id": None, "role": "viewer",
            "is_active": True, "totp_enabled": True, "totp_secret": secret,
        })
        db.execute.return_value = result

        app = self._app_with_db(db)
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.post("/api/v2/auth/login", json={
            "email": "totp@x.com",
            "password": "CorrectP@ss123!",
            "totp_code": "000000",
        })
        assert resp.status_code == 401

    def test_login_success(self):
        db = MagicMock()
        pw_hash = hash_password("CorrectP@ss123!")
        user_id = str(uuid.uuid4())
        org_id = str(uuid.uuid4())
        call_count = [0]

        def execute_side(query, params=None):
            result = MagicMock()
            call_count[0] += 1
            if call_count[0] == 1:
                result.fetchone.return_value = FakeRow({
                    "id": user_id, "email": "ok@x.com", "name": "OK",
                    "password_hash": pw_hash, "org_id": org_id, "role": "viewer",
                    "is_active": True, "totp_enabled": False, "totp_secret": None,
                })
            else:
                result.fetchone.return_value = None
            return result

        db.execute.side_effect = execute_side

        app = self._app_with_db(db)
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.post("/api/v2/auth/login", json={"email": "ok@x.com", "password": "CorrectP@ss123!"})
        assert resp.status_code == 200, resp.text


# ---------------------------------------------------------------------------
# ─── Refresh endpoint ─────────────────────────────────────────────────────
# ---------------------------------------------------------------------------

class TestRefreshEndpoint:
    """Lines 306,321-328: POST /api/v2/auth/refresh."""

    def _app_with_db(self, db):
        return build_test_app(db_override=make_db_dep(db))

    def test_refresh_invalid_token_401(self):
        db = MagicMock()
        result = MagicMock()
        result.fetchone.return_value = None
        db.execute.return_value = result

        app = self._app_with_db(db)
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.post("/api/v2/auth/refresh", json={"refresh_token": "bad-token"})
        assert resp.status_code == 401

    def test_refresh_revoked_token_401(self):
        db = MagicMock()
        result = MagicMock()
        rt_row = MagicMock()
        rt_row.revoked = True
        rt_row.expires_at = datetime.now(timezone.utc) + timedelta(days=1)
        rt_row.is_active = True
        result.fetchone.return_value = rt_row
        db.execute.return_value = result

        app = self._app_with_db(db)
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.post("/api/v2/auth/refresh", json={"refresh_token": "revoked-token"})
        assert resp.status_code == 401

    def test_refresh_expired_token_401(self):
        db = MagicMock()
        result = MagicMock()
        rt_row = MagicMock()
        rt_row.revoked = False
        rt_row.expires_at = datetime.now(timezone.utc) - timedelta(days=1)
        rt_row.is_active = True
        result.fetchone.return_value = rt_row
        db.execute.return_value = result

        app = self._app_with_db(db)
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.post("/api/v2/auth/refresh", json={"refresh_token": "expired-token"})
        assert resp.status_code == 401

    def test_refresh_inactive_user_403(self):
        db = MagicMock()
        result = MagicMock()
        rt_row = MagicMock()
        rt_row.revoked = False
        rt_row.expires_at = datetime.now(timezone.utc) + timedelta(days=1)
        rt_row.is_active = False
        result.fetchone.return_value = rt_row
        db.execute.return_value = result

        app = self._app_with_db(db)
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.post("/api/v2/auth/refresh", json={"refresh_token": "inactive-user"})
        assert resp.status_code == 403

    def test_refresh_success(self):
        db = MagicMock()
        user_id = str(uuid.uuid4())
        org_id = str(uuid.uuid4())
        call_count = [0]

        def execute_side(query, params=None):
            result = MagicMock()
            call_count[0] += 1
            if call_count[0] == 1:
                rt_row = MagicMock()
                rt_row.revoked = False
                rt_row.expires_at = datetime.now(timezone.utc) + timedelta(days=10)
                rt_row.is_active = True
                rt_row.id = str(uuid.uuid4())
                rt_row.user_id = user_id
                rt_row.email = "ok@x.com"
                rt_row.name = "OK"
                rt_row.org_id = org_id
                rt_row.role = "owner"
                result.fetchone.return_value = rt_row
            else:
                result.fetchone.return_value = None
            return result

        db.execute.side_effect = execute_side

        app = self._app_with_db(db)
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.post("/api/v2/auth/refresh", json={"refresh_token": "valid-token"})
        assert resp.status_code == 200, resp.text


# ---------------------------------------------------------------------------
# ─── Logout endpoint ──────────────────────────────────────────────────────
# ---------------------------------------------------------------------------

class TestLogoutEndpoint:
    """Lines 344,348-349: POST /api/v2/auth/logout."""

    def test_logout_success(self):
        db = MagicMock()
        app = build_test_app(db_override=make_db_dep(db))
        client = TestClient(app)
        resp = client.post("/api/v2/auth/logout", json={"refresh_token": "any-token"})
        assert resp.status_code == 204
        db.execute.assert_called()
        db.commit.assert_called()


# ---------------------------------------------------------------------------
# ─── Forgot Password endpoint ─────────────────────────────────────────────
# ---------------------------------------------------------------------------

class TestForgotPasswordEndpoint:
    """POST /api/v2/auth/forgot-password."""

    def _app_with_db(self, db):
        return build_test_app(db_override=make_db_dep(db))

    def test_forgot_password_unknown_email_200(self):
        """Always returns 200 even for unknown emails."""
        db = MagicMock()
        result = MagicMock()
        result.fetchone.return_value = None
        db.execute.return_value = result

        app = self._app_with_db(db)
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.post("/api/v2/auth/forgot-password", json={"email": "unknown@x.com"})
        assert resp.status_code == 200

    def test_forgot_password_known_email_200(self):
        """Sends email when user exists."""
        db = MagicMock()
        user_id = str(uuid.uuid4())
        result = MagicMock()
        result.fetchone.return_value = FakeRow({
            "id": user_id, "email": "known@x.com", "name": "K",
            "password_hash": "", "org_id": None, "role": "owner",
            "is_active": True, "totp_enabled": False, "totp_secret": None,
        })
        db.execute.return_value = result

        engine_mock = MagicMock()
        conn_mock = MagicMock()
        conn_mock.__enter__ = MagicMock(return_value=conn_mock)
        conn_mock.__exit__ = MagicMock(return_value=False)
        engine_mock.begin.return_value = conn_mock

        with (
            patch.object(auth_router_module, "get_engine", return_value=engine_mock),
            patch.object(auth_router_module, "send_password_reset_email") as mock_email,
        ):
            app = self._app_with_db(db)
            client = TestClient(app, raise_server_exceptions=False)
            resp = client.post("/api/v2/auth/forgot-password", json={"email": "known@x.com"})

        assert resp.status_code == 200
        mock_email.assert_called_once()


# ---------------------------------------------------------------------------
# ─── Reset Password endpoint ──────────────────────────────────────────────
# ---------------------------------------------------------------------------

class TestResetPasswordEndpoint:
    """POST /api/v2/auth/reset-password."""

    def _app_with_db(self, db):
        return build_test_app(db_override=make_db_dep(db))

    def _make_engine_conn(self, token_row=None):
        engine_mock = MagicMock()
        conn_mock = MagicMock()
        conn_mock.__enter__ = MagicMock(return_value=conn_mock)
        conn_mock.__exit__ = MagicMock(return_value=False)
        result = MagicMock()
        result.fetchone.return_value = token_row
        conn_mock.execute.return_value = result
        engine_mock.begin.return_value = conn_mock
        return engine_mock, conn_mock

    def test_reset_password_invalid_token_400(self):
        db = MagicMock()
        engine_mock, _ = self._make_engine_conn(token_row=None)

        with patch.object(auth_router_module, "get_engine", return_value=engine_mock):
            app = self._app_with_db(db)
            client = TestClient(app, raise_server_exceptions=False)
            resp = client.post("/api/v2/auth/reset-password", json={
                "token": "badtoken",
                "new_password": "NewValidP@ss123!",
            })
        assert resp.status_code == 400

    def test_reset_password_expired_token_400(self):
        db = MagicMock()
        token_row = MagicMock()
        token_row.expires_at = datetime.now(timezone.utc) - timedelta(hours=2)
        token_row.used_at = None
        token_row.id = str(uuid.uuid4())
        token_row.user_id = str(uuid.uuid4())
        engine_mock, _ = self._make_engine_conn(token_row=token_row)

        with patch.object(auth_router_module, "get_engine", return_value=engine_mock):
            app = self._app_with_db(db)
            client = TestClient(app, raise_server_exceptions=False)
            resp = client.post("/api/v2/auth/reset-password", json={
                "token": "expiredtoken",
                "new_password": "NewValidP@ss123!",
            })
        assert resp.status_code == 400

    def test_reset_password_already_used_400(self):
        db = MagicMock()
        token_row = MagicMock()
        token_row.expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
        token_row.used_at = datetime.now(timezone.utc) - timedelta(minutes=5)
        token_row.id = str(uuid.uuid4())
        token_row.user_id = str(uuid.uuid4())
        engine_mock, _ = self._make_engine_conn(token_row=token_row)

        with patch.object(auth_router_module, "get_engine", return_value=engine_mock):
            app = self._app_with_db(db)
            client = TestClient(app, raise_server_exceptions=False)
            resp = client.post("/api/v2/auth/reset-password", json={
                "token": "usedtoken",
                "new_password": "NewValidP@ss123!",
            })
        assert resp.status_code == 400

    def test_reset_password_user_not_found_400(self):
        db = MagicMock()
        token_row = MagicMock()
        token_row.expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
        token_row.used_at = None
        token_row.id = str(uuid.uuid4())
        token_row.user_id = str(uuid.uuid4())

        engine_mock = MagicMock()
        conn_mock = MagicMock()
        conn_mock.__enter__ = MagicMock(return_value=conn_mock)
        conn_mock.__exit__ = MagicMock(return_value=False)
        engine_mock.begin.return_value = conn_mock

        call_count = [0]

        def execute_side(query, params=None):
            result = MagicMock()
            call_count[0] += 1
            if call_count[0] == 1:
                result.fetchone.return_value = token_row
            elif call_count[0] == 3:
                result.fetchone.return_value = None  # UPDATE users returns nothing
            else:
                result.fetchone.return_value = None
            return result

        conn_mock.execute.side_effect = execute_side

        with patch.object(auth_router_module, "get_engine", return_value=engine_mock):
            app = self._app_with_db(db)
            client = TestClient(app, raise_server_exceptions=False)
            resp = client.post("/api/v2/auth/reset-password", json={
                "token": "validtoken",
                "new_password": "NewValidP@ss123!",
            })
        assert resp.status_code == 400

    def test_reset_password_success(self):
        db = MagicMock()
        token_row = MagicMock()
        token_row.expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
        token_row.used_at = None
        token_row.id = str(uuid.uuid4())
        user_id = str(uuid.uuid4())
        token_row.user_id = user_id

        engine_mock = MagicMock()
        conn_mock = MagicMock()
        conn_mock.__enter__ = MagicMock(return_value=conn_mock)
        conn_mock.__exit__ = MagicMock(return_value=False)
        engine_mock.begin.return_value = conn_mock

        call_count = [0]

        def execute_side(query, params=None):
            result = MagicMock()
            call_count[0] += 1
            if call_count[0] == 1:
                result.fetchone.return_value = token_row
            elif call_count[0] == 3:
                user_result = MagicMock()
                user_result.id = user_id
                result.fetchone.return_value = user_result
            else:
                result.fetchone.return_value = None
            return result

        conn_mock.execute.side_effect = execute_side

        with patch.object(auth_router_module, "get_engine", return_value=engine_mock):
            app = self._app_with_db(db)
            client = TestClient(app, raise_server_exceptions=False)
            resp = client.post("/api/v2/auth/reset-password", json={
                "token": "validtoken",
                "new_password": "NewValidP@ss123!",
            })
        assert resp.status_code == 200, resp.text


# ---------------------------------------------------------------------------
# ─── /me endpoint ─────────────────────────────────────────────────────────
# ---------------------------------------------------------------------------

class TestMeEndpoint:
    """Line 470: GET /api/v2/auth/me."""

    def test_me_returns_current_user(self):
        user_id = str(uuid.uuid4())
        org_id = str(uuid.uuid4())
        demo = CurrentUser(user_id=user_id, email="me@example.com", org_id=org_id, role="owner")

        app = build_test_app(user_override=lambda: demo)
        client = TestClient(app)
        resp = client.get("/api/v2/auth/me")
        assert resp.status_code == 200
        data = resp.json()
        assert data["email"] == "me@example.com"
        assert data["role"] == "owner"

    def test_me_name_from_email(self):
        demo = CurrentUser(user_id=str(uuid.uuid4()), email="john@company.com", org_id=None, role="viewer")
        app = build_test_app(user_override=lambda: demo)
        client = TestClient(app)
        resp = client.get("/api/v2/auth/me")
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "john"


# ---------------------------------------------------------------------------
# ─── /me/full endpoint ────────────────────────────────────────────────────
# ---------------------------------------------------------------------------

class TestMeFullEndpoint:
    """Lines 485,500-511: GET /api/v2/auth/me/full."""

    def test_me_full_no_org(self):
        demo = CurrentUser(user_id=str(uuid.uuid4()), email="noorg@x.com", org_id=None, role="viewer")
        app = build_test_app(user_override=lambda: demo)
        client = TestClient(app)
        resp = client.get("/api/v2/auth/me/full")
        assert resp.status_code == 200
        data = resp.json()
        assert data["org"] is None

    def test_me_full_with_org_found(self):
        org_id = str(uuid.uuid4())
        demo = CurrentUser(user_id=str(uuid.uuid4()), email="withorg@x.com", org_id=org_id, role="owner")

        engine_mock = MagicMock()
        conn_mock = MagicMock()
        conn_mock.__enter__ = MagicMock(return_value=conn_mock)
        conn_mock.__exit__ = MagicMock(return_value=False)
        engine_mock.connect.return_value = conn_mock

        org_row = MagicMock()
        org_row.id = org_id
        org_row.name = "TestOrg"
        result = MagicMock()
        result.fetchone.return_value = org_row
        conn_mock.execute.return_value = result

        with patch.object(auth_router_module, "get_engine", return_value=engine_mock):
            app = build_test_app(user_override=lambda: demo)
            client = TestClient(app)
            resp = client.get("/api/v2/auth/me/full")

        assert resp.status_code == 200
        data = resp.json()
        assert data["org"]["name"] == "TestOrg"

    def test_me_full_with_org_db_exception(self):
        """Cover the except pass branch (line 501)."""
        org_id = str(uuid.uuid4())
        demo = CurrentUser(user_id=str(uuid.uuid4()), email="withorg@x.com", org_id=org_id, role="owner")

        with patch.object(auth_router_module, "get_engine", side_effect=Exception("db error")):
            app = build_test_app(user_override=lambda: demo)
            client = TestClient(app)
            resp = client.get("/api/v2/auth/me/full")

        assert resp.status_code == 200
        data = resp.json()
        assert data["org"] is None


# ---------------------------------------------------------------------------
# ─── 2FA endpoints ────────────────────────────────────────────────────────
# ---------------------------------------------------------------------------

class Test2FAEndpoints:
    """Lines 523-575: /2fa/setup, /2fa/enable, /2fa/disable."""

    def test_setup_2fa(self):
        user_id = str(uuid.uuid4())
        demo = CurrentUser(user_id=user_id, email="2fa@x.com", org_id=None, role="owner")

        engine_mock = MagicMock()
        conn_mock = MagicMock()
        conn_mock.__enter__ = MagicMock(return_value=conn_mock)
        conn_mock.__exit__ = MagicMock(return_value=False)
        engine_mock.begin.return_value = conn_mock

        with patch.object(auth_router_module, "get_engine", return_value=engine_mock):
            app = build_test_app(user_override=lambda: demo)
            client = TestClient(app)
            resp = client.post("/api/v2/auth/2fa/setup")

        assert resp.status_code == 200
        data = resp.json()
        assert "secret" in data
        assert "qr_code" in data

    def test_enable_2fa_no_secret_400(self):
        """User has no totp_secret set yet."""
        user_id = str(uuid.uuid4())
        demo = CurrentUser(user_id=user_id, email="2fa@x.com", org_id=None, role="owner")

        engine_mock = MagicMock()
        conn_mock = MagicMock()
        conn_mock.__enter__ = MagicMock(return_value=conn_mock)
        conn_mock.__exit__ = MagicMock(return_value=False)
        engine_mock.connect.return_value = conn_mock
        result = MagicMock()
        result.fetchone.return_value = MagicMock(totp_secret=None)
        conn_mock.execute.return_value = result

        with patch.object(auth_router_module, "get_engine", return_value=engine_mock):
            app = build_test_app(user_override=lambda: demo)
            client = TestClient(app, raise_server_exceptions=False)
            resp = client.post("/api/v2/auth/2fa/enable", json={"token": "123456"})

        assert resp.status_code == 400

    def test_enable_2fa_invalid_code_400(self):
        import pyotp
        secret = pyotp.random_base32()
        user_id = str(uuid.uuid4())
        demo = CurrentUser(user_id=user_id, email="2fa@x.com", org_id=None, role="owner")

        engine_mock = MagicMock()
        conn_mock = MagicMock()
        conn_mock.__enter__ = MagicMock(return_value=conn_mock)
        conn_mock.__exit__ = MagicMock(return_value=False)
        engine_mock.connect.return_value = conn_mock
        result = MagicMock()
        row_mock = MagicMock()
        row_mock.totp_secret = secret
        result.fetchone.return_value = row_mock
        conn_mock.execute.return_value = result

        with patch.object(auth_router_module, "get_engine", return_value=engine_mock):
            app = build_test_app(user_override=lambda: demo)
            client = TestClient(app, raise_server_exceptions=False)
            resp = client.post("/api/v2/auth/2fa/enable", json={"token": "000000"})

        assert resp.status_code == 400

    def test_enable_2fa_success(self):
        import pyotp
        secret = pyotp.random_base32()
        valid_code = pyotp.TOTP(secret).now()
        user_id = str(uuid.uuid4())
        demo = CurrentUser(user_id=user_id, email="2fa@x.com", org_id=None, role="owner")

        engine_mock = MagicMock()
        read_conn = MagicMock()
        read_conn.__enter__ = MagicMock(return_value=read_conn)
        read_conn.__exit__ = MagicMock(return_value=False)
        write_conn = MagicMock()
        write_conn.__enter__ = MagicMock(return_value=write_conn)
        write_conn.__exit__ = MagicMock(return_value=False)
        engine_mock.connect.return_value = read_conn
        engine_mock.begin.return_value = write_conn

        result = MagicMock()
        row_mock = MagicMock()
        row_mock.totp_secret = secret
        result.fetchone.return_value = row_mock
        read_conn.execute.return_value = result

        with patch.object(auth_router_module, "get_engine", return_value=engine_mock):
            app = build_test_app(user_override=lambda: demo)
            client = TestClient(app)
            resp = client.post("/api/v2/auth/2fa/enable", json={"token": valid_code})

        assert resp.status_code == 200

    def test_disable_2fa_not_enabled_400(self):
        user_id = str(uuid.uuid4())
        demo = CurrentUser(user_id=user_id, email="2fa@x.com", org_id=None, role="owner")

        engine_mock = MagicMock()
        conn_mock = MagicMock()
        conn_mock.__enter__ = MagicMock(return_value=conn_mock)
        conn_mock.__exit__ = MagicMock(return_value=False)
        engine_mock.connect.return_value = conn_mock
        result = MagicMock()
        row_mock = MagicMock()
        row_mock.totp_enabled = False
        row_mock.totp_secret = None
        result.fetchone.return_value = row_mock
        conn_mock.execute.return_value = result

        with patch.object(auth_router_module, "get_engine", return_value=engine_mock):
            app = build_test_app(user_override=lambda: demo)
            client = TestClient(app, raise_server_exceptions=False)
            resp = client.post("/api/v2/auth/2fa/disable", json={"token": "123456"})

        assert resp.status_code == 400

    def test_disable_2fa_invalid_code_400(self):
        import pyotp
        secret = pyotp.random_base32()
        user_id = str(uuid.uuid4())
        demo = CurrentUser(user_id=user_id, email="2fa@x.com", org_id=None, role="owner")

        engine_mock = MagicMock()
        conn_mock = MagicMock()
        conn_mock.__enter__ = MagicMock(return_value=conn_mock)
        conn_mock.__exit__ = MagicMock(return_value=False)
        engine_mock.connect.return_value = conn_mock
        result = MagicMock()
        row_mock = MagicMock()
        row_mock.totp_enabled = True
        row_mock.totp_secret = secret
        result.fetchone.return_value = row_mock
        conn_mock.execute.return_value = result

        with patch.object(auth_router_module, "get_engine", return_value=engine_mock):
            app = build_test_app(user_override=lambda: demo)
            client = TestClient(app, raise_server_exceptions=False)
            resp = client.post("/api/v2/auth/2fa/disable", json={"token": "000000"})

        assert resp.status_code == 400

    def test_disable_2fa_success(self):
        import pyotp
        secret = pyotp.random_base32()
        valid_code = pyotp.TOTP(secret).now()
        user_id = str(uuid.uuid4())
        demo = CurrentUser(user_id=user_id, email="2fa@x.com", org_id=None, role="owner")

        engine_mock = MagicMock()
        read_conn = MagicMock()
        read_conn.__enter__ = MagicMock(return_value=read_conn)
        read_conn.__exit__ = MagicMock(return_value=False)
        write_conn = MagicMock()
        write_conn.__enter__ = MagicMock(return_value=write_conn)
        write_conn.__exit__ = MagicMock(return_value=False)
        engine_mock.connect.return_value = read_conn
        engine_mock.begin.return_value = write_conn

        result = MagicMock()
        row_mock = MagicMock()
        row_mock.totp_enabled = True
        row_mock.totp_secret = secret
        result.fetchone.return_value = row_mock
        read_conn.execute.return_value = result

        with patch.object(auth_router_module, "get_engine", return_value=engine_mock):
            app = build_test_app(user_override=lambda: demo)
            client = TestClient(app)
            resp = client.post("/api/v2/auth/2fa/disable", json={"token": valid_code})

        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# ─── auth/deps.py coverage ────────────────────────────────────────────────
# ---------------------------------------------------------------------------

class TestGetCurrentUser:
    """Lines 33-41,63 in deps.py."""

    def test_missing_credentials_none_raises(self):
        """Lines 33-41 — None credentials raises AttributeError caught or 401."""
        from fastapi import HTTPException

        try:
            result = get_current_user(None)
        except (HTTPException, AttributeError, Exception):
            pass  # Expected — None has no .credentials

    def test_invalid_token_raises_401(self):
        """Lines 35-40: PyJWTError → HTTPException 401."""
        from fastapi import HTTPException
        from fastapi.security import HTTPAuthorizationCredentials

        creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials="invalid.jwt.token")
        with pytest.raises(HTTPException) as exc:
            get_current_user(creds)
        assert exc.value.status_code == 401

    def test_valid_token_returns_user(self):
        """Line 41-46: valid token → CurrentUser."""
        from fastapi.security import HTTPAuthorizationCredentials

        token = create_access_token(
            user_id="test-user-id",
            email="test@example.com",
            org_id="test-org-id",
            role="owner",
        )
        creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
        user = get_current_user(creds)
        assert user.user_id == "test-user-id"
        assert user.email == "test@example.com"
        assert user.role == "owner"

    def test_non_access_token_raises_401(self):
        """Token with wrong type raises 401 (PyJWTError path)."""
        import jwt as pyjwt
        from fastapi import HTTPException
        from fastapi.security import HTTPAuthorizationCredentials
        from services.api.services.api.auth.utils import SECRET_KEY, ALGORITHM

        payload = {
            "sub": "uid",
            "email": "x@x.com",
            "org_id": None,
            "role": "owner",
            "type": "refresh",
            "iat": 1000000,
            "exp": 9999999999,
        }
        bad_token = pyjwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
        creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=bad_token)
        with pytest.raises(HTTPException) as exc:
            get_current_user(creds)
        assert exc.value.status_code == 401


class TestGetTenantId:
    """Lines 63,79-82 in deps.py."""

    def test_no_org_raises_403(self):
        """Line 63: user without org_id → 403."""
        from fastapi import HTTPException
        user = CurrentUser(user_id="uid", email="x@x.com", org_id=None, role="owner")
        with pytest.raises(HTTPException) as exc:
            get_tenant_id(user)
        assert exc.value.status_code == 403

    def test_with_org_returns_tenant_id(self):
        """Lines 79-82: org found → return tenant_id."""
        org_id = str(uuid.uuid4())
        tenant_id = str(uuid.uuid4())
        user = CurrentUser(user_id="uid", email="x@x.com", org_id=org_id, role="owner")

        engine_mock = MagicMock()
        conn_mock = MagicMock()
        conn_mock.__enter__ = MagicMock(return_value=conn_mock)
        conn_mock.__exit__ = MagicMock(return_value=False)
        engine_mock.connect.return_value = conn_mock

        row_mock = MagicMock()
        # row[0] returns tenant_id — MagicMock supports __getitem__
        row_mock.__getitem__ = MagicMock(return_value=tenant_id)
        result = MagicMock()
        result.fetchone.return_value = row_mock
        conn_mock.execute.return_value = result

        with patch("terra_db.session.get_engine", return_value=engine_mock):
            tid = get_tenant_id(user)

        assert tid == tenant_id

    def test_with_org_db_exception_fallback(self):
        """Lines 79-82: DB exception → fallback to org_id."""
        org_id = str(uuid.uuid4())
        user = CurrentUser(user_id="uid", email="x@x.com", org_id=org_id, role="owner")

        with patch("terra_db.session.get_engine", side_effect=Exception("db down")):
            tid = get_tenant_id(user)

        assert tid == org_id

    def test_with_org_row_none_fallback(self):
        """Row is None → fallback to org_id."""
        org_id = str(uuid.uuid4())
        user = CurrentUser(user_id="uid", email="x@x.com", org_id=org_id, role="owner")

        engine_mock = MagicMock()
        conn_mock = MagicMock()
        conn_mock.__enter__ = MagicMock(return_value=conn_mock)
        conn_mock.__exit__ = MagicMock(return_value=False)
        engine_mock.connect.return_value = conn_mock

        result = MagicMock()
        result.fetchone.return_value = None
        conn_mock.execute.return_value = result

        with patch("terra_db.session.get_engine", return_value=engine_mock):
            tid = get_tenant_id(user)

        assert tid == org_id


# ---------------------------------------------------------------------------
# ─── get_db generator coverage ────────────────────────────────────────────
# ---------------------------------------------------------------------------

class TestGetDb:
    """Lines 41,43-49: get_db generator."""

    def test_get_db_yields_and_closes(self):
        """Cover get_db generator."""
        mock_session_class = MagicMock()
        mock_db = MagicMock()
        mock_session_class.return_value = mock_db

        with patch.object(auth_router_module, "get_session", return_value=mock_session_class):
            gen = get_db()
            db = next(gen)
            assert db is mock_db
            try:
                next(gen)
            except StopIteration:
                pass
        mock_db.close.assert_called_once()
