window.TaxRate = class TaxRate {
  constructor(data) {
    this.id = data.id || null
    this.name = data.name || ''
    this.code = data.code || ''
    this.rate = data.rate || 0
    this.type = data.type || 'Sales'
    this.isActive = data.isActive !== undefined ? data.isActive : true
    this.isDefault = data.isDefault !== undefined ? data.isDefault : false
    this.description = data.description || null
  }
}
