window.AuditLogService = class AuditLogService {
  constructor() {
    this.api = new ApiClient('T0023I')
    this._entries = []
  }

  async load() {
    try {
      this._entries = await this.api.list() || []
    } catch (e) {
      console.warn('Failed to load audit log', e)
      this._entries = []
    }
  }

  getAll() { return this._entries }

  async getById(id) { return this.api.get(id) }

  getActionCounts() {
    var counts = { INSERT: 0, UPDATE: 0, DELETE: 0 }
    this._entries.forEach(function(e) {
      if (counts[e.action] !== undefined) counts[e.action]++
    })
    return counts
  }
}
