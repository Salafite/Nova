from modules.administration.models import UserCreate, UserUpdate, UserResponse
from modules.core.services.user_service import UserService
from modules.core.repositories.base import CrudRepository
from modules.core.controllers.base import create_crud_router

repo = CrudRepository('T0021', business_columns=['id', 'username', 'password_hash', 'full_name', 'email', 'role', 'permissions', 'status', 'last_login'])
service = UserService(repo)
router = create_crud_router('/api/T0021I', 'T0021 - System Users', service,
                            UserCreate, UserUpdate, UserResponse)
