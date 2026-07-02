class InventoryClient {
  constructor() {
    this.api = new ApiClient('T0009I')
    this.whApi = new ApiClient('T0008I')
    this._cache = []
    this._whMap = {}
  }

  async load() {
    try {
      this._cache = (await this.api.list()) || []
      const whs = (await this.whApi.list()) || []
      this._whMap = {}
      whs.forEach(w => { this._whMap[w.name] = w.id })
      this._whNameById = {}
      whs.forEach(w => { this._whNameById[w.id] = w.name })
    } catch (e) {
      console.warn('Failed to load inventory/warehouse data', e)
      this._cache = []
      this._whMap = {}
      this._whNameById = {}
    }
  }

  _whId(name) { return this._whMap[name] || 1 }

  _whName(id) { return this._whNameById[id] || 'Main' }

  getAll() {
    return this._cache.map(e => ({
      productId: e.productId,
      warehouse: this._whName(e.warehouseId),
      qty: e.qty,
      reorderLevel: e.reorderLevel,
    }))
  }

  findByProduct(productId) {
    return this._cache.filter(r => r.productId === productId).map(e => ({
      productId: e.productId,
      warehouse: this._whName(e.warehouseId),
      qty: e.qty,
      reorderLevel: e.reorderLevel,
    }))
  }

  findByWarehouse(warehouse) {
    return this._cache.filter(r => this._whName(r.warehouseId) === warehouse)
  }

  getTotal(productId) {
    return this._cache.filter(r => r.productId === productId).reduce((s, r) => s + r.qty, 0)
  }

  findLowStock() {
    return this._cache.filter(r => r.qty <= r.reorderLevel).map(e => ({
      productId: e.productId,
      warehouse: this._whName(e.warehouseId),
      qty: e.qty,
      reorderLevel: e.reorderLevel,
    }))
  }

  findEntry(productId, warehouse) {
    const whId = this._whId(warehouse)
    return this._cache.find(r => r.productId === productId && r.warehouseId === whId)
  }

  async adjust(productId, warehouse, delta) {
    const whId = this._whId(warehouse)
    let entry = this._cache.find(r => r.productId === productId && r.warehouseId === whId)
    if (!entry) {
      entry = { id: 0, productId, warehouseId: whId, qty: 0, reorderLevel: 10 }
      const created = await this.api.create({ productId, warehouseId: whId, qty: delta, reorderLevel: 10 })
      entry.id = created.id
      entry.qty = created.qty
      this._cache.push(entry)
    } else {
      entry.qty += delta
      const updated = await this.api.update(entry.id, { qty: entry.qty })
      Object.assign(entry, updated)
    }
    return entry.qty
  }

  async addEntry(entry) {
    const whId = this._whId(entry.warehouse)
    const created = await this.api.create({
      productId: entry.productId,
      warehouseId: whId,
      qty: entry.qty || 0,
      reorderLevel: entry.reorderLevel || 10,
    })
    this._cache.push(created)
  }

  removeByProduct(productId) {
    this._cache = this._cache.filter(r => r.productId !== productId)
  }

  getUniqueWarehouses() {
    return [...new Set(this._cache.map(r => this._whName(r.warehouseId)))]
  }
}
