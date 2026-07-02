window.Delivery = class Delivery {
  constructor(fields) {
    this.id = fields.id || ''
    this.deliveryNumber = fields.deliveryNumber || ''
    this.salesOrderId = fields.salesOrderId || ''
    this.deliveryDate = fields.deliveryDate || new Date().toISOString().slice(0,10)
    this.warehouseId = fields.warehouseId || ''
    this.status = fields.status || 'Draft'
    this.notes = fields.notes || ''
  }
}
