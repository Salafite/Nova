window.Document = class Document {
  constructor(fields) {
    this.id = fields.id || 0
    this.name = fields.name || ''
    this.type = fields.type || ''
    this.size = fields.size || 0
    this.uploadedBy = fields.uploadedBy || ''
    this.uploadedAt = fields.uploadedAt || ''
    this.status = fields.status || 'Draft'
  }
}
