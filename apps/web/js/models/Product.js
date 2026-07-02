window.ProductModel = class Product {
  constructor(fields) {
    this.id = fields.id || 0
    this.name = fields.name || ''
    this.sku = fields.sku || ''
    this.price = fields.price || 0
    this.category = fields.category || ''
    this.taxRate = fields.taxRate || 0.05
  }
}
