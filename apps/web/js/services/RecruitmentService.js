window.RecruitmentService = class RecruitmentService {
  constructor() {
    this._data = [
      { id: 1, candidate: 'Alice Wang', position: 'Software Engineer', stage: 'Interview', applied_date: '2026-06-01', status: 'Active' },
      { id: 2, candidate: 'Bob Chen', position: 'Product Manager', stage: 'Screening', applied_date: '2026-06-05', status: 'Active' },
      { id: 3, candidate: 'Carol Davis', position: 'UX Designer', stage: 'Offer', applied_date: '2026-05-20', status: 'Active' },
      { id: 4, candidate: 'David Lee', position: 'Data Analyst', stage: 'Hired', applied_date: '2026-05-15', status: 'Hired' }
    ]
  }
  getAll() { return this._data }
  getById(id) { return this._data.find(function(x) { return x.id == id }) }
  async create(payload) { var item = Object.assign({ id: this._data.length + 1 }, payload); this._data.push(item); return item }
  async update(id, payload) { var i = this._data.findIndex(function(x) { return x.id == id }); if (i > -1) { Object.assign(this._data[i], payload); return this._data[i] } return null }
  async remove(id) { this._data = this._data.filter(function(x) { return x.id != id }) }
}
