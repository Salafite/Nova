window.DocumentService = class DocumentService {
  constructor() {
    this.api = new ApiClient('T0062I')
    this._data = []
  }
  async load() {
    try {
      this._data = await this.api.list() || []
    } catch (e) {
      console.warn('Failed to load documents', e)
      this._data = []
    }
  }
  getAll() { return this._data }
  getById(id) { return this._data.find(function(x) { return x.id == id }) }
  async create(payload) {
    var item = await this.api.create(payload)
    this._data.push(item)
    return item
  }
  async remove(id) {
    await this.api.delete(id)
    this._data = this._data.filter(function(x) { return x.id != id })
  }
  getTotalSize() {
    return this._data.reduce(function(s, x) { return s + (x.size || 0) }, 0)
  }
}
