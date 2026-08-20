import pytest
from fastapi.testclient import TestClient
from apps.api.main import app, lifespan
from packages.auth.jwt import validate_secret_key


def test_startup_succeeds_with_valid_key_in_production(monkeypatch):
    monkeypatch.setenv('NOVA_ENV', 'production')
    monkeypatch.setenv('SECRET_KEY', 'valid-production-secret-key-that-is-at-least-32-chars-long!')

    with TestClient(app) as client:
        response = client.get('/api/health')
        assert response.status_code == 200
        assert response.json() == {'status': 'ok', 'app': 'Nova App'}


def test_startup_fails_fast_when_secret_key_missing_in_production(monkeypatch):
    monkeypatch.setenv('NOVA_ENV', 'production')
    monkeypatch.delenv('SECRET_KEY', raising=False)

    with pytest.raises(RuntimeError, match='SECRET_KEY environment variable is required'):
        with TestClient(app):
            pass


def test_startup_fails_fast_when_secret_key_short_in_production(monkeypatch):
    monkeypatch.setenv('NOVA_ENV', 'production')
    monkeypatch.setenv('SECRET_KEY', 'too-short-secret-key')

    with pytest.raises(RuntimeError, match='at least 32 characters long'):
        with TestClient(app):
            pass


def test_startup_fails_fast_when_secret_key_is_placeholder_in_production(monkeypatch):
    monkeypatch.setenv('ENVIRONMENT', 'production')
    monkeypatch.setenv('SECRET_KEY', 'change-me-in-production-long-enough-32chars')

    with pytest.raises(RuntimeError, match='insecure default or placeholder'):
        with TestClient(app):
            pass


def test_startup_permits_defaults_in_development_mode(monkeypatch):
    monkeypatch.delenv('NOVA_ENV', raising=False)
    monkeypatch.delenv('ENVIRONMENT', raising=False)
    monkeypatch.setenv('SECRET_KEY', 'change-me-in-production')

    with TestClient(app) as client:
        response = client.get('/api/health')
        assert response.status_code == 200


@pytest.mark.asyncio
async def test_lifespan_context_manager_validation(monkeypatch):
    # In production with invalid key, entering lifespan must raise RuntimeError
    monkeypatch.setenv('NOVA_ENV', 'production')
    monkeypatch.setenv('SECRET_KEY', 'short')

    with pytest.raises(RuntimeError):
        async with lifespan(app):
            pass

    # In production with valid key, entering lifespan succeeds
    monkeypatch.setenv('SECRET_KEY', 'another-valid-secure-key-32-chars-long-example!')
    async with lifespan(app):
        pass
