window.NovaModules = window.NovaModules || {}; window.NovaModules['executive'] = {
  render() {
    var search = this.searchTerm || ''
    var items = window.dashboardService.getAll()
    var filtered = search ? items.filter(function(d) { return (d.name || '').toLowerCase().indexOf(search) > -1 || (d.category || '').toLowerCase().indexOf(search) > -1 || (d.status || '').toLowerCase().indexOf(search) > -1 }) : items
    var rows = filtered.map(function(d) {
      var statusBadge = d.status === 'Active' ? '<span class="px-sm py-xs bg-secondary/10 text-secondary rounded text-[11px] font-medium uppercase">Active</span>' : '<span class="px-sm py-xs bg-surface-container-highest text-on-surface-variant rounded text-[11px] font-medium uppercase">' + escapeHtml(d.status || 'Draft') + '</span>'
      return '<tr class="hover:bg-primary/5 transition-colors group">' +
             '<td class="px-lg py-md font-body-md font-semibold text-on-surface">' + escapeHtml(d.name) + '</td>' +
             '<td class="px-lg py-md text-body-md text-on-surface-variant">' + escapeHtml(d.category || '-') + '</td>' +
             '<td class="px-lg py-md text-center font-data-mono text-data-mono">' + (d.widgetCount || 0) + '</td>' +
             '<td class="px-lg py-md text-center">' + statusBadge + '</td>' +
             '<td class="px-lg py-md text-body-md text-on-surface-variant">' + escapeHtml(d.lastUpdated || '-') + '</td>' +
             '<td class="px-lg py-md text-center opacity-0 group-hover:opacity-100 transition-opacity">' +
             '<div class="flex items-center justify-center gap-1">' +
             '<button class="p-1 hover:bg-surface-variant rounded-full text-primary" onclick="controllers.executive.showEditForm(' + d.id + ')"><span class="material-symbols-outlined text-[20px]">edit</span></button>' +
             '<button class="p-1 hover:bg-error-container rounded-full text-error" onclick="controllers.executive.deleteItem(' + d.id + ')"><span class="material-symbols-outlined text-[20px]">delete</span></button>' +
             '</div></td></tr>'
    }).join('')
    return renderHtml('screens/executive_dashboards', {
      dashboardRows: rows,
      activeDashboards: window.dashboardService.getActiveCount(),
      scheduledReports: items.filter(function(d) { return d.scheduledReports || 0 }).reduce(function(s, d) { return s + (d.scheduledReports || 0) }, 0),
      dataSources: items.filter(function(d) { return d.dataSources || 0 }).reduce(function(s, d) { return s + (d.dataSources || 0) }, 0)
    })
  },
  mount() { controllers.executive = this; var s = document.getElementById('dashboardSearch'); if (s) s.value = this.searchTerm || '' },
  search(q) { this.searchTerm = q.toLowerCase(); document.getElementById('content').innerHTML = this.render() },
  showCreateForm() {
    document.getElementById('content').innerHTML =
      '<div class="max-w-2xl mx-auto bg-surface-container-lowest border border-outline-variant rounded-xl p-lg shadow-sm">' +
      '<h3 class="font-title-md text-title-md font-bold mb-lg">New Dashboard</h3>' +
      '<form onsubmit="return controllers.executive.saveForm()">' +
      '<input type="hidden" id="dashboardFormId" value="" />' +
      '<div class="grid grid-cols-1 md:grid-cols-2 gap-md mb-md">' +
      '<div class="flex flex-col gap-xs"><label class="font-label-sm text-label-sm font-bold text-on-surface-variant uppercase">Name</label><input id="dashboardFormName" required class="w-full bg-surface border border-outline-variant rounded-lg px-3 py-2 text-body-md focus:ring-2 focus:ring-primary/20" /></div>' +
      '<div class="flex flex-col gap-xs"><label class="font-label-sm text-label-sm font-bold text-on-surface-variant uppercase">Category</label><select id="dashboardFormCategory" class="w-full bg-surface border border-outline-variant rounded-lg px-3 py-2 text-body-md focus:ring-2 focus:ring-primary/20"><option value="Executive">Executive</option><option value="Financial">Financial</option><option value="Operational">Operational</option><option value="Sales">Sales</option></select></div>' +
      '<div class="flex flex-col gap-xs"><label class="font-label-sm text-label-sm font-bold text-on-surface-variant uppercase">Widget Count</label><input id="dashboardFormWidgets" type="number" value="0" class="w-full bg-surface border border-outline-variant rounded-lg px-3 py-2 text-body-md focus:ring-2 focus:ring-primary/20" /></div>' +
      '<div class="flex flex-col gap-xs"><label class="font-label-sm text-label-sm font-bold text-on-surface-variant uppercase">Status</label><select id="dashboardFormStatus" class="w-full bg-surface border border-outline-variant rounded-lg px-3 py-2 text-body-md focus:ring-2 focus:ring-primary/20"><option value="Active">Active</option><option value="Draft">Draft</option><option value="Archived">Archived</option></select></div>' +
      '</div>' +
      '<div class="flex gap-sm mt-lg"><button type="submit" class="bg-primary text-on-primary px-lg py-sm rounded-lg font-label-md press-effect">Save</button>' +
      '<button type="button" class="bg-surface border border-outline-variant text-on-surface-variant px-lg py-sm rounded-lg font-label-md press-effect" onclick="controllers.executive.render()">Cancel</button></div>' +
      '</form></div>'
  },
  showEditForm(id) {
    var d = window.dashboardService.getById(id)
    if (!d) return
    var catOpts = ['Executive', 'Financial', 'Operational', 'Sales'].map(function(t) { return '<option value="' + t + '"' + (t === d.category ? ' selected' : '') + '>' + t + '</option>' }).join('')
    var statusOpts = ['Active', 'Draft', 'Archived'].map(function(s) { return '<option value="' + s + '"' + (s === d.status ? ' selected' : '') + '>' + s + '</option>' }).join('')
    document.getElementById('content').innerHTML =
      '<div class="max-w-2xl mx-auto bg-surface-container-lowest border border-outline-variant rounded-xl p-lg shadow-sm">' +
      '<h3 class="font-title-md text-title-md font-bold mb-lg">Edit Dashboard</h3>' +
      '<form onsubmit="return controllers.executive.saveForm()">' +
      '<input type="hidden" id="dashboardFormId" value="' + d.id + '" />' +
      '<div class="grid grid-cols-1 md:grid-cols-2 gap-md mb-md">' +
      '<div class="flex flex-col gap-xs"><label class="font-label-sm text-label-sm font-bold text-on-surface-variant uppercase">Name</label><input id="dashboardFormName" value="' + escapeHtml(d.name) + '" required class="w-full bg-surface border border-outline-variant rounded-lg px-3 py-2 text-body-md focus:ring-2 focus:ring-primary/20" /></div>' +
      '<div class="flex flex-col gap-xs"><label class="font-label-sm text-label-sm font-bold text-on-surface-variant uppercase">Category</label><select id="dashboardFormCategory" class="w-full bg-surface border border-outline-variant rounded-lg px-3 py-2 text-body-md focus:ring-2 focus:ring-primary/20">' + catOpts + '</select></div>' +
      '<div class="flex flex-col gap-xs"><label class="font-label-sm text-label-sm font-bold text-on-surface-variant uppercase">Widget Count</label><input id="dashboardFormWidgets" type="number" value="' + (d.widgetCount || 0) + '" class="w-full bg-surface border border-outline-variant rounded-lg px-3 py-2 text-body-md focus:ring-2 focus:ring-primary/20" /></div>' +
      '<div class="flex flex-col gap-xs"><label class="font-label-sm text-label-sm font-bold text-on-surface-variant uppercase">Status</label><select id="dashboardFormStatus" class="w-full bg-surface border border-outline-variant rounded-lg px-3 py-2 text-body-md focus:ring-2 focus:ring-primary/20">' + statusOpts + '</select></div>' +
      '</div>' +
      '<div class="flex gap-sm mt-lg"><button type="submit" class="bg-primary text-on-primary px-lg py-sm rounded-lg font-label-md press-effect">Save</button>' +
      '<button type="button" class="bg-surface border border-outline-variant text-on-surface-variant px-lg py-sm rounded-lg font-label-md press-effect" onclick="controllers.executive.render()">Cancel</button></div>' +
      '</form></div>'
  },
  async saveForm() {
    var id = document.getElementById('dashboardFormId').value
    var payload = {
      name: document.getElementById('dashboardFormName').value,
      category: document.getElementById('dashboardFormCategory').value,
      widgetCount: parseInt(document.getElementById('dashboardFormWidgets').value) || 0,
      status: document.getElementById('dashboardFormStatus').value
    }
    try {
      if (id) { await window.dashboardService.update(id, payload) } else { await window.dashboardService.create(payload) }
      app.toast('Dashboard saved', 'success')
      document.getElementById('content').innerHTML = this.render()
    } catch (e) { app.toast('Error saving dashboard: ' + e.message, 'error') }
    return false
  },
  async deleteItem(id) {
    if (!confirm('Delete this dashboard?')) return
    try { await window.dashboardService.remove(id); app.toast('Dashboard deleted', 'success'); document.getElementById('content').innerHTML = this.render() } catch (e) { app.toast('Error deleting: ' + e.message, 'error') }
  }
}
