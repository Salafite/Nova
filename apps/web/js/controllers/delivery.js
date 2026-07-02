window.NovaModules = window.NovaModules || {}; window.NovaModules['delivery'] = {
  render() {
    var search = this.searchTerm || ''
    var items = window.deliveryService.getAll()
    var filtered = search ? items.filter(function(r) { return (r.deliveryNumber || '').toLowerCase().indexOf(search) > -1 || String(r.salesOrderId || '').indexOf(search) > -1 }) : items
    var rows = filtered.map(function(r) {
      var statusBadge = r.status === 'Draft' ? 'bg-secondary/10 text-secondary border border-secondary/20' :
        (r.status === 'Shipped' ? 'bg-warning/10 text-warning border border-warning/20' :
        (r.status === 'Delivered' ? 'bg-success/10 text-success border border-success/20' :
        'bg-error/10 text-error border border-error/20'))
      var shipBtn = r.status === 'Draft' ? '<button class="text-secondary font-label-md text-label-md hover:underline" onclick="controllers.delivery.shipDelivery(' + r.id + ')">Ship</button> | ' : ''
      var deliverBtn = r.status === 'Shipped' ? '<button class="text-success font-label-md text-label-md hover:underline" onclick="controllers.delivery.markDelivered(' + r.id + ')">Mark Delivered</button> | ' : ''
      var cancelBtn = (r.status === 'Draft' || r.status === 'Shipped') ? '<button class="text-error font-label-md text-label-md hover:underline" onclick="controllers.delivery.cancelDelivery(' + r.id + ')">Cancel</button>' : ''
      return '<tr class="hover:bg-primary/5 transition-colors group">' +
        '<td class="px-lg py-md font-data-mono text-data-mono font-bold text-primary">' + escapeHtml(r.deliveryNumber) + '</td>' +
        '<td class="px-lg py-md font-body-md font-medium">' + escapeHtml(String(r.salesOrderId || '-')) + '</td>' +
        '<td class="px-lg py-md font-body-md text-on-surface-variant">' + escapeHtml(r.deliveryDate || '-') + '</td>' +
        '<td class="px-lg py-md"><span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-[11px] font-bold uppercase ' + statusBadge + '">' + escapeHtml(r.status) + '</span></td>' +
        '<td class="px-lg py-md text-center">' + shipBtn + deliverBtn + cancelBtn + '</td>' +
        '<td class="px-lg py-md text-right opacity-0 group-hover:opacity-100 transition-opacity">' +
        '<button class="p-1 hover:bg-surface-variant rounded-full text-primary" onclick="controllers.delivery.showEditForm(' + r.id + ')"><span class="material-symbols-outlined text-[20px]">edit</span></button>' +
        '<button class="p-1 hover:bg-error-container rounded-full text-error" onclick="controllers.delivery.deleteDelivery(' + r.id + ')"><span class="material-symbols-outlined text-[20px]">delete</span></button>' +
        '</td></tr>'
    }).join('')
    return renderHtml('screens/delivery', { rows: rows, count: filtered.length, draftCount: items.filter(function(r) { return r.status === 'Draft' }).length, shippedCount: items.filter(function(r) { return r.status === 'Shipped' }).length })
  },
  mount() { controllers.delivery = this; var s = document.getElementById('delSearch'); if (s) s.value = this.searchTerm || '' },
  async refresh() { await window.deliveryService.load(); document.getElementById('content').innerHTML = this.render() },
  search(q) { this.searchTerm = q.toLowerCase(); document.getElementById('content').innerHTML = this.render() },
  showCreateForm() {
    var today = new Date().toISOString().slice(0,10)
    document.getElementById('content').innerHTML = renderHtml('screens/delivery_form', { title: 'New Delivery Note', id: '', deliveryNumber: 'DEL-' + String(window.deliveryService.getAll().length + 1).padStart(3, '0'), salesOrderId: '', deliveryDate: today, warehouseId: '', notes: '' })
  },
  showEditForm(id) {
    var r = window.deliveryService.getById(id)
    if (!r) return
    document.getElementById('content').innerHTML = renderHtml('screens/delivery_form', {
      title: 'Edit Delivery Note', id: r.id, deliveryNumber: escapeHtml(r.deliveryNumber),
      salesOrderId: r.salesOrderId, deliveryDate: r.deliveryDate, warehouseId: r.warehouseId, notes: escapeHtml(r.notes || '')
    })
  },
  async saveForm() {
    var id = document.getElementById('delFormId').value
    var payload = {
      deliveryNumber: document.getElementById('delFormNumber').value,
      salesOrderId: parseInt(document.getElementById('delFormSO').value) || null,
      deliveryDate: document.getElementById('delFormDate').value,
      warehouseId: parseInt(document.getElementById('delFormWarehouse').value) || null,
      notes: document.getElementById('delFormNotes').value || null
    }
    if (!payload.deliveryDate) { app.toast('Delivery date is required', 'error'); return false }
    try {
      if (id) { await window.deliveryService.update(id, payload) }
      else { await window.deliveryService.create(payload) }
      app.toast('Delivery saved', 'success')
      document.getElementById('content').innerHTML = this.render()
    } catch (e) { app.toast('Error: ' + e.message, 'error') }
    return false
  },
  async shipDelivery(id) {
    if (!confirm('Ship this delivery?')) return
    try {
      await window.deliveryService.update(id, { status: 'Shipped' })
      app.toast('Delivery shipped', 'success')
      document.getElementById('content').innerHTML = this.render()
    } catch (e) { app.toast('Error: ' + e.message, 'error') }
  },
  async markDelivered(id) {
    if (!confirm('Mark this delivery as Delivered?')) return
    try {
      await window.deliveryService.update(id, { status: 'Delivered' })
      app.toast('Delivery marked as delivered', 'success')
      document.getElementById('content').innerHTML = this.render()
    } catch (e) { app.toast('Error: ' + e.message, 'error') }
  },
  async cancelDelivery(id) {
    if (!confirm('Cancel this delivery?')) return
    try {
      await window.deliveryService.update(id, { status: 'Cancelled' })
      app.toast('Delivery cancelled', 'success')
      document.getElementById('content').innerHTML = this.render()
    } catch (e) { app.toast('Error: ' + e.message, 'error') }
  },
  async deleteDelivery(id) {
    if (!confirm('Delete delivery?')) return
    try { await window.deliveryService.remove(id); document.getElementById('content').innerHTML = this.render() }
    catch (e) { app.toast('Error deleting: ' + e.message, 'error') }
  }
}
