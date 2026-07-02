window.MobilePOSService = class MobilePOSService {
  constructor() {
    this.api = new ApiClient('T0057I')
    this._data = []
  }
  async load() {
    try {
      this._data = await this.api.list() || []
    } catch (e) {
      console.warn('Failed to load mobile POS data', e)
      this._data = []
    }
  }
  getAll() { return this._data }
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
