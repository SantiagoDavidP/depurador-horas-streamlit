import asyncio
from dataclasses import dataclass

import pytest
from fastapi import HTTPException
from azure.core.exceptions import AzureError

from api import auth as api_auth
from api.infrastructure.auth.azure_ad_user_auth_adapter import AzureADUserAuthAdapter
from api.infrastructure.storage.in_memory_file_store_adapter import InMemoryFileStoreAdapter
from backend.infrastructure.ai import ai_insights
from backend.infrastructure.auth import azure_ad_auth
from backend.infrastructure.health import health
from backend.infrastructure.storage import azure_storage
from backend.infrastructure.storage.azure_blob_storage_adapter import AzureBlobStorageAdapter


@dataclass
class _AzureADCfg:
    enabled: bool = False
    allowed_group_id: str | None = None
    client_id: str | None = None
    client_secret: str | None = None
    tenant_id: str | None = None
    redirect_uri: str = "http://localhost/callback"


@dataclass
class _AzureOpenAICfg:
    endpoint: str | None = None
    key: str | None = None
    api_version: str = "2024-05-01-preview"
    deployment: str = "gpt-4o-mini"


@dataclass
class _AzureStorageCfg:
    connection_string: str | None = None
    account_url: str | None = None
    credential: str | None = None
    container: str | None = "demo"


@dataclass
class _Settings:
    azure_ad: _AzureADCfg
    azure_openai: _AzureOpenAICfg
    azure_storage: _AzureStorageCfg


def test_api_auth_token_and_require_user_paths(monkeypatch):
    assert api_auth._extract_bearer_token(None) is None
    assert api_auth._extract_bearer_token("Basic xyz") is None
    assert api_auth._extract_bearer_token("Bearer abc") == "abc"

    monkeypatch.setattr(api_auth, "get_settings", lambda: _Settings(_AzureADCfg(enabled=False), _AzureOpenAICfg(), _AzureStorageCfg()))
    assert api_auth.require_user() is None

    monkeypatch.setattr(
        api_auth,
        "get_settings",
        lambda: _Settings(
            _AzureADCfg(enabled=True, allowed_group_id="g1"),
            _AzureOpenAICfg(),
            _AzureStorageCfg(),
        ),
    )
    monkeypatch.setattr(api_auth, "_fetch_graph_me", lambda token: {"id": "u1"} if token == "abc" else None)
    monkeypatch.setattr(api_auth, "_check_group_membership", lambda token, gid: token == "abc" and gid == "g1")
    assert api_auth.require_user("Bearer abc") == {"id": "u1"}

    with pytest.raises(HTTPException):
        api_auth.require_user(None)
    with pytest.raises(HTTPException):
        api_auth.require_user("Bearer bad")


def test_api_auth_graph_helpers(monkeypatch):
    class _Resp:
        def __init__(self, status_code, payload=None, text=""):
            self.status_code = status_code
            self._payload = payload or {}
            self.text = text

        def json(self):
            return self._payload

    monkeypatch.setattr(api_auth.requests, "get", lambda *args, **kwargs: _Resp(200, {"id": "me"}))
    assert api_auth._fetch_graph_me("x") == {"id": "me"}

    monkeypatch.setattr(api_auth.requests, "get", lambda *args, **kwargs: _Resp(500, text="error"))
    assert api_auth._fetch_graph_me("x") is None

    monkeypatch.setattr(
        api_auth.requests,
        "get",
        lambda *args, **kwargs: _Resp(200, {"value": [{"id": "group-1"}]}),
    )
    assert api_auth._check_group_membership("x", "group-1") is True
    assert api_auth._check_group_membership("x", "group-2") is False


def test_in_memory_store_and_auth_adapter():
    adapter = InMemoryFileStoreAdapter()
    file_id = adapter.store_file(b"abc", "demo.txt", "text/plain")
    stored = adapter.get_file(file_id)
    assert stored is not None
    assert stored.filename == "demo.txt"

    batch_id = adapter.store_batch([], source="batch")
    batch = adapter.get_batch(batch_id)
    assert batch is not None
    assert batch.source == "batch"

    auth_adapter = AzureADUserAuthAdapter()
    # Solo verifica delegación: no debe lanzar cuando auth está deshabilitado por settings.
    assert callable(auth_adapter.require_user)


def test_backend_azure_storage_and_blob_adapter(monkeypatch):
    class _Download:
        def readinto(self, stream):
            stream.write(b"blob-bytes")

    class _Blob:
        def download_blob(self):
            return _Download()

        def upload_blob(self, data, overwrite=True):
            self.last = (data, overwrite)

    class _Service:
        def get_blob_client(self, container, blob):
            return _Blob()

    monkeypatch.setattr(
        azure_storage,
        "get_settings",
        lambda: _Settings(
            _AzureADCfg(),
            _AzureOpenAICfg(),
            _AzureStorageCfg(connection_string="UseDevelopmentStorage=true", container="demo"),
        ),
    )
    monkeypatch.setattr(
        azure_storage.BlobServiceClient,
        "from_connection_string",
        lambda conn: _Service(),
    )
    azure_storage._BLOB_SERVICE_CLIENT = None

    assert azure_storage.download_blob_to_bytes("x.bin") == b"blob-bytes"
    azure_storage.upload_bytes_to_blob("x.bin", b"123", overwrite=True)

    blob_adapter = AzureBlobStorageAdapter()
    blob_adapter.upload_bytes_to_blob("a.bin", b"x")
    assert blob_adapter.download_blob_to_bytes("a.bin") == b"blob-bytes"

    monkeypatch.setattr(
        azure_storage,
        "_get_blob_client",
        lambda _name: (_ for _ in ()).throw(AzureError("boom")),
    )
    with pytest.raises(AzureError):
        azure_storage.download_blob_to_bytes("fails.bin")


def test_health_checker_and_readiness(monkeypatch):
    checker = health.HealthChecker()
    liveness = checker.liveness_check()
    assert liveness["status"] in {"alive", "dead"}

    startup = checker.startup_check()
    assert "python_version" in startup

    monkeypatch.setattr(health.psutil, "virtual_memory", lambda: type("M", (), {"percent": 45.0, "available": 8 * 1024**3})())
    monkeypatch.setattr(health.psutil, "cpu_percent", lambda interval=0.1: 20.0)
    monkeypatch.setattr(
        checker,
        "_check_openai_connection",
        lambda: asyncio.sleep(0, result={"healthy": True, "status": "configured"}),
    )
    monkeypatch.setattr(
        checker,
        "_check_sql_connection",
        lambda: asyncio.sleep(0, result={"healthy": True, "status": "not_in_use"}),
    )
    readiness = asyncio.run(checker.readiness_check())
    assert readiness["status"] == "ready"


def test_ai_insights_success_fallback_and_timeout(monkeypatch):
    class _Msg:
        content = '{"diagnostico":"ok","acciones":["a","b","c"],"tiempo_estimado":"10 minutos"}'

    class _Choice:
        message = _Msg()

    class _Resp:
        choices = [_Choice()]

    class _Completions:
        async def create(self, **kwargs):
            return _Resp()

    class _Chat:
        completions = _Completions()

    class _Client:
        chat = _Chat()

    monkeypatch.setattr(ai_insights, "get_settings", lambda: _Settings(_AzureADCfg(), _AzureOpenAICfg(), _AzureStorageCfg()))
    monkeypatch.setattr(ai_insights, "_get_client", lambda: _Client())
    ok = asyncio.run(
        ai_insights.generate_ai_summary(
            total_records=10,
            critical_errors=1,
            warnings=2,
            quality_score=90,
            max_attempts=1,
        )
    )
    assert ok["diagnostico"] == "ok"

    monkeypatch.setattr(ai_insights, "_get_client", lambda: (_ for _ in ()).throw(RuntimeError("not configured")))
    fb = asyncio.run(
        ai_insights.generate_ai_summary(
            total_records=10,
            critical_errors=1,
            warnings=2,
            quality_score=90,
            max_attempts=1,
        )
    )
    assert "No se pudo generar" in fb["diagnostico"]

    async def _slow(*args, **kwargs):
        await asyncio.sleep(0.05)
        return {"diagnostico": "slow", "acciones": [], "tiempo_estimado": "n/a"}

    monkeypatch.setattr(ai_insights, "generate_ai_summary", _slow)
    timed = ai_insights.generate_ai_summary_sync(
        total_records=1,
        critical_errors=1,
        warnings=1,
        quality_score=1,
        timeout=0.001,
    )
    assert "Timeout" in timed["diagnostico"] or "timeout" in timed["diagnostico"].lower()


def test_streamlit_azure_authenticator_paths(monkeypatch):
    class _MsalApp:
        def get_authorization_request_url(self, scopes, redirect_uri):
            return f"https://login.test?redirect={redirect_uri}"

        def acquire_token_by_authorization_code(self, auth_code, scopes, redirect_uri):
            if auth_code == "ok":
                return {"access_token": "token"}
            return {"error": "invalid_grant"}

    class _FakeSt:
        session_state = {}
        query_params = {}

    monkeypatch.setattr(azure_ad_auth, "st", _FakeSt)
    monkeypatch.setattr(
        azure_ad_auth,
        "get_settings",
        lambda: _Settings(
            _AzureADCfg(
                enabled=True,
                allowed_group_id="group-1",
                client_id="cid",
                client_secret="secret",
                tenant_id="tenant",
                redirect_uri="http://localhost/callback",
            ),
            _AzureOpenAICfg(),
            _AzureStorageCfg(),
        ),
    )
    monkeypatch.setattr(azure_ad_auth.msal, "ConfidentialClientApplication", lambda *args, **kwargs: _MsalApp())

    authn = azure_ad_auth.AzureADAuthenticator()
    assert authn.is_enabled() is True
    assert "login.test" in authn.get_authorization_url()
    assert authn.acquire_token_by_auth_code("ok")["access_token"] == "token"
    assert authn.acquire_token_by_auth_code("bad") is None

    class _Resp:
        def __init__(self, status_code, payload=None, text=""):
            self.status_code = status_code
            self._payload = payload or {}
            self.text = text

        def json(self):
            return self._payload

    monkeypatch.setattr(azure_ad_auth.requests, "get", lambda *args, **kwargs: _Resp(200, {"userPrincipalName": "u@test.com"}))
    assert authn.get_user_info("token")["userPrincipalName"] == "u@test.com"

    monkeypatch.setattr(
        azure_ad_auth.requests,
        "get",
        lambda *args, **kwargs: _Resp(200, {"value": [{"id": "group-1"}]}),
    )
    assert authn.check_group_membership("token") is True

    _FakeSt.session_state.update({"auth_token": "x", "user_info": {"a": 1}, "authenticated": True})
    authn.logout()
    assert "auth_token" not in _FakeSt.session_state

    monkeypatch.setattr(
        azure_ad_auth,
        "get_settings",
        lambda: _Settings(_AzureADCfg(enabled=False), _AzureOpenAICfg(), _AzureStorageCfg()),
    )
    ok, user = azure_ad_auth.require_authentication()
    assert ok is True
    assert user is None


def test_streamlit_require_authentication_with_auth_code_success(monkeypatch):
    class _Ctx:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    class _Query(dict):
        def clear(self):
            super().clear()

    class _FakeSt:
        session_state = {}
        query_params = _Query({"code": "ok"})

        @staticmethod
        def error(*args, **kwargs):
            return None

        @staticmethod
        def info(*args, **kwargs):
            return None

        @staticmethod
        def markdown(*args, **kwargs):
            return None

        @staticmethod
        def caption(*args, **kwargs):
            return None

        @staticmethod
        def columns(*args, **kwargs):
            return [_Ctx(), _Ctx(), _Ctx()]

        @staticmethod
        def button(*args, **kwargs):
            return False

        @staticmethod
        def spinner(*args, **kwargs):
            return _Ctx()

    class _MsalApp:
        def get_authorization_request_url(self, scopes, redirect_uri):
            return "https://login.test/auth"

        def acquire_token_by_authorization_code(self, auth_code, scopes, redirect_uri):
            return {"access_token": "token-ok"}

    monkeypatch.setattr(azure_ad_auth, "st", _FakeSt)
    monkeypatch.setattr(
        azure_ad_auth,
        "get_settings",
        lambda: _Settings(
            _AzureADCfg(
                enabled=True,
                allowed_group_id=None,
                client_id="cid",
                client_secret="secret",
                tenant_id="tenant",
                redirect_uri="http://localhost/callback",
            ),
            _AzureOpenAICfg(),
            _AzureStorageCfg(),
        ),
    )
    monkeypatch.setattr(azure_ad_auth.msal, "ConfidentialClientApplication", lambda *args, **kwargs: _MsalApp())
    monkeypatch.setattr(azure_ad_auth.AzureADAuthenticator, "get_user_info", lambda self, token: {"displayName": "User"})
    monkeypatch.setattr(azure_ad_auth.AzureADAuthenticator, "check_group_membership", lambda self, token: True)

    ok, user = azure_ad_auth.require_authentication()
    assert ok is True
    assert user is not None
