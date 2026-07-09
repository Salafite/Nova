from modules.inventory.tests.conftest import client


class TestComplete:

    def test_not_found(self):
        resp = client.post('/api/T0105I/999/complete')
        assert resp.status_code == 404
        assert resp.json()['detail'] == 'Count not found'

    def test_wrong_status(self, cursor):
        cursor.fetchone.return_value = ('Draft',)
        resp = client.post('/api/T0105I/1/complete')
        assert resp.status_code == 400
        assert 'In Progress' in resp.json()['detail']

    def test_success_with_adjustment(self, cursor):
        cursor.fetchone.return_value = ('In Progress',)
        cursor.fetchall.return_value = [
            (1, 101, 10.0, 12.0),
            (2, 102, 5.0, 5.0),
            (3, 103, 20.0, None),
        ]

        resp = client.post('/api/T0105I/1/complete')

        assert resp.status_code == 200
        data = resp.json()
        assert data['completed'] is True
        assert data['adjustments'] == 1

        calls = [c[0][0] for c in cursor.execute.call_args_list]
        sql = '\n'.join(calls)

        assert 'SELECT status' in sql
        assert 'SELECT ci.id' in sql
        assert 'UPDATE "Nova".t0009' in sql
        assert 'balance_after' in sql
        assert 'reference_type' in sql
        assert 'reference_id' in sql
        assert "\"Nova\".t0064" in sql or "t0064" in sql
        assert "ADJUSTMENT" in sql
        assert "Inventory count adjustment" in sql
        assert "UPDATE" in sql and "t0105" in sql and "SET status" in sql

    def test_no_adjustments(self, cursor):
        cursor.fetchone.return_value = ('In Progress',)
        cursor.fetchall.return_value = [
            (1, 101, 10.0, 10.0),
        ]

        resp = client.post('/api/T0105I/1/complete')

        assert resp.status_code == 200
        assert resp.json()['adjustments'] == 0

    def test_all_null_counted(self, cursor):
        cursor.fetchone.return_value = ('In Progress',)
        cursor.fetchall.return_value = [
            (1, 101, 10.0, None),
            (2, 102, 5.0, None),
        ]

        resp = client.post('/api/T0105I/1/complete')

        assert resp.status_code == 200
        assert resp.json()['adjustments'] == 0

    def test_t0064_column_names(self, cursor):
        cursor.fetchone.return_value = ('In Progress',)
        cursor.fetchall.return_value = [
            (1, 101, 10.0, 15.0),
        ]

        resp = client.post('/api/T0105I/1/complete')

        assert resp.status_code == 200
        t0064_sql = ''
        for args in cursor.execute.call_args_list:
            sql = args[0][0]
            if 't0064' in sql.lower():
                t0064_sql = sql
                break

        assert 'balance_after' in t0064_sql, f"Missing 'balance_after' in: {t0064_sql}"
        assert 'reference_type' in t0064_sql, f"Missing 'reference_type' in: {t0064_sql}"
        assert 'reference_id' in t0064_sql, f"Missing 'reference_id' in: {t0064_sql}"
        assert 'movement_type' in t0064_sql
        assert 'qty_change' in t0064_sql


class TestPopulate:

    def test_not_found(self):
        resp = client.post('/api/T0105I/999/populate')
        assert resp.status_code == 404

    def test_wrong_status(self, cursor):
        cursor.fetchone.return_value = ('In Progress',)
        resp = client.post('/api/T0105I/1/populate')
        assert resp.status_code == 400
        assert 'Draft' in resp.json()['detail']

    def test_success(self, cursor):
        cursor.fetchone.return_value = ('Draft',)
        cursor.rowcount = 5
        resp = client.post('/api/T0105I/1/populate')
        assert resp.status_code == 200
        assert resp.json()['populated'] == 5
