window.EmployeeService = class EmployeeService {
  constructor() {
    this.api = new ApiClient('T0030I')
    this._data = []
    this._departments = []
  }
  async load() {
    try {
      this._data = await this.api.list() || []
    } catch (e) {
      console.warn('Failed to load employees', e)
      this._data = []
    }
    try {
      var deptApi = new ApiClient('T0028I')
      this._departments = await deptApi.list() || []
    } catch (e) {
      console.warn('Failed to load departments', e)
      this._departments = [
        { id: 1, name: 'Engineering', head: 'John Smith', employee_count: 12 },
        { id: 2, name: 'Marketing', head: 'Sarah Johnson', employee_count: 8 },
        { id: 3, name: 'Finance', head: 'Mike Brown', employee_count: 5 }
      ]
    }
  }
  getAll() { return this._data }
  getById(id) { return this._data.find(function(x) { return x.id == id }) }
  getDepartments() { return this._departments }
  async create(payload) {
    var item = await this.api.create(payload)
    this._data.push(item)
    return item
  }
  async update(id, payload) {
    var item = await this.api.update(id, payload)
    var i = this._data.findIndex(function(x) { return x.id == id })
    if (i > -1) this._data[i] = item
    return item
  }
  async remove(id) {
    await this.api.delete(id)
    this._data = this._data.filter(function(x) { return x.id != id })
  }
}
