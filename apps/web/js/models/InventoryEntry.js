window.InventoryEntryModel = class InventoryEntry {
  constructor(fields) {
    this.productId = fields.productId || 0
    this.warehouse = fields.warehouse || 'Main'
    this.qty = fields.qty || 0
    this.reorderLevel = fields.reorderLevel || 10
  }
}
