from typing import Optional
from fastapi import HTTPException
from modules.warehouse.models.serial_batch import BatchNumberCreate, BatchNumberUpdate, BatchNumberResponse
from modules.core.repositories.base import CrudRepository
from modules.core.controllers.base import create_crud_router
from modules.warehouse.services.batch_number_service import BatchNumberService

repo = CrudRepository('T0088', business_columns=[
    'id', 'product_id', 'batch_number', 'expiry_date', 'manufacturing_date',
    'quantity', 'warehouse_id', 'status', 'notes'
])
service = BatchNumberService(repo)
router = create_crud_router('/api/T0088I', 'T0088 - Batch Numbers', service,
                            BatchNumberCreate, BatchNumberUpdate, BatchNumberResponse)


@router.get('/recall-report')
def get_batch_recall_report(batch_number: Optional[str] = None, batch_id: Optional[int] = None, product_id: Optional[int] = None):
    if not batch_number and not batch_id:
        raise HTTPException(400, 'Either batch_number or batch_id query parameter is required')
    try:
        result = service.get_recall_report(batch_number=batch_number, batch_id=batch_id, product_id=product_id)
        return result
    except ValueError as e:
        raise HTTPException(404, str(e))
    except Exception as e:
        raise HTTPException(500, str(e))


@router.get('/{id}/trace')
def get_batch_trace(id: int):
    try:
        result = service.get_recall_report(batch_id=id)
        return result
    except ValueError as e:
        raise HTTPException(404, str(e))
    except Exception as e:
        raise HTTPException(500, str(e))

