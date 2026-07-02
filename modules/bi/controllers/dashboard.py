from fastapi import APIRouter, Depends
from packages.auth.deps import get_current_user
from ..services.dashboard_service import get_dashboard_summary

router = APIRouter(prefix='/api/bi/dashboard', tags=['BI Dashboard'], dependencies=[Depends(get_current_user)])


@router.get('/summary')
def dashboard_summary():
    return get_dashboard_summary()
