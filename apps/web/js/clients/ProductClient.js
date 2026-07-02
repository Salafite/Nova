class ProductClient {
  constructor() {
    this.api = new ApiClient('T0003I')
    this.invApi = new ApiClient('T0009I')
    this._cache = []
  }

  async load() {
    this._cache = (await this.api.list()) || []
  }

  getAll() { return this._cache }

  getById(id) { return this._cache.find(p => p.id === id) }

  getByName(name) { return this._cache.find(p => p.name === name) }

  async add(record) {
    const stock = record.stock || 0
    var body = Object.assign({}, record)
    delete body.stock
    if (!body.taxRate) body.taxRate = 0.05
    const product = await this.api.create(body)
    await this.invApi.create({ productId: product.id, warehouseId: 1, qty: stock, reorderLevel: 10 })
    this._cache.push(product)
    return product
  }

  async remove(id) {
    await this.api.delete(id)
    this._cache = this._cache.filter(p => p.id !== id)
  }
}
