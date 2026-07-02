window.NovaModules = window.NovaModules || {}; window.NovaModules['resource'] = {
  render() {
    var search = this.searchTerm || ''
    var items = window.resourcePlanningService.getAll()
    var filtered = search ? items.filter(function(r) { return (r.name || '').toLowerCase().indexOf(search) > -1 || (r.project || '').toLowerCase().indexOf(search) > -1 || (r.role || '').toLowerCase().indexOf(search) > -1 }) : items
    var rows = filtered.map(function(r) {
      var statusBadge = r.status === 'Allocated' || r.status === 'Active' ? '<span class="px-sm py-xs bg-primary-container text-primary rounded text-[11px] font-bold uppercase">Allocated</span>' : (r.status === 'Available' ? '<span class="px-sm py-xs bg-secondary-container text-on-secondary-container rounded text-[11px] font-bold uppercase">Available</span>' : '<span class="px-sm py-xs bg-surface-container-high text-on-surface-variant rounded text-[11px] font-bold uppercase">' + escapeHtml(r.status || '-') + '</span>')
      return '<tr class="hover:bg-primary-container/5 transition-colors group">' +
             '<td class="px-lg py-md"><div class="font-medium text-on-surface">' + escapeHtml(r.name || r.resourceName || '-') + '</div></td>' +
             '<td class="px-lg py-md text-body-md text-on-surface-variant">' + escapeHtml(r.project || '-') + '</td>' +
             '<td class="px-lg py-md text-body-md text-on-surface-variant">' + escapeHtml(r.role || '-') + '</td>' +
             '<td class="px-lg py-md">' + statusBadge + '</td>' +
             '<td class="px-lg py-md text-body-md text-on-surface-variant">' + escapeHtml(r.startDate || '-') + '</td>' +
             '<td class="px-lg py-md text-body-md text-on-surface-variant">' + escapeHtml(r.endDate || '-') + '</td>' +
             '<td class="px-lg py-md text-right"><button class="p-1 hover:bg-surface-variant rounded-full text-primary" onclick="controllers.resource.editItem(\'' + r.id + '\')"><span class="material-symbols-outlined text-[20px]">edit</span></button></td>' +
             '</tr>'
    }).join('')
    return renderHtml('screens/resource_planning', {
      resourceRows: rows,
      totalResources: items.length,
      utilizationRate: window.resourcePlanningService.getUtilizationRate(),
      availableResources: window.resourcePlanningService.getAvailableCount()
    })
  },
  mount() { controllers.resource = this; var s = document.getElementById('resourceSearch'); if (s) s.value = this.searchTerm || '' },
  search(q) { this.searchTerm = q.toLowerCase(); document.getElementById('content').innerHTML = this.render() },
  showCreateForm() {
    document.getElementById('content').innerHTML = renderHtml('models/inspection/form', {
      title: 'Allocate Resource', id: '', name: '', project: '', role: '', allocation: '100', startDate: '', endDate: ''
    })
  },
  async saveForm() {
    var id = document.getElementById('inspectionFormId') ? document.getElementById('inspectionFormId').value : ''
    try {
      if (id) {
        await window.resourcePlanningService.update(id, { status: 'Allocated' })
      } else {
        await window.resourcePlanningService.create({
          name: document.getElementById('inspectionFormProduct') ? document.getElementById('inspectionFormProduct').value : 'New Resource',
          project: '',
          role: '',
          status: 'Available',
          startDate: new Date().toISOString().split('T')[0],
          endDate: ''
        })
        app.toast('Resource allocated', 'success')
      }
      document.getElementById('content').innerHTML = this.render()
    } catch (e) {
      app.toast('Error saving resource allocation: ' + e.message, 'error')
    }
    return false
  },
  editItem(id) {
    var r = window.resourcePlanningService.getById(id)
    if (!r) return
    document.getElementById('content').innerHTML = renderHtml('models/inspection/form', {
      title: 'Edit Allocation', id: r.id, name: escapeHtml(r.name || ''), project: escapeHtml(r.project || ''), role: escapeHtml(r.role || ''), allocation: r.allocation || '100', startDate: r.startDate || '', endDate: r.endDate || ''
    })
  },
  async deleteItem(id) {
    if (!confirm('Delete this allocation?')) return
    try {
      await window.resourcePlanningService.remove(id)
      document.getElementById('content').innerHTML = this.render()
    } catch (e) {
      app.toast('Error deleting allocation: ' + e.message, 'error')
    }
  }
}
