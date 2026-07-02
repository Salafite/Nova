class SalesOrderClient {
  constructor() {
    this.api = new ApiClient('T0012I')
    this._cache = []
  }

  async load() {
    this._cache = (await this.api.list({ order: 'id', sort: 'DESC' })) || []
  }

  getAll() { return this._cache }

  async add(record) {
    await this.api.create(record)
    this._cache.unshift(record)
    return record
  }
}
