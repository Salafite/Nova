window.QuotationModel = class Quotation {
  constructor(fields) {
    this.id = fields.id || 0
    this.quoteNumber = fields.quoteNumber || ''
    this.customerId = fields.customerId || 0
    this.customerName = fields.customerName || ''
    this.quoteDate = fields.quoteDate || ''
    this.validUntil = fields.validUntil || ''
    this.subtotal = fields.subtotal || 0
    this.tax = fields.tax || 0
    this.grandTotal = fields.grandTotal || 0
    this.status = fields.status || 'Draft'
    this.notes = fields.notes || ''
    this.convertedOrderId = fields.convertedOrderId || null
  }
}
