window.OpportunityModel = class Opportunity {
  constructor(fields) {
    this.id = fields.id || 0
    this.opportunityName = fields.opportunityName || ''
    this.leadId = fields.leadId || null
    this.customerId = fields.customerId || null
    this.stage = fields.stage || 'Prospecting'
    this.amount = fields.amount || 0
    this.probability = fields.probability || 10
    this.expectedCloseDate = fields.expectedCloseDate || null
    this.assignedTo = fields.assignedTo || null
    this.notes = fields.notes || ''
  }
}
