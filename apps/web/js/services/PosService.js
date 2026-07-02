window.PosService = class PosService {
  constructor(inventoryService, salesService, productService) {
    this.inventory = inventoryService
    this.sales = salesService
    this.products = productService
  }

  getTaxRate() { return 0.05 }

  computeTotals(cartItems) {
    const subtotal = cartItems.reduce((s, i) => s + i.qty * i.price, 0)
    const tax = subtotal * this.getTaxRate()
    return { subtotal, tax, grandTotal: subtotal + tax }
  }

  async checkout(cartItems, customerName) {
    const { subtotal, tax, grandTotal } = this.computeTotals(cartItems)
    for (const item of cartItems) {
      await this.inventory.adjustStock(item.productId, 'Main', -item.qty)
    }
    return await this.sales.createInvoice(customerName, cartItems, subtotal, tax, grandTotal)
  }

  getAvailableStock(productId) { return this.inventory.getStock(productId) }

  getProduct(id) { return this.products.getById(id) }

  getAllProducts() { return this.products.getAll() }

  getCustomers() { return window.customerService.getAll() }
}
