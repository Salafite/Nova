import os
from unittest.mock import MagicMock, patch

os.environ.setdefault('SECRET_KEY', 'test-secret-key-for-pytest-32-bytes-long!!')
os.environ.setdefault('DB_HOST', 'localhost')
os.environ.setdefault('DB_PORT', '5432')
os.environ.setdefault('DB_NAME', 'nova_erp')
os.environ.setdefault('DB_USER', 'nova')
os.environ.setdefault('DB_PASSWORD', 'nova_secret')
os.environ.setdefault('DB_SCHEMA', 'Nova')
os.environ.setdefault('ACCESS_TOKEN_EXPIRE_MINUTES', '1440')
os.environ.setdefault('REFRESH_TOKEN_EXPIRE_DAYS', '7')
os.environ.setdefault('ALLOWED_ORIGINS', '*')

_mock_pool = MagicMock()
_mock_conn = MagicMock()
_mock_pool.getconn.return_value = _mock_conn

_pool_patcher = patch('psycopg2.pool.SimpleConnectionPool', return_value=_mock_pool)
_pool_patcher.start()

