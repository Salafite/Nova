from modules.accounting.models import InvoiceCreate, InvoiceUpdate, InvoiceResponse
from modules.accounting.services.invoice_service import InvoiceService
from modules.core.repositories.base import CrudRepository
from modules.core.controllers.base import create_crud_router

repo = CrudRepository(
    'T0090',
    business_columns=[
        'id',
        'invoice_number',
        'invoice_type',
        'partner_id',
        'sales_order_id',
        'sales_rep_id',
        'issue_date',
        'due_date',
        'total_amount',
        'freight_amount',
        'discount_amount',
        'status',
        'notes',
        'is_catch_weight',
        'nominal_total_weight',
        'actual_total_weight',
        'weight_adjustment_amount',
    ],
)
service = InvoiceService(repo)
router = create_crud_router(
    '/api/T0090I',
    'T0090 - Invoices',
    service,
    InvoiceCreate,
    InvoiceUpdate,
    InvoiceResponse,
)


@router.post('/from-order/{order_id}', status_code=201)
def create_invoice_from_order(order_id: int):
    """Generate a catch-weight adjusted invoice from a sales order."""
    try:
        return service.recalculate_and_invoice_order(order_id)
    except ValueError as e:
        from fastapi import HTTPException
        if 'not found' in str(e).lower():
            raise HTTPException(404, str(e))
        raise HTTPException(400, str(e))
    except HTTPException:
        raise
    except Exception as e:
        from fastapi import HTTPException
        raise HTTPException(500, f"Failed to create invoice from order: {e}")


@router.get('/{id}/catch-weight-breakdown')
def get_invoice_catch_weight_breakdown(id: int):
    """Retrieve catch-weight breakdown details for an invoice."""
    try:
        return service.get_catch_weight_breakdown(id)
    except ValueError as e:
        from fastapi import HTTPException
        raise HTTPException(404, str(e))
    except Exception as e:
        from fastapi import HTTPException
        raise HTTPException(500, f"Failed to get catch-weight breakdown: {e}")


