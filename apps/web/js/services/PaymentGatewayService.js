window.PaymentGatewayService = class PaymentGatewayService {
  constructor() {
    this.api = new ApiClient('T0059I')
    this._data = []
  }
  async load() {
    try {
      this._data = await this.api.list() || []
    } catch (e) {
      console.warn('Failed to load payment gateways', e)
      this._data = []
    }
  }
  getAll() { return this._data }
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
