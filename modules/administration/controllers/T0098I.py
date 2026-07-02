from modules.administration.models.notification import NotificationCreate, NotificationUpdate, NotificationResponse
from modules.administration.services.notification_service import NotificationService
from modules.core.repositories.base import CrudRepository
from modules.core.controllers.base import create_crud_router

repo = CrudRepository('T0098', business_columns=['id', 'user_id', 'title', 'message', 'notification_type', 'reference_type', 'reference_id', 'is_read'])
service = NotificationService(repo)
router = create_crud_router('/api/T0098I', 'T0098 - User Notifications', service,
                            NotificationCreate, NotificationUpdate, NotificationResponse)

@router.put('/{id}/read')
def mark_read(id: int):
    return {'ok': service.mark_read(id)}

@router.put('/read-all/{user_id}')
def mark_all_read(user_id: int):
    return {'ok': service.mark_all_read(user_id)}
