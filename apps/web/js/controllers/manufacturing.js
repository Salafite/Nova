window.NovaModules = window.NovaModules || {}; window.NovaModules['manufacturing'] = {
  render() {
    var orders = window.manufacturingService ? window.manufacturingService.getOrders() : []
    var products = window.productService.getAll()
    var orderRows = orders.map(function(o) {
      var btn = Badge.mfgStatusActions(o.status, o.id, 'controllers.manufacturing.completeOrder(\'' + escapeHtml(o.id) + '\')')
      return '<tr class="hover:bg-primary/5 transition-colors h-12">' +
               '<td class="px-md font-data-mono text-data-mono">' + escapeHtml(o.id) + '</td>' +
               '<td class="px-md font-body-md text-body-md">' + escapeHtml(o.productName) + '</td>' +
               '<td class="px-md">' + o.quantity + '</td>' +
               '<td class="px-md">' + Badge.mfgOrderStatus(o.status) + '</td>' +
               '<td class="px-md font-body-md">' + escapeHtml(o.dueDate || '-') + '</td>' +
               '<td class="px-md text-right">' + btn + '</td>' +
             '</tr>'
    }).join('')
    var bomRows = products.filter(function(p) { return p.bom }).map(function(p) {
      return '<tr class="hover:bg-primary/5 transition-colors"><td class="px-md py-3 font-body-md text-body-md font-semibold">' + escapeHtml(p.name) + '</td><td class="px-md py-3 font-body-md text-on-surface-variant">' + escapeHtml(p.bom.map(function(b) { return b.name + ' x' + b.qty }).join(', ')) + '</td></tr>'
    }).join('')
    return renderHtml('screens/manufacturing', { orderRows: orderRows, bomRows: bomRows })
  },
  mount() { controllers.manufacturing = this },
  showCreateForm() {
    document.getElementById('content').innerHTML = renderHtml('models/manufacturingorder/form', {})
  },
  async saveForm() {
    var productName = document.getElementById('mfgFormProduct').value
    var qty = parseInt(document.getElementById('mfgFormQty').value)
    var date = document.getElementById('mfgFormDate').value
    var priority = document.getElementById('mfgFormPriority').value
    try {
      if (window.manufacturingService) {
        await window.manufacturingService.createOrder(productName, qty, date, priority)
        app.toast('Manufacturing Order Created', 'success')
      }
      document.getElementById('content').innerHTML = this.render()
    } catch (e) {
      app.toast('Error creating order: ' + e.message, 'error')
    }
    return false
  },
  async completeOrder(id) {
    try {
      if (window.manufacturingService) {
        await window.manufacturingService.updateStatus(id, 'Completed')
        app.toast('Order ' + id + ' completed', 'success')
      }
      document.getElementById('content').innerHTML = this.render()
    } catch (e) {
      app.toast('Error completing order: ' + e.message, 'error')
    }
  }
}
