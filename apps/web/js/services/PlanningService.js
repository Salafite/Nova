window.PlanningService = class PlanningService {
  constructor() {
    this.api = new ApiClient('T0024I')
    this._plans = []
  }

  async load() {
    try {
      this._plans = await this.api.list() || []
    } catch (e) {
      console.warn('Failed to load plans from API', e)
      this._plans = []
    }
  }

  getPlans() { return this._plans }

  async getPlan(id) {
    return this.api.get(id)
  }

  async createPlan(planNumber, productName, quantity, startDate, endDate) {
    var plan = await this.api.create({
      plan_number: planNumber,
      product_name: productName,
      quantity: quantity,
      start_date: startDate,
      end_date: endDate,
      status: 'Draft'
    })
    this._plans.push(plan)
    return plan
  }

  async updateStatus(id, status) {
    var plan = await this.api.update(id, { status: status })
    var idx = this._plans.findIndex(function(p) { return p.id === id })
    if (idx !== -1) this._plans[idx] = plan
    return plan
  }
}
