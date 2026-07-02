window.NovaModules = window.NovaModules || {}; window.NovaModules['purchase_returns'] = {
  render() {
    var search = this.searchTerm || ''
    var items = window.purchaseReturnService.getAll()
    var filtered = search ? items.filter(function(r) { return (r.returnNumber || '').toLowerCase().indexOf(search) > -1 || (r.supplierId || '').toString().indexOf(search) > -1 }) : items
    var stats = window.purchaseReturnService.getStats()
    var rows = filtered.map(function(r) {
      var statusBadge = r.status === 'Draft' ? 'bg-surface-container text-on-surface-variant border border-outline-variant' :
        (r.status === 'Approved' ? 'bg-warning/10 text-warning border border-warning/20' :
        (r.status === 'Returned' ? 'bg-primary/10 text-primary border border-primary/20' :
        (r.status === 'Cancelled' ? 'bg-error/10 text-error border border-error/20' :
        'bg-surface-container text-on-surface-variant border border-outline-variant')))
      var actions = ''
      if (r.status === 'Draft') {
        actions += '<button class="text-success font-label-md text-label-md hover:underline" onclick="controllers.purchase_returns.approve(' + r.id + ')">Approve</button> | <button class="text-error font-label-md text-label-md hover:underline" onclick="controllers.purchase_returns.cancel(' + r.id + ')">Cancel</button>'
      } else if (r.status === 'Approved') {
        actions += '<button class="text-primary font-label-md text-label-md hover:underline" onclick="controllers.purchase_returns.markReturned(' + r.id + ')">Mark Returned</button> | <button class="text-error font-label-md text-label-md hover:underline" onclick="controllers.purchase_returns.cancel(' + r.id + ')">Cancel</button>'
      } else if (r.status === 'Returned') {
        actions += '<span class="text-secondary font-label-md">Completed</span>'
      } else {
        actions += '<span class="text-on-surface-variant font-label-md">Cancelled</span>'
      }
      return '<tr class="hover:bg-primary/5 transition-colors group">' +
        '<td class="px-lg py-md font-data-mono text-data-mono font-bold text-primary">' + escapeHtml(r.returnNumber) + '</td>' +
        '<td class="px-lg py-md font-body-md text-on-surface-variant">' + escapeHtml(r.purchaseOrderId || '-') + '</td>' +
        '<td class="px-lg py-md font-body-md text-on-surface-variant">' + escapeHtml(r.returnDate || '-') + '</td>' +
        '<td class="px-lg py-md"><span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-[11px] font-bold uppercase ' + statusBadge + '">' + escapeHtml(r.status) + '</span></td>' +
        '<td class="px-lg py-md text-center font-label-md text-label-md">' + actions + '</td>' +
        '<td class="px-lg py-md text-right opacity-0 group-hover:opacity-100 transition-opacity">' +
        '<button class="p-1 hover:bg-surface-variant rounded-full text-primary" onclick="controllers.purchase_returns.showEditForm(' + r.id + ')"><span class="material-symbols-outlined text-[20px]">edit</span></button>' +
        '<button class="p-1 hover:bg-error-container rounded-full text-error" onclick="controllers.purchase_returns.deleteReturn(' + r.id + ')"><span class="material-symbols-outlined text-[20px]">delete</span></button>' +
        '</td></tr>'
    }).join('')
    return renderHtml('screens/purchase_returns', { rows: rows, count: filtered.length, total: stats.total, draft: stats.draft, returned: stats.returned })
  },
  mount() { controllers.purchase_returns = this; var s = document.getElementById('returnSearch'); if (s) s.value = this.searchTerm || '' },
  async refresh() { await window.purchaseReturnService.load(); document.getElementById('content').innerHTML = this.render() },
  search(q) { this.searchTerm = q.toLowerCase(); document.getElementById('content').innerHTML = this.render() },
  showCreateForm() {
    document.getElementById('content').innerHTML = renderHtml('screens/purchase_returns_form', {
      title: 'New Purchase Return', id: '',
      returnNumber: 'PR-' + String(window.purchaseReturnService.getAll().length + 1).padStart(3, '0'),
      purchaseOrderId: '', supplierId: '', reason: '', notes: '', returnDate: new Date().toISOString().slice(0, 10)
    })
  },
  showEditForm(id) {
    var r = window.purchaseReturnService.getById(id)
    if (!r) return
    document.getElementById('content').innerHTML = renderHtml('screens/purchase_returns_form', {
      title: 'Edit Purchase Return', id: r.id,
      returnNumber: escapeHtml(r.returnNumber), purchaseOrderId: r.purchaseOrderId || '',
      supplierId: r.supplierId, reason: escapeHtml(r.reason || ''),
      notes: escapeHtml(r.notes || ''), returnDate: r.returnDate || ''
    })
  },
  async saveForm() {
    var id = document.getElementById('retFormId').value
    var payload = {
      returnNumber: document.getElementById('retFormNumber').value,
      purchaseOrderId: parseInt(document.getElementById('retFormPO').value) || null,
      supplierId: parseInt(document.getElementById('retFormSupplier').value),
      returnDate: document.getElementById('retFormDate').value || new Date().toISOString().slice(0, 10),
      reason: document.getElementById('retFormReason').value || null,
      notes: document.getElementById('retFormNotes').value || null
    }
    if (!payload.supplierId) { app.toast('Supplier is required', 'error'); return false }
    try {
      if (id) { await window.purchaseReturnService.update(id, payload) }
      else { await window.purchaseReturnService.create(payload) }
      app.toast('Purchase Return saved', 'success')
      document.getElementById('content').innerHTML = this.render()
    } catch (e) { app.toast('Error: ' + e.message, 'error') }
    return false
  },
  async approve(id) {
    if (!confirm('Approve this return?')) return
    try {
      await window.purchaseReturnService.approve(id)
      app.toast('Return approved', 'success')
      document.getElementById('content').innerHTML = this.render()
    } catch (e) { app.toast('Error: ' + e.message, 'error') }
  },
  async markReturned(id) {
    if (!confirm('Mark this return as returned?')) return
    try {
      await window.purchaseReturnService.markReturned(id)
      app.toast('Return marked as Returned', 'success')
      document.getElementById('content').innerHTML = this.render()
    } catch (e) { app.toast('Error: ' + e.message, 'error') }
  },
  async cancel(id) {
    if (!confirm('Cancel this return?')) return
    try {
      await window.purchaseReturnService.cancel(id)
      app.toast('Return cancelled', 'success')
      document.getElementById('content').innerHTML = this.render()
    } catch (e) { app.toast('Error: ' + e.message, 'error') }
  },
  async deleteReturn(id) {
    if (!confirm('Delete this return?')) return
    try { await window.purchaseReturnService.remove(id); document.getElementById('content').innerHTML = this.render() }
    catch (e) { app.toast('Error deleting: ' + e.message, 'error') }
  }
}
