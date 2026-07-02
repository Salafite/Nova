window.NovaModules = window.NovaModules || {}; window.NovaModules['bi'] = {
  render() {
    var search = this.searchTerm || ''
    var items = window.analyticsService.getAll()
    var filtered = search ? items.filter(function(k) { return (k.name || '').toLowerCase().indexOf(search) > -1 || (k.category || '').toLowerCase().indexOf(search) > -1 || (k.status || '').toLowerCase().indexOf(search) > -1 }) : items
    var rows = filtered.map(function(k) {
      var statusBadge = k.status === 'On Track' ? '<span class="px-sm py-xs bg-secondary/10 text-secondary rounded text-[11px] font-medium uppercase">On Track</span>' : (k.status === 'At Risk' ? '<span class="px-sm py-xs bg-warning/10 text-warning rounded text-[11px] font-medium uppercase">At Risk</span>' : (k.status === 'Critical' ? '<span class="px-sm py-xs bg-error/10 text-error rounded text-[11px] font-medium uppercase">Critical</span>' : '<span class="px-sm py-xs bg-surface-container-highest text-on-surface-variant rounded text-[11px] font-medium uppercase">' + escapeHtml(k.status) + '</span>'))
      return '<tr class="hover:bg-primary/5 transition-colors group">' +
             '<td class="px-lg py-md font-body-md font-semibold text-on-surface">' + escapeHtml(k.name) + '</td>' +
             '<td class="px-lg py-md text-body-md text-on-surface-variant">' + escapeHtml(k.category || '-') + '</td>' +
             '<td class="px-lg py-md font-data-mono text-data-mono text-on-surface-variant">' + (k.target || 0) + '</td>' +
             '<td class="px-lg py-md font-data-mono text-data-mono text-on-surface-variant">' + (k.value || 0) + '</td>' +
             '<td class="px-lg py-md text-center">' + statusBadge + '</td>' +
             '<td class="px-lg py-md text-center opacity-0 group-hover:opacity-100 transition-opacity">' +
             '<div class="flex items-center justify-center gap-1">' +
             '<button class="p-1 hover:bg-surface-variant rounded-full text-primary" onclick="controllers.bi.showEditForm(' + k.id + ')"><span class="material-symbols-outlined text-[20px]">edit</span></button>' +
             '<button class="p-1 hover:bg-error-container rounded-full text-error" onclick="controllers.bi.deleteItem(' + k.id + ')"><span class="material-symbols-outlined text-[20px]">delete</span></button>' +
             '</div></td></tr>'
    }).join('')
    return renderHtml('screens/business_intelligence_foundation', {
      kpiRows: rows,
      totalKpis: items.length,
      onTarget: window.analyticsService.getOnTarget(),
      atRisk: window.analyticsService.getAtRisk()
    })
  },
  mount() { controllers.bi = this; var s = document.getElementById('kpiSearch'); if (s) s.value = this.searchTerm || '' },
  search(q) { this.searchTerm = q.toLowerCase(); document.getElementById('content').innerHTML = this.render() },
  showCreateForm() {
    document.getElementById('content').innerHTML =
      '<div class="max-w-2xl mx-auto bg-surface-container-lowest border border-outline-variant rounded-xl p-lg shadow-sm">' +
      '<h3 class="font-title-md text-title-md font-bold mb-lg">Add KPI</h3>' +
      '<form onsubmit="return controllers.bi.saveForm()">' +
      '<input type="hidden" id="kpiFormId" value="" />' +
      '<div class="grid grid-cols-1 md:grid-cols-2 gap-md mb-md">' +
      '<div class="flex flex-col gap-xs"><label class="font-label-sm text-label-sm font-bold text-on-surface-variant uppercase">Name</label><input id="kpiFormName" required class="w-full bg-surface border border-outline-variant rounded-lg px-3 py-2 text-body-md focus:ring-2 focus:ring-primary/20" /></div>' +
      '<div class="flex flex-col gap-xs"><label class="font-label-sm text-label-sm font-bold text-on-surface-variant uppercase">Category</label><select id="kpiFormCategory" class="w-full bg-surface border border-outline-variant rounded-lg px-3 py-2 text-body-md focus:ring-2 focus:ring-primary/20"><option value="Financial">Financial</option><option value="Operational">Operational</option><option value="Sales">Sales</option><option value="HR">HR</option><option value="Quality">Quality</option></select></div>' +
      '<div class="flex flex-col gap-xs"><label class="font-label-sm text-label-sm font-bold text-on-surface-variant uppercase">Target</label><input id="kpiFormTarget" type="number" required class="w-full bg-surface border border-outline-variant rounded-lg px-3 py-2 text-body-md focus:ring-2 focus:ring-primary/20" /></div>' +
      '<div class="flex flex-col gap-xs"><label class="font-label-sm text-label-sm font-bold text-on-surface-variant uppercase">Current Value</label><input id="kpiFormValue" type="number" class="w-full bg-surface border border-outline-variant rounded-lg px-3 py-2 text-body-md focus:ring-2 focus:ring-primary/20" /></div>' +
      '<div class="flex flex-col gap-xs"><label class="font-label-sm text-label-sm font-bold text-on-surface-variant uppercase">Status</label><select id="kpiFormStatus" class="w-full bg-surface border border-outline-variant rounded-lg px-3 py-2 text-body-md focus:ring-2 focus:ring-primary/20"><option value="On Track">On Track</option><option value="At Risk">At Risk</option><option value="Critical">Critical</option><option value="Completed">Completed</option></select></div>' +
      '</div>' +
      '<div class="flex gap-sm mt-lg"><button type="submit" class="bg-primary text-on-primary px-lg py-sm rounded-lg font-label-md press-effect">Save</button>' +
      '<button type="button" class="bg-surface border border-outline-variant text-on-surface-variant px-lg py-sm rounded-lg font-label-md press-effect" onclick="controllers.bi.render()">Cancel</button></div>' +
      '</form></div>'
  },
  showEditForm(id) {
    var k = window.analyticsService.getById(id)
    if (!k) return
    var catOpts = ['Financial', 'Operational', 'Sales', 'HR', 'Quality'].map(function(t) { return '<option value="' + t + '"' + (t === k.category ? ' selected' : '') + '>' + t + '</option>' }).join('')
    var statusOpts = ['On Track', 'At Risk', 'Critical', 'Completed'].map(function(s) { return '<option value="' + s + '"' + (s === k.status ? ' selected' : '') + '>' + s + '</option>' }).join('')
    document.getElementById('content').innerHTML =
      '<div class="max-w-2xl mx-auto bg-surface-container-lowest border border-outline-variant rounded-xl p-lg shadow-sm">' +
      '<h3 class="font-title-md text-title-md font-bold mb-lg">Edit KPI</h3>' +
      '<form onsubmit="return controllers.bi.saveForm()">' +
      '<input type="hidden" id="kpiFormId" value="' + k.id + '" />' +
      '<div class="grid grid-cols-1 md:grid-cols-2 gap-md mb-md">' +
      '<div class="flex flex-col gap-xs"><label class="font-label-sm text-label-sm font-bold text-on-surface-variant uppercase">Name</label><input id="kpiFormName" value="' + escapeHtml(k.name) + '" required class="w-full bg-surface border border-outline-variant rounded-lg px-3 py-2 text-body-md focus:ring-2 focus:ring-primary/20" /></div>' +
      '<div class="flex flex-col gap-xs"><label class="font-label-sm text-label-sm font-bold text-on-surface-variant uppercase">Category</label><select id="kpiFormCategory" class="w-full bg-surface border border-outline-variant rounded-lg px-3 py-2 text-body-md focus:ring-2 focus:ring-primary/20">' + catOpts + '</select></div>' +
      '<div class="flex flex-col gap-xs"><label class="font-label-sm text-label-sm font-bold text-on-surface-variant uppercase">Target</label><input id="kpiFormTarget" type="number" value="' + (k.target || 0) + '" required class="w-full bg-surface border border-outline-variant rounded-lg px-3 py-2 text-body-md focus:ring-2 focus:ring-primary/20" /></div>' +
      '<div class="flex flex-col gap-xs"><label class="font-label-sm text-label-sm font-bold text-on-surface-variant uppercase">Current Value</label><input id="kpiFormValue" type="number" value="' + (k.value || 0) + '" class="w-full bg-surface border border-outline-variant rounded-lg px-3 py-2 text-body-md focus:ring-2 focus:ring-primary/20" /></div>' +
      '<div class="flex flex-col gap-xs"><label class="font-label-sm text-label-sm font-bold text-on-surface-variant uppercase">Status</label><select id="kpiFormStatus" class="w-full bg-surface border border-outline-variant rounded-lg px-3 py-2 text-body-md focus:ring-2 focus:ring-primary/20">' + statusOpts + '</select></div>' +
      '</div>' +
      '<div class="flex gap-sm mt-lg"><button type="submit" class="bg-primary text-on-primary px-lg py-sm rounded-lg font-label-md press-effect">Save</button>' +
      '<button type="button" class="bg-surface border border-outline-variant text-on-surface-variant px-lg py-sm rounded-lg font-label-md press-effect" onclick="controllers.bi.render()">Cancel</button></div>' +
      '</form></div>'
  },
  async saveForm() {
    var id = document.getElementById('kpiFormId').value
    var payload = {
      name: document.getElementById('kpiFormName').value,
      category: document.getElementById('kpiFormCategory').value,
      target: parseFloat(document.getElementById('kpiFormTarget').value) || 0,
      value: parseFloat(document.getElementById('kpiFormValue').value) || 0,
      status: document.getElementById('kpiFormStatus').value
    }
    try {
      if (id) { await window.analyticsService.update(id, payload) } else { await window.analyticsService.create(payload) }
      app.toast('KPI saved', 'success')
      document.getElementById('content').innerHTML = this.render()
    } catch (e) { app.toast('Error saving KPI: ' + e.message, 'error') }
    return false
  },
  async deleteItem(id) {
    if (!confirm('Delete this KPI?')) return
    try { await window.analyticsService.remove(id); app.toast('KPI deleted', 'success'); document.getElementById('content').innerHTML = this.render() } catch (e) { app.toast('Error deleting: ' + e.message, 'error') }
  }
}
