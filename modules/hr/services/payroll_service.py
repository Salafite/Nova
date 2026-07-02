from modules.core.services.base import CrudService

class PayrollEntryService(CrudService):
    def create(self, payload: dict):
        # Auto-calculate gross_pay and net_pay
        basic = payload.get('basic_salary', 0) or 0
        housing = payload.get('housing_allowance', 0) or 0
        transport = payload.get('transport_allowance', 0) or 0
        other = payload.get('other_allowances', 0) or 0
        overtime = payload.get('overtime', 0) or 0
        deductions = payload.get('deductions', 0) or 0
        tax = payload.get('tax', 0) or 0

        gross = basic + housing + transport + other + overtime
        total_deductions = deductions + tax
        net = gross - total_deductions

        payload['gross_pay'] = round(gross, 2)
        payload['net_pay'] = round(max(net, 0), 2)

        return super().create(payload)

    def update(self, id_val, payload: dict):
        financial_fields = ['basic_salary', 'housing_allowance', 'transport_allowance', 'other_allowances', 'overtime', 'deductions', 'tax']
        if any(f in payload for f in financial_fields):
            old = self.repo.get(id_val)
            if old:
                basic = payload.get('basic_salary', old.get('basic_salary', 0)) or 0
                housing = payload.get('housing_allowance', old.get('housing_allowance', 0)) or 0
                transport = payload.get('transport_allowance', old.get('transport_allowance', 0)) or 0
                other = payload.get('other_allowances', old.get('other_allowances', 0)) or 0
                overtime = payload.get('overtime', old.get('overtime', 0)) or 0
                deductions = payload.get('deductions', old.get('deductions', 0)) or 0
                tax = payload.get('tax', old.get('tax', 0)) or 0

                gross = basic + housing + transport + other + overtime
                total_deductions = deductions + tax
                net = gross - total_deductions

                payload['gross_pay'] = round(gross, 2)
                payload['net_pay'] = round(max(net, 0), 2)

        return super().update(id_val, payload)
