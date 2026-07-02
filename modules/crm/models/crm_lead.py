from typing import Optional
from pydantic import Field
from modules.core.models.factory import crud_model


LeadCreate, LeadUpdate, LeadResponse = crud_model('Lead', [
    ('first_name', str, Field(..., max_length=100)),
    ('last_name', str, Field(..., max_length=100)),
    ('email', Optional[str], Field(None, max_length=255)),
    ('phone', Optional[str], Field(None, max_length=50)),
    ('company', Optional[str], Field(None, max_length=200)),
    ('title', Optional[str], Field(None, max_length=100)),
    ('source', str, 'Website'),
    ('status', str, 'New'),
    ('assigned_to', Optional[int], None),
    ('notes', Optional[str], None),
])

LeadActivityCreate, LeadActivityUpdate, LeadActivityResponse = crud_model('LeadActivity', [
    ('lead_id', int, ...),
    ('activity_type', str, Field(..., max_length=30)),
    ('subject', str, Field(..., max_length=200)),
    ('description', Optional[str], None),
    ('activity_date', str, None),
    ('completed', bool, False),
])

OpportunityCreate, OpportunityUpdate, OpportunityResponse = crud_model('Opportunity', [
    ('opportunity_name', str, Field(..., max_length=200)),
    ('lead_id', Optional[int], None),
    ('customer_id', Optional[int], None),
    ('stage', str, 'Prospecting'),
    ('amount', float, Field(0, ge=0)),
    ('probability', int, Field(10, ge=0, le=100)),
    ('expected_close_date', Optional[str], None),
    ('assigned_to', Optional[int], None),
    ('notes', Optional[str], None),
])

OpportunityLineCreate, OpportunityLineUpdate, OpportunityLineResponse = crud_model('OpportunityLine', [
    ('opportunity_id', int, ...),
    ('product_id', Optional[int], None),
    ('product_name', str, Field(..., max_length=200)),
    ('qty', float, Field(..., gt=0)),
    ('unit_price', float, Field(0, ge=0)),
    ('line_total', float, Field(0, ge=0)),
    ('line_number', int, 0),
])
