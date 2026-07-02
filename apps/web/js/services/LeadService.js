window.LeadService = class LeadService {
  constructor() {
    this.api = new ApiClient('T0092I')
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

  async qualify(id) {
    const r = await this.api._fetch(this.api.base + '/' + id + '/qualify', { method: 'POST' })
    const idx = this._cache.findIndex(c => c.id === id)
    if (idx >= 0) this._cache[idx] = r
    return r
  }

  async disqualify(id) {
    const r = await this.api._fetch(this.api.base + '/' + id + '/disqualify', { method: 'POST' })
    const idx = this._cache.findIndex(c => c.id === id)
    if (idx >= 0) this._cache[idx] = r
    return r
  }

  async convert(id) {
    const r = await this.api._fetch(this.api.base + '/' + id + '/convert', { method: 'POST' })
    const idx = this._cache.findIndex(c => c.id === id)
    if (idx >= 0) this._cache[idx] = r
    return r
  }
}
