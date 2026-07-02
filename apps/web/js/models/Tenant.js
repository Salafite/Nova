window.Tenant = class Tenant {
  constructor(fields) {
    this.id = fields.id || 0
    this.name = fields.name || ''
    this.domain = fields.domain || ''
    this.plan = fields.plan || ''
    this.status = fields.status || 'Active'
    this.usersCount = fields.usersCount || 0
    this.createdAt = fields.createdAt || ''
  }
}
