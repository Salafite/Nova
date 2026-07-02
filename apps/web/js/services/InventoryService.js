window.InventoryService = class InventoryService {
  constructor(inventoryRepo) {
    this.repo = inventoryRepo
  }

  getStock(productId) { return this.repo.getTotal(productId) }

  async adjustStock(productId, warehouse, delta) {
    return await this.repo.adjust(productId, warehouse, delta)
  }

  getLowStockEntries() { return this.repo.findLowStock() }

  getLowStockCount() { return this.repo.findLowStock().length }

  getWarehouses() { return this.repo.getUniqueWarehouses() }

  getEntriesForProduct(productId) { return this.repo.findByProduct(productId) }

  async createInitialEntry(productId, warehouse, qty) {
    await this.repo.addEntry({ productId, warehouse, qty, reorderLevel: 10 })
  }

  removeEntriesForProduct(productId) { this.repo.removeByProduct(productId) }

  getAllEntries() { return this.repo.getAll() }

  getAll() { return this.repo.getAll() }

  getCriticalStockCount() {
    return this.repo.getAll().filter(function(i) { return i.quantity <= (i.minStock || 5) }).length
  }

  getReorderQueueCount() {
    return this.repo.getAll().filter(function(i) { return i.quantity <= (i.minStock || 5) && i.quantity > 0 }).length
  }
}
