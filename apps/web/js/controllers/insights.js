window.NovaModules = window.NovaModules || {}; window.NovaModules['insights'] = {
  render() {
    var search = this.searchTerm || ''
    var items = window.insightService.getAll()
    var filtered = search ? items.filter(function(i) { return (i.insight || '').toLowerCase().indexOf(search) > -1 || (i.category || '').toLowerCase().indexOf(search) > -1 || (i.status || '').toLowerCase().indexOf(search) > -1 }) : items
    var rows = filtered.map(function(i) {
      var statusBadge = i.status === 'Active' ? '<span class="px-sm py-xs bg-secondary/10 text-secondary rounded text-[11px] font-medium uppercase">Active</span>' : (i.status === 'Implemented' ? '<span class="px-sm py-xs bg-primary/10 text-primary rounded text-[11px] font-medium uppercase">Implemented</span>' : '<span class="px-sm py-xs bg-surface-container-highest text-on-surface-variant rounded text-[11px] font-medium uppercase">' + escapeHtml(i.status || 'Pending') + '</span>')
      var impactBadge = i.impact === 'High' ? '<span class="px-sm py-xs bg-error/10 text-error rounded text-[11px] font-medium uppercase">High</span>' : (i.impact === 'Medium' ? '<span class="px-sm py-xs bg-warning/10 text-warning rounded text-[11px] font-medium uppercase">Medium</span>' : '<span class="px-sm py-xs bg-secondary/10 text-secondary rounded text-[11px] font-medium uppercase">Low</span>')
      return '<tr class="hover:bg-primary/5 transition-colors group">' +
             '<td class="px-lg py-md font-body-md font-semibold text-on-surface">' + escapeHtml(i.insight) + '</td>' +
             '<td class="px-lg py-md text-body-md text-on-surface-variant">' + escapeHtml(i.category || '-') + '</td>' +
             '<td class="px-lg py-md text-center font-data-mono text-data-mono">' + (i.confidence || 0) + '%</td>' +
             '<td class="px-lg py-md text-center">' + impactBadge + '</td>' +
             '<td class="px-lg py-md text-center">' + statusBadge + '</td>' +
             '<td class="px-lg py-md text-center opacity-0 group-hover:opacity-100 transition-opacity">' +
             '<div class="flex items-center justify-center gap-1">' +
             '<button class="p-1 hover:bg-surface-variant rounded-full text-primary" onclick="controllers.insights.showEditForm(' + i.id + ')"><span class="material-symbols-outlined text-[20px]">edit</span></button>' +
             '<button class="p-1 hover:bg-error-container rounded-full text-error" onclick="controllers.insights.deleteItem(' + i.id + ')"><span class="material-symbols-outlined text-[20px]">delete</span></button>' +
             '</div></td></tr>'
    }).join('')
    var avgConfidence = filtered.length ? Math.round(filtered.reduce(function(s, i) { return s + (i.confidence || 0) }, 0) / filtered.length) : 0
    return renderHtml('screens/ai___insights', {
      insightRows: rows,
      activeInsights: window.insightService.getAll().filter(function(i) { return i.status === 'Active' }).length,
      recommendations: items.filter(function(i) { return i.category === 'Recommendation' }).length || Math.ceil(items.length / 2),
      accuracy: avgConfidence
    })
  },
  mount() { controllers.insights = this; var s = document.getElementById('insightSearch'); if (s) s.value = this.searchTerm || '' },
  search(q) { this.searchTerm = q.toLowerCase(); document.getElementById('content').innerHTML = this.render() },
  showCreateForm() {
    document.getElementById('content').innerHTML =
      '<div class="max-w-2xl mx-auto bg-surface-container-lowest border border-outline-variant rounded-xl p-lg shadow-sm">' +
      '<h3 class="font-title-md text-title-md font-bold mb-lg">New Insight</h3>' +
      '<form onsubmit="return controllers.insights.saveForm()">' +
      '<input type="hidden" id="insightFormId" value="" />' +
      '<div class="grid grid-cols-1 md:grid-cols-2 gap-md mb-md">' +
      '<div class="flex flex-col gap-xs"><label class="font-label-sm text-label-sm font-bold text-on-surface-variant uppercase">Insight</label><input id="insightFormName" required class="w-full bg-surface border border-outline-variant rounded-lg px-3 py-2 text-body-md focus:ring-2 focus:ring-primary/20" /></div>' +
      '<div class="flex flex-col gap-xs"><label class="font-label-sm text-label-sm font-bold text-on-surface-variant uppercase">Category</label><select id="insightFormCategory" class="w-full bg-surface border border-outline-variant rounded-lg px-3 py-2 text-body-md focus:ring-2 focus:ring-primary/20"><option value="Prediction">Prediction</option><option value="Recommendation">Recommendation</option><option value="Anomaly">Anomaly</option><option value="Trend">Trend</option></select></div>' +
      '<div class="flex flex-col gap-xs"><label class="font-label-sm text-label-sm font-bold text-on-surface-variant uppercase">Confidence (%)</label><input id="insightFormConfidence" type="number" value="75" class="w-full bg-surface border border-outline-variant rounded-lg px-3 py-2 text-body-md focus:ring-2 focus:ring-primary/20" /></div>' +
      '<div class="flex flex-col gap-xs"><label class="font-label-sm text-label-sm font-bold text-on-surface-variant uppercase">Impact</label><select id="insightFormImpact" class="w-full bg-surface border border-outline-variant rounded-lg px-3 py-2 text-body-md focus:ring-2 focus:ring-primary/20"><option value="High">High</option><option value="Medium">Medium</option><option value="Low">Low</option></select></div>' +
      '<div class="flex flex-col gap-xs"><label class="font-label-sm text-label-sm font-bold text-on-surface-variant uppercase">Status</label><select id="insightFormStatus" class="w-full bg-surface border border-outline-variant rounded-lg px-3 py-2 text-body-md focus:ring-2 focus:ring-primary/20"><option value="Pending">Pending</option><option value="Active">Active</option><option value="Implemented">Implemented</option><option value="Dismissed">Dismissed</option></select></div>' +
      '</div>' +
      '<div class="flex gap-sm mt-lg"><button type="submit" class="bg-primary text-on-primary px-lg py-sm rounded-lg font-label-md press-effect">Save</button>' +
      '<button type="button" class="bg-surface border border-outline-variant text-on-surface-variant px-lg py-sm rounded-lg font-label-md press-effect" onclick="controllers.insights.render()">Cancel</button></div>' +
      '</form></div>'
  },
  showEditForm(id) {
    var i = window.insightService.getById(id)
    if (!i) return
    var catOpts = ['Prediction', 'Recommendation', 'Anomaly', 'Trend'].map(function(t) { return '<option value="' + t + '"' + (t === i.category ? ' selected' : '') + '>' + t + '</option>' }).join('')
    var impactOpts = ['High', 'Medium', 'Low'].map(function(t) { return '<option value="' + t + '"' + (t === i.impact ? ' selected' : '') + '>' + t + '</option>' }).join('')
    var statusOpts = ['Pending', 'Active', 'Implemented', 'Dismissed'].map(function(s) { return '<option value="' + s + '"' + (s === i.status ? ' selected' : '') + '>' + s + '</option>' }).join('')
    document.getElementById('content').innerHTML =
      '<div class="max-w-2xl mx-auto bg-surface-container-lowest border border-outline-variant rounded-xl p-lg shadow-sm">' +
      '<h3 class="font-title-md text-title-md font-bold mb-lg">Edit Insight</h3>' +
      '<form onsubmit="return controllers.insights.saveForm()">' +
      '<input type="hidden" id="insightFormId" value="' + i.id + '" />' +
      '<div class="grid grid-cols-1 md:grid-cols-2 gap-md mb-md">' +
      '<div class="flex flex-col gap-xs"><label class="font-label-sm text-label-sm font-bold text-on-surface-variant uppercase">Insight</label><input id="insightFormName" value="' + escapeHtml(i.insight) + '" required class="w-full bg-surface border border-outline-variant rounded-lg px-3 py-2 text-body-md focus:ring-2 focus:ring-primary/20" /></div>' +
      '<div class="flex flex-col gap-xs"><label class="font-label-sm text-label-sm font-bold text-on-surface-variant uppercase">Category</label><select id="insightFormCategory" class="w-full bg-surface border border-outline-variant rounded-lg px-3 py-2 text-body-md focus:ring-2 focus:ring-primary/20">' + catOpts + '</select></div>' +
      '<div class="flex flex-col gap-xs"><label class="font-label-sm text-label-sm font-bold text-on-surface-variant uppercase">Confidence (%)</label><input id="insightFormConfidence" type="number" value="' + (i.confidence || 0) + '" class="w-full bg-surface border border-outline-variant rounded-lg px-3 py-2 text-body-md focus:ring-2 focus:ring-primary/20" /></div>' +
      '<div class="flex flex-col gap-xs"><label class="font-label-sm text-label-sm font-bold text-on-surface-variant uppercase">Impact</label><select id="insightFormImpact" class="w-full bg-surface border border-outline-variant rounded-lg px-3 py-2 text-body-md focus:ring-2 focus:ring-primary/20">' + impactOpts + '</select></div>' +
      '<div class="flex flex-col gap-xs"><label class="font-label-sm text-label-sm font-bold text-on-surface-variant uppercase">Status</label><select id="insightFormStatus" class="w-full bg-surface border border-outline-variant rounded-lg px-3 py-2 text-body-md focus:ring-2 focus:ring-primary/20">' + statusOpts + '</select></div>' +
      '</div>' +
      '<div class="flex gap-sm mt-lg"><button type="submit" class="bg-primary text-on-primary px-lg py-sm rounded-lg font-label-md press-effect">Save</button>' +
      '<button type="button" class="bg-surface border border-outline-variant text-on-surface-variant px-lg py-sm rounded-lg font-label-md press-effect" onclick="controllers.insights.render()">Cancel</button></div>' +
      '</form></div>'
  },
  async saveForm() {
    var id = document.getElementById('insightFormId').value
    var payload = {
      insight: document.getElementById('insightFormName').value,
      category: document.getElementById('insightFormCategory').value,
      confidence: parseInt(document.getElementById('insightFormConfidence').value) || 0,
      impact: document.getElementById('insightFormImpact').value,
      status: document.getElementById('insightFormStatus').value
    }
    try {
      if (id) { await window.insightService.update(id, payload) } else { await window.insightService.create(payload) }
      app.toast('Insight saved', 'success')
      document.getElementById('content').innerHTML = this.render()
    } catch (e) { app.toast('Error saving insight: ' + e.message, 'error') }
    return false
  },
  async deleteItem(id) {
    if (!confirm('Delete this insight?')) return
    try { await window.insightService.remove(id); app.toast('Insight deleted', 'success'); document.getElementById('content').innerHTML = this.render() } catch (e) { app.toast('Error deleting: ' + e.message, 'error') }
  }
}
