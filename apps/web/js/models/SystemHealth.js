window.SystemHealth = class SystemHealth {
  constructor(fields) {
    this.id = fields.id || 0
    this.serviceName = fields.serviceName || ''
    this.status = fields.status || 'Healthy'
    this.version = fields.version || ''
    this.uptime = fields.uptime || '0%'
    this.lastChecked = fields.lastChecked || ''
  }
}
