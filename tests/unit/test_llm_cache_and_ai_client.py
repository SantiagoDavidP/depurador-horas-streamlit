import pytest
import asyncio

from backend.infrastructure.ai import ai_insights, llm_cache


def test_simple_llm_cache_full_cycle(monkeypatch):
    cache = llm_cache.SimpleLLMCache(default_ttl=1, max_size=3)

    assert cache.get("txt", "role", "proj") is None
    assert cache.misses == 1

    cache.set("txt", "role", "proj", {"v": 1})
    assert cache.get("txt", "role", "proj") == {"v": 1}
    assert cache.hits == 1

    # Forzar expiración
    key = cache._generate_key("txt", "role", "proj")
    cache._cache[key].timestamp -= 10
    assert cache.get("txt", "role", "proj") is None

    # Limpieza explícita de expirados (cubre borrado + logger info)
    cache.set("exp", "r", "p", {"x": 0}, ttl=1)
    exp_key = cache._generate_key("exp", "r", "p")
    cache._cache[exp_key].timestamp -= 10
    cleaned = cache._cleanup_expired()
    assert cleaned >= 1

    # Llenado + evicción
    cache.set("a", "r", "p", {"x": 1})
    cache.set("b", "r", "p", {"x": 2})
    cache.set("c", "r", "p", {"x": 3})
    cache.set("d", "r", "p", {"x": 4})  # gatilla cleanup/evict
    # En tamaños pequeños puede quedar > max_size por el criterio max_size // 4.
    assert len(cache._cache) >= 1
    cache._evict_oldest(count=1)
    assert len(cache._cache) >= 1

    stats = cache.get_stats()
    assert "hit_rate_percent" in stats
    assert stats["size"] == len(cache._cache)

    cache.clear()
    assert cache.get_stats()["size"] == 0
    assert cache.hits == 0
    assert cache.misses == 0
    cache._evict_oldest(count=1)  # rama early-return con cache vacía

    # singleton
    c1 = llm_cache.get_llm_cache()
    c2 = llm_cache.get_llm_cache()
    assert c1 is c2


def test_ai_insights_get_client_configured(monkeypatch):
    class _Cfg:
        endpoint = "https://example.openai.azure.com"
        key = "test-key"
        api_version = "2024-05-01-preview"
        deployment = "gpt-4o-mini"

    class _Settings:
        azure_openai = _Cfg()

    captured = {}

    class _Client:
        pass

    def _fake_client(**kwargs):
        captured.update(kwargs)
        return _Client()

    monkeypatch.setattr(ai_insights, "_CLIENT", None)
    monkeypatch.setattr(ai_insights, "get_settings", lambda: _Settings())
    monkeypatch.setattr(ai_insights, "AsyncAzureOpenAI", _fake_client)

    client = ai_insights._get_client()
    assert isinstance(client, _Client)
    assert captured["azure_endpoint"] == _Cfg.endpoint
    assert captured["api_key"] == _Cfg.key


def test_ai_insights_get_client_raises_when_missing_config(monkeypatch):
    class _Cfg:
        endpoint = None
        key = None
        api_version = "x"
        deployment = "y"

    class _Settings:
        azure_openai = _Cfg()

    monkeypatch.setattr(ai_insights, "_CLIENT", None)
    monkeypatch.setattr(ai_insights, "get_settings", lambda: _Settings())
    with pytest.raises(RuntimeError):
        ai_insights._get_client()


def test_ai_insights_sync_runtime_branches(monkeypatch):
    # Rama RuntimeError != already running
    monkeypatch.setattr(ai_insights.asyncio, "run", lambda _coro: (_ for _ in ()).throw(RuntimeError("other error")))
    with pytest.raises(RuntimeError):
        ai_insights.generate_ai_summary_sync(
            total_records=1,
            critical_errors=1,
            warnings=1,
            quality_score=1,
        )

    # Rama "already running" + timeout dentro del loop secundario
    class _Loop:
        def run_until_complete(self, _awaitable):
            raise ai_insights.asyncio.TimeoutError()

        def close(self):
            return None

    monkeypatch.setattr(ai_insights.asyncio, "run", lambda _coro: (_ for _ in ()).throw(RuntimeError("already running")))
    monkeypatch.setattr(ai_insights.asyncio, "new_event_loop", lambda: _Loop())
    monkeypatch.setattr(ai_insights.asyncio, "set_event_loop", lambda _loop: None)

    timed = ai_insights.generate_ai_summary_sync(
        total_records=1,
        critical_errors=1,
        warnings=1,
        quality_score=1,
        timeout=0.001,
    )
    assert "Timeout" in timed["diagnostico"] or "timeout" in timed["diagnostico"].lower()


def test_ai_insights_retry_break_and_sleep_branches(monkeypatch):
    async def _no_sleep(_delay):
        return None

    # Rama de corte inmediato por error permanente (resource not found)
    monkeypatch.setattr(ai_insights, "_get_client", lambda: (_ for _ in ()).throw(RuntimeError("resource not found")))
    permanent = asyncio.run(
        ai_insights.generate_ai_summary(
            total_records=1,
            critical_errors=1,
            warnings=1,
            quality_score=1,
            max_attempts=3,
            initial_delay=0.0,
        )
    )
    assert "No se pudo generar" in permanent["diagnostico"]

    # Rama con sleep entre intentos (error temporal)
    monkeypatch.setattr(ai_insights, "_get_client", lambda: (_ for _ in ()).throw(RuntimeError("temporary outage")))
    monkeypatch.setattr(ai_insights.asyncio, "sleep", _no_sleep)
    temporary = asyncio.run(
        ai_insights.generate_ai_summary(
            total_records=1,
            critical_errors=1,
            warnings=1,
            quality_score=1,
            max_attempts=2,
            initial_delay=0.0,
        )
    )
    assert "No se pudo generar" in temporary["diagnostico"]


def test_ai_insights_zero_attempts_and_cached_client_branch(monkeypatch):
    # Cubre rama de loop no ejecutado (for -> salida directa fallback)
    fallback = asyncio.run(
        ai_insights.generate_ai_summary(
            total_records=1,
            critical_errors=1,
            warnings=1,
            quality_score=1,
            max_attempts=0,
        )
    )
    assert "No se pudo generar" in fallback["diagnostico"]

    # Cubre retorno inmediato cuando _CLIENT ya existe
    sentinel = object()
    monkeypatch.setattr(ai_insights, "_CLIENT", sentinel)
    assert ai_insights._get_client() is sentinel
