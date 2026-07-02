window.SalesOrderModel = class SalesOrder {
  constructor(fields) {
    this.id = fields.id || ''
    this.customer = fields.customer || ''
    this.items = fields.items || []
    this.total = fields.total || 0
    this.tax = fields.tax || 0
    this.grandTotal = fields.grandTotal || 0
    this.status = fields.status || 'Pending'
    this.date = fields.date || new Date().toISOString().slice(0, 10)
  }
}
