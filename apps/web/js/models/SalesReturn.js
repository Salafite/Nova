window.SalesReturn = class SalesReturn {
  constructor(fields) {
    this.id = fields.id || ''
    this.returnNumber = fields.returnNumber || ''
    this.salesOrderId = fields.salesOrderId || ''
    this.customerId = fields.customerId || ''
    this.returnDate = fields.returnDate || new Date().toISOString().slice(0,10)
    this.status = fields.status || 'Draft'
    this.reason = fields.reason || ''
    this.notes = fields.notes || ''
  }
}
