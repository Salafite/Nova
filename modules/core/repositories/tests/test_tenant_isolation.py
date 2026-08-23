from unittest.mock import patch, MagicMock
import pytest
import psycopg2
from modules.core.repositories.base import CrudRepository
from modules.core.context import tenant_context, set_current_tenant, clear_current_tenant, get_current_tenant


@pytest.fixture(autouse=True)
def mock_db():
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_cursor.rowcount = 1
    mock_context = MagicMock()
    mock_context.__enter__.return_value = mock_cursor
    mock_conn.cursor.return_value = mock_context

    with patch('modules.core.repositories.base.get_connection', return_value=mock_conn), \
         patch('modules.core.repositories.base.release_connection') as mock_release, \
         patch('packages.database.connection.get_connection', return_value=mock_conn), \
         patch('packages.database.connection.release_connection'):
        yield {
            'conn': mock_conn,
            'cursor': mock_cursor,
            'ctx': mock_context,
            'release': mock_release,
        }


class TestTenantIsolationCrudRepositoryRead:
    """Test read operations (list, get, count, get_unscoped) for tenant scoping and isolation."""

    def test_list_scopes_by_active_tenant_context(self, mock_db):
        repo = CrudRepository('T0003', business_columns=['id', 'code', 'name'])
        mock_db['cursor'].fetchall.return_value = [
            {'id': 101, 'code': 'PRD-01', 'name': 'Item A', 'business_id': 5}
        ]

        with tenant_context(5):
            results = repo.list()

        call_args = mock_db['cursor'].execute.call_args
        sql = call_args[0][0]
        params = call_args[0][1]

        assert '"business_id" = %s' in sql
        assert 5 in params
        assert results == [{'id': 101, 'code': 'PRD-01', 'name': 'Item A', 'business_id': 5}]
        mock_db['release'].assert_called_once_with(mock_db['conn'])

    def test_list_without_tenant_context_returns_unfiltered(self, mock_db):
        repo = CrudRepository('T0003', business_columns=['id', 'code', 'name'])
        mock_db['cursor'].fetchall.return_value = [
            {'id': 1, 'code': 'PRD-01', 'name': 'Item 1', 'business_id': 1},
            {'id': 2, 'code': 'PRD-02', 'name': 'Item 2', 'business_id': 2},
        ]

        clear_current_tenant()
        results = repo.list()

        call_args = mock_db['cursor'].execute.call_args
        sql = call_args[0][0]
        assert '"business_id"' not in sql
        assert len(results) == 2

    def test_list_explicit_tenant_overrides_active_context(self, mock_db):
        repo = CrudRepository('T0003', business_columns=['id', 'code', 'name'])
        mock_db['cursor'].fetchall.return_value = []

        with tenant_context(10):
            repo.list(business_id=20)

        call_args = mock_db['cursor'].execute.call_args
        sql = call_args[0][0]
        params = call_args[0][1]

        assert '"business_id" = %s' in sql
        assert 20 in params
        assert 10 not in params

    def test_list_combines_custom_filters_with_tenant_condition(self, mock_db):
        repo = CrudRepository('T0003', business_columns=['id', 'category_id', 'is_active'])
        mock_db['cursor'].fetchall.return_value = []

        with tenant_context(7):
            repo.list(filters={'category_id': 42})

        call_args = mock_db['cursor'].execute.call_args
        sql = call_args[0][0]
        params = call_args[0][1]

        assert '"business_id" = %s' in sql
        assert 'is_active = TRUE' in sql
        assert '"category_id" = %s' in sql
        assert 7 in params
        assert 42 in params

    def test_list_preserves_order_and_pagination_with_tenant(self, mock_db):
        repo = CrudRepository('T0010', business_columns=['id', 'customer_name'])
        mock_db['cursor'].fetchall.return_value = []

        with tenant_context(15):
            repo.list(order_by='customer_name', limit=25, offset=50)

        call_args = mock_db['cursor'].execute.call_args
        sql = call_args[0][0]
        params = call_args[0][1]

        assert '"business_id" = %s' in sql
        assert 'ORDER BY "customer_name"' in sql
        assert 'LIMIT %s' in sql
        assert 'OFFSET %s' in sql
        assert params == [15, 25, 50]

    def test_get_scopes_by_tenant_and_returns_matching_row(self, mock_db):
        repo = CrudRepository('T0012', business_columns=['id', 'order_number'])
        mock_db['cursor'].fetchone.return_value = {
            'id': 1,
            'order_number': 'SO-001',
            'business_id': 3,
        }

        with tenant_context(3):
            result = repo.get(1)

        call_args = mock_db['cursor'].execute.call_args
        sql = call_args[0][0]
        params = call_args[0][1]

        assert '"id" = %s' in sql
        assert '"business_id" = %s' in sql
        assert params == (1, 3)
        assert result['order_number'] == 'SO-001'

    def test_get_cross_tenant_returns_none(self, mock_db):
        repo = CrudRepository('T0012', business_columns=['id', 'order_number'])
        mock_db['cursor'].fetchone.return_value = None

        with tenant_context(99):
            result = repo.get(1)

        call_args = mock_db['cursor'].execute.call_args
        params = call_args[0][1]
        assert params == (1, 99)
        assert result is None

    def test_get_explicit_tenant_overrides_active_context(self, mock_db):
        repo = CrudRepository('T0012', business_columns=['id', 'order_number'])
        mock_db['cursor'].fetchone.return_value = {'id': 5, 'business_id': 88}

        with tenant_context(11):
            repo.get(5, business_id=88)

        call_args = mock_db['cursor'].execute.call_args
        params = call_args[0][1]
        assert params == (5, 88)

    def test_get_unscoped_bypasses_active_tenant_context(self, mock_db):
        repo = CrudRepository('T0012', business_columns=['id', 'order_number'])
        mock_db['cursor'].fetchone.return_value = {
            'id': 100,
            'order_number': 'SO-999',
            'business_id': 99,
        }

        with tenant_context(1):
            result = repo.get_unscoped(100)

        call_args = mock_db['cursor'].execute.call_args
        sql = call_args[0][0]
        params = call_args[0][1]

        assert '"id" = %s' in sql
        assert '"business_id"' not in sql
        assert params == (100,)
        assert result['business_id'] == 99

    def test_count_scopes_by_active_tenant_context(self, mock_db):
        repo = CrudRepository('T0090', business_columns=['id', 'invoice_number', 'is_active'])
        mock_db['cursor'].fetchone.return_value = {'cnt': 18}

        with tenant_context(4):
            count = repo.count(filters={'status': 'Paid'})

        call_args = mock_db['cursor'].execute.call_args
        sql = call_args[0][0]
        params = call_args[0][1]

        assert '"business_id" = %s' in sql
        assert 'is_active = TRUE' in sql
        assert '"status" = %s' in sql
        assert 4 in params
        assert 'Paid' in params
        assert count == 18

    def test_count_explicit_tenant_overrides_context(self, mock_db):
        repo = CrudRepository('T0090', business_columns=['id', 'invoice_number'])
        mock_db['cursor'].fetchone.return_value = {'cnt': 5}

        with tenant_context(10):
            count = repo.count(business_id=50)

        call_args = mock_db['cursor'].execute.call_args
        params = call_args[0][1]
        assert 50 in params
        assert 10 not in params
        assert count == 5


class TestTenantIsolationCrudRepositoryWrite:
    """Test write operations (create, update, delete) for tenant scoping, injection, and tampering prevention."""

    def test_create_auto_populates_business_id_from_active_context(self, mock_db):
        repo = CrudRepository('T0001', business_columns=['id', 'name', 'code'])
        mock_db['cursor'].fetchone.return_value = {'id': 1, 'name': 'Widget', 'business_id': 12}

        with tenant_context(12):
            result = repo.create({'name': 'Widget', 'code': 'WDG-01'})

        call_args = mock_db['cursor'].execute.call_args
        sql = call_args[0][0]
        vals = call_args[0][1]

        assert '"business_id"' in sql
        assert 12 in vals
        mock_db['conn'].commit.assert_called_once()
        assert result['business_id'] == 12

    def test_create_preserves_explicit_payload_business_id(self, mock_db):
        repo = CrudRepository('T0001', business_columns=['id', 'name', 'business_id'])
        mock_db['cursor'].fetchone.return_value = {'id': 1, 'name': 'AdminWidget', 'business_id': 88}

        with tenant_context(10):
            repo.create({'name': 'AdminWidget', 'business_id': 88})

        call_args = mock_db['cursor'].execute.call_args
        vals = call_args[0][1]
        assert 88 in vals
        assert 10 not in vals

    def test_create_explicit_tenant_arg_overrides_context(self, mock_db):
        repo = CrudRepository('T0001', business_columns=['id', 'name'])
        mock_db['cursor'].fetchone.return_value = {'id': 1, 'name': 'Overridden', 'business_id': 77}

        with tenant_context(10):
            repo.create({'name': 'Overridden'}, business_id=77)

        call_args = mock_db['cursor'].execute.call_args
        vals = call_args[0][1]
        assert 77 in vals
        assert 10 not in vals

    def test_create_without_tenant_context_does_not_inject_business_id(self, mock_db):
        repo = CrudRepository('T0001', business_columns=['id', 'name'])
        mock_db['cursor'].fetchone.return_value = {'id': 1, 'name': 'SystemRecord'}

        clear_current_tenant()
        repo.create({'name': 'SystemRecord'})

        call_args = mock_db['cursor'].execute.call_args
        sql = call_args[0][0]
        assert '"business_id"' not in sql

    def test_update_scopes_where_clause_by_active_tenant_context(self, mock_db):
        repo = CrudRepository('T0001', business_columns=['id', 'name'])
        mock_db['cursor'].fetchone.return_value = {'id': 20, 'name': 'Updated', 'business_id': 6}

        with tenant_context(6):
            result = repo.update(20, {'name': 'Updated'})

        call_args = mock_db['cursor'].execute.call_args
        sql = call_args[0][0]
        vals = call_args[0][1]

        assert 'WHERE "id" = %s AND "business_id" = %s' in sql
        assert vals[-2:] == [20, 6]
        mock_db['conn'].commit.assert_called_once()
        assert result['name'] == 'Updated'

    def test_update_explicit_tenant_arg_overrides_context(self, mock_db):
        repo = CrudRepository('T0001', business_columns=['id', 'name'])
        mock_db['cursor'].fetchone.return_value = {'id': 20, 'name': 'Updated', 'business_id': 40}

        with tenant_context(6):
            repo.update(20, {'name': 'Updated'}, business_id=40)

        call_args = mock_db['cursor'].execute.call_args
        sql = call_args[0][0]
        vals = call_args[0][1]

        assert 'WHERE "id" = %s AND "business_id" = %s' in sql
        assert vals[-2:] == [20, 40]

    def test_update_strips_business_id_preventing_tenant_hijack(self, mock_db):
        repo = CrudRepository('T0001', business_columns=['id', 'name'])
        mock_db['cursor'].fetchone.return_value = {'id': 30, 'name': 'SecureUpdate', 'business_id': 14}

        with tenant_context(14):
            repo.update(30, {'name': 'SecureUpdate', 'business_id': 999})

        call_args = mock_db['cursor'].execute.call_args
        sql = call_args[0][0]
        vals = call_args[0][1]

        set_clause = sql.split('WHERE')[0]
        assert '"business_id" = %s' not in set_clause
        assert 999 not in vals
        assert vals[-2:] == [30, 14]

    def test_update_empty_payload_after_stripping_falls_back_to_scoped_get(self, mock_db):
        repo = CrudRepository('T0001', business_columns=['id', 'name'])
        mock_db['cursor'].fetchone.return_value = {'id': 15, 'name': 'Unchanged', 'business_id': 2}

        with tenant_context(2):
            result = repo.update(15, {'id': 15, 'business_id': 999, 'created_at': '2026-01-01'})

        call_args = mock_db['cursor'].execute.call_args
        sql = call_args[0][0]
        params = call_args[0][1]

        assert 'SELECT * FROM' in sql
        assert '"business_id" = %s' in sql
        assert params == (15, 2)
        assert result['id'] == 15

    def test_delete_soft_scopes_by_active_tenant_context(self, mock_db):
        repo = CrudRepository('T0001', business_columns=['id', 'name', 'is_active'])

        with tenant_context(8):
            res = repo.delete(50)

        call_args = mock_db['cursor'].execute.call_args
        sql = call_args[0][0]
        params = call_args[0][1]

        assert 'UPDATE' in sql
        assert 'is_active = FALSE' in sql
        assert 'WHERE "id" = %s AND "business_id" = %s' in sql
        assert params == (50, 8)
        assert res is True
        mock_db['conn'].commit.assert_called_once()

    def test_delete_hard_scopes_by_active_tenant_context(self, mock_db):
        repo = CrudRepository('T0001', business_columns=['id', 'name'])

        with tenant_context(8):
            res = repo.delete(50)

        call_args = mock_db['cursor'].execute.call_args
        sql = call_args[0][0]
        params = call_args[0][1]

        assert 'DELETE FROM' in sql
        assert 'WHERE "id" = %s AND "business_id" = %s' in sql
        assert params == (50, 8)
        assert res is True

    def test_delete_explicit_tenant_arg_overrides_context(self, mock_db):
        repo = CrudRepository('T0001', business_columns=['id', 'name'])

        with tenant_context(8):
            repo.delete(50, business_id=90)

        call_args = mock_db['cursor'].execute.call_args
        params = call_args[0][1]
        assert params == (50, 90)


class TestNonTenantTablesExemption:
    """Test that non-tenant tables (such as T0059) are completely exempt from tenant filtering."""

    @pytest.mark.parametrize('table_name', ['T0059', 't0059'])
    def test_t0059_tenants_table_exempt_from_tenant_filtering_on_all_operations(self, mock_db, table_name):
        repo = CrudRepository(table_name, business_columns=['id', 'tenant_name', 'status'])
        mock_db['cursor'].fetchall.return_value = [{'id': 1, 'tenant_name': 'Alpha'}]
        mock_db['cursor'].fetchone.return_value = {'id': 1, 'tenant_name': 'Alpha', 'cnt': 1}

        with tenant_context(99):
            # 1. list
            repo.list()
            sql_list = mock_db['cursor'].execute.call_args[0][0]
            assert '"business_id"' not in sql_list

            # 2. get
            repo.get(1)
            sql_get = mock_db['cursor'].execute.call_args[0][0]
            assert '"business_id"' not in sql_get

            # 3. count
            repo.count()
            sql_count = mock_db['cursor'].execute.call_args[0][0]
            assert '"business_id"' not in sql_count

            # 4. create
            repo.create({'tenant_name': 'Beta'})
            sql_create = mock_db['cursor'].execute.call_args[0][0]
            assert '"business_id"' not in sql_create

            # 5. update
            repo.update(1, {'tenant_name': 'Alpha Prime'})
            sql_update = mock_db['cursor'].execute.call_args[0][0]
            assert '"business_id"' not in sql_update

            # 6. delete
            repo.delete(1)
            sql_delete = mock_db['cursor'].execute.call_args[0][0]
            assert '"business_id"' not in sql_delete


class TestMultiTenantConcurrencyAndContextSwitching:
    """Test switching and nesting tenant contexts across concurrent / sequential repository invocations."""

    def test_nested_tenant_contexts_isolated(self, mock_db):
        repo = CrudRepository('T0003', business_columns=['id', 'name'])
        mock_db['cursor'].fetchall.return_value = []

        with tenant_context(10):
            assert get_current_tenant() == 10
            repo.list()
            assert 10 in mock_db['cursor'].execute.call_args[0][1]

            with tenant_context(20):
                assert get_current_tenant() == 20
                repo.list()
                assert 20 in mock_db['cursor'].execute.call_args[0][1]

            # Reverts back to outer tenant 10
            assert get_current_tenant() == 10
            repo.list()
            assert 10 in mock_db['cursor'].execute.call_args[0][1]

        # Context manager exited, tenant should be None
        assert get_current_tenant() is None
        repo.list()
        assert '"business_id"' not in mock_db['cursor'].execute.call_args[0][0]

    def test_context_clearing_and_manual_setting(self, mock_db):
        repo = CrudRepository('T0003', business_columns=['id', 'name'])
        mock_db['cursor'].fetchall.return_value = []

        set_current_tenant(35)
        repo.list()
        assert 35 in mock_db['cursor'].execute.call_args[0][1]

        clear_current_tenant()
        repo.list()
        assert '"business_id"' not in mock_db['cursor'].execute.call_args[0][0]


class TestRepositoryTransactionRollbackAndConnectionHandling:
    """Test database transaction rollback and resource cleanup in tenant-scoped operations."""

    def test_create_rolls_back_and_releases_connection_on_db_error(self, mock_db):
        repo = CrudRepository('T0001', business_columns=['id', 'name'])
        mock_db['cursor'].execute.side_effect = psycopg2.Error('Simulated DB constraint error')

        with tenant_context(10):
            with pytest.raises(psycopg2.Error):
                repo.create({'name': 'WillFail'})

        mock_db['conn'].rollback.assert_called_once()
        mock_db['release'].assert_called_once_with(mock_db['conn'])

    def test_update_rolls_back_and_releases_connection_on_db_error(self, mock_db):
        repo = CrudRepository('T0001', business_columns=['id', 'name'])
        mock_db['cursor'].execute.side_effect = psycopg2.Error('Simulated DB lock timeout')

        with tenant_context(10):
            with pytest.raises(psycopg2.Error):
                repo.update(1, {'name': 'WillFail'})

        mock_db['conn'].rollback.assert_called_once()
        mock_db['release'].assert_called_once_with(mock_db['conn'])

    def test_delete_rolls_back_and_releases_connection_on_db_error(self, mock_db):
        repo = CrudRepository('T0001', business_columns=['id', 'name'])
        mock_db['cursor'].execute.side_effect = psycopg2.Error('Simulated foreign key violation')

        with tenant_context(10):
            with pytest.raises(psycopg2.Error):
                repo.delete(1)

        mock_db['conn'].rollback.assert_called_once()
        mock_db['release'].assert_called_once_with(mock_db['conn'])


class TestAsyncAndThreadTenantIsolation:
    """Test tenant context isolation across asynchronous event loops and multi-threaded worker pools."""

    @pytest.mark.asyncio
    async def test_async_coroutines_maintain_isolated_tenant_contexts(self, mock_db):
        import asyncio
        repo = CrudRepository('T0003', business_columns=['id', 'name'])
        recorded_tenants = {}

        async def worker(tenant_id: int):
            with tenant_context(tenant_id):
                # simulate async yield
                await asyncio.sleep(0.01)
                assert get_current_tenant() == tenant_id
                repo.list()
                call_args = mock_db['cursor'].execute.call_args
                recorded_tenants[tenant_id] = call_args[0][1]

        await asyncio.gather(
            worker(101),
            worker(202),
            worker(303),
        )

        assert 101 in recorded_tenants[101]
        assert 202 in recorded_tenants[202]
        assert 303 in recorded_tenants[303]

    def test_threads_maintain_isolated_tenant_contexts(self, mock_db):
        import threading
        repo = CrudRepository('T0003', business_columns=['id', 'name'])
        thread_results = {}
        errors = []

        def thread_target(tenant_id: int):
            try:
                with tenant_context(tenant_id):
                    assert get_current_tenant() == tenant_id
                    repo.list()
                    call_args = mock_db['cursor'].execute.call_args
                    thread_results[tenant_id] = call_args[0][1]
            except Exception as e:
                errors.append(e)

        threads = [
            threading.Thread(target=thread_target, args=(501,)),
            threading.Thread(target=thread_target, args=(502,)),
            threading.Thread(target=thread_target, args=(503,)),
        ]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        assert len(thread_results) == 3
        assert 501 in thread_results[501]
        assert 502 in thread_results[502]
        assert 503 in thread_results[503]


class TestCustomPrimaryKeyAndSchemaTenantScoping:
    """Test tenant scoping when custom primary keys and custom database schemas are used."""

    def test_custom_primary_key_scopes_get_update_delete_by_tenant(self, mock_db):
        repo = CrudRepository('T0005', pk='item_code', business_columns=['item_code', 'description'])
        mock_db['cursor'].fetchone.return_value = {'item_code': 'IC-99', 'description': 'Special Item', 'business_id': 17}

        with tenant_context(17):
            # 1. Get
            res_get = repo.get('IC-99')
            call_args_get = mock_db['cursor'].execute.call_args
            sql_get, params_get = call_args_get[0][0], call_args_get[0][1]
            assert '"item_code" = %s AND "business_id" = %s' in sql_get
            assert params_get == ('IC-99', 17)
            assert res_get['item_code'] == 'IC-99'

            # 2. Update
            res_update = repo.update('IC-99', {'description': 'Updated Description'})
            call_args_update = mock_db['cursor'].execute.call_args
            sql_update, vals_update = call_args_update[0][0], call_args_update[0][1]
            assert 'WHERE "item_code" = %s AND "business_id" = %s' in sql_update
            assert vals_update[-2:] == ['IC-99', 17]

            # 3. Delete
            res_delete = repo.delete('IC-99')
            call_args_delete = mock_db['cursor'].execute.call_args
            sql_delete, params_delete = call_args_delete[0][0], call_args_delete[0][1]
            assert 'WHERE "item_code" = %s AND "business_id" = %s' in sql_delete
            assert params_delete == ('IC-99', 17)
            assert res_delete is True

    def test_custom_db_schema_env_var_scopes_queries(self, mock_db, monkeypatch):
        monkeypatch.setenv('DB_SCHEMA', 'CustomNova')
        repo = CrudRepository('T0001', business_columns=['id', 'name'])
        mock_db['cursor'].fetchall.return_value = []

        with tenant_context(8):
            repo.list()

        call_args = mock_db['cursor'].execute.call_args
        sql = call_args[0][0]
        params = call_args[0][1]
        assert '"CustomNova".t0001' in sql
        assert '"business_id" = %s' in sql
        assert 8 in params


class TestExplicitFilterDictionaryTenantHandling:
    """Test that explicit business_id in the filters dictionary is respected and does not cause query syntax errors."""

    def test_list_with_explicit_business_id_in_filters_dict_preserves_filter_without_duplication(self, mock_db):
        repo = CrudRepository('T0001', business_columns=['id', 'name'])
        mock_db['cursor'].fetchall.return_value = []

        with tenant_context(10):
            repo.list(filters={'business_id': 99, 'name': 'widget'})

        call_args = mock_db['cursor'].execute.call_args
        sql = call_args[0][0]
        params = call_args[0][1]

        # Should only have one business_id filter clause
        assert sql.count('"business_id" = %s') == 1
        assert params == [99, 'widget']

    def test_count_with_explicit_business_id_in_filters_dict_preserves_filter_without_duplication(self, mock_db):
        repo = CrudRepository('T0001', business_columns=['id', 'name'])
        mock_db['cursor'].fetchone.return_value = {'cnt': 3}

        with tenant_context(10):
            cnt = repo.count(filters={'business_id': 99})

        call_args = mock_db['cursor'].execute.call_args
        sql = call_args[0][0]
        params = call_args[0][1]

        assert sql.count('"business_id" = %s') == 1
        assert params == [99]
        assert cnt == 3


class TestEdgeCasesAndPayloadSanitization:
    """Test boundary edge cases, None values, and zero-row return scenarios."""

    def test_create_with_explicit_none_business_id_injects_context_tenant(self, mock_db):
        repo = CrudRepository('T0001', business_columns=['id', 'name', 'business_id'])
        mock_db['cursor'].fetchone.return_value = {'id': 1, 'name': 'Item', 'business_id': 45}

        with tenant_context(45):
            repo.create({'name': 'Item', 'business_id': None})

        call_args = mock_db['cursor'].execute.call_args
        vals = call_args[0][1]
        assert 45 in vals

    def test_delete_returns_false_when_zero_rows_affected_in_tenant(self, mock_db):
        repo = CrudRepository('T0001', business_columns=['id', 'name'])
        mock_db['cursor'].rowcount = 0

        with tenant_context(12):
            res = repo.delete(999)

        assert res is False

    def test_count_returns_zero_when_no_records_match_tenant(self, mock_db):
        repo = CrudRepository('T0001', business_columns=['id', 'name'])
        mock_db['cursor'].fetchone.return_value = None

        with tenant_context(12):
            cnt = repo.count()

        assert cnt == 0


class TestRepositoryBusinessIdDetection:
    """Test _has_business_id detection logic across various table configurations."""

    def test_business_id_detected_by_default_for_business_tables(self):
        repo = CrudRepository('T0001', business_columns=['id', 'name'])
        assert repo._has_business_id() is True

    def test_business_id_detected_when_explicitly_in_business_columns(self):
        repo = CrudRepository('T0001', business_columns=['id', 'name', 'business_id'])
        assert repo._has_business_id() is True

    def test_business_id_false_for_t0059_tenants_table_case_insensitive(self):
        repo_upper = CrudRepository('T0059', business_columns=['id', 'tenant_name'])
        assert repo_upper._has_business_id() is False

        repo_lower = CrudRepository('t0059', business_columns=['id', 'tenant_name'])
        assert repo_lower._has_business_id() is False


class TestCrossTenantOperationGuards:
    """Test that records from other tenants cannot be accessed, modified, or deleted."""

    def test_get_filters_out_other_tenant_record(self, mock_db):
        repo = CrudRepository('T0010', business_columns=['id', 'customer_name'])
        # If DB query with tenant=10 finds nothing
        mock_db['cursor'].fetchone.return_value = None

        with tenant_context(10):
            record = repo.get(42)

        assert record is None
        call_args = mock_db['cursor'].execute.call_args
        sql = call_args[0][0]
        params = call_args[0][1]
        assert 'WHERE "id" = %s AND "business_id" = %s' in sql
        assert params == (42, 10)

    def test_update_does_not_affect_other_tenant_record(self, mock_db):
        repo = CrudRepository('T0010', business_columns=['id', 'customer_name'])
        # DB UPDATE WHERE id = 42 AND business_id = 10 returns no row because record belongs to tenant 20
        mock_db['cursor'].fetchone.return_value = None

        with tenant_context(10):
            result = repo.update(42, {'customer_name': 'Hacked Name'})

        assert result is None
        call_args = mock_db['cursor'].execute.call_args
        sql = call_args[0][0]
        assert 'WHERE "id" = %s AND "business_id" = %s' in sql
        assert 10 in call_args[0][1]

    def test_delete_does_not_affect_other_tenant_record(self, mock_db):
        repo = CrudRepository('T0010', business_columns=['id', 'customer_name'])
        # DB DELETE WHERE id = 42 AND business_id = 10 updates/deletes 0 rows
        mock_db['cursor'].rowcount = 0

        with tenant_context(10):
            result = repo.delete(42)

        assert result is False
        call_args = mock_db['cursor'].execute.call_args
        sql = call_args[0][0]
        assert '"business_id" = %s' in sql
        assert (42, 10) == call_args[0][1]


