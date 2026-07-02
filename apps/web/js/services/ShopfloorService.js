window.ShopfloorService = class ShopfloorService {
  constructor() {
    this.api = new ApiClient('T0020I')
    this._cache = []
  }

  async load() {
    if (!this._cache.length) {
      this._cache = (await this.api.list()) || []
    }
  }

  getJobs() {
    return this._cache
  }

  getJob(id) {
    return this._cache.find(function(j) { return String(j.id) === String(id) })
  }

  async createJob(productName, quantity, workstation) {
    const job = await this.api.create({
      jobNumber: 'JOB-' + Date.now(),
      productName: productName,
      quantity: quantity,
      workstation: workstation || 'Unassigned',
      status: 'Pending'
    })
    this._cache.push(job)
    return job
  }

  async updateStatus(id, status) {
    const job = await this.getJob(id)
    if (!job) return
    job.status = status
    const updated = await this.api.update(id, { status: status })
    Object.assign(job, updated)
  }

  getActiveCount() {
    return this._cache.filter(function(j) { return j.status === 'In Progress' }).length
  }

  getPendingCount() {
    return this._cache.filter(function(j) { return j.status === 'Pending' }).length
  }

  getCompletedCount() {
    return this._cache.filter(function(j) { return j.status === 'Completed' }).length
  }

  getWorkstations() {
    var ws = [...new Set(this._cache.map(function(j) { return j.workstation }).filter(Boolean))]
    return ws.length ? ws : []
  }

  getAvailableWSCount() {
    var activeWS = this._cache.filter(function(j) { return j.status === 'In Progress' }).length
    var workstations = this.getWorkstations()
    return Math.max(0, workstations.length - activeWS)
  }
}
