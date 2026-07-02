window.PurchaseRequisitionModel = class PurchaseRequisition {
  constructor(fields) {
    this.id = fields.id || ''
    this.reqNumber = fields.reqNumber || ''
    this.title = fields.title || ''
    this.description = fields.description || ''
    this.departmentId = fields.departmentId || ''
    this.requestedBy = fields.requestedBy || ''
    this.approvedBy = fields.approvedBy || ''
    this.status = fields.status || 'Draft'
    this.priority = fields.priority || 'Medium'
    this.notes = fields.notes || ''
    this.createdAt = fields.createdAt || ''
  }
}
