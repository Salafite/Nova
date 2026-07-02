window.PurchaseService = class PurchaseService {
  constructor(purchaseOrderRepo, inventoryService) {
    this.poRepo = purchaseOrderRepo
    this.inventory = inventoryService
  }

  async createOrder(supplier, items, total) {
    return await this.poRepo.add({ supplier, items, total })
  }

  async receiveOrder(poId) {
    const po = this.poRepo.getById(poId)
    if (!po) return
    po.status = 'Received'
    for (const item of po.items) {
      await this.inventory.adjustStock(item.productId, 'Main', item.qty)
    }
    return await this.poRepo.update(po)
  }

  getOrders() { return this.poRepo.getAll() }

  getPendingCount() {
    return this.getOrders().filter(function(p) { return p.status === 'Pending' }).length
  }
}
