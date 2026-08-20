import pytest
from unittest.mock import MagicMock, patch, call
from pydantic import ValidationError

from packages.database.sequence import (
    _qualify_sequence_name,
    _extract_int_value,
    get_next_sequence_value,
    generate_document_number,
    generate_invoice_number,
    generate_pick_list_number,
    set_sequence_value,
    reset_sequence,
    get_current_sequence_value,
    DOCUMENT_SEQUENCES,
    DOCUMENT_PREFIXES,
)
from modules.accounting.models.finance import InvoiceCreate, InvoiceUpdate
from modules.warehouse.models.pick_list import PickListCreate, PickListUpdate
from modules.accounting.services.invoice_service import InvoiceService
from modules.warehouse.services.pick_list_service import PickListService


# ============================================================================
# 1. Sequence Name Qualification Tests
# ============================================================================

class TestQualifySequenceName:
    def test_simple_sequence_name_default_schema(self, monkeypatch):
        monkeypatch.setenv('DB_SCHEMA', 'Nova')
        result = _qualify_sequence_name('seq_invoice_number')
        assert result == '"Nova"."seq_invoice_number"'

    def test_simple_sequence_name_custom_schema(self):
        result = _qualify_sequence_name('seq_pick_list_number', schema='Tenant42')
        assert result == '"Tenant42"."seq_pick_list_number"'

    def test_already_qualified_sequence_name(self):
        result = _qualify_sequence_name('"Public"."seq_orders"')
        assert result == '"Public"."seq_orders"'

    def test_already_qualified_sequence_name_with_dot(self):
        result = _qualify_sequence_name('myschema.myseq')
        assert result == 'myschema.myseq'

    def test_strips_outer_quotes_from_names(self, monkeypatch):
        monkeypatch.setenv('DB_SCHEMA', '"Nova"')
        result = _qualify_sequence_name('"seq_invoice_number"')
        assert result == '"Nova"."seq_invoice_number"'


# ============================================================================
# 2. Integer Value Extraction Tests
# ============================================================================

class TestExtractIntValue:
    def test_extract_from_tuple(self):
        assert _extract_int_value((42,)) == 42
        assert _extract_int_value((100, 'extra')) == 100

    def test_extract_from_list(self):
        assert _extract_int_value([7]) == 7
        assert _extract_int_value([999, 'foo']) == 999

    def test_extract_from_dict(self):
        assert _extract_int_value({'nextval': 123}) == 123
        assert _extract_int_value({'last_value': 456}) == 456

    def test_extract_from_scalar_int(self):
        assert _extract_int_value(1) == 1

    def test_extract_from_scalar_str(self):
        assert _extract_int_value('55') == 55


# ============================================================================
# 3. Next Sequence Value Generation Tests
# ============================================================================

class TestGetNextSequenceValue:
    def test_get_next_sequence_value_with_default_connection(self):
        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cur
        mock_cur.fetchone.return_value = (1,)

        with patch('packages.database.sequence.get_connection', return_value=mock_conn) as mock_get_conn, \
             patch('packages.database.sequence.release_connection') as mock_rel_conn:
            val = get_next_sequence_value('seq_invoice_number', schema='Nova')
            assert val == 1
            mock_get_conn.assert_called_once()
            mock_cur.execute.assert_called_once_with('SELECT nextval(%s)', ('"Nova"."seq_invoice_number"',))
            mock_rel_conn.assert_called_once_with(mock_conn)

    def test_get_next_sequence_value_with_provided_connection(self):
        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cur
        mock_cur.fetchone.return_value = (42,)

        with patch('packages.database.sequence.get_connection') as mock_get_conn, \
             patch('packages.database.sequence.release_connection') as mock_rel_conn:
            val = get_next_sequence_value('seq_pick_list_number', conn=mock_conn, schema='Nova')
            assert val == 42
            mock_get_conn.assert_not_called()
            mock_cur.execute.assert_called_once_with('SELECT nextval(%s)', ('"Nova"."seq_pick_list_number"',))
            # Must NOT release connection managed by caller
            mock_rel_conn.assert_not_called()

    def test_get_next_sequence_value_raises_runtime_error_on_empty_row(self):
        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cur
        mock_cur.fetchone.return_value = None

        with patch('packages.database.sequence.get_connection', return_value=mock_conn), \
             patch('packages.database.sequence.release_connection') as mock_rel_conn:
            with pytest.raises(RuntimeError, match="Failed to fetch next value for sequence"):
                get_next_sequence_value('seq_invoice_number', schema='Nova')
            mock_rel_conn.assert_called_once_with(mock_conn)

    def test_get_next_sequence_value_releases_conn_on_cursor_error(self):
        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cur
        mock_cur.execute.side_effect = Exception("Database connection failed")

        with patch('packages.database.sequence.get_connection', return_value=mock_conn), \
             patch('packages.database.sequence.release_connection') as mock_rel_conn:
            with pytest.raises(Exception, match="Database connection failed"):
                get_next_sequence_value('seq_invoice_number', schema='Nova')
            mock_rel_conn.assert_called_once_with(mock_conn)


# ============================================================================
# 4. Document Number Formatting & Padding Tests
# ============================================================================

class TestGenerateDocumentNumber:
    def test_generate_document_number_default_padding(self):
        with patch('packages.database.sequence.get_next_sequence_value', return_value=1):
            doc_num = generate_document_number('seq_invoice_number', prefix='INV', padding=5)
            assert doc_num == 'INV-00001'

    def test_generate_document_number_large_sequence_value(self):
        with patch('packages.database.sequence.get_next_sequence_value', return_value=123456):
            doc_num = generate_document_number('seq_invoice_number', prefix='INV', padding=5)
            assert doc_num == 'INV-123456'

    def test_generate_document_number_custom_padding(self):
        with patch('packages.database.sequence.get_next_sequence_value', return_value=7):
            doc_num = generate_document_number('seq_test', prefix='DOC', padding=3)
            assert doc_num == 'DOC-007'

            doc_num_long = generate_document_number('seq_test', prefix='DOC', padding=8)
            assert doc_num_long == 'DOC-00000007'

    def test_generate_document_number_prefix_with_trailing_dash(self):
        with patch('packages.database.sequence.get_next_sequence_value', return_value=42):
            doc_num = generate_document_number('seq_test', prefix='INV-', padding=5)
            assert doc_num == 'INV-00042'

    def test_generate_document_number_empty_prefix(self):
        with patch('packages.database.sequence.get_next_sequence_value', return_value=5):
            doc_num = generate_document_number('seq_test', prefix='', padding=5)
            assert doc_num == '00005'

    def test_passes_conn_and_schema_to_get_next_sequence_value(self):
        mock_conn = MagicMock()
        with patch('packages.database.sequence.get_next_sequence_value', return_value=1) as mock_get_next:
            generate_document_number(
                sequence_name='seq_invoice_number',
                prefix='INV',
                padding=5,
                conn=mock_conn,
                schema='CustomSchema'
            )
            mock_get_next.assert_called_once_with('seq_invoice_number', conn=mock_conn, schema='CustomSchema')


# ============================================================================
# 5. Dedicated Invoice and Pick List Number Generator Tests
# ============================================================================

class TestDedicatedGenerators:
    def test_generate_invoice_number_defaults(self):
        with patch('packages.database.sequence.get_next_sequence_value', return_value=1) as mock_get_next:
            num = generate_invoice_number()
            assert num == 'INV-00001'
            mock_get_next.assert_called_once_with(
                DOCUMENT_SEQUENCES['invoice'],
                conn=None,
                schema=None
            )

    def test_generate_invoice_number_custom_args(self):
        mock_conn = MagicMock()
        with patch('packages.database.sequence.get_next_sequence_value', return_value=99) as mock_get_next:
            num = generate_invoice_number(conn=mock_conn, schema='Nova', prefix='INVOICE', padding=6)
            assert num == 'INVOICE-000099'
            mock_get_next.assert_called_once_with('seq_invoice_number', conn=mock_conn, schema='Nova')

    def test_generate_pick_list_number_defaults(self):
        with patch('packages.database.sequence.get_next_sequence_value', return_value=1) as mock_get_next:
            num = generate_pick_list_number()
            assert num == 'PKL-00001'
            mock_get_next.assert_called_once_with(
                DOCUMENT_SEQUENCES['pick_list'],
                conn=None,
                schema=None
            )

    def test_generate_pick_list_number_custom_args(self):
        mock_conn = MagicMock()
        with patch('packages.database.sequence.get_next_sequence_value', return_value=250) as mock_get_next:
            num = generate_pick_list_number(conn=mock_conn, schema='Nova', prefix='PICK', padding=4)
            assert num == 'PICK-0250'
            mock_get_next.assert_called_once_with('seq_pick_list_number', conn=mock_conn, schema='Nova')


# ============================================================================
# 6. Set, Reset and Get Current Sequence Value Tests
# ============================================================================

class TestSequenceManagementFunctions:
    def test_set_sequence_value_with_default_conn(self):
        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cur
        mock_cur.fetchone.return_value = (50,)

        with patch('packages.database.sequence.get_connection', return_value=mock_conn), \
             patch('packages.database.sequence.release_connection') as mock_rel:
            res = set_sequence_value('seq_invoice_number', value=50, is_called=True, schema='Nova')
            assert res == 50
            mock_cur.execute.assert_called_once_with(
                'SELECT setval(%s, %s, %s)',
                ('"Nova"."seq_invoice_number"', 50, True)
            )
            mock_rel.assert_called_once_with(mock_conn)

    def test_reset_sequence_calls_set_sequence_value_with_is_called_false(self):
        with patch('packages.database.sequence.set_sequence_value', return_value=1) as mock_setval:
            res = reset_sequence('seq_invoice_number', start_val=1, schema='Nova')
            assert res == 1
            mock_setval.assert_called_once_with(
                sequence_name='seq_invoice_number',
                value=1,
                is_called=False,
                conn=None,
                schema='Nova'
            )

    def test_get_current_sequence_value(self):
        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cur
        mock_cur.fetchone.return_value = (105,)

        with patch('packages.database.sequence.get_connection', return_value=mock_conn), \
             patch('packages.database.sequence.release_connection') as mock_rel:
            res = get_current_sequence_value('seq_invoice_number', schema='Nova')
            assert res == 105
            mock_cur.execute.assert_called_once_with('SELECT last_value FROM "Nova"."seq_invoice_number"')
            mock_rel.assert_called_once_with(mock_conn)

    def test_get_current_sequence_value_raises_if_empty_row(self):
        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cur
        mock_cur.fetchone.return_value = None

        with patch('packages.database.sequence.get_connection', return_value=mock_conn), \
             patch('packages.database.sequence.release_connection'):
            with pytest.raises(RuntimeError, match="Could not retrieve last value"):
                get_current_sequence_value('seq_invoice_number', schema='Nova')


# ============================================================================
# 7. Model Schema Optional Sequence Defaults Tests
# ============================================================================

class TestModelSequenceDefaults:
    def test_invoice_create_optional_invoice_number(self):
        data = {
            'partner_id': 10,
            'issue_date': '2026-08-20',
            'due_date': '2026-09-20',
            'total_amount': 250.0,
        }
        invoice = InvoiceCreate(**data)
        assert invoice.invoice_number is None
        assert invoice.partner_id == 10
        assert invoice.total_amount == 250.0

    def test_invoice_create_explicit_invoice_number(self):
        data = {
            'invoice_number': 'INV-MANUAL-001',
            'partner_id': 10,
            'issue_date': '2026-08-20',
            'due_date': '2026-09-20',
            'total_amount': 250.0,
        }
        invoice = InvoiceCreate(**data)
        assert invoice.invoice_number == 'INV-MANUAL-001'

    def test_invoice_update_optional_invoice_number(self):
        update = InvoiceUpdate(notes='Updated notes')
        assert update.invoice_number is None
        assert update.notes == 'Updated notes'

    def test_pick_list_create_optional_pick_list_number(self):
        data = {
            'sales_order_id': 5,
            'warehouse_id': 2,
        }
        pl = PickListCreate(**data)
        assert pl.pick_list_number is None
        assert pl.sales_order_id == 5
        assert pl.warehouse_id == 2
        assert pl.status == 'Pending'

    def test_pick_list_create_explicit_pick_list_number(self):
        data = {
            'pick_list_number': 'PKL-CUSTOM-99',
            'sales_order_id': 5,
        }
        pl = PickListCreate(**data)
        assert pl.pick_list_number == 'PKL-CUSTOM-99'

    def test_pick_list_update_optional_pick_list_number(self):
        update = PickListUpdate(status='In Progress')
        assert update.pick_list_number is None
        assert update.status == 'In Progress'


# ============================================================================
# 8. Service Auto-Generation & Fallback Integration Tests
# ============================================================================

class TestServiceSequenceIntegration:
    def test_invoice_service_auto_generates_invoice_number_when_omitted(self):
        mock_repo = MagicMock()
        mock_repo.create.side_effect = lambda payload, conn=None: {'id': 1, **payload}
        svc = InvoiceService(mock_repo)

        with patch('modules.accounting.services.invoice_service.generate_invoice_number', return_value='INV-00001') as mock_gen:
            created = svc.create({
                'partner_id': 1,
                'issue_date': '2026-08-20',
                'due_date': '2026-09-20',
                'total_amount': 100.0,
            })
            assert mock_gen.called
            assert created['invoice_number'] == 'INV-00001'
            assert created['partner_id'] == 1

    def test_invoice_service_preserves_explicit_invoice_number(self):
        mock_repo = MagicMock()
        mock_repo.create.side_effect = lambda payload, conn=None: {'id': 1, **payload}
        svc = InvoiceService(mock_repo)

        with patch('modules.accounting.services.invoice_service.generate_invoice_number') as mock_gen:
            created = svc.create({
                'invoice_number': 'INV-EXPLICIT-100',
                'partner_id': 1,
                'issue_date': '2026-08-20',
                'due_date': '2026-09-20',
                'total_amount': 100.0,
            })
            assert not mock_gen.called
            assert created['invoice_number'] == 'INV-EXPLICIT-100'

    def test_pick_list_service_auto_generates_pick_list_number_when_omitted(self):
        mock_repo = MagicMock()
        mock_repo.create.side_effect = lambda payload, conn=None: {'id': 1, **payload}
        svc = PickListService(mock_repo)

        with patch('modules.warehouse.services.pick_list_service.generate_pick_list_number', return_value='PKL-00001') as mock_gen:
            created = svc.create({
                'sales_order_id': 10,
                'warehouse_id': 1,
                'status': 'Pending',
            })
            assert mock_gen.called
            assert created['pick_list_number'] == 'PKL-00001'
            assert created['sales_order_id'] == 10

    def test_pick_list_service_preserves_explicit_pick_list_number(self):
        mock_repo = MagicMock()
        mock_repo.create.side_effect = lambda payload, conn=None: {'id': 1, **payload}
        svc = PickListService(mock_repo)

        with patch('modules.warehouse.services.pick_list_service.generate_pick_list_number') as mock_gen:
            created = svc.create({
                'pick_list_number': 'PKL-CUSTOM-123',
                'sales_order_id': 10,
                'warehouse_id': 1,
                'status': 'Pending',
            })
            assert not mock_gen.called
            assert created['pick_list_number'] == 'PKL-CUSTOM-123'

    def test_pick_list_service_raises_runtime_error_if_sequence_generation_fails(self):
        mock_repo = MagicMock()
        svc = PickListService(mock_repo)

        with patch('modules.warehouse.services.pick_list_service.generate_pick_list_number', side_effect=Exception("Database down")):
            with pytest.raises(RuntimeError, match="Failed to generate pick list number"):
                svc.create({
                    'sales_order_id': 10,
                    'warehouse_id': 1,
                })
            assert not mock_repo.create.called
