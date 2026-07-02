window.NovaModules = window.NovaModules || {}; window.NovaModules['inventory'] = {
  render() {
    var search = this.searchTerm || ''
    var items = window.inventoryService.getAll()
    var filtered = search ? items.filter(function(i) { return (i.productName || '').toLowerCase().indexOf(search) > -1 || (i.location || '').toLowerCase().indexOf(search) > -1 }) : items
    var rows = filtered.map(function(i) {
      var status = Badge.stock(i.quantity, i.minStock)
      return '<tr class="active-row-hover group transition-colors cursor-pointer border-b border-outline-variant">' +
             '<td class="px-lg py-md font-body-md font-semibold text-on-surface">' + escapeHtml(i.productName) + '</td>' +
             '<td class="px-lg py-md text-body-md text-on-surface-variant">' + escapeHtml(i.location || 'Main') + '</td>' +
             '<td class="px-lg py-md text-right font-data-mono font-medium">' + i.quantity + '</td>' +
             '<td class="px-lg py-md text-right font-data-mono">' + (i.minStock || 5) + ' / ' + (i.maxStock || 100) + '</td>' +
             '<td class="px-lg py-md">' + status + '</td>' +
             '</tr>'
    }).join('')
    var criticalStock = window.inventoryService.getCriticalStockCount()
    var reorderQueue = window.inventoryService.getReorderQueueCount()
    var whUtil = window.warehouseService ? window.warehouseService.getOverallUtilization() : 0
    var whTotal = window.warehouseService ? window.warehouseService.getTotalCapacity() : 0
    var whUsed = window.warehouseService ? window.warehouseService.getTotalUsed() : 0
    var whLabel = (whUsed / 1000).toFixed(1) + 'k / ' + (whTotal / 1000).toFixed(1) + 'k units'
    return renderHtml('models/inventoryentry/list', {
      rows: rows,
      criticalStock: criticalStock,
      reorderQueue: reorderQueue,
      warehouseUtil: whUtil,
      warehouseUsedLabel: whLabel
    })
  },
  mount() { controllers.inventory = this; var s = document.getElementById('invSearch'); if (s) s.value = this.searchTerm || '' },
  search(q) { this.searchTerm = q.toLowerCase(); document.getElementById('content').innerHTML = this.render() },
  showMoveForm() {
    document.getElementById('content').innerHTML = renderHtml('models/inventoryentry/form', {
      productId: '', fromLocation: '', toLocation: ''
    })
  },
  saveMove() {
    var prod = document.getElementById('invMoveProduct').value
    var qty = parseInt(document.getElementById('invMoveQty').value) || 0
    var from = document.getElementById('invMoveFrom').value
    var to = document.getElementById('invMoveTo').value
    window.inventoryService.moveStock(prod, qty, from, to)
    document.getElementById('content').innerHTML = this.render()
    return false
  }
}
