window.NovaModules = window.NovaModules || {}; window.NovaModules['opportunities'] = {
  render() {
    var search = this.searchTerm || ''
    var list = window.opportunityService.getAll()
    var filtered = search ? list.filter(function(o) {
      var q = search.toLowerCase()
      return (o.opportunityName || '').toLowerCase().indexOf(q) > -1
    }) : list

    var total = list.length
    var prospecting = list.filter(function(o) { return o.stage === 'Prospecting' }).length
    var won = list.filter(function(o) { return o.stage === 'Closed Won' }).length
    var lost = list.filter(function(o) { return o.stage === 'Closed Lost' }).length
    var pipeline = total - won - lost

    var badgeMap = { 'Prospecting': 'gray', 'Qualification': 'warning', 'Needs Analysis': 'primary', 'Proposal': 'info', 'Negotiation': 'secondary', 'Closed Won': 'success', 'Closed Lost': 'error' }

    var rows = filtered.map(function(o) {
      var badgeColor = badgeMap[o.stage] || 'gray'
      var expRev = (o.amount || 0) * (o.probability || 0) / 100
      return '<tr class="hover:bg-primary-container/5 transition-colors group cursor-pointer">' +
        '<td class="p-md"><div class="font-title-md text-title-md text-on-surface">' + escapeHtml(o.opportunityName) + '</div></td>' +
        '<td class="p-md"><span class="px-sm py-1 rounded text-xs font-medium bg-' + badgeColor + '-container text-on-' + badgeColor + '-container">' + escapeHtml(o.stage) + '</span></td>' +
        '<td class="p-md text-right font-data-mono text-data-mono">$' + (o.amount || 0).toFixed(2) + '</td>' +
        '<td class="p-md text-center font-data-mono text-data-mono">' + (o.probability || 0) + '%</td>' +
        '<td class="p-md text-right font-data-mono text-data-mono text-secondary">$' + expRev.toFixed(2) + '</td>' +
        '<td class="p-md text-center opacity-0 group-hover:opacity-100 transition-opacity">' +
        '<div class="flex items-center justify-end gap-1">' +
        '<button class="p-1 hover:bg-surface-variant rounded-full text-primary" onclick="controllers.opportunities.showEditForm(' + o.id + ')"><span class="material-symbols-outlined text-[18px]">edit</span></button>' +
        '</div></td></tr>'
    }).join('')

    return renderHtml('screens/opportunities', {
      rows: rows, count: filtered.length,
      total: total, prospecting: prospecting, won: won, lost: lost, pipeline: pipeline
    })
  },
  mount() { controllers.opportunities = this; var s = document.getElementById('opportunitySearch'); if (s) s.value = this.searchTerm || '' },
  search(q) { this.searchTerm = q.toLowerCase(); document.getElementById('content').innerHTML = this.render() },
  showCreateForm() {
    document.getElementById('content').innerHTML = renderHtml('screens/opportunities_form', {
      title: 'Add Opportunity', id: '', opportunityName: '', stage: 'Prospecting', amount: '0', probability: '10', expectedCloseDate: '', notes: ''
    })
  },
  showEditForm(id) {
    var o = window.opportunityService.getById(id)
    if (!o) return
    document.getElementById('content').innerHTML = renderHtml('screens/opportunities_form', {
      title: 'Edit Opportunity', id: o.id,
      opportunityName: escapeHtml(o.opportunityName || ''),
      stage: o.stage || 'Prospecting',
      amount: o.amount || '0',
      probability: o.probability || '10',
      expectedCloseDate: o.expectedCloseDate || '',
      notes: escapeHtml(o.notes || '')
    })
  },
  async saveForm() {
    var id = document.getElementById('opportunityFormId').value
    var data = {
      opportunityName: document.getElementById('opportunityFormName').value,
      stage: document.getElementById('opportunityFormStage').value,
      amount: parseFloat(document.getElementById('opportunityFormAmount').value) || 0,
      probability: parseInt(document.getElementById('opportunityFormProbability').value) || 10,
      expectedCloseDate: document.getElementById('opportunityFormCloseDate').value || null,
      notes: document.getElementById('opportunityFormNotes').value
    }
    try {
      if (id) { await window.opportunityService.update(data) } else { await window.opportunityService.add(data) }
      document.getElementById('content').innerHTML = this.render()
    } catch (e) { app.toast('Error: ' + e.message, 'error') }
    return false
  }
}
