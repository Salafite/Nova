window.FinanceService = class FinanceService {
  constructor(salesService, purchaseService, customerService) {
    this.sales = salesService
    this.purchases = purchaseService
    this.customers = customerService
  }

  getTotalRevenue() {
    return this.sales.getInvoices().reduce((s, i) => s + (i.grandTotal || i.total || 0), 0)
  }

  getTotalExpenses() {
    return this.purchases.getOrders()
      .filter(p => p.status === 'Received')
      .reduce((s, p) => s + (p.total || 0), 0)
  }

  getNetProfit() { return this.getTotalRevenue() - this.getTotalExpenses() }

  getOutstandingAR() {
    try { return this.customers.getOutstandingBalance() } catch (e) { console.warn('Outstanding AR failed', e); return 0 }
  }

  getPendingInvoiceCount() {
    return this.sales.getInvoices().filter(i => i.status === 'Pending' || i.status === 'Unpaid').length
  }

  getSummary() {
    return {
      totalRevenue: this.getTotalRevenue(),
      totalExpenses: this.getTotalExpenses(),
      netProfit: this.getNetProfit(),
      pendingInvoices: this.getPendingInvoiceCount(),
      outstandingAR: this.getOutstandingAR()
    }
  }

  getTransactions() {
    var txns = []
    this.sales.getInvoices().forEach(function(inv) {
      txns.push({
        date: inv.date,
        description: 'Sale #' + inv.id + ' — ' + (inv.customer || 'Customer'),
        type: 'Revenue',
        amount: inv.grandTotal || inv.total || 0
      })
    })
    this.purchases.getOrders().filter(function(po) { return po.status === 'Received' }).forEach(function(po) {
      txns.push({
        date: po.date || new Date().toISOString().slice(0, 10),
        description: 'PO #' + po.id + ' — ' + (po.supplier || 'Vendor'),
        type: 'Expense',
        amount: po.total || 0
      })
    })
    txns.sort(function(a, b) { return a.date < b.date ? 1 : -1 })
    return txns
  }
}
