window.NovaModules = window.NovaModules || {}; window.NovaModules['contracts'] = {
  render() {
    var search = this.searchTerm || ''
    var items = window.contractService.getAll()
    var filtered = search ? items.filter(function(c) { return (c.title || c.name || '').toLowerCase().indexOf(search) > -1 || (c.vendor || '').toLowerCase().indexOf(search) > -1 }) : items
    var contractRows = filtered.map(function(c) {
      var statusBadge = c.status === 'Active' ? '<span class="px-sm py-xs bg-secondary-container text-on-secondary-container rounded text-[11px] font-bold uppercase">Active</span>' : (c.status === 'Expired' ? '<span class="px-sm py-xs bg-error-container text-error rounded text-[11px] font-bold uppercase">Expired</span>' : '<span class="px-sm py-xs bg-surface-container-high text-on-surface-variant rounded text-[11px] font-bold uppercase">' + escapeHtml(c.status || 'Draft') + '</span>')
      return '<tr class="hover:bg-primary-container/5 transition-colors group">' +
             '<td class="px-lg py-md"><div class="font-medium text-on-surface">' + escapeHtml(c.title || c.name || '-') + '</div></td>' +
             '<td class="px-lg py-md text-body-md text-on-surface-variant">' + escapeHtml(c.vendor || '-') + '</td>' +
             '<td class="px-lg py-md">' + statusBadge + '</td>' +
             '<td class="px-lg py-md text-body-md text-on-surface-variant">' + escapeHtml(c.startDate || '-') + '</td>' +
             '<td class="px-lg py-md text-body-md text-on-surface-variant">' + escapeHtml(c.endDate || '-') + '</td>' +
             '<td class="px-lg py-md text-right"><button class="p-1 hover:bg-surface-variant rounded-full text-primary" onclick="controllers.contracts.editItem(\'' + c.id + '\')"><span class="material-symbols-outlined text-[20px]">edit</span></button></td>' +
             '</tr>'
    }).join('')
    var slaItems = window.slaService ? window.slaService.getAll() : []
    var slaRows = slaItems.map(function(s) {
      return '<tr class="hover:bg-primary-container/5 transition-colors">' +
             '<td class="px-lg py-md"><div class="font-medium text-on-surface">' + escapeHtml(s.name || '-') + '</div></td>' +
             '<td class="px-lg py-md text-body-md text-on-surface-variant">' + escapeHtml(s.responseTime || s.responseTimeHrs || '-') + 'h</td>' +
             '<td class="px-lg py-md text-body-md text-on-surface-variant">' + escapeHtml(s.resolutionTime || s.resolutionTimeHrs || '-') + 'h</td>' +
             '<td class="px-lg py-md"><span class="px-sm py-xs bg-surface-container-high text-on-surface-variant rounded text-[11px] font-bold uppercase">' + escapeHtml(s.priority || '-') + '</span></td>' +
             '</tr>'
    }).join('')
    return renderHtml('screens/contracts___slas', {
      contractRows: contractRows,
      slaRows: slaRows,
      activeContracts: window.contractService.getActiveCount(),
      slaDefinitions: slaItems.length,
      complianceRate: 95
    })
  },
  mount() { controllers.contracts = this; var s = document.getElementById('contractSearch'); if (s) s.value = this.searchTerm || '' },
  search(q) { this.searchTerm = q.toLowerCase(); document.getElementById('content').innerHTML = this.render() },
  showCreateForm() {
    document.getElementById('content').innerHTML = renderHtml('models/inspection/form', {
      title: 'New Contract', id: '', name: '', vendor: '', status: 'Draft', startDate: '', endDate: ''
    })
  },
  async saveForm() {
    var id = document.getElementById('inspectionFormId') ? document.getElementById('inspectionFormId').value : ''
    try {
      if (id) {
        await window.contractService.update(id, { status: 'Active' })
      } else {
        await window.contractService.create({
          title: document.getElementById('inspectionFormProduct') ? document.getElementById('inspectionFormProduct').value : 'New Contract',
          vendor: '',
          status: 'Draft',
          startDate: new Date().toISOString().split('T')[0],
          endDate: ''
        })
        app.toast('Contract created', 'success')
      }
      document.getElementById('content').innerHTML = this.render()
    } catch (e) {
      app.toast('Error saving contract: ' + e.message, 'error')
    }
    return false
  },
  editItem(id) {
    var c = window.contractService.getById(id)
    if (!c) return
    document.getElementById('content').innerHTML = renderHtml('models/inspection/form', {
      title: 'Edit Contract', id: c.id, name: escapeHtml(c.title || c.name || ''), vendor: escapeHtml(c.vendor || ''), status: c.status || '', startDate: c.startDate || '', endDate: c.endDate || ''
    })
  },
  async deleteItem(id) {
    if (!confirm('Delete this contract?')) return
    try {
      await window.contractService.remove(id)
      document.getElementById('content').innerHTML = this.render()
    } catch (e) {
      app.toast('Error deleting contract: ' + e.message, 'error')
    }
  }
}
