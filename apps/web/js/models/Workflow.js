window.Workflow = class Workflow {
  constructor(fields) {
    this.id = fields.id || 0
    this.name = fields.name || ''
    this.type = fields.type || ''
    this.status = fields.status || 'Active'
    this.steps = fields.steps || 0
    this.lastRunAt = fields.lastRunAt || ''
  }
}
