window.NovaModules = window.NovaModules || {}; window.NovaModules['governance'] = {
  render() {
    var search = this.searchTerm || ''
    var items = window.complianceService.getAll()
    var filtered = search ? items.filter(function(r) { return (r.name || '').toLowerCase().indexOf(search) > -1 || (r.category || '').toLowerCase().indexOf(search) > -1 }) : items
    var rows = filtered.map(function(r) {
      var statusBadge = r.status === 'Active' ? '<span class="px-sm py-xs bg-secondary-container text-on-secondary-container rounded text-[11px] font-bold uppercase">Active</span>' : '<span class="px-sm py-xs bg-surface-container-high text-on-surface-variant rounded text-[11px] font-bold uppercase">' + escapeHtml(r.status || 'Inactive') + '</span>'
      var riskBadge = r.riskLevel === 'High' || r.riskLevel === 'Critical' ? '<span class="px-sm py-xs bg-error-container text-error rounded text-[11px] font-bold uppercase">' + escapeHtml(r.riskLevel) + '</span>' : (r.riskLevel === 'Medium' ? '<span class="px-sm py-xs bg-surface-container-highest text-secondary rounded text-[11px] font-bold uppercase">Medium</span>' : '<span class="px-sm py-xs bg-surface-container-high text-on-surface-variant rounded text-[11px] font-bold uppercase">' + escapeHtml(r.riskLevel || 'Low') + '</span>')
      return '<tr class="hover:bg-primary/5 transition-colors group">' +
             '<td class="px-lg py-md font-body-md font-semibold text-primary">' + escapeHtml(r.name) + '</td>' +
             '<td class="px-lg py-md text-body-md text-on-surface-variant">' + escapeHtml(r.category || '-') + '</td>' +
             '<td class="px-lg py-md">' + statusBadge + '</td>' +
             '<td class="px-lg py-md text-body-md text-on-surface-variant">' + escapeHtml(r.lastAuditAt || '-') + '</td>' +
             '<td class="px-lg py-md">' + riskBadge + '</td>' +
             '</tr>'
    }).join('')
    return renderHtml('screens/enterprise_governance', {
      ruleRows: rows,
      totalRules: items.length,
      activeRules: window.complianceService.getActiveCount(),
      highRiskRules: window.complianceService.getHighRiskCount()
    })
  },
  mount() { controllers.governance = this; var s = document.getElementById('ruleSearch'); if (s) s.value = this.searchTerm || '' },
  search(q) { this.searchTerm = q.toLowerCase(); document.getElementById('content').innerHTML = this.render() },
  showCreateForm() {
    document.getElementById('content').innerHTML = renderHtml('models/product/form', {
      title: 'New Compliance Rule', id: '', name: '', category: 'Security', status: 'Active'
    })
  },
  async saveForm() {
    try {
      await window.complianceService.create({
        name: document.getElementById('inspectionFormProduct') ? document.getElementById('inspectionFormProduct').value : 'New Rule',
        category: 'Security',
        status: 'Active',
        riskLevel: 'Low'
      })
      app.toast('Compliance rule created', 'success')
      document.getElementById('content').innerHTML = this.render()
    } catch (e) {
      app.toast('Error creating rule: ' + e.message, 'error')
    }
    return false
  },
  async deleteItem(id) {
    if (!confirm('Delete this compliance rule?')) return
    try {
      await window.complianceService.remove(id)
      document.getElementById('content').innerHTML = this.render()
    } catch (e) {
      app.toast('Error deleting rule: ' + e.message, 'error')
    }
  }
}
