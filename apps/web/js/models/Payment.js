window.PaymentModel = class Payment {
  constructor(fields) {
    this.id = fields.id || 0
    this.paymentDate = fields.paymentDate || new Date().toISOString().split('T')[0]
    this.invoiceId = fields.invoiceId || 0
    this.partnerId = fields.partnerId || 0
    this.amount = fields.amount || 0
    this.paymentMethod = fields.paymentMethod || 'Bank Transfer'
    this.reference = fields.reference || ''
    this.status = fields.status || 'Completed'
    this.notes = fields.notes || ''
  }
}
