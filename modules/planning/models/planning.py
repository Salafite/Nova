from typing import Optional
from datetime import date
from pydantic import Field
from models.factory import crud_model


PlanCreate, PlanUpdate, PlanResponse = crud_model('Plan', [
    ('plan_number', str, Field(..., max_length=30)),
    ('product_id', Optional[int], None),
    ('product_name', str, Field(..., max_length=200)),
    ('quantity', float, Field(..., gt=0)),
    ('start_date', Optional[date], None),
    ('end_date', Optional[date], None),
    ('status', str, 'Draft'),
    ('notes', Optional[str], None),
])
