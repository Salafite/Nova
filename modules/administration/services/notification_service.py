from typing import Optional, List, Dict, Any
import logging
from modules.core.services.base import CrudService
from modules.core.repositories.base import CrudRepository

logger = logging.getLogger(__name__)


class NotificationService(CrudService):
    def __init__(self, repo=None):
        if repo is None:
            repo = CrudRepository('T0098', business_columns=['id', 'user_id', 'title', 'message', 'notification_type', 'reference_type', 'reference_id', 'is_read'])
        super().__init__(repo)
        self.user_repo = CrudRepository('T0021', business_columns=['id', 'username', 'role', 'permissions', 'is_active'])

    def mark_read(self, id_val: int) -> Optional[dict]:
        return self.repo.update(id_val, {'is_read': True})

    def mark_all_read(self, user_id: int) -> bool:
        notifications = self.repo.list({'user_id': user_id})
        for n in notifications:
            if not n.get('is_read'):
                self.repo.update(n['id'], {'is_read': True})
        return True

    def create_notification(
        self,
        user_id: int,
        title: str,
        message: Optional[str] = None,
        notification_type: str = 'Info',
        reference_type: Optional[str] = None,
        reference_id: Optional[int] = None,
        conn=None,
    ) -> dict:
        payload = {
            'user_id': user_id,
            'title': title,
            'message': message,
            'notification_type': notification_type,
            'reference_type': reference_type,
            'reference_id': reference_id,
            'is_read': False,
        }
        return self.repo.create(payload, conn=conn)

    def notify_roles(
        self,
        roles: Optional[List[str]] = None,
        title: str = "",
        message: Optional[str] = None,
        notification_type: str = 'Info',
        reference_type: Optional[str] = None,
        reference_id: Optional[int] = None,
        conn=None,
    ) -> List[dict]:
        """Send notifications to all active users whose role or permissions match the specified roles.
        If no matching users are found, defaults to user_id=1.
        """
        target_roles = [r.lower() for r in (roles or ['admin', 'purchasing', 'procurement', 'manager'])]
        user_ids = []

        try:
            users = self.user_repo.list(conn=conn)
            for u in users:
                u_role = str(u.get('role', '') or '').lower()
                u_perms = str(u.get('permissions', '') or '').lower()
                if any(r in u_role or r in u_perms for r in target_roles):
                    user_ids.append(u.get('id'))
        except Exception as e:
            logger.warning(f"Error querying users for notification dispatch: {e}")

        if not user_ids:
            user_ids = [1]

        created = []
        for uid in set(user_ids):
            if uid is not None:
                notif = self.create_notification(
                    user_id=uid,
                    title=title,
                    message=message,
                    notification_type=notification_type,
                    reference_type=reference_type,
                    reference_id=reference_id,
                    conn=conn,
                )
                created.append(notif)
        return created

