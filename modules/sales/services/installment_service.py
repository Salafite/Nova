from modules.core.services.base import CrudService
from modules.core.repositories.base import CrudRepository

class InstallmentPlanService(CrudService):
    def create(self, payload: dict):
        result = super().create(payload)
        if result:
            plan_id = result['id']
            num = payload.get('num_installments', 1)
            total = payload.get('total_amount', 0)
            first_due = payload.get('first_due_date')
            freq = payload.get('frequency_days', 30)
            amount_per = round(total / num, 2)
            line_repo = CrudRepository('T0017', business_columns=['id', 'installment_plan_id', 'installment_number', 'due_date', 'amount_due'])
            from datetime import timedelta
            for i in range(num):
                due = first_due + timedelta(days=i * freq) if first_due else None
                line_repo.create({
                    'installment_plan_id': plan_id,
                    'installment_number': i + 1,
                    'due_date': str(due) if due else None,
                    'amount_due': amount_per if i < num - 1 else round(total - amount_per * (num - 1), 2),
                    'status': 'Pending',
                })
        return result
