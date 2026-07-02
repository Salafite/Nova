from modules.core.services.base import CrudService


class SchedulerService(CrudService):
    def run_now(self, id_val):
        return self.repo.update(id_val, {'status': 'Running'})
