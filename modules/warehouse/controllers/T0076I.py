from modules.warehouse.models.warehouse import GoodsReceiptLineCreate, GoodsReceiptLineUpdate, GoodsReceiptLineResponse
from modules.warehouse.services.goods_receipt_line_service import GoodsReceiptLineService
from modules.core.repositories.base import CrudRepository
from modules.core.controllers.base import create_crud_router

repo = CrudRepository('T0076', business_columns=['id', 'receipt_id', 'purchase_order_line_id', 'product_id', 'product_name', 'qty_received', 'qty_ordered', 'uom_id', 'line_number'])
service = GoodsReceiptLineService(repo)
router = create_crud_router('/api/T0076I', 'T0076 - Goods Receipt Lines', service,
                            GoodsReceiptLineCreate, GoodsReceiptLineUpdate, GoodsReceiptLineResponse)
