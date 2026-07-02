window.NovaModules = window.NovaModules || {}; window.NovaModules['forecast'] = {
  render() {
    var search = this.searchTerm || ''
    var items = window.forecastService.getAll()
    var filtered = search ? items.filter(function(f) { return (f.name || '').toLowerCase().indexOf(search) > -1 || (f.type || '').toLowerCase().indexOf(search) > -1 || (f.status || '').toLowerCase().indexOf(search) > -1 }) : items
    var rows = filtered.map(function(f) {
      var statusBadge = f.status === 'Active' ? '<span class="px-sm py-xs bg-secondary/10 text-secondary rounded text-[11px] font-medium uppercase">Active</span>' : (f.status === 'Completed' ? '<span class="px-sm py-xs bg-primary/10 text-primary rounded text-[11px] font-medium uppercase">Completed</span>' : '<span class="px-sm py-xs bg-surface-container-highest text-on-surface-variant rounded text-[11px] font-medium uppercase">' + escapeHtml(f.status || 'Draft') + '</span>')
      var accuracyPct = f.accuracy || 0
      return '<tr class="hover:bg-primary/5 transition-colors group">' +
             '<td class="px-lg py-md font-body-md font-semibold text-on-surface">' + escapeHtml(f.name) + '</td>' +
             '<td class="px-lg py-md text-body-md text-on-surface-variant">' + escapeHtml(f.type || '-') + '</td>' +
             '<td class="px-lg py-md text-body-md text-on-surface-variant">' + escapeHtml(f.period || '-') + '</td>' +
             '<td class="px-lg py-md text-center">' + statusBadge + '</td>' +
             '<td class="px-lg py-md text-right"><div class="flex items-center gap-sm justify-end"><span class="font-data-mono text-data-mono text-on-surface-variant">' + accuracyPct + '%</span><div class="w-16 bg-surface-container-high h-1.5 rounded-full overflow-hidden"><div class="bg-secondary h-full rounded-full" style="width:' + accuracyPct + '%"></div></div></div></td>' +
             '<td class="px-lg py-md text-center opacity-0 group-hover:opacity-100 transition-opacity">' +
             '<div class="flex items-center justify-center gap-1">' +
             '<button class="p-1 hover:bg-surface-variant rounded-full text-primary" onclick="controllers.forecast.showEditForm(' + f.id + ')"><span class="material-symbols-outlined text-[20px]">edit</span></button>' +
             '<button class="p-1 hover:bg-error-container rounded-full text-error" onclick="controllers.forecast.deleteItem(' + f.id + ')"><span class="material-symbols-outlined text-[20px]">delete</span></button>' +
             '</div></td></tr>'
    }).join('')
    var totalAccuracy = filtered.length ? Math.round(filtered.reduce(function(s, f) { return s + (f.accuracy || 0) }, 0) / filtered.length) : 0
    return renderHtml('screens/forecasting', {
      forecastRows: rows,
      activeForecasts: window.forecastService.getActiveCount(),
      accuracyRate: totalAccuracy,
      dataSources: items.length > 0 ? Math.max(1, Math.ceil(items.length / 2)) : 0
    })
  },
  mount() { controllers.forecast = this; var s = document.getElementById('forecastSearch'); if (s) s.value = this.searchTerm || '' },
  search(q) { this.searchTerm = q.toLowerCase(); document.getElementById('content').innerHTML = this.render() },
  showCreateForm() {
    document.getElementById('content').innerHTML =
      '<div class="max-w-2xl mx-auto bg-surface-container-lowest border border-outline-variant rounded-xl p-lg shadow-sm">' +
      '<h3 class="font-title-md text-title-md font-bold mb-lg">New Forecast</h3>' +
      '<form onsubmit="return controllers.forecast.saveForm()">' +
      '<input type="hidden" id="forecastFormId" value="" />' +
      '<div class="grid grid-cols-1 md:grid-cols-2 gap-md mb-md">' +
      '<div class="flex flex-col gap-xs"><label class="font-label-sm text-label-sm font-bold text-on-surface-variant uppercase">Name</label><input id="forecastFormName" required class="w-full bg-surface border border-outline-variant rounded-lg px-3 py-2 text-body-md focus:ring-2 focus:ring-primary/20" /></div>' +
      '<div class="flex flex-col gap-xs"><label class="font-label-sm text-label-sm font-bold text-on-surface-variant uppercase">Type</label><select id="forecastFormType" class="w-full bg-surface border border-outline-variant rounded-lg px-3 py-2 text-body-md focus:ring-2 focus:ring-primary/20"><option value="Demand">Demand</option><option value="Revenue">Revenue</option><option value="Sales">Sales</option><option value="Inventory">Inventory</option></select></div>' +
      '<div class="flex flex-col gap-xs"><label class="font-label-sm text-label-sm font-bold text-on-surface-variant uppercase">Period</label><select id="forecastFormPeriod" class="w-full bg-surface border border-outline-variant rounded-lg px-3 py-2 text-body-md focus:ring-2 focus:ring-primary/20"><option value="Monthly">Monthly</option><option value="Quarterly">Quarterly</option><option value="Yearly">Yearly</option></select></div>' +
      '<div class="flex flex-col gap-xs"><label class="font-label-sm text-label-sm font-bold text-on-surface-variant uppercase">Status</label><select id="forecastFormStatus" class="w-full bg-surface border border-outline-variant rounded-lg px-3 py-2 text-body-md focus:ring-2 focus:ring-primary/20"><option value="Draft">Draft</option><option value="Active">Active</option><option value="Completed">Completed</option></select></div>' +
      '<div class="flex flex-col gap-xs"><label class="font-label-sm text-label-sm font-bold text-on-surface-variant uppercase">Accuracy (%)</label><input id="forecastFormAccuracy" type="number" value="0" class="w-full bg-surface border border-outline-variant rounded-lg px-3 py-2 text-body-md focus:ring-2 focus:ring-primary/20" /></div>' +
      '</div>' +
      '<div class="flex gap-sm mt-lg"><button type="submit" class="bg-primary text-on-primary px-lg py-sm rounded-lg font-label-md press-effect">Save</button>' +
      '<button type="button" class="bg-surface border border-outline-variant text-on-surface-variant px-lg py-sm rounded-lg font-label-md press-effect" onclick="controllers.forecast.render()">Cancel</button></div>' +
      '</form></div>'
  },
  showEditForm(id) {
    var f = window.forecastService.getById(id)
    if (!f) return
    var typeOpts = ['Demand', 'Revenue', 'Sales', 'Inventory'].map(function(t) { return '<option value="' + t + '"' + (t === f.type ? ' selected' : '') + '>' + t + '</option>' }).join('')
    var periodOpts = ['Monthly', 'Quarterly', 'Yearly'].map(function(p) { return '<option value="' + p + '"' + (p === f.period ? ' selected' : '') + '>' + p + '</option>' }).join('')
    var statusOpts = ['Draft', 'Active', 'Completed'].map(function(s) { return '<option value="' + s + '"' + (s === f.status ? ' selected' : '') + '>' + s + '</option>' }).join('')
    document.getElementById('content').innerHTML =
      '<div class="max-w-2xl mx-auto bg-surface-container-lowest border border-outline-variant rounded-xl p-lg shadow-sm">' +
      '<h3 class="font-title-md text-title-md font-bold mb-lg">Edit Forecast</h3>' +
      '<form onsubmit="return controllers.forecast.saveForm()">' +
      '<input type="hidden" id="forecastFormId" value="' + f.id + '" />' +
      '<div class="grid grid-cols-1 md:grid-cols-2 gap-md mb-md">' +
      '<div class="flex flex-col gap-xs"><label class="font-label-sm text-label-sm font-bold text-on-surface-variant uppercase">Name</label><input id="forecastFormName" value="' + escapeHtml(f.name) + '" required class="w-full bg-surface border border-outline-variant rounded-lg px-3 py-2 text-body-md focus:ring-2 focus:ring-primary/20" /></div>' +
      '<div class="flex flex-col gap-xs"><label class="font-label-sm text-label-sm font-bold text-on-surface-variant uppercase">Type</label><select id="forecastFormType" class="w-full bg-surface border border-outline-variant rounded-lg px-3 py-2 text-body-md focus:ring-2 focus:ring-primary/20">' + typeOpts + '</select></div>' +
      '<div class="flex flex-col gap-xs"><label class="font-label-sm text-label-sm font-bold text-on-surface-variant uppercase">Period</label><select id="forecastFormPeriod" class="w-full bg-surface border border-outline-variant rounded-lg px-3 py-2 text-body-md focus:ring-2 focus:ring-primary/20">' + periodOpts + '</select></div>' +
      '<div class="flex flex-col gap-xs"><label class="font-label-sm text-label-sm font-bold text-on-surface-variant uppercase">Status</label><select id="forecastFormStatus" class="w-full bg-surface border border-outline-variant rounded-lg px-3 py-2 text-body-md focus:ring-2 focus:ring-primary/20">' + statusOpts + '</select></div>' +
      '<div class="flex flex-col gap-xs"><label class="font-label-sm text-label-sm font-bold text-on-surface-variant uppercase">Accuracy (%)</label><input id="forecastFormAccuracy" type="number" value="' + (f.accuracy || 0) + '" class="w-full bg-surface border border-outline-variant rounded-lg px-3 py-2 text-body-md focus:ring-2 focus:ring-primary/20" /></div>' +
      '</div>' +
      '<div class="flex gap-sm mt-lg"><button type="submit" class="bg-primary text-on-primary px-lg py-sm rounded-lg font-label-md press-effect">Save</button>' +
      '<button type="button" class="bg-surface border border-outline-variant text-on-surface-variant px-lg py-sm rounded-lg font-label-md press-effect" onclick="controllers.forecast.render()">Cancel</button></div>' +
      '</form></div>'
  },
  async saveForm() {
    var id = document.getElementById('forecastFormId').value
    var payload = {
      name: document.getElementById('forecastFormName').value,
      type: document.getElementById('forecastFormType').value,
      period: document.getElementById('forecastFormPeriod').value,
      status: document.getElementById('forecastFormStatus').value,
      accuracy: parseInt(document.getElementById('forecastFormAccuracy').value) || 0
    }
    try {
      if (id) { await window.forecastService.update(id, payload) } else { await window.forecastService.create(payload) }
      app.toast('Forecast saved', 'success')
      document.getElementById('content').innerHTML = this.render()
    } catch (e) { app.toast('Error saving forecast: ' + e.message, 'error') }
    return false
  },
  async deleteItem(id) {
    if (!confirm('Delete this forecast?')) return
    try { await window.forecastService.remove(id); app.toast('Forecast deleted', 'success'); document.getElementById('content').innerHTML = this.render() } catch (e) { app.toast('Error deleting: ' + e.message, 'error') }
  }
}
