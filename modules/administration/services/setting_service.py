from collections import defaultdict
from modules.core.services.base import CrudService


class SettingService(CrudService):
    def get_by_group(self):
        all_rows = self.repo.list()
        grouped = defaultdict(list)
        for row in all_rows:
            group = row.get('setting_group') or 'General'
            grouped[group].append(row)
        return [
            {'group': g, 'count': len(settings), 'settings': settings}
            for g, settings in grouped.items()
        ]

    def bulk_update(self, updates: list[dict]) -> int:
        count = 0
        for item in updates:
            sid = item.get('id')
            values = {k: v for k, v in item.items() if k != 'id' and v is not None}
            if not sid or not values:
                continue
            existing = self.repo.get(sid)
            if not existing:
                continue
            self.repo.update(sid, values)
            count += 1
        return count

    def list_by_group(self, group: str = None):
        filters = {}
        if group:
            filters['setting_group'] = group
        return self.repo.list(filters)
