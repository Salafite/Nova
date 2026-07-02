window.SupplierModel = class Supplier {
  constructor(fields) {
    this.id = fields.id || 0
    this.name = fields.name || ''
    this.category = fields.category || ''
    this.phone = fields.phone || ''
    this.email = fields.email || ''
    this.rating = fields.rating || 0
  }
}
