window.AttendanceModel = class Attendance {
  constructor(fields) {
    this.id = fields.id || 0
    this.employee_id = fields.employee_id || 0
    this.employee_name = fields.employee_name || ''
    this.date = fields.date || ''
    this.clock_in = fields.clock_in || ''
    this.clock_out = fields.clock_out || ''
    this.status = fields.status || 'Present'
  }
}
