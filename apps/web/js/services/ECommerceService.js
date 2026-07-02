window.ECommerceService = class ECommerceService {
  constructor() {
    this.api = new ApiClient('T0058I')
    this._data = []
    this._stores = []
  }
  async load() {
    try {
      this._data = await this.api.list() || []
    } catch (e) {
      console.warn('Failed to load e-commerce data', e)
      this._data = []
    }
    try {
      var storeApi = new ApiClient('T0059I')
      this._stores = await storeApi.list() || []
    } catch (e) {
      console.warn('Failed to load store connections', e)
      this._stores = []
    }
  }
  getAll() { return this._data }
  getStores() { return this._stores }
  async create(payload) {
    var item = await this.api.create(payload)
    this._data.push(item)
    return item
  }
  async remove(id) {
    await this.api.delete(id)
    this._data = this._data.filter(function(x) { return x.id != id })
  }
}
