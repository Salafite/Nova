from unittest.mock import patch, MagicMock
import pytest
import json


@pytest.fixture(autouse=True)
def mock_all():
    mock_batch_repo = MagicMock()
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_cursor.rowcount = 1
    mock_context = MagicMock()
    mock_context.__enter__.return_value = mock_cursor
    mock_conn.cursor.return_value = mock_context

    with patch('modules.migration.services.migration_service.BATCH_REPO', mock_batch_repo), \
         patch('packages.database.connection.get_connection', return_value=mock_conn), \
         patch('packages.database.connection.release_connection'), \
         patch('modules.core.repositories.base.get_connection', return_value=mock_conn), \
         patch('modules.core.repositories.base.release_connection'):
        yield {'batch_repo': mock_batch_repo, 'conn': mock_conn, 'cursor': mock_cursor}


class TestUploadCSV:
    def test_unknown_entity_type(self, mock_all):
        from modules.migration.services.migration_service import MigrationService
        svc = MigrationService()
        with pytest.raises(ValueError, match='Unknown entity type'):
            svc.upload_csv('invalid', '')

    def test_empty_csv(self, mock_all):
        from modules.migration.services.migration_service import MigrationService
        svc = MigrationService()
        with pytest.raises(ValueError, match='CSV file is empty'):
            svc.upload_csv('products', 'name,sku,price\n')

    def test_valid_csv(self, mock_all):
        mock_all['batch_repo'].create.return_value = {'id': 1, 'batch_key': 'abc123'}
        from modules.migration.services.migration_service import MigrationService
        svc = MigrationService()
        csv_content = 'name,sku,price\nWidget,WGT-001,19.99\nGadget,GDG-001,29.99'

        result = svc.upload_csv('products', csv_content)

        assert result['total_rows'] == 2
        assert result['valid_rows'] == 2
        assert result['error_rows'] == 0
        assert len(result['sample']) == 2
        assert result['columns'] == ['name', 'sku', 'price']

    def test_csv_with_errors(self, mock_all):
        mock_all['batch_repo'].create.return_value = {'id': 1, 'batch_key': 'abc123'}
        from modules.migration.services.migration_service import MigrationService
        svc = MigrationService()
        csv_content = 'name,sku,price\n,,' 

        result = svc.upload_csv('products', csv_content)

        assert result['valid_rows'] == 0
        assert result['error_rows'] == 1
        assert result['errors'][0]['row'] == 2

    def test_column_mapping(self, mock_all):
        mock_all['batch_repo'].create.return_value = {'id': 1, 'batch_key': 'abc123'}
        from modules.migration.services.migration_service import MigrationService
        svc = MigrationService()
        csv_content = 'Product Name,SKU,Price\nWidget,WGT-001,19.99'

        result = svc.upload_csv('products', csv_content, column_mapping={
            'Product Name': 'name', 'SKU': 'sku', 'Price': 'price',
        })

        assert result['valid_rows'] == 1
        assert result['error_rows'] == 0


class TestCommit:
    def test_commit_success(self, mock_all):
        mock_all['batch_repo'].get.return_value = {
            'id': 1, 'status': 'Preview', 'entity_type': 'products',
        }
        mock_all['cursor'].fetchall.return_value = [
            (json.dumps({'name': 'Widget', 'sku': 'WGT-001', 'price': 19.99}),),
        ]
        from modules.migration.services.migration_service import MigrationService
        svc = MigrationService()
        result = svc.commit(1)

        assert result['status'] == 'Committed'
        assert result['inserted_rows'] == 1

    def test_commit_batch_not_found(self, mock_all):
        mock_all['batch_repo'].get.return_value = None
        from modules.migration.services.migration_service import MigrationService
        svc = MigrationService()
        with pytest.raises(ValueError, match='not found'):
            svc.commit(1)

    def test_commit_wrong_status(self, mock_all):
        mock_all['batch_repo'].get.return_value = {'id': 1, 'status': 'Committed'}
        from modules.migration.services.migration_service import MigrationService
        svc = MigrationService()
        with pytest.raises(ValueError, match='expected Preview'):
            svc.commit(1)


class TestRollback:
    def test_rollback_preview_batch(self, mock_all):
        mock_all['batch_repo'].get.return_value = {'id': 1, 'status': 'Preview'}
        from modules.migration.services.migration_service import MigrationService
        svc = MigrationService()
        result = svc.rollback(1)

        assert result['status'] == 'RolledBack'

    def test_rollback_committed_batch(self, mock_all):
        mock_all['batch_repo'].get.return_value = {
            'id': 1, 'status': 'Committed', 'entity_type': 'products',
        }
        mock_all['cursor'].fetchall.return_value = [
            (json.dumps({'id': 10, 'name': 'Widget', 'sku': 'WGT-001'}),),
        ]
        from modules.migration.services.migration_service import MigrationService
        svc = MigrationService()
        result = svc.rollback(1)

        assert result['status'] == 'RolledBack'

    def test_rollback_batch_not_found(self, mock_all):
        mock_all['batch_repo'].get.return_value = None
        from modules.migration.services.migration_service import MigrationService
        svc = MigrationService()
        with pytest.raises(ValueError, match='not found'):
            svc.rollback(1)


class TestGetBatch:
    def test_get_batch(self, mock_all):
        mock_all['batch_repo'].get.return_value = {'id': 1, 'batch_key': 'abc', 'status': 'Preview'}
        from modules.migration.services.migration_service import MigrationService
        svc = MigrationService()
        result = svc.get_batch(1)

        assert result['id'] == 1
        assert result['status'] == 'Preview'
