window.PriceListModel = class PriceList {
  constructor(fields) {
    this.id = fields.id || 0
    this.name = fields.name || ''
    this.code = fields.code || ''
    this.description = fields.description || ''
    this.currency = fields.currency || 'USD'
    this.isActive = fields.isActive !== undefined ? fields.isActive : true
    this.isDefault = fields.isDefault !== undefined ? fields.isDefault : false
  }
}
