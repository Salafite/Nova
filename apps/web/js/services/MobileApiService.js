window.MobileApiService = class MobileApiService {
  constructor() {
    this.api = new ApiClient('T0056I')
    this._data = []
    this._syncLogs = []
  }
  async load() {
    try {
      this._data = await this.api.list() || []
    } catch (e) {
      console.warn('Failed to load mobile API data', e)
      this._data = []
    }
    try {
      var syncApi = new ApiClient('T0058I')
      this._syncLogs = await syncApi.list() || []
    } catch (e) {
      console.warn('Failed to load sync logs', e)
      this._syncLogs = []
    }
  }
  getAll() { return this._data }
  getSyncLogs() { return this._syncLogs }
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
