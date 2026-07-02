window.NovaModules = window.NovaModules || {}; window.NovaModules['mobilepos'] = {
  render() {
    var orders = window.mobilePOSService.getAll()
    var orderRows = orders.map(function(o) {
      var statusBadge = o.status === 'Completed' ? '<span class="px-sm py-xs bg-secondary/10 text-secondary rounded text-[11px] font-medium uppercase">Completed</span>' :
        (o.status === 'Pending' ? '<span class="px-sm py-xs bg-surface-container-highest text-on-surface-variant rounded text-[11px] font-medium uppercase">Pending</span>' :
         '<span class="px-sm py-xs bg-primary-container/10 text-primary rounded text-[11px] font-medium uppercase">' + escapeHtml(o.status || 'Processing') + '</span>')
      return '<tr class="hover:bg-primary/5 transition-colors group">' +
               '<td class="px-lg py-md font-data-mono text-data-mono">' + escapeHtml(o.order_id || o.id) + '</td>' +
               '<td class="px-lg py-md font-body-md font-semibold">' + escapeHtml(o.customer || '-') + '</td>' +
               '<td class="px-lg py-md text-body-md text-on-surface-variant">' + escapeHtml(o.items || '-') + '</td>' +
               '<td class="px-lg py-md font-data-mono text-right">$' + (o.total || 0).toFixed(2) + '</td>' +
               '<td class="px-lg py-md text-center">' + statusBadge + '</td>' +
               '<td class="px-lg py-md text-center opacity-0 group-hover:opacity-100 transition-opacity">' +
               '<button class="p-1 hover:bg-error-container rounded-full text-error" onclick="controllers.mobilepos.deleteOrder(\'' + o.id + '\')"><span class="material-symbols-outlined text-[20px]">delete</span></button></td>' +
             '</tr>'
    }).join('')
    return renderHtml('screens/mobile_pos', {
      orderRows: orderRows,
      orderCount: orders.length,
      pendingCount: orders.filter(function(o) { return o.status !== 'Completed' }).length
    })
  },
  mount() { controllers.mobilepos = this },
  search(q) { this.searchTerm = q.toLowerCase(); document.getElementById('content').innerHTML = this.render() },
  showCreateForm() {
    document.getElementById('content').innerHTML =
      '<div class="max-w-2xl mx-auto bg-surface-container-lowest border border-outline-variant rounded-xl p-lg shadow-sm">' +
      '<h3 class="font-title-md text-title-md font-bold mb-lg">Create Mobile Order</h3>' +
      '<form onsubmit="return controllers.mobilepos.saveForm()">' +
      '<div class="grid grid-cols-1 md:grid-cols-2 gap-md mb-md">' +
      '<div class="flex flex-col gap-xs"><label class="font-label-sm text-label-sm font-bold text-on-surface-variant uppercase">Customer</label><input id="posFormCustomer" required class="w-full bg-surface border border-outline-variant rounded-lg px-3 py-2 text-body-md focus:ring-2 focus:ring-primary/20" /></div>' +
      '<div class="flex flex-col gap-xs"><label class="font-label-sm text-label-sm font-bold text-on-surface-variant uppercase">Items</label><input id="posFormItems" required class="w-full bg-surface border border-outline-variant rounded-lg px-3 py-2 text-body-md focus:ring-2 focus:ring-primary/20" /></div>' +
      '<div class="flex flex-col gap-xs"><label class="font-label-sm text-label-sm font-bold text-on-surface-variant uppercase">Total</label><input id="posFormTotal" type="number" step="0.01" required class="w-full bg-surface border border-outline-variant rounded-lg px-3 py-2 text-body-md focus:ring-2 focus:ring-primary/20" /></div>' +
      '</div>' +
      '<div class="flex gap-sm mt-lg"><button type="submit" class="bg-primary text-on-primary px-lg py-sm rounded-lg font-label-md press-effect">Create</button>' +
      '<button type="button" class="bg-surface border border-outline-variant text-on-surface-variant px-lg py-sm rounded-lg font-label-md press-effect" onclick="controllers.mobilepos.render()">Cancel</button></div>' +
      '</form></div>'
  },
  async saveForm() {
    var payload = {
      customer: document.getElementById('posFormCustomer').value,
      items: document.getElementById('posFormItems').value,
      total: parseFloat(document.getElementById('posFormTotal').value) || 0,
      status: 'Pending',
      order_id: 'MPOS-' + Date.now()
    }
    try {
      await window.mobilePOSService.create(payload)
      app.toast('Mobile order created', 'success')
      document.getElementById('content').innerHTML = this.render()
    } catch (e) {
      app.toast('Error creating order: ' + e.message, 'error')
    }
    return false
  },
  async deleteOrder(id) {
    if (!confirm('Delete this order?')) return
    try {
      await window.mobilePOSService.remove(id)
      app.toast('Order deleted', 'success')
      document.getElementById('content').innerHTML = this.render()
    } catch (e) {
      app.toast('Error deleting order: ' + e.message, 'error')
    }
  }
}
