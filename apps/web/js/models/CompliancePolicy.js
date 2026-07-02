window.CompliancePolicy = class CompliancePolicy {
  constructor(fields) {
    this.id = fields.id || 0
    this.name = fields.name || ''
    this.category = fields.category || ''
    this.status = fields.status || 'Active'
    this.lastAuditAt = fields.lastAuditAt || ''
    this.riskLevel = fields.riskLevel || 'Low'
  }
}
