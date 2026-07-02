from modules.core.services.base import CrudService


class NotificationService(CrudService):
    def mark_read(self, id_val):
        return self.repo.update(id_val, {'is_read': True})

    def mark_all_read(self, user_id):
        notifications = self.repo.list({'user_id': user_id})
        for n in notifications:
            if not n.get('is_read'):
                self.repo.update(n['id'], {'is_read': True})
        return True
