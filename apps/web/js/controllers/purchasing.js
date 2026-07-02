window.NovaModules = window.NovaModules || {}; window.NovaModules['purchasing'] = {
  render() {
    var orders = window.purchaseService.getOrders()
    var rows = orders.map(function(po) {
      var btn = Badge.poReceiveActions(po.status, po.id)
      return '<tr class="hover:bg-primary/5 transition-colors group">' +
               '<td class="px-lg py-md font-data-mono text-data-mono font-bold text-primary">' + escapeHtml(po.id) + '</td>' +
               '<td class="px-lg py-md font-body-md text-on-surface font-medium">' + escapeHtml(po.supplier) + '</td>' +
               '<td class="px-lg py-md font-body-md">' + (po.items ? po.items.length : 0) + '</td>' +
               '<td class="px-lg py-md font-data-mono text-data-mono font-bold text-right">$' + po.total.toFixed(2) + '</td>' +
               '<td class="px-lg py-md text-center">' + Badge.poStatus(po.status) + '</td>' +
               '<td class="px-lg py-md text-right">' + btn + '</td>' +
             '</tr>'
    }).join('')
    return renderHtml('models/purchaseorder/list', { rows: rows })
  },
  mount() { controllers.purchasing = this },
  showCreateForm() {
    document.getElementById('content').innerHTML = renderHtml('models/purchaseorder/form', {
      title: 'Create Purchase Order', supplier: '', itemInputs: '<div class="flex gap-md items-end bg-surface-container-low p-md rounded-lg border border-outline-variant"><div class="flex-1 flex flex-col gap-xs"><label class="font-label-sm text-label-sm font-bold text-on-surface-variant uppercase">Item 1 Name</label><input type="text" id="poItem0Name" placeholder="Product name" class="w-full bg-surface border border-outline-variant rounded-lg px-3 py-2 text-body-md focus:ring-2 focus:ring-primary/20"></div><div class="w-32 flex flex-col gap-xs"><label class="font-label-sm text-label-sm font-bold text-on-surface-variant uppercase">Qty</label><input type="number" id="poItem0Qty" value="1" class="w-full bg-surface border border-outline-variant rounded-lg px-3 py-2 text-body-md focus:ring-2 focus:ring-primary/20"></div></div>'
    })
  },
  async saveForm() {
    var supplier = document.getElementById('poFormSupplier').value
    if (!supplier) { alert('Supplier name required'); return false }
    var count = parseInt(document.getElementById('poFormItemCount').value) || 1
    var items = []
    var total = 0
    for (var i = 0; i < count; i++) {
      var prodName = document.getElementById('poItem' + i + 'Name')
      if (!prodName) continue
      var product = window.productService.getByName(prodName.value)
      if (!product) { alert('Product "' + prodName.value + '" not found'); return false }
      var qty = parseInt(document.getElementById('poItem' + i + 'Qty').value) || 1
      items.push({ productId: product.id, name: product.name, qty: qty, price: product.price })
      total += qty * product.price
    }
    try {
      await window.purchaseService.createOrder(supplier, items, total)
      document.getElementById('content').innerHTML = this.render()
    } catch (e) {
      app.toast('Error creating PO: ' + e.message, 'error')
    }
    return false
  },
  async receiveOrder(poId) {
    try {
      await window.purchaseService.receiveOrder(poId)
      app.toast('PO ' + poId + ' received — stock updated', 'success')
      document.getElementById('content').innerHTML = this.render()
    } catch (e) {
      app.toast('Error receiving PO: ' + e.message, 'error')
    }
  }
}
