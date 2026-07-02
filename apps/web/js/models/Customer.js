window.CustomerModel = class Customer {
  constructor(fields) {
    this.id = fields.id || 0
    this.name = fields.name || ''
    this.group = fields.group || 'Retail'
    this.phone = fields.phone || ''
    this.creditLimit = fields.creditLimit || 0
    this.balance = fields.balance || 0
  }
}
