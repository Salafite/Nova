window.LeadModel = class Lead {
  constructor(fields) {
    this.id = fields.id || 0
    this.firstName = fields.firstName || ''
    this.lastName = fields.lastName || ''
    this.email = fields.email || ''
    this.phone = fields.phone || ''
    this.company = fields.company || ''
    this.title = fields.title || ''
    this.source = fields.source || 'Website'
    this.status = fields.status || 'New'
    this.assignedTo = fields.assignedTo || null
    this.notes = fields.notes || ''
  }
}
