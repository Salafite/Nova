window.EmployeeModel = class Employee {
  constructor(fields) {
    this.id = fields.id || 0
    this.name = fields.name || ''
    this.email = fields.email || ''
    this.phone = fields.phone || ''
    this.department_id = fields.department_id || 0
    this.department = fields.department || ''
    this.designation_id = fields.designation_id || 0
    this.designation = fields.designation || ''
    this.hire_date = fields.hire_date || ''
    this.status = fields.status || 'Active'
  }
}
