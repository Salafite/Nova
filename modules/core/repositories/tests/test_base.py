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

    def test_list_with_active_tenant_context(self, mock_db):
        from modules.core.repositories.base import CrudRepository
        from modules.core.context import tenant_context

        repo = CrudRepository('T0001', business_columns=['id', 'name'])
        mock_db['cursor'].fetchall.return_value = [{'id': 1, 'name': 'item_t10', 'business_id': 10}]

        with tenant_context(10):
            res = repo.list()

        call_args = mock_db['cursor'].execute.call_args
        sql = call_args[0][0]
        params = call_args[0][1]
        assert '"business_id" = %s' in sql
        assert 10 in params
        assert res == [{'id': 1, 'name': 'item_t10', 'business_id': 10}]

    def test_list_with_active_tenant_context_and_filters(self, mock_db):
        from modules.core.repositories.base import CrudRepository
        from modules.core.context import tenant_context

        repo = CrudRepository('T0001', business_columns=['id', 'name'])
        mock_db['cursor'].fetchall.return_value = []

        with tenant_context(42):
            repo.list(filters={'name': 'widget'})

        call_args = mock_db['cursor'].execute.call_args
        sql = call_args[0][0]
        params = call_args[0][1]
        assert '"business_id" = %s' in sql
        assert '"name" = %s' in sql
        assert 42 in params
        assert 'widget' in params

    def test_list_non_tenant_table_t0059_ignores_tenant_context(self, mock_db):
        from modules.core.repositories.base import CrudRepository
        from modules.core.context import tenant_context

        repo = CrudRepository('T0059', business_columns=['id', 'tenant_name'])
        mock_db['cursor'].fetchall.return_value = [{'id': 1, 'tenant_name': 'Tenant Alpha'}]

        with tenant_context(10):
            repo.list()

        sql = mock_db['cursor'].execute.call_args[0][0]
        assert '"business_id"' not in sql

    def test_list_with_explicit_business_id_arg(self, mock_db):
        from modules.core.repositories.base import CrudRepository

        repo = CrudRepository('T0001', business_columns=['id', 'name'])
        mock_db['cursor'].fetchall.return_value = []

        repo.list(business_id=99)

        call_args = mock_db['cursor'].execute.call_args
        sql = call_args[0][0]
        params = call_args[0][1]
        assert '"business_id" = %s' in sql
        assert 99 in params

    def test_get_with_active_tenant_context(self, mock_db):
        from modules.core.repositories.base import CrudRepository
        from modules.core.context import tenant_context

        repo = CrudRepository('T0001', business_columns=['id', 'name'])
        mock_db['cursor'].fetchone.return_value = {'id': 5, 'name': 'my_item', 'business_id': 12}

        with tenant_context(12):
            res = repo.get(5)

        call_args = mock_db['cursor'].execute.call_args
        sql = call_args[0][0]
        params = call_args[0][1]
        assert '"id" = %s' in sql
        assert '"business_id" = %s' in sql
        assert params == (5, 12)
        assert res == {'id': 5, 'name': 'my_item', 'business_id': 12}

    def test_get_without_tenant_context(self, mock_db):
        from modules.core.repositories.base import CrudRepository

        repo = CrudRepository('T0001', business_columns=['id', 'name'])
        mock_db['cursor'].fetchone.return_value = {'id': 5, 'name': 'my_item'}

        repo.get(5)

        call_args = mock_db['cursor'].execute.call_args
        sql = call_args[0][0]
        params = call_args[0][1]
        assert '"id" = %s' in sql
        assert '"business_id"' not in sql
        assert params == (5,)

    def test_get_unscoped_ignores_tenant_context(self, mock_db):
        from modules.core.repositories.base import CrudRepository
        from modules.core.context import tenant_context

        repo = CrudRepository('T0001', business_columns=['id', 'name'])
        mock_db['cursor'].fetchone.return_value = {'id': 7, 'name': 'cross_tenant_item', 'business_id': 99}

        with tenant_context(10):
            res = repo.get_unscoped(7)

        call_args = mock_db['cursor'].execute.call_args
        sql = call_args[0][0]
        params = call_args[0][1]
        assert '"id" = %s' in sql
        assert '"business_id"' not in sql
        assert params == (7,)
        assert res['id'] == 7

    def test_create_auto_injects_tenant_from_context(self, mock_db):
        from modules.core.repositories.base import CrudRepository
        from modules.core.context import tenant_context

        repo = CrudRepository('T0001', business_columns=['id', 'name'])
        mock_db['cursor'].fetchone.return_value = {'id': 1, 'name': 'item1', 'business_id': 25}

        with tenant_context(25):
            res = repo.create({'name': 'item1'})

        call_args = mock_db['cursor'].execute.call_args
        sql = call_args[0][0]
        vals = call_args[0][1]
        assert '"business_id"' in sql
        assert 25 in vals
        assert res['business_id'] == 25

    def test_create_preserves_explicit_business_id(self, mock_db):
        from modules.core.repositories.base import CrudRepository
        from modules.core.context import tenant_context

        repo = CrudRepository('T0001', business_columns=['id', 'name'])
        mock_db['cursor'].fetchone.return_value = {'id': 1, 'name': 'item1', 'business_id': 50}

        with tenant_context(25):
            repo.create({'name': 'item1', 'business_id': 50})

        call_args = mock_db['cursor'].execute.call_args
        sql = call_args[0][0]
        vals = call_args[0][1]
        assert '"business_id"' in sql
        assert 50 in vals

    def test_create_non_tenant_table_t0059_does_not_inject_business_id(self, mock_db):
        from modules.core.repositories.base import CrudRepository
        from modules.core.context import tenant_context

        repo = CrudRepository('T0059', business_columns=['id', 'tenant_name'])
        mock_db['cursor'].fetchone.return_value = {'id': 1, 'tenant_name': 'Corp'}

        with tenant_context(10):
            repo.create({'tenant_name': 'Corp'})

        sql = mock_db['cursor'].execute.call_args[0][0]
        assert '"business_id"' not in sql

    def test_update_with_active_tenant_context(self, mock_db):
        from modules.core.repositories.base import CrudRepository
        from modules.core.context import tenant_context

        repo = CrudRepository('T0001', business_columns=['id', 'name'])
        mock_db['cursor'].fetchone.return_value = {'id': 3, 'name': 'new_val', 'business_id': 15}

        with tenant_context(15):
            repo.update(3, {'name': 'new_val'})

        call_args = mock_db['cursor'].execute.call_args
        sql = call_args[0][0]
        vals = call_args[0][1]
        assert '"business_id" = %s' in sql
        assert 3 in vals
        assert 15 in vals

    def test_update_excludes_business_id_from_set_clause(self, mock_db):
        from modules.core.repositories.base import CrudRepository
        from modules.core.context import tenant_context

        repo = CrudRepository('T0001', business_columns=['id', 'name'])
        mock_db['cursor'].fetchone.return_value = {'id': 3, 'name': 'updated'}

        with tenant_context(15):
            # Attempt to change business_id via payload
            repo.update(3, {'name': 'updated', 'business_id': 999})

        call_args = mock_db['cursor'].execute.call_args
        sql = call_args[0][0]
        set_part = sql.split('WHERE')[0]
        assert '"business_id" = %s' not in set_part

    def test_delete_soft_with_tenant_context(self, mock_db):
        from modules.core.repositories.base import CrudRepository
        from modules.core.context import tenant_context

        repo = CrudRepository('T0001', business_columns=['id', 'name', 'is_active'])

        with tenant_context(33):
            res = repo.delete(10)

        call_args = mock_db['cursor'].execute.call_args
        sql = call_args[0][0]
        params = call_args[0][1]
        assert 'is_active = FALSE' in sql
        assert '"business_id" = %s' in sql
        assert params == (10, 33)
        assert res is True

    def test_delete_hard_with_tenant_context(self, mock_db):
        from modules.core.repositories.base import CrudRepository
        from modules.core.context import tenant_context

        repo = CrudRepository('T0001', business_columns=['id', 'name'])

        with tenant_context(33):
            res = repo.delete(10)

        call_args = mock_db['cursor'].execute.call_args
        sql = call_args[0][0]
        params = call_args[0][1]
        assert 'DELETE FROM' in sql
        assert '"business_id" = %s' in sql
        assert params == (10, 33)
        assert res is True

    def test_count_with_active_tenant_context(self, mock_db):
        from modules.core.repositories.base import CrudRepository
        from modules.core.context import tenant_context

        repo = CrudRepository('T0001', business_columns=['id', 'name'])
        mock_db['cursor'].fetchone.return_value = {'cnt': 42}

        with tenant_context(77):
            cnt = repo.count()

        call_args = mock_db['cursor'].execute.call_args
        sql = call_args[0][0]
        params = call_args[0][1]
        assert '"business_id" = %s' in sql
        assert 77 in params
        assert cnt == 42

    def test_count_without_tenant_context(self, mock_db):
        from modules.core.repositories.base import CrudRepository

        repo = CrudRepository('T0001', business_columns=['id', 'name'])
        mock_db['cursor'].fetchone.return_value = {'cnt': 100}

        cnt = repo.count()

        call_args = mock_db['cursor'].execute.call_args
        sql = call_args[0][0]
        assert '"business_id"' not in sql
        assert cnt == 100


class TestRepositorySanitizationAndPagination:
    def test_sanitize_order_by_default_and_empty(self):
        from modules.core.repositories.base import CrudRepository
        repo = CrudRepository('T0001', pk='id')

        assert repo._sanitize_order_by(None) == 'ORDER BY "id" DESC'
        assert repo._sanitize_order_by('') == 'ORDER BY "id" DESC'
        assert repo._sanitize_order_by('   ') == 'ORDER BY "id" DESC'

    def test_sanitize_order_by_single_column(self):
        from modules.core.repositories.base import CrudRepository
        repo = CrudRepository('T0001', pk='id')

        assert repo._sanitize_order_by('name') == 'ORDER BY "name"'
        assert repo._sanitize_order_by('created_at') == 'ORDER BY "created_at"'

    def test_sanitize_order_by_directions(self):
        from modules.core.repositories.base import CrudRepository
        repo = CrudRepository('T0001', pk='id')

        assert repo._sanitize_order_by('name ASC') == 'ORDER BY "name" ASC'
        assert repo._sanitize_order_by('name desc') == 'ORDER BY "name" DESC'
        assert repo._sanitize_order_by('created_at DESC') == 'ORDER BY "created_at" DESC'

    def test_sanitize_order_by_prefix_notation(self):
        from modules.core.repositories.base import CrudRepository
        repo = CrudRepository('T0001', pk='id')

        assert repo._sanitize_order_by('-created_at') == 'ORDER BY "created_at" DESC'
        assert repo._sanitize_order_by('+name') == 'ORDER BY "name" ASC'

    def test_sanitize_order_by_multiple_columns(self):
        from modules.core.repositories.base import CrudRepository
        repo = CrudRepository('T0001', pk='id')

        assert repo._sanitize_order_by('name ASC, created_at DESC') == 'ORDER BY "name" ASC, "created_at" DESC'
        assert repo._sanitize_order_by('+name, -created_at') == 'ORDER BY "name" ASC, "created_at" DESC'

    def test_sanitize_order_by_sql_injection_neutralized(self):
        from modules.core.repositories.base import CrudRepository
        repo = CrudRepository('T0001', pk='id')

        # Semicolons and SQL statements
        assert repo._sanitize_order_by('name; DROP TABLE t0001; --') == 'ORDER BY "id" DESC'
        # Quotes and booleans
        assert repo._sanitize_order_by("name' OR '1'='1") == 'ORDER BY "id" DESC'
        # Nested subqueries and functions
        assert repo._sanitize_order_by('id ASC, (SELECT password FROM users)') == 'ORDER BY "id" ASC'

    def test_sanitize_filters_valid(self):
        from modules.core.repositories.base import CrudRepository
        repo = CrudRepository('T0001', pk='id')

        clauses, params = repo._sanitize_filters({'name': 'Widget', 'is_active': True})
        assert clauses == ['"name" = %s', '"is_active" = %s']
        assert params == ['Widget', True]

    def test_sanitize_filters_rejects_malformed_keys(self):
        from modules.core.repositories.base import CrudRepository
        repo = CrudRepository('T0001', pk='id')

        clauses, params = repo._sanitize_filters({
            'valid_col': 123,
            'name; DROP TABLE t0001; --': 'exploit',
            'bad col name': 'val',
            'col"quoted': 'val',
        })
        assert clauses == ['"valid_col" = %s']
        assert params == [123]

    def test_list_combines_sanitized_order_pagination_and_tenant(self, mock_db):
        from modules.core.repositories.base import CrudRepository
        from modules.core.context import tenant_context

        repo = CrudRepository('T0001', business_columns=['id', 'name', 'created_at'])
        mock_db['cursor'].fetchall.return_value = []

        with tenant_context(42):
            repo.list(filters={'name': 'Widget'}, order_by='-created_at', limit=25, offset=50)

        call_args = mock_db['cursor'].execute.call_args
        sql = call_args[0][0]
        params = call_args[0][1]

        assert '"business_id" = %s' in sql
        assert '"name" = %s' in sql
        assert 'ORDER BY "created_at" DESC' in sql
        assert 'LIMIT %s' in sql
        assert 'OFFSET %s' in sql
        assert params == [42, 'Widget', 25, 50]


