window.LeaveRequestModel = class LeaveRequest {
  constructor(fields) {
    this.id = fields.id || 0
    this.employee_id = fields.employee_id || 0
    this.employee_name = fields.employee_name || ''
    this.leave_type = fields.leave_type || ''
    this.start_date = fields.start_date || ''
    this.end_date = fields.end_date || ''
    this.days = fields.days || 0
    this.reason = fields.reason || ''
    this.status = fields.status || 'Pending'
  }
}
