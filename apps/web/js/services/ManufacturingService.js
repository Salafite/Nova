window.ManufacturingService = class ManufacturingService {
  constructor(productService) {
    this.api = new ApiClient('T0018I')
    this.productService = productService
    this._cache = []
  }

  async load() {
    if (!this._cache.length) {
      this._cache = (await this.api.list()) || []
    }
  }

  getOrders() {
    return this._cache
  }

  getOrder(id) {
    return this._cache.find(function(o) { return String(o.id) === String(id) })
  }

  async createOrder(productName, quantity, dueDate, priority) {
    const order = await this.api.create({
      orderNumber: 'MFG-' + Date.now(),
      productName: productName,
      quantity: quantity,
      status: 'Pending',
      dueDate: dueDate || null,
      priority: priority || 'Medium'
    })
    this._cache.push(order)
    return order
  }

  async updateStatus(id, status) {
    const order = await this.getOrder(id)
    if (!order) return
    order.status = status
    const updated = await this.api.update(id, { status: status })
    Object.assign(order, updated)
  }

  getByStatus(status) {
    return this._cache.filter(function(o) { return o.status === status })
  }

  getActiveCount() {
    return this._cache.filter(function(o) { return o.status !== 'Completed' }).length
  }
}
