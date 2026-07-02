window.BatchNumber = class BatchNumber {
  constructor(fields) {
    this.id = fields.id || 0
    this.productId = fields.productId || fields.product_id || ''
    this.batchNumber = fields.batchNumber || fields.batch_number || ''
    this.expiryDate = fields.expiryDate || fields.expiry_date || ''
    this.manufacturingDate = fields.manufacturingDate || fields.manufacturing_date || ''
    this.quantity = fields.quantity || 0
    this.warehouseId = fields.warehouseId || fields.warehouse_id || ''
    this.status = fields.status || 'Available'
    this.notes = fields.notes || ''
  }
}
