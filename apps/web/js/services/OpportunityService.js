window.OpportunityService = class OpportunityService {
  constructor() {
    this.api = new ApiClient('T0094I')
    this._cache = []
  }

  async load() {
    this._cache = (await this.api.list()) || []
  }

  getAll() { return this._cache }

  getById(id) { return this._cache.find(c => c.id === id) }

  async add(record) {
    const r = await this.api.create(record)
    this._cache.push(r)
    return r
  }

  async update(record) {
    const r = await this.api.update(record.id, record)
    const idx = this._cache.findIndex(c => c.id === record.id)
    if (idx >= 0) this._cache[idx] = r
    return r
  }

  async remove(id) {
    await this.api.delete(id)
    this._cache = this._cache.filter(c => c.id !== id)
  }
}
