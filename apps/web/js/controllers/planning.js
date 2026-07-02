window.NovaModules = window.NovaModules || {}; window.NovaModules['planning'] = {
  render() {
    var plans = window.planningService ? window.planningService.getPlans() : []
    var products = window.productService.getAll()
    var planRows = plans.map(function(p) {
      return '<tr class="hover:bg-primary/5 transition-colors group">' +
               '<td class="px-lg py-md font-data-mono text-data-mono text-primary font-bold">' + escapeHtml(p.id) + '</td>' +
               '<td class="px-lg py-md text-body-md font-semibold">' + escapeHtml(p.productName) + '</td>' +
               '<td class="px-lg py-md font-data-mono text-data-mono">' + p.quantity + '</td>' +
               '<td class="px-lg py-md text-body-md text-on-surface-variant">' + escapeHtml(p.startDate || '-') + '</td>' +
               '<td class="px-lg py-md text-body-md text-on-surface-variant">' + escapeHtml(p.endDate || '-') + '</td>' +
               '<td class="px-lg py-md text-center">' + Badge.planStatus(p.status) + '</td>' +
             '</tr>'
    }).join('')
    return renderHtml('screens/planning', { planRows: planRows, forecastRows: '' })
  },
  mount() { controllers.planning = this },
  showCreateForm() {
    document.getElementById('content').innerHTML = renderHtml('models/plan/form', {})
  },
  async saveForm() {
    var productName = document.getElementById('planFormProduct').value
    var qty = parseInt(document.getElementById('planFormQty').value)
    var start = document.getElementById('planFormStart').value
    var end = document.getElementById('planFormEnd').value
    try {
      if (window.planningService) {
        await window.planningService.createPlan(productName, qty, start, end)
        app.toast('Production Plan Created', 'success')
      }
      document.getElementById('content').innerHTML = this.render()
    } catch (e) {
      app.toast('Error creating plan: ' + e.message, 'error')
    }
    return false
  }
}
