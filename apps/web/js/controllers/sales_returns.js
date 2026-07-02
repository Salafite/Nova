window.NovaModules = window.NovaModules || {}; window.NovaModules['sales_returns'] = {
  render() {
    var search = this.searchTerm || ''
    var items = window.salesReturnService.getAll()
    var filtered = search ? items.filter(function(r) { return (r.returnNumber || '').toLowerCase().indexOf(search) > -1 || String(r.customerId || '').indexOf(search) > -1 }) : items
    var rows = filtered.map(function(r) {
      var statusBadge = r.status === 'Draft' ? 'bg-secondary/10 text-secondary border border-secondary/20' :
        (r.status === 'Approved' ? 'bg-warning/10 text-warning border border-warning/20' :
        (r.status === 'Received' ? 'bg-success/10 text-success border border-success/20' :
        'bg-error/10 text-error border border-error/20'))
      var approveBtn = r.status === 'Draft' ? '<button class="text-secondary font-label-md text-label-md hover:underline" onclick="controllers.sales_returns.approveReturn(' + r.id + ')">Approve</button> | ' : ''
      var receiveBtn = r.status === 'Approved' ? '<button class="text-success font-label-md text-label-md hover:underline" onclick="controllers.sales_returns.receiveReturn(' + r.id + ')">Receive</button> | ' : ''
      var cancelBtn = (r.status === 'Draft' || r.status === 'Approved') ? '<button class="text-error font-label-md text-label-md hover:underline" onclick="controllers.sales_returns.cancelReturn(' + r.id + ')">Cancel</button>' : ''
      return '<tr class="hover:bg-primary/5 transition-colors group">' +
        '<td class="px-lg py-md font-data-mono text-data-mono font-bold text-primary">' + escapeHtml(r.returnNumber) + '</td>' +
        '<td class="px-lg py-md font-body-md font-medium">' + escapeHtml(String(r.salesOrderId || '-')) + '</td>' +
        '<td class="px-lg py-md font-body-md text-on-surface-variant">' + escapeHtml(r.returnDate || '-') + '</td>' +
        '<td class="px-lg py-md"><span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-[11px] font-bold uppercase ' + statusBadge + '">' + escapeHtml(r.status) + '</span></td>' +
        '<td class="px-lg py-md text-center">' + approveBtn + receiveBtn + cancelBtn + '</td>' +
        '<td class="px-lg py-md text-right opacity-0 group-hover:opacity-100 transition-opacity">' +
        '<button class="p-1 hover:bg-surface-variant rounded-full text-primary" onclick="controllers.sales_returns.showEditForm(' + r.id + ')"><span class="material-symbols-outlined text-[20px]">edit</span></button>' +
        '<button class="p-1 hover:bg-error-container rounded-full text-error" onclick="controllers.sales_returns.deleteReturn(' + r.id + ')"><span class="material-symbols-outlined text-[20px]">delete</span></button>' +
        '</td></tr>'
    }).join('')
    return renderHtml('screens/sales_returns', { rows: rows, count: filtered.length, draftCount: items.filter(function(r) { return r.status === 'Draft' }).length, receivedCount: items.filter(function(r) { return r.status === 'Received' }).length })
  },
  mount() { controllers.sales_returns = this; var s = document.getElementById('srSearch'); if (s) s.value = this.searchTerm || '' },
  async refresh() { await window.salesReturnService.load(); document.getElementById('content').innerHTML = this.render() },
  search(q) { this.searchTerm = q.toLowerCase(); document.getElementById('content').innerHTML = this.render() },
  showCreateForm() {
    var today = new Date().toISOString().slice(0,10)
    document.getElementById('content').innerHTML = renderHtml('screens/sales_returns_form', { title: 'New Sales Return', id: '', returnNumber: 'SR-' + String(window.salesReturnService.getAll().length + 1).padStart(3, '0'), salesOrderId: '', customerId: '', returnDate: today, reason: '', notes: '' })
  },
  showEditForm(id) {
    var r = window.salesReturnService.getById(id)
    if (!r) return
    document.getElementById('content').innerHTML = renderHtml('screens/sales_returns_form', {
      title: 'Edit Sales Return', id: r.id, returnNumber: escapeHtml(r.returnNumber),
      salesOrderId: r.salesOrderId, customerId: r.customerId, returnDate: r.returnDate, reason: escapeHtml(r.reason || ''), notes: escapeHtml(r.notes || '')
    })
  },
  async saveForm() {
    var id = document.getElementById('srFormId').value
    var payload = {
      returnNumber: document.getElementById('srFormNumber').value,
      salesOrderId: parseInt(document.getElementById('srFormSO').value) || null,
      customerId: parseInt(document.getElementById('srFormCustomer').value) || null,
      returnDate: document.getElementById('srFormDate').value,
      reason: document.getElementById('srFormReason').value || null,
      notes: document.getElementById('srFormNotes').value || null
    }
    if (!payload.customerId) { app.toast('Customer ID is required', 'error'); return false }
    try {
      if (id) { await window.salesReturnService.update(id, payload) }
      else { await window.salesReturnService.create(payload) }
      app.toast('Sales return saved', 'success')
      document.getElementById('content').innerHTML = this.render()
    } catch (e) { app.toast('Error: ' + e.message, 'error') }
    return false
  },
  async approveReturn(id) {
    if (!confirm('Approve this sales return?')) return
    try {
      await window.salesReturnService.update(id, { status: 'Approved' })
      app.toast('Sales return approved', 'success')
      document.getElementById('content').innerHTML = this.render()
    } catch (e) { app.toast('Error: ' + e.message, 'error') }
  },
  async receiveReturn(id) {
    if (!confirm('Receive this sales return? This will update stock.')) return
    try {
      await window.salesReturnService.update(id, { status: 'Received' })
      app.toast('Sales return received - stock updated', 'success')
      document.getElementById('content').innerHTML = this.render()
    } catch (e) { app.toast('Error: ' + e.message, 'error') }
  },
  async cancelReturn(id) {
    if (!confirm('Cancel this sales return?')) return
    try {
      await window.salesReturnService.update(id, { status: 'Cancelled' })
      app.toast('Sales return cancelled', 'success')
      document.getElementById('content').innerHTML = this.render()
    } catch (e) { app.toast('Error: ' + e.message, 'error') }
  },
  async deleteReturn(id) {
    if (!confirm('Delete sales return?')) return
    try { await window.salesReturnService.remove(id); document.getElementById('content').innerHTML = this.render() }
    catch (e) { app.toast('Error deleting: ' + e.message, 'error') }
  }
}
