"""
Nova ERP — Stock Transfer Lines REST Controller (T0109I)
CRUD operations and line-item management for multi-warehouse stock transfers.
"""
from modules.warehouse.models.stock_transfer import (
    StockTransferLineCreate,
    StockTransferLineUpdate,
    StockTransferLineResponse,
)
from modules.core.services.base import CrudService
from modules.core.repositories.base import CrudRepository
from modules.core.controllers.base import create_crud_router

repo = CrudRepository(
    'T0109',
    business_columns=[
        'id', 'transfer_id', 'product_id', 'qty_requested', 'qty_dispatched',
        'qty_received', 'qty_lost', 'loss_reason', 'loss_notes', 'batch_id',
        'batch_number', 'line_number', 'notes', 'is_active', 'business_id'
    ]
)
service = CrudService(repo)

router = create_crud_router(
    '/api/T0109I',
    'T0109 - Stock Transfer Lines',
    service,
    StockTransferLineCreate,
    StockTransferLineUpdate,
    StockTransferLineResponse,
)
