window.PurchaseReturnModel = class PurchaseReturn {
  constructor(fields) {
    this.id = fields.id || ''
    this.returnNumber = fields.returnNumber || ''
    this.purchaseOrderId = fields.purchaseOrderId || ''
    this.supplierId = fields.supplierId || ''
    this.returnDate = fields.returnDate || new Date().toISOString().slice(0, 10)
    this.status = fields.status || 'Draft'
    this.reason = fields.reason || ''
    this.notes = fields.notes || ''
  }
}
