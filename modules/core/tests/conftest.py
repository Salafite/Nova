from unittest.mock import MagicMock, patch
import bcrypt
import pytest

_mock_pool = MagicMock()
_mock_conn = MagicMock()
_mock_pool.getconn.return_value = _mock_conn

_pool_patcher = patch('psycopg2.pool.SimpleConnectionPool', return_value=_mock_pool)
_pool_patcher.start()

from packages.auth.jwt import create_access_token, create_refresh_token, decode_token


@pytest.fixture
def mock_db():
    with patch('packages.database.connection.get_connection', return_value=_mock_conn):
        with patch('packages.database.connection.release_connection'):
            yield


@pytest.fixture
def mock_bcrypt():
    with patch('bcrypt.checkpw', return_value=True):
        yield


@pytest.fixture
def sample_user():
    return {
        'id': 1,
        'username': 'testuser',
        'password_hash': bcrypt.hashpw('password'.encode(), bcrypt.gensalt()).decode(),
        'full_name': 'Test User',
        'email': 'test@novaerp.local',
        'role': 'Admin',
        'permissions': ['*'],
        'status': 'Active',
    }


@pytest.fixture
def valid_token():
    return create_access_token(1)


@pytest.fixture
def valid_refresh_token():
    return create_refresh_token(1)
