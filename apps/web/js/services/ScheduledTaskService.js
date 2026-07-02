window.ScheduledTaskService = class ScheduledTaskService {
  constructor() {
    this.api = new ApiClient('T0099I')
    this._tasks = []
  }

  async load() {
    try {
      this._tasks = await this.api.list() || []
    } catch (e) {
      console.warn('Failed to load scheduled tasks', e)
      this._tasks = []
    }
  }

  getAll() { return this._tasks }

  async getById(id) { return this.api.get(id) }

  async create(data) {
    var task = await this.api.create(data)
    this._tasks.push(task)
    return task
  }

  async update(id, data) {
    var task = await this.api.update(id, data)
    var idx = this._tasks.findIndex(function(t) { return t.id === id })
    if (idx > -1) this._tasks[idx] = task
    return task
  }

  async remove(id) {
    await this.api.delete(id)
    this._tasks = this._tasks.filter(function(t) { return t.id !== id })
  }

  async runNow(id) {
    await fetch(this.api.base + '/' + id + '/run-now', { method: 'PUT', headers: this.api._headers() })
    var task = this._tasks.find(function(t) { return t.id === id })
    if (task) task.status = 'Running'
  }

  getActiveCount() {
    return this._tasks.filter(function(t) { return t.isActive }).length
  }

  getRunningCount() {
    return this._tasks.filter(function(t) { return t.status === 'Running' }).length
  }
}
