window.SalesService = class SalesService {
  constructor(salesOrderRepo, customerRepo) {
    this.salesRepo = salesOrderRepo
    this.customerRepo = customerRepo
    this.api = new ApiClient('T0012I')
  }

  async createInvoice(customerName, cartItems, subtotal, tax, grandTotal) {
    const id = 'INV-' + String(this.salesRepo.getAll().length + 1).padStart(3, '0')
    const invoice = {
      id, customer: customerName, items: cartItems.length,
      total: subtotal, tax, grandTotal,
      status: 'Paid',
      date: new Date().toISOString().slice(0, 10),
      items: cartItems
    }
    await this.salesRepo.add(invoice)
    const customer = this.customerRepo.getByName(customerName)
    if (customer) customer.balance += grandTotal
    return invoice
  }

  getInvoices() { return this.salesRepo.getAll() }

  searchInvoices(term) {
    if (!term) return this.salesRepo.getAll()
    var q = term.toLowerCase()
    return this.salesRepo.getAll().filter(function(inv) {
      return (inv.id || '').toLowerCase().indexOf(q) > -1 || (inv.customer || '').toLowerCase().indexOf(q) > -1
    })
  }

  getInvoice(id) {
    return this.salesRepo.getAll().find(function(inv) { return inv.id === id })
  }

  getTodaySalesTotal(dateStr) {
    var today = dateStr || new Date().toISOString().slice(0, 10)
    return this.getInvoices().filter(function(s) { return s.date === today }).reduce(function(s, i) { return s + i.total }, 0)
  }

  getPendingCount() {
    return this.getInvoices().filter(function(i) { return i.status === 'Pending' || i.status === 'Unpaid' }).length
  }

  async createWithLines(orderData, lines) {
    return this.api._fetch(this.api.base + '/with-lines', {
      method: 'POST',
      body: JSON.stringify({ order: ApiClient._snake(orderData), lines: lines.map(function(l) { return ApiClient._snake(l) }) }),
    })
  }
}
