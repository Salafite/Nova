import csv
import io
import json
import uuid
from modules.core.repositories.base import CrudRepository

BATCH_REPO = CrudRepository('T0104', business_columns=[
    'id', 'batch_key', 'entity_type', 'total_rows', 'inserted_rows', 'status',
])

ENTITY_MAP = {
    'products': ('T0003', 'name', ['name', 'sku', 'price', 'cost_price', 'category', 'brand', 'tax_rate', 'image_url']),
    'customers': ('T0010', 'name', ['name', 'group_name', 'phone', 'email', 'credit_limit']),
    'suppliers': ('T0011', 'name', ['name', 'category', 'phone', 'email', 'payment_terms', 'rating']),
}

FIELD_MAP = {
    'products': {
        'name': 'name', 'sku': 'sku', 'price': 'price', 'cost': 'cost_price',
        'category': 'category', 'brand': 'brand', 'tax': 'tax_rate',
    },
    'customers': {
        'name': 'name', 'group': 'group_name', 'phone': 'phone',
        'email': 'email', 'credit': 'credit_limit',
    },
    'suppliers': {
        'name': 'name', 'category': 'category', 'phone': 'phone',
        'email': 'email', 'terms': 'payment_terms', 'rating': 'rating',
    },
}


class MigrationService:
    def upload_csv(self, entity_type, csv_content, column_mapping=None):
        if entity_type not in ENTITY_MAP:
            raise ValueError(f'Unknown entity type {entity_type}')

        reader = csv.DictReader(io.StringIO(csv_content))
        raw_rows = list(reader)
        if not raw_rows:
            raise ValueError('CSV file is empty')

        batch_key = str(uuid.uuid4())[:8]
        batch = BATCH_REPO.create({
            'batch_key': batch_key,
            'entity_type': entity_type,
            'total_rows': len(raw_rows),
            'inserted_rows': 0,
            'status': 'Preview',
        })

        mapping = column_mapping or {}
        field_map = FIELD_MAP.get(entity_type, {})
        _, name_col, _ = ENTITY_MAP[entity_type]

        parsed_rows = []
        errors = []
        for i, row in enumerate(raw_rows):
            try:
                parsed = self._map_row(row, mapping, field_map, entity_type)
                if name_col not in parsed:
                    raise ValueError(f'Missing required field: {name_col}')
                parsed_rows.append(parsed)
            except Exception as e:
                errors.append({'row': i + 2, 'error': str(e), 'data': dict(row)})

        self._store_parsed(batch['id'], parsed_rows)

        return {
            'batch_key': batch_key,
            'batch_id': batch['id'],
            'entity_type': entity_type,
            'total_rows': len(raw_rows),
            'valid_rows': len(parsed_rows),
            'error_rows': len(errors),
            'errors': errors,
            'sample': parsed_rows[:5],
            'columns': list(raw_rows[0].keys()) if raw_rows else [],
        }

    def commit(self, batch_id):
        batch = BATCH_REPO.get(batch_id)
        if not batch:
            raise ValueError(f'Batch {batch_id} not found')
        if batch['status'] != 'Preview':
            raise ValueError(f'Batch status is {batch["status"]}, expected Preview')

        entity_type = batch['entity_type']
        table, _, columns = ENTITY_MAP[entity_type]
        repo = CrudRepository(table, business_columns=columns)

        rows = self._load_stored(batch_id)
        if not rows:
            raise ValueError('No rows to commit')

        inserted = 0
        for data in rows:
            repo.create(data)
            inserted += 1

        BATCH_REPO.update(batch_id, {'status': 'Committed', 'inserted_rows': inserted})
        self._drop_storage(batch_id)

        return {'batch_id': batch_id, 'inserted_rows': inserted, 'status': 'Committed'}

    def rollback(self, batch_id):
        batch = BATCH_REPO.get(batch_id)
        if not batch:
            raise ValueError(f'Batch {batch_id} not found')
        if batch['status'] != 'Committed':
            BATCH_REPO.update(batch_id, {'status': 'RolledBack'})
            return {'batch_id': batch_id, 'status': 'RolledBack'}

        entity_type = batch['entity_type']
        table, _, columns = ENTITY_MAP[entity_type]
        repo = CrudRepository(table, business_columns=columns)

        rows = self._load_stored(batch_id)
        for data in rows:
            pk_val = data.get('id')
            if pk_val:
                repo.delete(pk_val)

        BATCH_REPO.update(batch_id, {'status': 'RolledBack', 'inserted_rows': 0})
        self._drop_storage(batch_id)

        return {'batch_id': batch_id, 'status': 'RolledBack'}

    def get_batch(self, batch_id):
        return BATCH_REPO.get(batch_id)

    def _map_row(self, row, mapping, field_map, entity_type):
        result = {}
        for csv_col, value in row.items():
            value = value.strip() if value else ''
            target = mapping.get(csv_col, '') or field_map.get(csv_col, '')
            if not target:
                continue
            if value == '':
                continue
            if target in ('price', 'cost_price', 'credit_limit', 'rating', 'tax_rate'):
                try:
                    value = float(value)
                except ValueError:
                    raise ValueError(f'Invalid number "{value}" in column {csv_col}')
            result[target] = value
        return result

    def _storage_table(self, batch_id):
        return f'temp_mig_{batch_id}'

    def _store_parsed(self, batch_id, rows):
        from packages.database.connection import get_connection
        conn = get_connection()
        try:
            with conn.cursor() as cur:
                tbl = self._storage_table(batch_id)
                cur.execute(f'CREATE TEMP TABLE {tbl} (id SERIAL, data JSONB) ON COMMIT DROP')
                for row in rows:
                    cur.execute(f'INSERT INTO {tbl} (data) VALUES (%s)', (json.dumps(row, default=str),))
                conn.commit()
        finally:
            from packages.database.connection import release_connection
            release_connection(conn)

    def _load_stored(self, batch_id):
        from packages.database.connection import get_connection
        conn = get_connection()
        try:
            with conn.cursor() as cur:
                tbl = self._storage_table(batch_id)
                cur.execute(f'SELECT data FROM {tbl} ORDER BY id')
                return [json.loads(r[0]) for r in cur.fetchall()]
        finally:
            release_connection(conn)

    def _drop_storage(self, batch_id):
        from packages.database.connection import get_connection
        conn = get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(f'DROP TABLE IF EXISTS {self._storage_table(batch_id)}')
                conn.commit()
        finally:
            release_connection(conn)
