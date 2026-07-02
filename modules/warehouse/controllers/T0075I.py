from modules.warehouse.models.warehouse import GoodsReceiptCreate, GoodsReceiptUpdate, GoodsReceiptResponse
from modules.warehouse.services.goods_receipt_service import GoodsReceiptService
from modules.core.repositories.base import CrudRepository
from modules.core.controllers.base import create_crud_router

repo = CrudRepository('T0075', business_columns=['id', 'receipt_number', 'purchase_order_id', 'receipt_date', 'warehouse_id', 'status', 'notes'])
service = GoodsReceiptService(repo)
router = create_crud_router('/api/T0075I', 'T0075 - Goods Receipts', service,
                            GoodsReceiptCreate, GoodsReceiptUpdate, GoodsReceiptResponse)
