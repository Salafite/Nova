window.RFQModel = class RFQ {
  constructor(fields) {
    this.id = fields.id || ''
    this.rfqNumber = fields.rfqNumber || ''
    this.title = fields.title || ''
    this.description = fields.description || ''
    this.status = fields.status || 'Draft'
    this.dueDate = fields.dueDate || ''
    this.notes = fields.notes || ''
    this.createdAt = fields.createdAt || ''
  }
}
