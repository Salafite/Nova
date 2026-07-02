window.NovaModules = window.NovaModules || {}; window.NovaModules['purchase_requisitions'] = {
  render() {
    var search = this.searchTerm || ''
    var items = window.purchaseRequisitionService.getAll()
    var filtered = search ? items.filter(function(r) { return (r.reqNumber || '').toLowerCase().indexOf(search) > -1 || (r.title || '').toLowerCase().indexOf(search) > -1 }) : items
    var rows = filtered.map(function(r) {
      var statusBadge = r.status === 'Approved' ? 'bg-secondary/10 text-secondary border border-secondary/20' :
        (r.status === 'Ordered' ? 'bg-primary/10 text-primary border border-primary/20' :
        (r.status === 'Pending Approval' ? 'bg-warning/10 text-warning border border-warning/20' :
        (r.status === 'Rejected' ? 'bg-error/10 text-error border border-error/20' :
        (r.status === 'Partially Ordered' ? 'bg-info/10 text-info border border-info/20' :
        'bg-surface-container text-on-surface-variant border border-outline-variant'))))
      var priorityBadge = r.priority === 'Urgent' ? 'bg-error/10 text-error border border-error/20' :
        (r.priority === 'High' ? 'bg-warning/10 text-warning border border-warning/20' :
        (r.priority === 'Low' ? 'bg-surface-container-low text-on-surface-variant border border-outline-variant' :
        'bg-surface-container text-on-surface-variant border border-outline-variant'))
      var approveBtn = r.status === 'Pending Approval' ? '<button class="text-success font-label-md text-label-md hover:underline" onclick="controllers.purchase_requisitions.approve(' + r.id + ')">Approve</button> | <button class="text-error font-label-md text-label-md hover:underline" onclick="controllers.purchase_requisitions.reject(' + r.id + ')">Reject</button>' : ''
      return '<tr class="hover:bg-primary/5 transition-colors group">' +
        '<td class="px-lg py-md font-data-mono text-data-mono font-bold text-primary">' + escapeHtml(r.reqNumber) + '</td>' +
        '<td class="px-lg py-md font-body-md font-medium">' + escapeHtml(r.title) + '</td>' +
        '<td class="px-lg py-md font-body-md text-on-surface-variant">' + escapeHtml(r.departmentId || '-') + '</td>' +
        '<td class="px-lg py-md"><span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-[11px] font-bold uppercase ' + priorityBadge + '">' + escapeHtml(r.priority) + '</span></td>' +
        '<td class="px-lg py-md"><span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-[11px] font-bold uppercase ' + statusBadge + '">' + escapeHtml(r.status) + '</span></td>' +
        '<td class="px-lg py-md text-center">' + approveBtn + '</td>' +
        '<td class="px-lg py-md text-right opacity-0 group-hover:opacity-100 transition-opacity">' +
        '<button class="p-1 hover:bg-surface-variant rounded-full text-primary" onclick="controllers.purchase_requisitions.showEditForm(' + r.id + ')"><span class="material-symbols-outlined text-[20px]">edit</span></button>' +
        '<button class="p-1 hover:bg-error-container rounded-full text-error" onclick="controllers.purchase_requisitions.deleteReq(' + r.id + ')"><span class="material-symbols-outlined text-[20px]">delete</span></button>' +
        '</td></tr>'
    }).join('')
    return renderHtml('screens/purchase_requisitions', { rows: rows, count: filtered.length, pending: window.purchaseRequisitionService.getPendingCount(), approvedCount: items.filter(function(r) { return r.status === 'Approved' }).length })
  },
  mount() { controllers.purchase_requisitions = this; var s = document.getElementById('reqSearch'); if (s) s.value = this.searchTerm || '' },
  async refresh() { await window.purchaseRequisitionService.load(); document.getElementById('content').innerHTML = this.render() },
  search(q) { this.searchTerm = q.toLowerCase(); document.getElementById('content').innerHTML = this.render() },
  showCreateForm() {
    document.getElementById('content').innerHTML = renderHtml('screens/purchase_requisitions_form', { title: 'New Purchase Requisition', id: '', reqNumber: 'REQ-' + String(window.purchaseRequisitionService.getAll().length + 1).padStart(3, '0'), title: '', description: '', departmentId: '', priority: 'Medium', notes: '' })
  },
  showEditForm(id) {
    var r = window.purchaseRequisitionService.getById(id)
    if (!r) return
    document.getElementById('content').innerHTML = renderHtml('screens/purchase_requisitions_form', {
      title: 'Edit Requisition', id: r.id, reqNumber: escapeHtml(r.reqNumber), title: escapeHtml(r.title),
      description: escapeHtml(r.description || ''), departmentId: r.departmentId, priority: r.priority, notes: escapeHtml(r.notes || '')
    })
  },
  async saveForm() {
    var id = document.getElementById('reqFormId').value
    var payload = {
      reqNumber: document.getElementById('reqFormNumber').value,
      title: document.getElementById('reqFormTitle').value,
      description: document.getElementById('reqFormDesc').value || null,
      departmentId: parseInt(document.getElementById('reqFormDept').value) || null,
      priority: document.getElementById('reqFormPriority').value,
      notes: document.getElementById('reqFormNotes').value || null,
      requestedBy: window.Auth && window.Auth.user ? window.Auth.user.id : 1
    }
    if (!payload.title) { app.toast('Title is required', 'error'); return false }
    try {
      if (id) { await window.purchaseRequisitionService.update(id, payload) }
      else { await window.purchaseRequisitionService.create(payload) }
      app.toast('Requisition saved', 'success')
      document.getElementById('content').innerHTML = this.render()
    } catch (e) { app.toast('Error: ' + e.message, 'error') }
    return false
  },
  async approve(id) {
    if (!confirm('Approve this requisition?')) return
    try {
      await window.purchaseRequisitionService.update(id, { status: 'Approved' })
      app.toast('Requisition approved', 'success')
      document.getElementById('content').innerHTML = this.render()
    } catch (e) { app.toast('Error: ' + e.message, 'error') }
  },
  async reject(id) {
    if (!confirm('Reject this requisition?')) return
    try {
      await window.purchaseRequisitionService.update(id, { status: 'Rejected' })
      app.toast('Requisition rejected', 'success')
      document.getElementById('content').innerHTML = this.render()
    } catch (e) { app.toast('Error: ' + e.message, 'error') }
  },
  async deleteReq(id) {
    if (!confirm('Delete requisition?')) return
    try { await window.purchaseRequisitionService.remove(id); document.getElementById('content').innerHTML = this.render() }
    catch (e) { app.toast('Error deleting: ' + e.message, 'error') }
  }
}
