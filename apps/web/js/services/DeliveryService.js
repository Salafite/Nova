window.DeliveryService = class DeliveryService {
  constructor() {
    this.api = new ApiClient('/api/T0077I');
    this._data = [];
  }

  async load() {
    try { this._data = await this.api.list() || [] } catch (e) { console.warn('Failed to load deliveries', e); this._data = [] }
  }

  getAll() { return this._data }

  getById(id) { return this._data.find(function(r) { return r.id == id }) }

  async create(payload) { var r = await this.api.create(payload); this._data.push(r); return r }

  async update(id, payload) { var r = await this.api.update(id, payload); var i = this._data.findIndex(function(x) { return x.id == id }); if (i > -1) this._data[i] = r; return r }

  async remove(id) { await this.api.delete(id); this._data = this._data.filter(function(x) { return x.id != id }) }

  getPendingCount() { return this._data.filter(function(r) { return r.status === 'Draft' }).length }
}
