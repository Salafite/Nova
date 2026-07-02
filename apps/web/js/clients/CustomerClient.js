class CustomerClient {
  constructor() {
    this.api = new ApiClient('T0010I')
    this._cache = []
  }

  async load() {
    this._cache = (await this.api.list()) || []
  }

  getAll() { return this._cache }

  getById(id) { return this._cache.find(c => c.id === id) }

  getByName(name) { return this._cache.find(c => c.name === name) }

  async add(record) {
    const customer = await this.api.create(record)
    customer.balance = 0
    this._cache.push(customer)
    return customer
  }

  async update(record) {
    const updated = await this.api.update(record.id, record)
    const idx = this._cache.findIndex(c => c.id === record.id)
    if (idx >= 0) this._cache[idx] = updated
    return updated
  }
}
