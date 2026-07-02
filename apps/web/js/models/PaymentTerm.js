window.PaymentTerm = class PaymentTerm {
  constructor(data) {
    this.id = data.id || null
    this.name = data.name || ''
    this.code = data.code || ''
    this.description = data.description || ''
    this.dueDays = data.dueDays !== undefined ? data.dueDays : 30
    this.discountPercentage = data.discountPercentage !== undefined ? data.discountPercentage : 0
    this.discountDays = data.discountDays !== undefined ? data.discountDays : 0
    this.isActive = data.isActive !== undefined ? data.isActive : true
    this.isDefault = data.isDefault !== undefined ? data.isDefault : false
  }
}
