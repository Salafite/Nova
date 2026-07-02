window.SerialNumber = class SerialNumber {
  constructor(fields) {
    this.id = fields.id || 0
    this.productId = fields.productId || fields.product_id || ''
    this.serialNumber = fields.serialNumber || fields.serial_number || ''
    this.status = fields.status || 'In Stock'
    this.warehouseId = fields.warehouseId || fields.warehouse_id || ''
    this.purchaseOrderLineId = fields.purchaseOrderLineId || fields.purchase_order_line_id || ''
    this.salesOrderLineId = fields.salesOrderLineId || fields.sales_order_line_id || ''
    this.notes = fields.notes || ''
  }
}
