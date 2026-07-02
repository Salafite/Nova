window.NovaFacade = {
  get products() { return window.productService.getAll() },
  get inventory() { return window.inventoryService.getAllEntries() },
  get customers() { return window.customerService.getAll() },
  get suppliers() { return window.supplierService.getAll() },
  get salesOrders() { return window.salesService.getInvoices() },
  get purchaseOrders() { return window.purchaseService.getOrders() },

  addProduct(data) { return window.productService.add(data.name, data.sku, data.price, data.category, data.stock) },
  removeProduct(id) { window.productService.remove(id) },
  getStock(productId) { return window.inventoryService.getStock(productId) },
  adjustStock(productId, warehouse, delta) { return window.inventoryService.adjustStock(productId, warehouse, delta) },

  createSale(order) {
    return window.salesService.createInvoice(order.customerName, order.items, order.total, order.tax, order.grandTotal)
  },

  createPurchaseOrder(data) { return window.purchaseService.createOrder(data.supplier, data.items, data.total) },
  receivePurchaseOrder(poId) { return window.purchaseService.receiveOrder(poId) },

  addCustomer(data) { return window.customerService.add(data.name, data.group, data.phone, data.creditLimit) }
}
