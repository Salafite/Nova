from unittest.mock import MagicMock, patch

import pytest

_mock_pool = MagicMock()
_mock_conn = MagicMock()
_mock_cursor = MagicMock()
_mock_conn.cursor.return_value = _mock_cursor
_mock_pool.getconn.return_value = _mock_conn

_pool_patcher = patch('psycopg2.pool.SimpleConnectionPool', return_value=_mock_pool)
_pool_patcher.start()

from fastapi import FastAPI
from fastapi.testclient import TestClient
from modules.core.controllers import all_routers
from modules.inventory.controllers.adjustments import router as adjustments_router
from packages.auth.deps import get_current_user

all_routers.append(adjustments_router)

app = FastAPI()
app.dependency_overrides[get_current_user] = lambda: {'id': 1, 'username': 'test', 'role': 'Admin', 'permissions': ['*']}
for router in all_routers:
    app.include_router(router)
client = TestClient(app)


@pytest.fixture(autouse=True)
def cursor():
    _mock_cursor.fetchone.return_value = None
    _mock_cursor.fetchall.return_value = []
    _mock_cursor.rowcount = 0
    yield _mock_cursor
