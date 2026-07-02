window.NovaModules = window.NovaModules || {}; window.NovaModules['maintenance'] = {
  render() {
    var search = this.searchTerm || ''
    var items = window.maintenanceService.getAll()
    var filtered = search ? items.filter(function(w) { return (w.assetName || '').toLowerCase().indexOf(search) > -1 || (w.assignedTo || '').toLowerCase().indexOf(search) > -1 }) : items
    var rows = filtered.map(function(w) {
      var statusBadge = w.status === 'Completed' ? '<span class="px-sm py-xs bg-secondary-container text-on-secondary-container rounded text-[11px] font-bold uppercase">Completed</span>' : (w.status === 'In Progress' ? '<span class="px-sm py-xs bg-primary-container text-primary rounded text-[11px] font-bold uppercase">In Progress</span>' : (w.status === 'Overdue' ? '<span class="px-sm py-xs bg-error-container text-error rounded text-[11px] font-bold uppercase">Overdue</span>' : '<span class="px-sm py-xs bg-surface-container-high text-on-surface-variant rounded text-[11px] font-bold uppercase">' + escapeHtml(w.status) + '</span>'))
      var actionBtn = w.status === 'Completed' ? '<span class="text-secondary font-label-md text-label-md flex items-center justify-end"><span class="material-symbols-outlined text-[16px] mr-1">check_circle</span>Done</span>' : '<button class="bg-primary text-on-primary px-3 py-1 rounded text-label-md font-label-md hover:brightness-110 press-effect transition-all" onclick="controllers.maintenance.completeWorkOrder(\'' + w.id + '\')">Complete</button>'
      return '<tr class="hover:bg-primary-container/5 transition-colors group">' +
             '<td class="px-lg py-md"><div class="font-medium text-on-surface">' + escapeHtml(w.assetName || '-') + '</div></td>' +
             '<td class="px-lg py-md text-body-md text-on-surface-variant">' + escapeHtml(w.type || '-') + '</td>' +
             '<td class="px-lg py-md">' + statusBadge + '</td>' +
             '<td class="px-lg py-md text-body-md text-on-surface-variant">' + escapeHtml(w.scheduledDate || '-') + '</td>' +
             '<td class="px-lg py-md text-body-md text-on-surface-variant">' + escapeHtml(w.assignedTo || 'Unassigned') + '</td>' +
             '<td class="px-lg py-md text-right">' + actionBtn + '</td>' +
             '</tr>'
    }).join('')
    return renderHtml('screens/nova_maintenance_management', {
      workOrderRows: rows,
      totalAssets: window.assetService ? window.assetService.getAll().length : items.length,
      pendingOrders: window.maintenanceService.getPendingCount(),
      overdueOrders: window.maintenanceService.getOverdueCount()
    })
  },
  mount() { controllers.maintenance = this; var s = document.getElementById('maintenanceSearch'); if (s) s.value = this.searchTerm || '' },
  search(q) { this.searchTerm = q.toLowerCase(); document.getElementById('content').innerHTML = this.render() },
  showCreateForm() {
    document.getElementById('content').innerHTML = renderHtml('models/inspection/form', {
      title: 'Add Work Order', id: '', assetName: '', type: 'Repair', status: 'Pending', scheduledDate: '', assignedTo: '', notes: ''
    })
  },
  async saveForm() {
    var id = document.getElementById('inspectionFormId') ? document.getElementById('inspectionFormId').value : ''
    var assetName = document.getElementById('inspectionFormProduct') ? document.getElementById('inspectionFormProduct').value : ''
    try {
      if (id) {
        await window.maintenanceService.update(id, { assetName: assetName, status: 'In Progress' })
      } else {
        await window.maintenanceService.create({
          assetName: assetName || 'New Asset',
          type: document.getElementById('inspectionFormInspector') ? document.getElementById('inspectionFormInspector').value : 'Repair',
          status: 'Pending',
          scheduledDate: new Date().toISOString().split('T')[0],
          assignedTo: 'Unassigned'
        })
        app.toast('Work order created', 'success')
      }
      document.getElementById('content').innerHTML = this.render()
    } catch (e) {
      app.toast('Error saving work order: ' + e.message, 'error')
    }
    return false
  },
  async completeWorkOrder(id) {
    try {
      await window.maintenanceService.update(id, { status: 'Completed' })
      app.toast('Work order completed', 'success')
      document.getElementById('content').innerHTML = this.render()
    } catch (e) {
      app.toast('Error completing work order: ' + e.message, 'error')
    }
  },
  async deleteItem(id) {
    if (!confirm('Delete this work order?')) return
    try {
      await window.maintenanceService.remove(id)
      document.getElementById('content').innerHTML = this.render()
    } catch (e) {
      app.toast('Error deleting work order: ' + e.message, 'error')
    }
  }
}
