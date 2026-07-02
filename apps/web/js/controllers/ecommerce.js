window.NovaModules = window.NovaModules || {}; window.NovaModules['ecommerce'] = {
  render() {
    var orders = window.eCommerceService.getAll()
    var stores = window.eCommerceService.getStores()
    var orderRows = orders.map(function(o) {
      var statusBadge = o.status === 'Shipped' ? '<span class="px-sm py-xs bg-secondary/10 text-secondary rounded text-[11px] font-medium uppercase">Shipped</span>' :
        (o.status === 'Pending' ? '<span class="px-sm py-xs bg-surface-container-highest text-on-surface-variant rounded text-[11px] font-medium uppercase">Pending</span>' :
         (o.status === 'Cancelled' ? '<span class="px-sm py-xs bg-error-container text-error rounded text-[11px] font-medium uppercase">Cancelled</span>' :
          '<span class="px-sm py-xs bg-primary-container/10 text-primary rounded text-[11px] font-medium uppercase">' + escapeHtml(o.status || 'Processing') + '</span>'))
      return '<tr class="hover:bg-primary/5 transition-colors group">' +
               '<td class="px-lg py-md font-data-mono text-data-mono">' + escapeHtml(o.order_id || o.id) + '</td>' +
               '<td class="px-lg py-md font-body-md font-semibold">' + escapeHtml(o.store || '-') + '</td>' +
               '<td class="px-lg py-md text-body-md text-on-surface-variant">' + escapeHtml(o.customer || '-') + '</td>' +
               '<td class="px-lg py-md font-data-mono text-right">$' + (o.total || 0).toFixed(2) + '</td>' +
               '<td class="px-lg py-md text-center">' + statusBadge + '</td>' +
               '<td class="px-lg py-md text-center opacity-0 group-hover:opacity-100 transition-opacity">' +
               '<button class="p-1 hover:bg-error-container rounded-full text-error" onclick="controllers.ecommerce.deleteOrder(\'' + o.id + '\')"><span class="material-symbols-outlined text-[20px]">delete</span></button></td>' +
             '</tr>'
    }).join('')
    var storeRows = stores.map(function(s) {
      var storeStatus = s.status === 'Connected' ? '<span class="px-sm py-xs bg-secondary/10 text-secondary rounded text-[11px] font-medium uppercase">Connected</span>' : '<span class="px-sm py-xs bg-surface-container-highest text-on-surface-variant rounded text-[11px] font-medium uppercase">' + escapeHtml(s.status || 'Disconnected') + '</span>'
      return '<tr class="hover:bg-primary/5 transition-colors">' +
               '<td class="px-lg py-md font-body-md font-semibold text-primary">' + escapeHtml(s.name || '-') + '</td>' +
               '<td class="px-lg py-md text-body-md text-on-surface-variant">' + escapeHtml(s.platform || '-') + '</td>' +
               '<td class="px-lg py-md text-center">' + storeStatus + '</td>' +
               '<td class="px-lg py-md text-body-md text-on-surface-variant">' + escapeHtml(s.last_sync || '-') + '</td>' +
             '</tr>'
    }).join('')
    return renderHtml('screens/e_commerce_integration', {
      orderRows: orderRows,
      storeRows: storeRows,
      orderCount: orders.length,
      storeCount: stores.length
    })
  },
  mount() { controllers.ecommerce = this },
  search(q) { this.searchTerm = q.toLowerCase(); document.getElementById('content').innerHTML = this.render() },
  showCreateForm() {
    document.getElementById('content').innerHTML =
      '<div class="max-w-2xl mx-auto bg-surface-container-lowest border border-outline-variant rounded-xl p-lg shadow-sm">' +
      '<h3 class="font-title-md text-title-md font-bold mb-lg">Connect Store</h3>' +
      '<form onsubmit="return controllers.ecommerce.saveForm()">' +
      '<div class="grid grid-cols-1 md:grid-cols-2 gap-md mb-md">' +
      '<div class="flex flex-col gap-xs"><label class="font-label-sm text-label-sm font-bold text-on-surface-variant uppercase">Store Name</label><input id="ecomFormName" required class="w-full bg-surface border border-outline-variant rounded-lg px-3 py-2 text-body-md focus:ring-2 focus:ring-primary/20" /></div>' +
      '<div class="flex flex-col gap-xs"><label class="font-label-sm text-label-sm font-bold text-on-surface-variant uppercase">Platform</label><select id="ecomFormPlatform" class="w-full bg-surface border border-outline-variant rounded-lg px-3 py-2 text-body-md focus:ring-2 focus:ring-primary/20"><option>Shopify</option><option>WooCommerce</option><option>Magento</option><option>BigCommerce</option></select></div>' +
      '</div>' +
      '<div class="flex gap-sm mt-lg"><button type="submit" class="bg-primary text-on-primary px-lg py-sm rounded-lg font-label-md press-effect">Connect</button>' +
      '<button type="button" class="bg-surface border border-outline-variant text-on-surface-variant px-lg py-sm rounded-lg font-label-md press-effect" onclick="controllers.ecommerce.render()">Cancel</button></div>' +
      '</form></div>'
  },
  async saveForm() {
    var payload = {
      name: document.getElementById('ecomFormName').value,
      platform: document.getElementById('ecomFormPlatform').value,
      status: 'Connected',
      last_sync: new Date().toISOString()
    }
    try {
      await window.eCommerceService.create(payload)
      app.toast('Store connected', 'success')
      document.getElementById('content').innerHTML = this.render()
    } catch (e) {
      app.toast('Error connecting store: ' + e.message, 'error')
    }
    return false
  },
  async deleteOrder(id) {
    if (!confirm('Delete this order?')) return
    try {
      await window.eCommerceService.remove(id)
      app.toast('Order deleted', 'success')
      document.getElementById('content').innerHTML = this.render()
    } catch (e) {
      app.toast('Error deleting order: ' + e.message, 'error')
    }
  }
}
