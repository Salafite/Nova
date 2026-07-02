window.ProductService = class ProductService {
  constructor(productRepo, inventoryService) {
    this.repo = productRepo
    this.inventory = inventoryService
  }

  getAll() { return this.repo.getAll() }

  getById(id) { return this.repo.getById(id) }

  getByName(name) { return this.repo.getByName(name) }

  async add(name, sku, price, category, stock) {
    const product = await this.repo.add({ name, sku, price, category, stock })
    if (this.inventory) {
      await this.inventory.createInitialEntry(product.id, 'Main', stock || 0)
    }
    return product
  }

  async remove(id) {
    await this.repo.remove(id)
    this.inventory.removeEntriesForProduct(id)
  }

  getLowStockCount() {
    return this.getAll().filter(function(p) { return (p.stock||0) <= (p.minStock||5) && (p.stock||0) > 0 }).length
  }

  getOutOfStockCount() {
    return this.getAll().filter(function(p) { return (p.stock||0) <= 0 }).length
  }

  getInventoryValue() {
    return this.getAll().reduce(function(sum, p) { return sum + (p.price * (p.stock || 0)) }, 0)
  }
}
