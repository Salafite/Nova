window.QualityService = class QualityService {
  constructor() {
    this.api = new ApiClient('T0019I')
    this._cache = []
  }

  async load() {
    if (!this._cache.length) {
      this._cache = (await this.api.list({ order: 'id', sort: 'DESC' })) || []
    }
  }

  getInspections() {
    return this._cache
  }

  getInspection(id) {
    return this._cache.find(function(i) { return String(i.id) === String(id) })
  }

  async createInspection(productName, batch, inspector) {
    const inspection = await this.api.create({
      inspectionNo: 'QC-' + Date.now(),
      productName: productName,
      batchNo: batch || '',
      result: 'Pending',
      inspector: inspector || 'Unassigned'
    })
    this._cache.unshift(inspection)
    return inspection
  }

  async updateResult(id, result) {
    const updated = await this.api.update(id, { result: result })
    const idx = this._cache.findIndex(function(i) { return String(i.id) === String(id) })
    if (idx >= 0) this._cache[idx] = updated
  }

  async getPassRate() {
    var total = this._cache.length
    if (!total) return 0
    var passed = this._cache.filter(function(i) { return i.result === 'Pass' }).length
    return Math.round(passed / total * 100)
  }

  getPendingCount() {
    return this._cache.filter(function(i) { return i.result === 'Pending' }).length
  }

  getFailCount() {
    return this._cache.filter(function(i) { return i.result === 'Fail' }).length
  }
}
