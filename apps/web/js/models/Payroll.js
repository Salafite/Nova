window.PayrollModel = class Payroll {
  constructor(fields) {
    this.id = fields.id || 0
    this.employee_id = fields.employee_id || 0
    this.employee_name = fields.employee_name || ''
    this.period = fields.period || ''
    this.basic_salary = fields.basic_salary || 0
    this.allowances = fields.allowances || 0
    this.deductions = fields.deductions || 0
    this.net_pay = fields.net_pay || 0
    this.status = fields.status || 'Draft'
  }
}
