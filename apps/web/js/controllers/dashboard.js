window.NovaModules = window.NovaModules || {}; window.NovaModules['dashboard'] = {
  _recentSalesRows: function(sales) {
    return sales.slice(0, 3).map(function(o) {
      return '<tr class="border-b border-outline-variant">' +
             '<td class="px-lg py-md font-data-mono text-data-mono">#' + escapeHtml(o.id) + '</td>' +
             '<td class="px-lg py-md">' + escapeHtml(o.customer) + '</td>' +
             '<td class="px-lg py-md text-right font-data-mono text-data-mono">$' + o.total.toFixed(2) + '</td>' +
             '<td class="px-lg py-md">' + Badge.orderStatus(o.status) + '</td>' +
             '</tr>'
    }).join('') || '<tr><td colspan="4" class="px-lg py-md text-on-surface-variant text-center">No sales yet</td></tr>'
  },
  _pendingAlert: function(count) {
    return count ? '<div class="mt-md text-error font-bold flex items-center gap-xs"><span class="material-symbols-outlined text-[18px]">warning</span><span>' + count + ' pending PO' + (count > 1 ? 's' : '') + ' need attention</span></div>' : ''
  },
  _warehouseUtil: function(name) {
    var zones = window.warehouseService ? window.warehouseService.getZoneDetails() : []
    var zone = zones.find(function(z) { return z.name === name })
    return zone ? zone.utilization : 0
  },
  render() {
    var todayStr = new Date().toISOString().slice(0, 10)
    var sales = window.salesService.getInvoices()
    return renderHtml('screens/dashboard', {
      todaySales: window.salesService.getTodaySalesTotal(todayStr).toFixed(2),
      totalOrders: sales.length,
      customerCount: window.customerService.getAll().length,
      lowStock: window.inventoryService.getLowStockCount(),
      recentSalesRows: this._recentSalesRows(sales),
      pendingAlert: this._pendingAlert(window.purchaseService.getPendingCount()),
      mainWarehouseUtil: this._warehouseUtil('Main Storage'),
      distCenterUtil: this._warehouseUtil('Shipping')
    })
  }
}
