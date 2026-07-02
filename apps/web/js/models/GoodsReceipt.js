window.GoodsReceipt = class GoodsReceipt {
  constructor(fields) {
    this.id = fields.id || ''
    this.receiptNumber = fields.receiptNumber || ''
    this.purchaseOrderId = fields.purchaseOrderId || ''
    this.receiptDate = fields.receiptDate || new Date().toISOString().slice(0,10)
    this.warehouseId = fields.warehouseId || ''
    this.status = fields.status || 'Draft'
    this.notes = fields.notes || ''
  }
}
