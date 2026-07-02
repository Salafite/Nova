class PurchaseOrderClient {
  constructor() {
    this.api = new ApiClient('T0014I')
    this._cache = []
  }

  async load() {
    this._cache = (await this.api.list()) || []
  }

  getAll() { return this._cache }

  getById(id) { return this._cache.find(r => r.id === id) }

  async add(record) {
    if (!record.id) {
      const maxId = this._cache.reduce((m, r) => {
        if (r.id && r.id.startsWith('PO-')) {
          const n = parseInt(r.id.substring(3), 10)
          return isNaN(n) ? m : Math.max(m, n)
        }
        return m
      }, 0)
      record.id = 'PO-' + String(maxId + 1).padStart(3, '0')
    }
    record.status = 'Pending'
    record.date = new Date().toISOString().slice(0, 10)
    await this.api.create(record)
    this._cache.unshift(record)
    return record
  }

  async update(record) {
    const updated = await this.api.update(record.id, record)
    const idx = this._cache.findIndex(r => r.id === record.id)
    if (idx >= 0) this._cache[idx] = updated
    return updated
  }
}
