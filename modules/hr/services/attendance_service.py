from modules.core.services.base import CrudService
from modules.core.repositories.base import CrudRepository
from datetime import datetime

class AttendanceService(CrudService):
    def update(self, id_val, payload: dict):
        if 'clock_out' in payload or 'clock_in' in payload:
            old = self.repo.get(id_val)
            if old:
                clock_in = payload.get('clock_in', old.get('clock_in'))
                clock_out = payload.get('clock_out', old.get('clock_out'))
                if clock_in and clock_out:
                    try:
                        ci = clock_in if isinstance(clock_in, datetime) else datetime.fromisoformat(str(clock_in).replace('Z', '+00:00'))
                        co = clock_out if isinstance(clock_out, datetime) else datetime.fromisoformat(str(clock_out).replace('Z', '+00:00'))
                        hours = (co - ci).total_seconds() / 3600
                        shift_id = payload.get('shift_id', old.get('shift_id'))
                        expected_hours = 8
                        if shift_id:
                            shift_repo = CrudRepository('T0033', business_columns=['id', 'shift_code', 'shift_name', 'start_time', 'end_time', 'grace_minutes'])
                            shift = shift_repo.get(shift_id)
                        if hours >= expected_hours:
                            payload['status'] = 'Present'
                        elif hours >= expected_hours * 0.5:
                            payload['status'] = 'Half Day'
                        elif hours > 0:
                            payload['status'] = 'Short'
                        else:
                            payload['status'] = 'Absent'
                    except (ValueError, TypeError):
                        pass
        return super().update(id_val, payload)
