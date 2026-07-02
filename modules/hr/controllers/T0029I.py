from modules.hr.models.employee import DesignationCreate, DesignationUpdate, DesignationResponse
from modules.core.services.base import CrudService
from modules.core.repositories.base import CrudRepository
from modules.core.controllers.base import create_crud_router

repo = CrudRepository('T0029', business_columns=['id', 'designation_code', 'designation_name', 'department_id', 'is_active'])
service = CrudService(repo)
router = create_crud_router('/api/T0029I', 'T0029 - Designations', service,
                            DesignationCreate, DesignationUpdate, DesignationResponse)
