window.ChartOfAccountModel = class ChartOfAccount {
  constructor(fields) {
    this.id = fields.id || 0
    this.accountCode = fields.accountCode || ''
    this.accountName = fields.accountName || ''
    this.accountType = fields.accountType || ''
    this.parentId = fields.parentId || null
    this.currency = fields.currency || 'USD'
    this.isActive = fields.isActive !== undefined ? fields.isActive : true
  }
}
