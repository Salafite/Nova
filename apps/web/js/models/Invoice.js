window.InvoiceModel = class Invoice {
  constructor(fields) {
    this.id = fields.id || 0
    this.invoiceNumber = fields.invoiceNumber || ''
    this.invoiceType = fields.invoiceType || 'Sales'
    this.partnerId = fields.partnerId || 0
    this.issueDate = fields.issueDate || new Date().toISOString().split('T')[0]
    this.dueDate = fields.dueDate || ''
    this.totalAmount = fields.totalAmount || 0
    this.status = fields.status || 'Draft'
    this.notes = fields.notes || ''
  }
}
