window.PurchaseOrderModel = class PurchaseOrder {
  constructor(fields) {
    this.id = fields.id || ''
    this.supplier = fields.supplier || ''
    this.items = fields.items || []
    this.total = fields.total || 0
    this.status = fields.status || 'Pending'
    this.date = fields.date || new Date().toISOString().slice(0, 10)
  }
}
