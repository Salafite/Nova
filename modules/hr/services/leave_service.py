from modules.core.services.base import CrudService
from modules.core.repositories.base import CrudRepository

class LeaveRequestService(CrudService):
    def create(self, payload: dict):
        employee_id = payload.get('employee_id')
        leave_type_id = payload.get('leave_type_id')
        days = payload.get('days', 0)

        if employee_id and leave_type_id and days:
            leave_type_repo = CrudRepository('T0035', business_columns=['id', 'leave_code', 'leave_name', 'days_per_year', 'is_paid'])
            leave_type = leave_type_repo.get(leave_type_id)
            if leave_type:
                max_days = leave_type.get('days_per_year', 0)
                if max_days > 0:
                    leave_repo = CrudRepository('T0036', business_columns=['id', 'employee_id', 'leave_type_id', 'days', 'status'])
                    all_leave = leave_repo.list(filters={'employee_id': employee_id, 'leave_type_id': leave_type_id})
                    taken = sum(l.get('days', 0) for l in all_leave if l.get('status') in ('Approved', 'Pending'))
                    remaining = max_days - taken
                    if days > remaining:
                        from fastapi import HTTPException
                        raise HTTPException(400, f'Insufficient leave balance. Requested: {days}, Remaining: {remaining}, Entitled: {max_days}')

        return super().create(payload)
