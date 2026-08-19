from fastapi import APIRouter, Depends
from packages.auth.deps import require_permission
from ..services.dashboard_service import get_dashboard_summary

router = APIRouter(prefix='/api/bi/dashboard', tags=['BI Dashboard'], dependencies=[Depends(require_permission('BI_VIEW'))])


@router.get('/summary')
def dashboard_summary():
    return get_dashboard_summary()
