from unittest.mock import patch, MagicMock
import pytest
import psycopg2


@pytest.fixture(autouse=True)
def mock_db():
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_cursor.rowcount = 1
    mock_context = MagicMock()
    mock_context.__enter__.return_value = mock_cursor
    mock_conn.cursor.return_value = mock_context

    with patch('modules.core.repositories.base.get_connection', return_value=mock_conn), \
         patch('modules.core.repositories.base.release_connection'), \
         patch('packages.database.connection.get_connection', return_value=mock_conn), \
         patch('packages.database.connection.release_connection'):
        yield {'conn': mock_conn, 'cursor': mock_cursor, 'ctx': mock_context}


class TestCrudRepository:
    def test_list_without_filters(self, mock_db):
        from modules.core.repositories.base import CrudRepository
        repo = CrudRepository('T0001', business_columns=['id', 'name'])
        mock_db['cursor'].fetchall.return_value = [{'id': 1, 'name': 'test'}]

        result = repo.list()

        sql = mock_db['cursor'].execute.call_args[0][0]
        assert 't0001' in sql.lower()
        assert result == [{'id': 1, 'name': 'test'}]

    def test_list_with_filters(self, mock_db):
        from modules.core.repositories.base import CrudRepository
        repo = CrudRepository('T0001', business_columns=['id', 'name', 'is_active'])
        mock_db['cursor'].fetchall.return_value = [{'id': 2, 'name': 'filtered'}]

        result = repo.list(filters={'name': 'test'})

        sql = mock_db['cursor'].execute.call_args[0][0]
        assert '"name" = %s' in sql
        assert 'TRUE' in sql

    def test_get_returns_row(self, mock_db):
        from modules.core.repositories.base import CrudRepository
        repo = CrudRepository('T0001', business_columns=['id', 'name'])
        mock_db['cursor'].fetchone.return_value = {'id': 1, 'name': 'test'}

        result = repo.get(1)

        assert result == {'id': 1, 'name': 'test'}

    def test_get_returns_none(self, mock_db):
        from modules.core.repositories.base import CrudRepository
        repo = CrudRepository('T0001', business_columns=['id', 'name'])
        mock_db['cursor'].fetchone.return_value = None

        result = repo.get(999)

        assert result is None

    def test_create_returns_row(self, mock_db):
        from modules.core.repositories.base import CrudRepository
        repo = CrudRepository('T0001', business_columns=['id', 'name'])
        mock_db['cursor'].fetchone.return_value = {'id': 1, 'name': 'new_item'}

        result = repo.create({'name': 'new_item'})

        assert result == {'id': 1, 'name': 'new_item'}
        mock_db['conn'].commit.assert_called_once()

    def test_create_rollback_on_error(self, mock_db):
        from modules.core.repositories.base import CrudRepository
        repo = CrudRepository('T0001', business_columns=['id', 'name'])
        mock_db['cursor'].execute.side_effect = psycopg2.Error('db error')

        with pytest.raises(psycopg2.Error):
            repo.create({'name': 'fail'})
        mock_db['conn'].rollback.assert_called_once()

    def test_update_returns_row(self, mock_db):
        from modules.core.repositories.base import CrudRepository
        repo = CrudRepository('T0001', business_columns=['id', 'name'])
        mock_db['cursor'].fetchone.return_value = {'id': 1, 'name': 'updated'}

        result = repo.update(1, {'name': 'updated_name'})

        assert result == {'id': 1, 'name': 'updated'}
        mock_db['conn'].commit.assert_called_once()

    def test_update_rollback_on_error(self, mock_db):
        from modules.core.repositories.base import CrudRepository
        repo = CrudRepository('T0001', business_columns=['id', 'name'])
        mock_db['cursor'].execute.side_effect = psycopg2.Error('db error')

        with pytest.raises(psycopg2.Error):
            repo.update(1, {'name': 'fail'})
        mock_db['conn'].rollback.assert_called_once()

    def test_delete_soft_with_is_active(self, mock_db):
        from modules.core.repositories.base import CrudRepository
        repo = CrudRepository('T0001', business_columns=['id', 'name', 'is_active'])

        result = repo.delete(1)

        sql = mock_db['cursor'].execute.call_args[0][0]
        assert 'is_active = FALSE' in sql
        assert result is True

    def test_delete_hard_without_is_active(self, mock_db):
        from modules.core.repositories.base import CrudRepository
        repo = CrudRepository('T0001', business_columns=['id', 'name'])

        result = repo.delete(1)

        sql = mock_db['cursor'].execute.call_args[0][0]
        assert 'DELETE FROM' in sql
        assert result is True

    def test_delete_rollback_on_error(self, mock_db):
        from modules.core.repositories.base import CrudRepository
        repo = CrudRepository('T0001', business_columns=['id', 'name'])
        mock_db['cursor'].execute.side_effect = psycopg2.Error('db error')

        with pytest.raises(psycopg2.Error):
            repo.delete(1)
        mock_db['conn'].rollback.assert_called_once()

    def test_list_with_limit_and_offset(self, mock_db):
        from modules.core.repositories.base import CrudRepository
        repo = CrudRepository('T0001', business_columns=['id', 'name'])
        mock_db['cursor'].fetchall.return_value = []

        repo.list(limit=10, offset=5)

        call_args = mock_db['cursor'].execute.call_args
        sql = call_args[0][0]
        params = call_args[0][1]
        assert 'LIMIT' in sql
        assert 'OFFSET' in sql
        assert 10 in params
        assert 5 in params

    def test_list_with_order_by(self, mock_db):
        from modules.core.repositories.base import CrudRepository
        repo = CrudRepository('T0001', business_columns=['id', 'name'])
        mock_db['cursor'].fetchall.return_value = []

        repo.list(order_by='name')

        sql = mock_db['cursor'].execute.call_args[0][0]
        assert 'ORDER BY "name"' in sql

    def test_list_adds_is_active_for_tables_with_column(self, mock_db):
        from modules.core.repositories.base import CrudRepository
        repo = CrudRepository('T0001', business_columns=['id', 'name', 'is_active'])
        mock_db['cursor'].fetchall.return_value = [{'id': 1, 'name': 'test', 'is_active': True}]

        repo.list()

        sql = mock_db['cursor'].execute.call_args[0][0]
        assert 'is_active = TRUE' in sql

    def test_create_excludes_pk_and_audit_columns(self, mock_db):
        from modules.core.repositories.base import CrudRepository
        repo = CrudRepository('T0001', business_columns=['id', 'name'])
        mock_db['cursor'].fetchone.return_value = {'id': 1, 'name': 'item'}

        repo.create({'id': 999, 'name': 'item', 'created_at': 'ignored'})

        sql = mock_db['cursor'].execute.call_args[0][0]
        assert '"id"' not in sql
        assert '"created_at"' not in sql
        assert '"name"' in sql
