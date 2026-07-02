window.NovaModules = window.NovaModules || {}; window.NovaModules['project'] = {
  render() {
    var search = this.searchTerm || ''
    var items = window.projectService.getAll()
    var filtered = search ? items.filter(function(p) { return (p.name || '').toLowerCase().indexOf(search) > -1 || (p.status || '').toLowerCase().indexOf(search) > -1 }) : items
    var rows = filtered.map(function(p) {
      var statusBadge = p.status === 'Completed' ? '<span class="px-sm py-xs bg-secondary-container text-on-secondary-container rounded text-[11px] font-bold uppercase">Completed</span>' : (p.status === 'In Progress' || p.status === 'Active' ? '<span class="px-sm py-xs bg-primary-container text-primary rounded text-[11px] font-bold uppercase">In Progress</span>' : '<span class="px-sm py-xs bg-surface-container-high text-on-surface-variant rounded text-[11px] font-bold uppercase">' + escapeHtml(p.status || 'Draft') + '</span>')
      var progress = p.progress || 0
      return '<tr class="hover:bg-primary-container/5 transition-colors group">' +
             '<td class="px-lg py-md"><div class="font-medium text-on-surface">' + escapeHtml(p.name) + '</div></td>' +
             '<td class="px-lg py-md">' + statusBadge + '</td>' +
             '<td class="px-lg py-md text-body-md text-on-surface-variant">' + escapeHtml(p.startDate || '-') + '</td>' +
             '<td class="px-lg py-md text-body-md text-on-surface-variant">' + escapeHtml(p.endDate || '-') + '</td>' +
             '<td class="px-lg py-md text-body-md text-on-surface-variant">' + (p.taskCount || 0) + '</td>' +
             '<td class="px-lg py-md text-right"><div class="flex items-center gap-sm justify-end"><span class="font-data-mono text-data-mono text-on-surface-variant">' + progress + '%</span><div class="w-16 bg-surface-container-high h-1.5 rounded-full overflow-hidden"><div class="bg-primary h-full rounded-full" style="width:' + progress + '%"></div></div></div></td>' +
             '</tr>'
    }).join('')
    return renderHtml('screens/project_management', {
      projectRows: rows,
      activeProjects: window.projectService.getActiveCount(),
      totalTasks: items.reduce(function(s, p) { return s + (p.taskCount || 0) }, 0),
      completionRate: window.projectService.getCompletionRate()
    })
  },
  mount() { controllers.project = this; var s = document.getElementById('projectSearch'); if (s) s.value = this.searchTerm || '' },
  search(q) { this.searchTerm = q.toLowerCase(); document.getElementById('content').innerHTML = this.render() },
  showCreateForm() {
    document.getElementById('content').innerHTML = renderHtml('models/inspection/form', {
      title: 'New Project', id: '', name: '', description: '', status: 'Draft', startDate: '', endDate: '', budget: ''
    })
  },
  async saveForm() {
    var id = document.getElementById('inspectionFormId') ? document.getElementById('inspectionFormId').value : ''
    try {
      if (id) {
        await window.projectService.update(id, { status: 'In Progress' })
      } else {
        await window.projectService.create({
          name: document.getElementById('inspectionFormProduct') ? document.getElementById('inspectionFormProduct').value : 'New Project',
          description: '',
          status: 'Draft',
          startDate: new Date().toISOString().split('T')[0],
          endDate: '',
          budget: 0
        })
        app.toast('Project created', 'success')
      }
      document.getElementById('content').innerHTML = this.render()
    } catch (e) {
      app.toast('Error saving project: ' + e.message, 'error')
    }
    return false
  },
  async deleteItem(id) {
    if (!confirm('Delete this project?')) return
    try {
      await window.projectService.remove(id)
      document.getElementById('content').innerHTML = this.render()
    } catch (e) {
      app.toast('Error deleting project: ' + e.message, 'error')
    }
  }
}
