window.PaymentMethod = class PaymentMethod {
  constructor(data) {
    this.id = data.id || null
    this.name = data.name || ''
    this.code = data.code || ''
    this.description = data.description || ''
    this.isActive = data.isActive !== undefined ? data.isActive : true
    this.isDefault = data.isDefault !== undefined ? data.isDefault : false
  }
}
