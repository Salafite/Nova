window.NovaModules = window.NovaModules || {}; window.NovaModules['integrations'] = {
  render() {
    var gateways = window.paymentGatewayService.getAll()
    var shippers = window.shippingService.getAll()
    var integrationRows = gateways.map(function(g) {
      var gwStatus = g.status === 'Active' ? '<span class="px-sm py-xs bg-secondary/10 text-secondary rounded text-[11px] font-medium uppercase">Active</span>' : '<span class="px-sm py-xs bg-surface-container-highest text-on-surface-variant rounded text-[11px] font-medium uppercase">' + escapeHtml(g.status || 'Inactive') + '</span>'
      return '<tr class="hover:bg-primary/5 transition-colors group">' +
               '<td class="px-lg py-md font-body-md font-semibold text-primary">' + escapeHtml(g.name || '-') + '</td>' +
               '<td class="px-lg py-md text-body-md text-on-surface-variant">' + escapeHtml(g.type || '-') + '</td>' +
               '<td class="px-lg py-md text-center">' + gwStatus + '</td>' +
               '<td class="px-lg py-md text-body-md text-on-surface-variant">' + escapeHtml(g.last_transaction || '-') + '</td>' +
               '<td class="px-lg py-md text-center opacity-0 group-hover:opacity-100 transition-opacity">' +
               '<button class="p-1 hover:bg-error-container rounded-full text-error" onclick="controllers.integrations.deleteGateway(\'' + g.id + '\')"><span class="material-symbols-outlined text-[20px]">delete</span></button></td>' +
             '</tr>'
    }).join('')
    var shippingRows = shippers.map(function(s) {
      var shipStatus = s.status === 'Active' ? '<span class="px-sm py-xs bg-secondary/10 text-secondary rounded text-[11px] font-medium uppercase">Active</span>' : '<span class="px-sm py-xs bg-surface-container-highest text-on-surface-variant rounded text-[11px] font-medium uppercase">' + escapeHtml(s.status || 'Inactive') + '</span>'
      return '<tr class="hover:bg-primary/5 transition-colors">' +
               '<td class="px-lg py-md font-body-md font-semibold text-primary">' + escapeHtml(s.name || '-') + '</td>' +
               '<td class="px-lg py-md text-body-md text-on-surface-variant">' + escapeHtml(s.account || '-') + '</td>' +
               '<td class="px-lg py-md text-center">' + shipStatus + '</td>' +
             '</tr>'
    }).join('')
    return renderHtml('screens/third_party_integrations', {
      integrationRows: integrationRows,
      shippingRows: shippingRows,
      gatewayCount: gateways.length,
      shippingCount: shippers.length
    })
  },
  mount() { controllers.integrations = this },
  search(q) { this.searchTerm = q.toLowerCase(); document.getElementById('content').innerHTML = this.render() },
  showCreateForm() {
    document.getElementById('content').innerHTML =
      '<div class="max-w-2xl mx-auto bg-surface-container-lowest border border-outline-variant rounded-xl p-lg shadow-sm">' +
      '<h3 class="font-title-md text-title-md font-bold mb-lg">Add Integration</h3>' +
      '<form onsubmit="return controllers.integrations.saveForm()">' +
      '<div class="grid grid-cols-1 md:grid-cols-2 gap-md mb-md">' +
      '<div class="flex flex-col gap-xs"><label class="font-label-sm text-label-sm font-bold text-on-surface-variant uppercase">Name</label><input id="intFormName" required class="w-full bg-surface border border-outline-variant rounded-lg px-3 py-2 text-body-md focus:ring-2 focus:ring-primary/20" /></div>' +
      '<div class="flex flex-col gap-xs"><label class="font-label-sm text-label-sm font-bold text-on-surface-variant uppercase">Type</label><select id="intFormType" class="w-full bg-surface border border-outline-variant rounded-lg px-3 py-2 text-body-md focus:ring-2 focus:ring-primary/20"><option>Payment Gateway</option><option>Shipping Provider</option><option>CRM</option><option>Accounting</option></select></div>' +
      '</div>' +
      '<div class="flex gap-sm mt-lg"><button type="submit" class="bg-primary text-on-primary px-lg py-sm rounded-lg font-label-md press-effect">Add</button>' +
      '<button type="button" class="bg-surface border border-outline-variant text-on-surface-variant px-lg py-sm rounded-lg font-label-md press-effect" onclick="controllers.integrations.render()">Cancel</button></div>' +
      '</form></div>'
  },
  async saveForm() {
    var payload = {
      name: document.getElementById('intFormName').value,
      type: document.getElementById('intFormType').value,
      status: 'Active',
      last_transaction: '-'
    }
    try {
      await window.paymentGatewayService.create(payload)
      app.toast('Integration added', 'success')
      document.getElementById('content').innerHTML = this.render()
    } catch (e) {
      app.toast('Error adding integration: ' + e.message, 'error')
    }
    return false
  },
  async deleteGateway(id) {
    if (!confirm('Remove this integration?')) return
    try {
      await window.paymentGatewayService.remove(id)
      app.toast('Integration removed', 'success')
      document.getElementById('content').innerHTML = this.render()
    } catch (e) {
      app.toast('Error removing integration: ' + e.message, 'error')
    }
  }
}
