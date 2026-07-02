window.NovaModules = window.NovaModules || {}; window.NovaModules['operational'] = {
  render() {
    var search = this.searchTerm || ''
    var items = window.operationalAnalyticsService.getAll()
    var filtered = search ? items.filter(function(m) { return (m.metric || '').toLowerCase().indexOf(search) > -1 || (m.category || '').toLowerCase().indexOf(search) > -1 || (m.unit || '').toLowerCase().indexOf(search) > -1 }) : items
    var rows = filtered.map(function(m) {
      var trendIcon = m.trend === 'up' ? '<span class="material-symbols-outlined text-secondary text-[20px]">trending_up</span>' : (m.trend === 'down' ? '<span class="material-symbols-outlined text-error text-[20px]">trending_down</span>' : '<span class="material-symbols-outlined text-on-surface-variant text-[20px]">trending_flat</span>')
      return '<tr class="hover:bg-primary/5 transition-colors group">' +
             '<td class="px-lg py-md font-body-md font-semibold text-on-surface">' + escapeHtml(m.metric) + '</td>' +
             '<td class="px-lg py-md text-body-md text-on-surface-variant">' + escapeHtml(m.category || '-') + '</td>' +
             '<td class="px-lg py-md font-data-mono text-data-mono text-on-surface-variant">' + (m.value || 0) + '</td>' +
             '<td class="px-lg py-md text-body-md text-on-surface-variant">' + escapeHtml(m.unit || '-') + '</td>' +
             '<td class="px-lg py-md text-center">' + trendIcon + '</td>' +
             '<td class="px-lg py-md text-center opacity-0 group-hover:opacity-100 transition-opacity">' +
             '<div class="flex items-center justify-center gap-1">' +
             '<button class="p-1 hover:bg-surface-variant rounded-full text-primary" onclick="controllers.operational.showEditForm(' + m.id + ')"><span class="material-symbols-outlined text-[20px]">edit</span></button>' +
             '<button class="p-1 hover:bg-error-container rounded-full text-error" onclick="controllers.operational.deleteItem(' + m.id + ')"><span class="material-symbols-outlined text-[20px]">delete</span></button>' +
             '</div></td></tr>'
    }).join('')
    var totalValue = filtered.reduce(function(s, m) { return s + (m.value || 0) }, 0)
    return renderHtml('screens/operational_analytics', {
      metricRows: rows,
      activeSessions: items.filter(function(m) { return m.category === 'Session' }).length || Math.ceil(items.length / 3),
      dataPoints: totalValue || items.length * 100,
      reportsGenerated: items.filter(function(m) { return m.category === 'Report' }).length || Math.ceil(items.length / 4)
    })
  },
  mount() { controllers.operational = this; var s = document.getElementById('opsSearch'); if (s) s.value = this.searchTerm || '' },
  search(q) { this.searchTerm = q.toLowerCase(); document.getElementById('content').innerHTML = this.render() },
  showCreateForm() {
    document.getElementById('content').innerHTML =
      '<div class="max-w-2xl mx-auto bg-surface-container-lowest border border-outline-variant rounded-xl p-lg shadow-sm">' +
      '<h3 class="font-title-md text-title-md font-bold mb-lg">Add Operational Metric</h3>' +
      '<form onsubmit="return controllers.operational.saveForm()">' +
      '<input type="hidden" id="metricFormId" value="" />' +
      '<div class="grid grid-cols-1 md:grid-cols-2 gap-md mb-md">' +
      '<div class="flex flex-col gap-xs"><label class="font-label-sm text-label-sm font-bold text-on-surface-variant uppercase">Metric</label><input id="metricFormName" required class="w-full bg-surface border border-outline-variant rounded-lg px-3 py-2 text-body-md focus:ring-2 focus:ring-primary/20" /></div>' +
      '<div class="flex flex-col gap-xs"><label class="font-label-sm text-label-sm font-bold text-on-surface-variant uppercase">Category</label><select id="metricFormCategory" class="w-full bg-surface border border-outline-variant rounded-lg px-3 py-2 text-body-md focus:ring-2 focus:ring-primary/20"><option value="Performance">Performance</option><option value="Session">Session</option><option value="Report">Report</option><option value="Quality">Quality</option></select></div>' +
      '<div class="flex flex-col gap-xs"><label class="font-label-sm text-label-sm font-bold text-on-surface-variant uppercase">Value</label><input id="metricFormValue" type="number" required class="w-full bg-surface border border-outline-variant rounded-lg px-3 py-2 text-body-md focus:ring-2 focus:ring-primary/20" /></div>' +
      '<div class="flex flex-col gap-xs"><label class="font-label-sm text-label-sm font-bold text-on-surface-variant uppercase">Unit</label><input id="metricFormUnit" placeholder="e.g. ms, %, count" class="w-full bg-surface border border-outline-variant rounded-lg px-3 py-2 text-body-md focus:ring-2 focus:ring-primary/20" /></div>' +
      '<div class="flex flex-col gap-xs"><label class="font-label-sm text-label-sm font-bold text-on-surface-variant uppercase">Trend</label><select id="metricFormTrend" class="w-full bg-surface border border-outline-variant rounded-lg px-3 py-2 text-body-md focus:ring-2 focus:ring-primary/20"><option value="up">Up</option><option value="down">Down</option><option value="flat">Flat</option></select></div>' +
      '</div>' +
      '<div class="flex gap-sm mt-lg"><button type="submit" class="bg-primary text-on-primary px-lg py-sm rounded-lg font-label-md press-effect">Save</button>' +
      '<button type="button" class="bg-surface border border-outline-variant text-on-surface-variant px-lg py-sm rounded-lg font-label-md press-effect" onclick="controllers.operational.render()">Cancel</button></div>' +
      '</form></div>'
  },
  showEditForm(id) {
    var m = window.operationalAnalyticsService.getById(id)
    if (!m) return
    var catOpts = ['Performance', 'Session', 'Report', 'Quality'].map(function(t) { return '<option value="' + t + '"' + (t === m.category ? ' selected' : '') + '>' + t + '</option>' }).join('')
    var trendOpts = ['up', 'down', 'flat'].map(function(t) { return '<option value="' + t + '"' + (t === m.trend ? ' selected' : '') + '>' + t.charAt(0).toUpperCase() + t.slice(1) + '</option>' }).join('')
    document.getElementById('content').innerHTML =
      '<div class="max-w-2xl mx-auto bg-surface-container-lowest border border-outline-variant rounded-xl p-lg shadow-sm">' +
      '<h3 class="font-title-md text-title-md font-bold mb-lg">Edit Metric</h3>' +
      '<form onsubmit="return controllers.operational.saveForm()">' +
      '<input type="hidden" id="metricFormId" value="' + m.id + '" />' +
      '<div class="grid grid-cols-1 md:grid-cols-2 gap-md mb-md">' +
      '<div class="flex flex-col gap-xs"><label class="font-label-sm text-label-sm font-bold text-on-surface-variant uppercase">Metric</label><input id="metricFormName" value="' + escapeHtml(m.metric) + '" required class="w-full bg-surface border border-outline-variant rounded-lg px-3 py-2 text-body-md focus:ring-2 focus:ring-primary/20" /></div>' +
      '<div class="flex flex-col gap-xs"><label class="font-label-sm text-label-sm font-bold text-on-surface-variant uppercase">Category</label><select id="metricFormCategory" class="w-full bg-surface border border-outline-variant rounded-lg px-3 py-2 text-body-md focus:ring-2 focus:ring-primary/20">' + catOpts + '</select></div>' +
      '<div class="flex flex-col gap-xs"><label class="font-label-sm text-label-sm font-bold text-on-surface-variant uppercase">Value</label><input id="metricFormValue" type="number" value="' + (m.value || 0) + '" required class="w-full bg-surface border border-outline-variant rounded-lg px-3 py-2 text-body-md focus:ring-2 focus:ring-primary/20" /></div>' +
      '<div class="flex flex-col gap-xs"><label class="font-label-sm text-label-sm font-bold text-on-surface-variant uppercase">Unit</label><input id="metricFormUnit" value="' + escapeHtml(m.unit || '') + '" class="w-full bg-surface border border-outline-variant rounded-lg px-3 py-2 text-body-md focus:ring-2 focus:ring-primary/20" /></div>' +
      '<div class="flex flex-col gap-xs"><label class="font-label-sm text-label-sm font-bold text-on-surface-variant uppercase">Trend</label><select id="metricFormTrend" class="w-full bg-surface border border-outline-variant rounded-lg px-3 py-2 text-body-md focus:ring-2 focus:ring-primary/20">' + trendOpts + '</select></div>' +
      '</div>' +
      '<div class="flex gap-sm mt-lg"><button type="submit" class="bg-primary text-on-primary px-lg py-sm rounded-lg font-label-md press-effect">Save</button>' +
      '<button type="button" class="bg-surface border border-outline-variant text-on-surface-variant px-lg py-sm rounded-lg font-label-md press-effect" onclick="controllers.operational.render()">Cancel</button></div>' +
      '</form></div>'
  },
  async saveForm() {
    var id = document.getElementById('metricFormId').value
    var payload = {
      metric: document.getElementById('metricFormName').value,
      category: document.getElementById('metricFormCategory').value,
      value: parseFloat(document.getElementById('metricFormValue').value) || 0,
      unit: document.getElementById('metricFormUnit').value,
      trend: document.getElementById('metricFormTrend').value
    }
    try {
      if (id) { await window.operationalAnalyticsService.update(id, payload) } else { await window.operationalAnalyticsService.create(payload) }
      app.toast('Metric saved', 'success')
      document.getElementById('content').innerHTML = this.render()
    } catch (e) { app.toast('Error saving metric: ' + e.message, 'error') }
    return false
  },
  async deleteItem(id) {
    if (!confirm('Delete this metric?')) return
    try { await window.operationalAnalyticsService.remove(id); app.toast('Metric deleted', 'success'); document.getElementById('content').innerHTML = this.render() } catch (e) { app.toast('Error deleting: ' + e.message, 'error') }
  }
}
