from modules.maintenance.models.asset import AssetCreate, AssetUpdate, AssetResponse
from modules.core.services.base import CrudService
from modules.core.repositories.base import CrudRepository
from modules.core.controllers.base import create_crud_router

repo = CrudRepository('T0041', business_columns=['id', 'asset_code', 'asset_name', 'asset_type', 'asset_model', 'serial_no', 'location', 'department_id', 'purchase_date', 'purchase_cost', 'useful_life', 'warranty_expiry', 'status', 'is_active'])
service = CrudService(repo)
router = create_crud_router('/api/T0041I', 'T0041 - Assets', service,
                            AssetCreate, AssetUpdate, AssetResponse)
