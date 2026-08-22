import json
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any

from modules.core.services.base import CrudService
from modules.core.repositories.base import CrudRepository

logger = logging.getLogger(__name__)


class SchedulerService(CrudService):
    def __init__(self, repo=None):
        if repo is None:
            repo = CrudRepository('T0099', business_columns=['id', 'task_name', 'task_type', 'cron_expression', 'description', 'config', 'is_active', 'last_run_at', 'next_run_at', 'status'])
        super().__init__(repo)

    def run_now(self, id_val: int) -> bool:
        task = self.repo.get(id_val)
        if not task:
            raise ValueError(f"Scheduled task #{id_val} not found")

        now_utc = datetime.now(timezone.utc)
        self.repo.update(id_val, {'status': 'Running', 'last_run_at': now_utc})

        task_type = str(task.get('task_type', '') or '')
        config = task.get('config')
        if isinstance(config, str):
            try:
                config = json.loads(config)
            except Exception:
                config = {}
        elif not isinstance(config, dict):
            config = {}

        try:
            if task_type == 'DemandForecastRestock' or 'restock' in task_type.lower() or 'restock' in str(task.get('task_name', '')).lower():
                from modules.purchasing.services.restock_agent import RestockAgentService
                agent = RestockAgentService()
                days = config.get('days', 30)
                safety_margin = config.get('safety_margin_days', 7)
                target_coverage = config.get('target_coverage_days', 30)
                warehouse_id = config.get('warehouse_id')
                send_notif = config.get('send_notification', True)

                agent.run_evaluation(
                    warehouse_id=warehouse_id,
                    days=days,
                    safety_margin_days=safety_margin,
                    target_coverage_days=target_coverage,
                    send_notification=send_notif,
                )

            self.repo.update(id_val, {'status': 'Completed', 'last_run_at': datetime.now(timezone.utc)})
            return True
        except Exception as e:
            logger.error(f"Error running scheduled task #{id_val} ({task_type}): {e}")
            self.repo.update(id_val, {'status': 'Failed', 'last_run_at': datetime.now(timezone.utc)})
            raise

