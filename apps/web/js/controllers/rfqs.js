window.NovaModules = window.NovaModules || {}; window.NovaModules['rfqs'] = {
  render() {
    var search = this.searchTerm || ''
    var items = window.rfqService.getAll()
    var filtered = search ? items.filter(function(r) { return (r.rfqNumber || '').toLowerCase().indexOf(search) > -1 || (r.title || '').toLowerCase().indexOf(search) > -1 }) : items
    var rows = filtered.map(function(r) {
      var statusBadge = r.status === 'Draft' ? 'bg-surface-container text-on-surface-variant border border-outline-variant' :
        (r.status === 'Sent' ? 'bg-warning/10 text-warning border border-warning/20' :
        (r.status === 'Open' ? 'bg-secondary/10 text-secondary border border-secondary/20' :
        (r.status === 'Closed' ? 'bg-primary/10 text-primary border border-primary/20' :
        (r.status === 'Cancelled' ? 'bg-error/10 text-error border border-error/20' :
        'bg-surface-container text-on-surface-variant border border-outline-variant'))))
      var sendBtn = r.status === 'Draft' ? '<button class="text-warning font-label-md text-label-md hover:underline" onclick="controllers.rfqs.sendToVendors(' + r.id + ')">Send to Vendors</button>' : ''
      var closeBtn = (r.status === 'Sent' || r.status === 'Open') ? ' | <button class="text-primary font-label-md text-label-md hover:underline" onclick="controllers.rfqs.closeRFQ(' + r.id + ')">Close</button>' : ''
      var convertBtn = r.status === 'Open' ? ' | <button class="text-success font-label-md text-label-md hover:underline" onclick="controllers.rfqs.convertToPO(' + r.id + ')">Convert to PO</button>' : ''
      return '<tr class="hover:bg-primary/5 transition-colors group">' +
        '<td class="px-lg py-md font-data-mono text-data-mono font-bold text-primary">' + escapeHtml(r.rfqNumber) + '</td>' +
        '<td class="px-lg py-md font-body-md font-medium">' + escapeHtml(r.title) + '</td>' +
        '<td class="px-lg py-md font-body-md text-on-surface-variant">' + (r.dueDate ? escapeHtml(r.dueDate) : '-') + '</td>' +
        '<td class="px-lg py-md"><span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-[11px] font-bold uppercase ' + statusBadge + '">' + escapeHtml(r.status) + '</span></td>' +
        '<td class="px-lg py-md text-center">' + sendBtn + closeBtn + convertBtn + '</td>' +
        '<td class="px-lg py-md text-right opacity-0 group-hover:opacity-100 transition-opacity">' +
        '<button class="p-1 hover:bg-surface-variant rounded-full text-primary" onclick="controllers.rfqs.showEditForm(' + r.id + ')"><span class="material-symbols-outlined text-[20px]">edit</span></button>' +
        '<button class="p-1 hover:bg-error-container rounded-full text-error" onclick="controllers.rfqs.deleteRFQ(' + r.id + ')"><span class="material-symbols-outlined text-[20px]">delete</span></button>' +
        '</td></tr>'
    }).join('')
    return renderHtml('screens/rfqs', { rows: rows, count: filtered.length, openCount: items.filter(function(r) { return r.status === 'Sent' || r.status === 'Open' }).length, closedCount: items.filter(function(r) { return r.status === 'Closed' }).length })
  },
  mount() { controllers.rfqs = this; var s = document.getElementById('rfqSearch'); if (s) s.value = this.searchTerm || '' },
  async refresh() { await window.rfqService.load(); document.getElementById('content').innerHTML = this.render() },
  search(q) { this.searchTerm = q.toLowerCase(); document.getElementById('content').innerHTML = this.render() },
  showCreateForm() {
    document.getElementById('content').innerHTML = renderHtml('screens/rfqs_form', { title: 'New RFQ', id: '', rfqNumber: 'RFQ-' + String(window.rfqService.getAll().length + 1).padStart(3, '0'), title: '', description: '', dueDate: '', notes: '' })
  },
  showEditForm(id) {
    var r = window.rfqService.getById(id)
    if (!r) return
    document.getElementById('content').innerHTML = renderHtml('screens/rfqs_form', {
      title: 'Edit RFQ', id: r.id, rfqNumber: escapeHtml(r.rfqNumber), title: escapeHtml(r.title),
      description: escapeHtml(r.description || ''), dueDate: r.dueDate || '', notes: escapeHtml(r.notes || '')
    })
  },
  async saveForm() {
    var id = document.getElementById('rfqFormId').value
    var payload = {
      rfqNumber: document.getElementById('rfqFormNumber').value,
      title: document.getElementById('rfqFormTitle').value,
      description: document.getElementById('rfqFormDesc').value || null,
      dueDate: document.getElementById('rfqFormDueDate').value || null,
      notes: document.getElementById('rfqFormNotes').value || null
    }
    if (!payload.title) { app.toast('Title is required', 'error'); return false }
    try {
      if (id) { await window.rfqService.update(id, payload) }
      else { await window.rfqService.create(payload) }
      app.toast('RFQ saved', 'success')
      document.getElementById('content').innerHTML = this.render()
    } catch (e) { app.toast('Error: ' + e.message, 'error') }
    return false
  },
  async sendToVendors(id) {
    if (!confirm('Send this RFQ to vendors?')) return
    try {
      await window.rfqService.update(id, { status: 'Sent' })
      app.toast('RFQ sent to vendors', 'success')
      document.getElementById('content').innerHTML = this.render()
    } catch (e) { app.toast('Error: ' + e.message, 'error') }
  },
  async closeRFQ(id) {
    if (!confirm('Close this RFQ?')) return
    try {
      await window.rfqService.update(id, { status: 'Closed' })
      app.toast('RFQ closed', 'success')
      document.getElementById('content').innerHTML = this.render()
    } catch (e) { app.toast('Error: ' + e.message, 'error') }
  },
  async convertToPO(id) {
    var vendorId = prompt('Enter Vendor ID to accept their quote:')
    if (!vendorId) return
    if (!confirm('Convert this RFQ to a Purchase Order?')) return
    try {
      var po = await window.rfqService.convertToPO(id, parseInt(vendorId))
      app.toast('RFQ converted to PO #' + po.orderNumber, 'success')
      document.getElementById('content').innerHTML = this.render()
    } catch (e) { app.toast('Error converting: ' + e.message, 'error') }
  },
  async deleteRFQ(id) {
    if (!confirm('Delete RFQ?')) return
    try { await window.rfqService.remove(id); document.getElementById('content').innerHTML = this.render() }
    catch (e) { app.toast('Error deleting: ' + e.message, 'error') }
  }
}
