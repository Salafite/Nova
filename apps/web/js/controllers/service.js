window.NovaModules = window.NovaModules || {}; window.NovaModules['service'] = {
  render() {
    var search = this.searchTerm || ''
    var items = window.serviceManagementService.getAll()
    var filtered = search ? items.filter(function(s) { return (s.customerName || '').toLowerCase().indexOf(search) > -1 || (s.type || '').toLowerCase().indexOf(search) > -1 || (s.status || '').toLowerCase().indexOf(search) > -1 }) : items
    var rows = filtered.map(function(s) {
      var statusBadge = s.status === 'Resolved' || s.status === 'Closed' ? '<span class="px-sm py-xs bg-secondary-container text-on-secondary-container rounded text-[11px] font-bold uppercase">' + escapeHtml(s.status) + '</span>' : (s.status === 'In Progress' ? '<span class="px-sm py-xs bg-primary-container text-primary rounded text-[11px] font-bold uppercase">In Progress</span>' : '<span class="px-sm py-xs bg-surface-container-high text-on-surface-variant rounded text-[11px] font-bold uppercase">' + escapeHtml(s.status || 'Open') + '</span>')
      var priorityBadge = s.priority === 'High' || s.priority === 'Critical' ? '<span class="px-sm py-xs bg-error-container text-error rounded text-[11px] font-bold uppercase">' + escapeHtml(s.priority) + '</span>' : (s.priority === 'Medium' ? '<span class="px-sm py-xs bg-warning/10 text-warning rounded text-[11px] font-bold uppercase">Medium</span>' : '<span class="px-sm py-xs bg-surface-container-high text-on-surface-variant rounded text-[11px] font-bold uppercase">' + escapeHtml(s.priority || 'Low') + '</span>')
      return '<tr class="hover:bg-primary-container/5 transition-colors group">' +
             '<td class="px-lg py-md"><span class="font-data-mono text-data-mono text-primary">#' + escapeHtml(s.requestNumber || s.id) + '</span></td>' +
             '<td class="px-lg py-md"><div class="font-medium text-on-surface">' + escapeHtml(s.customerName || '-') + '</div></td>' +
             '<td class="px-lg py-md text-body-md text-on-surface-variant">' + escapeHtml(s.type || '-') + '</td>' +
             '<td class="px-lg py-md">' + statusBadge + '</td>' +
             '<td class="px-lg py-md">' + priorityBadge + '</td>' +
             '<td class="px-lg py-md text-body-md text-on-surface-variant">' + escapeHtml(s.createdAt || s.createdDate || '-') + '</td>' +
             '<td class="px-lg py-md text-right"><button class="p-1 hover:bg-surface-variant rounded-full text-primary" onclick="controllers.service.editItem(\'' + s.id + '\')"><span class="material-symbols-outlined text-[20px]">edit</span></button></td>' +
             '</tr>'
    }).join('')
    return renderHtml('screens/service_management', {
      serviceRows: rows,
      openRequests: window.serviceManagementService.getOpenCount(),
      slaCompliance: window.serviceManagementService.getSlaCompliance(),
      avgResponseTime: window.serviceManagementService.getAvgResponseTime()
    })
  },
  mount() { controllers.service = this; var s = document.getElementById('serviceSearch'); if (s) s.value = this.searchTerm || '' },
  search(q) { this.searchTerm = q.toLowerCase(); document.getElementById('content').innerHTML = this.render() },
  showCreateForm() {
    document.getElementById('content').innerHTML = renderHtml('models/inspection/form', {
      title: 'New Service Request', id: '', customerName: '', type: 'Support', status: 'Open', priority: 'Medium', notes: ''
    })
  },
  async saveForm() {
    var id = document.getElementById('inspectionFormId') ? document.getElementById('inspectionFormId').value : ''
    try {
      if (id) {
        await window.serviceManagementService.update(id, { status: 'In Progress' })
      } else {
        await window.serviceManagementService.create({
          requestNumber: 'SRQ-' + Date.now(),
          customerName: document.getElementById('inspectionFormProduct') ? document.getElementById('inspectionFormProduct').value : 'Customer',
          type: 'Support',
          status: 'Open',
          priority: 'Medium',
          createdAt: new Date().toISOString().split('T')[0]
        })
        app.toast('Service request created', 'success')
      }
      document.getElementById('content').innerHTML = this.render()
    } catch (e) {
      app.toast('Error saving service request: ' + e.message, 'error')
    }
    return false
  },
  editItem(id) {
    var s = window.serviceManagementService.getById(id)
    if (!s) return
    document.getElementById('content').innerHTML = renderHtml('models/inspection/form', {
      title: 'Edit Request', id: s.id, customerName: escapeHtml(s.customerName || ''), type: s.type || '', status: s.status || '', priority: s.priority || '', notes: escapeHtml(s.notes || '')
    })
  },
  async deleteItem(id) {
    if (!confirm('Delete this service request?')) return
    try {
      await window.serviceManagementService.remove(id)
      document.getElementById('content').innerHTML = this.render()
    } catch (e) {
      app.toast('Error deleting service request: ' + e.message, 'error')
    }
  }
}
