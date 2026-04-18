"""Tests for Clerk auth integration (Slice 1 + Slice 2).

Covers:
    - JWT verification against a locally-generated RSA key pair, with JWKS
      served by a monkeypatched signing-key fetcher.
    - JIT user provisioning (create / link by email / link by clerk id).
    - Svix webhook HMAC verification and user.created/updated/deleted flows.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import time
from typing import Any

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
import jwt as pyjwt

from hexmind.archive.db_models import Base, UserDB
from hexmind.archive import database as db_module
from hexmind.api.routes_clerk_webhooks import router as clerk_webhook_router
from hexmind.auth import clerk_verifier
from hexmind.auth.clerk_provisioner import get_or_provision_user
from hexmind.auth.clerk_verifier import ClerkAuthError, ClerkClaims, verify_clerk_jwt


# ---------------------------------------------------------------------------
# Key generation helpers
# ---------------------------------------------------------------------------

TEST_ISSUER = "https://test-clerk.example.com"
TEST_KID = "test-kid-1"


@pytest.fixture(scope="module")
def rsa_key_pair():
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    return private_key, private_pem


def _issue_clerk_jwt(
    private_pem: bytes,
    *,
    sub: str = "user_test_abc",
    issuer: str = TEST_ISSUER,
    exp_delta: int = 60,
    email: str | None = None,
    include_sid: bool = True,
) -> str:
    now = int(time.time())
    payload: dict[str, Any] = {
        "sub": sub,
        "iss": issuer,
        "iat": now,
        "exp": now + exp_delta,
    }
    if email is not None:
        payload["email"] = email
    if include_sid:
        payload["sid"] = "sess_test_xyz"
    return pyjwt.encode(
        payload,
        private_pem,
        algorithm="RS256",
        headers={"kid": TEST_KID},
    )


@pytest.fixture
def patch_clerk_issuer(monkeypatch):
    monkeypatch.setenv("CLERK_JWT_ISSUER", TEST_ISSUER)
    # Reset module-level JWKS cache between tests.
    clerk_verifier._jwks_client = None
    clerk_verifier._cached_issuer = None
    yield
    clerk_verifier._jwks_client = None
    clerk_verifier._cached_issuer = None


@pytest.fixture
def patch_signing_key(monkeypatch, rsa_key_pair):
    """Replace JWKS lookup with the local RSA public key."""
    private_key, _ = rsa_key_pair
    public_key = private_key.public_key()

    class _FakeSigningKey:
        def __init__(self, key):
            self.key = key

    class _FakeJWKSClient:
        def get_signing_key_from_jwt(self, token):
            return _FakeSigningKey(public_key)

    monkeypatch.setattr(
        clerk_verifier,
        "get_jwks_client",
        lambda: _FakeJWKSClient(),
    )


# ---------------------------------------------------------------------------
# Database fixtures (mirror test_database.py pattern)
# ---------------------------------------------------------------------------


@pytest.fixture
async def engine():
    eng = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield eng
    await eng.dispose()


@pytest.fixture
async def session(engine) -> AsyncSession:
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as sess:
        yield sess


# ---------------------------------------------------------------------------
# JWT verification
# ---------------------------------------------------------------------------


class TestVerifyClerkJWT:
    def test_valid_token(self, rsa_key_pair, patch_clerk_issuer, patch_signing_key):
        _, private_pem = rsa_key_pair
        token = _issue_clerk_jwt(private_pem, sub="user_abc", email="x@example.com")
        claims = verify_clerk_jwt(token)
        assert isinstance(claims, ClerkClaims)
        assert claims.sub == "user_abc"
        assert claims.email == "x@example.com"
        assert claims.issuer == TEST_ISSUER
        assert claims.session_id == "sess_test_xyz"

    def test_expired_token(self, rsa_key_pair, patch_clerk_issuer, patch_signing_key):
        _, private_pem = rsa_key_pair
        token = _issue_clerk_jwt(private_pem, exp_delta=-10)
        with pytest.raises(ClerkAuthError, match="expired"):
            verify_clerk_jwt(token)

    def test_wrong_issuer(self, rsa_key_pair, patch_clerk_issuer, patch_signing_key):
        _, private_pem = rsa_key_pair
        token = _issue_clerk_jwt(private_pem, issuer="https://evil.com")
        with pytest.raises(ClerkAuthError, match="issuer"):
            verify_clerk_jwt(token)

    def test_missing_issuer_env(self, monkeypatch):
        monkeypatch.delenv("CLERK_JWT_ISSUER", raising=False)
        with pytest.raises(ClerkAuthError, match="CLERK_JWT_ISSUER"):
            verify_clerk_jwt("anything")


# ---------------------------------------------------------------------------
# JIT provisioning
# ---------------------------------------------------------------------------


class TestProvisionUser:
    async def test_creates_new_user(self, session: AsyncSession):
        claims = ClerkClaims(sub="user_new_1", email="new@example.com", issuer=TEST_ISSUER)
        user = await get_or_provision_user(session, claims)
        assert user.clerk_user_id == "user_new_1"
        assert user.email == "new@example.com"
        assert user.password_hash.startswith("clerk:")

    async def test_returns_existing_by_clerk_id(self, session: AsyncSession):
        claims = ClerkClaims(sub="user_exist_1", email="a@b.com", issuer=TEST_ISSUER)
        u1 = await get_or_provision_user(session, claims)
        u2 = await get_or_provision_user(session, claims)
        assert u1.id == u2.id

    async def test_links_legacy_email_user(self, session: AsyncSession):
        legacy = UserDB(
            email="legacy@example.com",
            display_name="Legacy",
            password_hash="bcrypt-hash",
        )
        session.add(legacy)
        await session.flush()
        assert legacy.clerk_user_id is None

        claims = ClerkClaims(
            sub="user_clerk_1",
            email="legacy@example.com",
            issuer=TEST_ISSUER,
        )
        user = await get_or_provision_user(session, claims)
        assert user.id == legacy.id
        assert user.clerk_user_id == "user_clerk_1"
        # Password hash is preserved on linking (they can still log in via
        # legacy path if we ever flip back).
        assert user.password_hash == "bcrypt-hash"


# ---------------------------------------------------------------------------
# Webhook HMAC verification
# ---------------------------------------------------------------------------


def _sign_svix(secret_raw: bytes, svix_id: str, ts: str, body: bytes) -> str:
    signed = f"{svix_id}.{ts}.".encode() + body
    return base64.b64encode(hmac.new(secret_raw, signed, hashlib.sha256).digest()).decode()


@pytest.fixture
def webhook_app(monkeypatch, engine):
    """Build a FastAPI app with the Clerk webhook router + shared DB factory."""
    factory = async_sessionmaker(engine, expire_on_commit=False)

    monkeypatch.setattr(db_module, "_session_factory", factory, raising=False)
    # Webhook module calls get_session_factory(); make sure that path returns ours.
    from hexmind.archive.database import get_session_factory  # noqa: F401

    secret_raw = b"0123456789abcdef0123456789abcdef"
    secret_b64 = base64.b64encode(secret_raw).decode()
    monkeypatch.setenv("CLERK_WEBHOOK_SECRET", f"whsec_{secret_b64}")

    app = FastAPI()
    app.include_router(clerk_webhook_router)
    return app, secret_raw, factory


class TestClerkWebhook:
    def test_rejects_missing_headers(self, webhook_app):
        app, _, _ = webhook_app
        client = TestClient(app)
        resp = client.post("/api/webhooks/clerk", json={"type": "user.created"})
        assert resp.status_code == 400

    def test_rejects_bad_signature(self, webhook_app):
        app, _, _ = webhook_app
        client = TestClient(app)
        body = json.dumps({"type": "user.created", "data": {"id": "user_x"}}).encode()
        resp = client.post(
            "/api/webhooks/clerk",
            content=body,
            headers={
                "svix-id": "msg_1",
                "svix-timestamp": str(int(time.time())),
                "svix-signature": "v1,badsignature",
                "content-type": "application/json",
            },
        )
        assert resp.status_code == 401

    def test_rejects_stale_timestamp(self, webhook_app):
        app, secret, _ = webhook_app
        client = TestClient(app)
        body = json.dumps({"type": "user.created", "data": {"id": "user_x"}}).encode()
        old_ts = str(int(time.time()) - 3600)
        sig = _sign_svix(secret, "msg_1", old_ts, body)
        resp = client.post(
            "/api/webhooks/clerk",
            content=body,
            headers={
                "svix-id": "msg_1",
                "svix-timestamp": old_ts,
                "svix-signature": f"v1,{sig}",
                "content-type": "application/json",
            },
        )
        assert resp.status_code == 400

    async def test_user_created_inserts_row(self, webhook_app):
        app, secret, factory = webhook_app
        client = TestClient(app)
        body = json.dumps(
            {
                "type": "user.created",
                "data": {
                    "id": "user_wh_1",
                    "primary_email_address_id": "idn_1",
                    "email_addresses": [
                        {"id": "idn_1", "email_address": "wh@example.com"}
                    ],
                    "first_name": "Web",
                    "last_name": "Hook",
                },
            }
        ).encode()
        ts = str(int(time.time()))
        sig = _sign_svix(secret, "msg_user_1", ts, body)
        resp = client.post(
            "/api/webhooks/clerk",
            content=body,
            headers={
                "svix-id": "msg_user_1",
                "svix-timestamp": ts,
                "svix-signature": f"v1,{sig}",
                "content-type": "application/json",
            },
        )
        assert resp.status_code == 204

        async with factory() as sess:
            result = await sess.execute(
                select(UserDB).where(UserDB.clerk_user_id == "user_wh_1")
            )
            user = result.scalar_one()
            assert user.email == "wh@example.com"
            assert user.display_name == "Web Hook"

    async def test_user_deleted_detaches(self, webhook_app):
        app, secret, factory = webhook_app
        client = TestClient(app)

        # Pre-seed a linked user.
        async with factory() as sess:
            sess.add(
                UserDB(
                    email="del@example.com",
                    display_name="del",
                    password_hash="clerk:user_wh_del",
                    clerk_user_id="user_wh_del",
                )
            )
            await sess.commit()

        body = json.dumps(
            {"type": "user.deleted", "data": {"id": "user_wh_del"}}
        ).encode()
        ts = str(int(time.time()))
        sig = _sign_svix(secret, "msg_user_del", ts, body)
        resp = client.post(
            "/api/webhooks/clerk",
            content=body,
            headers={
                "svix-id": "msg_user_del",
                "svix-timestamp": ts,
                "svix-signature": f"v1,{sig}",
                "content-type": "application/json",
            },
        )
        assert resp.status_code == 204

        async with factory() as sess:
            result = await sess.execute(
                select(UserDB).where(UserDB.email == "del@example.com")
            )
            user = result.scalar_one()
            assert user.clerk_user_id is None
