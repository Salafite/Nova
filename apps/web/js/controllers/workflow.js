window.NovaModules = window.NovaModules || {}; window.NovaModules['workflow'] = {
  render() {
    var search = this.searchTerm || ''
    var items = window.workflowEngineService.getAll()
    var filtered = search ? items.filter(function(w) { return (w.name || '').toLowerCase().indexOf(search) > -1 || (w.type || '').toLowerCase().indexOf(search) > -1 }) : items
    var rows = filtered.map(function(w) {
      var statusBadge = w.status === 'Active' || w.status === 'Running' ? '<span class="px-sm py-xs bg-secondary-container text-on-secondary-container rounded text-[11px] font-bold uppercase">' + escapeHtml(w.status) + '</span>' : '<span class="px-sm py-xs bg-surface-container-high text-on-surface-variant rounded text-[11px] font-bold uppercase">' + escapeHtml(w.status || 'Draft') + '</span>'
      return '<tr class="hover:bg-primary/5 transition-colors group">' +
             '<td class="px-lg py-md font-body-md font-semibold text-primary">' + escapeHtml(w.name) + '</td>' +
             '<td class="px-lg py-md text-body-md text-on-surface-variant">' + escapeHtml(w.type || '-') + '</td>' +
             '<td class="px-lg py-md">' + statusBadge + '</td>' +
             '<td class="px-lg py-md text-body-md font-data-mono">' + (w.steps || 0) + '</td>' +
             '<td class="px-lg py-md text-body-md text-on-surface-variant">' + escapeHtml(w.lastRunAt || '-') + '</td>' +
             '</tr>'
    }).join('')
    return renderHtml('screens/workflow_automation', {
      workflowRows: rows,
      totalWorkflows: items.length,
      activeWorkflows: window.workflowEngineService.getActiveCount(),
      totalSteps: items.reduce(function(s, w) { return s + (w.steps || 0) }, 0)
    })
  },
  mount() { controllers.workflow = this; var s = document.getElementById('workflowSearch'); if (s) s.value = this.searchTerm || '' },
  search(q) { this.searchTerm = q.toLowerCase(); document.getElementById('content').innerHTML = this.render() },
  showCreateForm() {
    document.getElementById('content').innerHTML = renderHtml('models/product/form', {
      title: 'New Workflow', id: '', name: '', type: 'Automation', status: 'Draft'
    })
  },
  async saveForm() {
    try {
      await window.workflowEngineService.create({
        name: document.getElementById('inspectionFormProduct') ? document.getElementById('inspectionFormProduct').value : 'New Workflow',
        type: 'Automation',
        status: 'Draft',
        steps: 0
      })
      app.toast('Workflow created', 'success')
      document.getElementById('content').innerHTML = this.render()
    } catch (e) {
      app.toast('Error creating workflow: ' + e.message, 'error')
    }
    return false
  },
  async deleteItem(id) {
    if (!confirm('Delete this workflow?')) return
    try {
      await window.workflowEngineService.remove(id)
      document.getElementById('content').innerHTML = this.render()
    } catch (e) {
      app.toast('Error deleting workflow: ' + e.message, 'error')
    }
  }
}
