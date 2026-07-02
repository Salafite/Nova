window.PriceListService = class PriceListService {
  constructor() {
    this.api = new ApiClient('T0083I')
    this._data = []
  }

  async load() {
    try { this._data = await this.api.list() || [] } catch (e) { console.warn('Failed to load price lists', e); this._data = [] }
  }

  getAll() { return this._data }

  getById(id) { return this._data.find(function(p) { return p.id == id }) }

  async create(payload) { var item = await this.api.create(payload); this._data.push(item); return item }

  async update(id, payload) { var item = await this.api.update(id, payload); var i = this._data.findIndex(function(p) { return p.id == id }); if (i > -1) this._data[i] = item; return item }

  async remove(id) { await this.api.delete(id); this._data = this._data.filter(function(p) { return p.id != id }) }

  toggleActive(id) {
    var item = this.getById(id)
    if (!item) return
    return this.update(id, { isActive: !item.isActive })
  }
}
