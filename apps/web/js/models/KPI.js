window.KPIModel = class KPI {
  constructor(fields) {
    this.id = fields.id || 0
    this.name = fields.name || ''
    this.category = fields.category || ''
    this.target = fields.target || 0
    this.value = fields.value || 0
    this.status = fields.status || 'On Track'
  }
}
