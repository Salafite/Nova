window.NovaModules = window.NovaModules || {}; window.NovaModules['chart_of_accounts'] = {
  render() {
    var search = this.searchTerm || ''
    var items = window.chartOfAccountService.getAll()
    var filtered = search ? items.filter(function(p) { return p.accountCode.toLowerCase().indexOf(search) > -1 || p.accountName.toLowerCase().indexOf(search) > -1 }) : items
    var rows = filtered.map(function(p) {
      var activeBadge = p.isActive ? 'bg-secondary/10 text-secondary border border-secondary/20' : 'bg-surface-variant/50 text-on-surface-variant border border-outline-variant'
      var activeLabel = p.isActive ? 'Active' : 'Inactive'
      return '<tr class="hover:bg-primary/5 transition-colors group">' +
        '<td class="px-lg py-md font-data-mono text-data-mono font-bold text-primary">' + escapeHtml(p.accountCode) + '</td>' +
        '<td class="px-lg py-md font-semibold text-on-surface">' + escapeHtml(p.accountName) + '</td>' +
        '<td class="px-lg py-md font-body-md">' + escapeHtml(p.accountType) + '</td>' +
        '<td class="px-lg py-md font-body-md">' + escapeHtml(p.currency || 'USD') + '</td>' +
        '<td class="px-lg py-md"><span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-[11px] font-bold uppercase ' + activeBadge + '">' + activeLabel + '</span></td>' +
        '<td class="px-lg py-md text-right opacity-0 group-hover:opacity-100 transition-opacity">' +
        '<button class="p-1 hover:bg-surface-variant rounded-full text-primary" onclick="controllers.chart_of_accounts.showEditForm(' + p.id + ')"><span class="material-symbols-outlined text-[20px]">edit</span></button>' +
        '<button class="p-1 hover:bg-surface-variant rounded-full text-on-surface-variant" onclick="controllers.chart_of_accounts.toggleActive(' + p.id + ')"><span class="material-symbols-outlined text-[20px]">' + (p.isActive ? 'toggle_off' : 'toggle_on') + '</span></button>' +
        '</td></tr>'
    }).join('')
    var byType = {}
    items.forEach(function(p) { byType[p.accountType] = (byType[p.accountType] || 0) + 1 })
    return renderHtml('screens/chart_of_accounts', {
      rows: rows, count: filtered.length,
      total: items.length,
      active: items.filter(function(p) { return p.isActive }).length,
      assetCount: byType['Asset'] || 0,
      liabilityCount: byType['Liability'] || 0,
      equityCount: byType['Equity'] || 0,
      revenueCount: byType['Revenue'] || 0,
      expenseCount: byType['Expense'] || 0
    })
  },
  mount() { controllers.chart_of_accounts = this; var s = document.getElementById('coaSearch'); if (s) s.value = this.searchTerm || '' },
  search(q) { this.searchTerm = q.toLowerCase(); document.getElementById('content').innerHTML = this.render() },
  refresh() { this.render(); document.getElementById('content').innerHTML = this.render() },
  makeTypeSelected(type) {
    var types = ['Asset','Liability','Equity','Revenue','Expense']
    var result = {}
    types.forEach(function(t) { result['accountTypeSelected_' + t] = t === type ? 'selected' : '' })
    return result
  },
  showCreateForm() {
    document.getElementById('content').innerHTML = renderHtml('screens/chart_of_accounts_form', Object.assign({
      title: 'New Account', id: '', accountCode: '', accountName: '', accountType: '', currency: 'USD', isActive: 'checked'
    }, this.makeTypeSelected('')))
  },
  showEditForm(id) {
    var p = window.chartOfAccountService.getById(id)
    if (!p) return
    document.getElementById('content').innerHTML = renderHtml('screens/chart_of_accounts_form', Object.assign({
      title: 'Edit Account', id: p.id,
      accountCode: escapeHtml(p.accountCode), accountName: escapeHtml(p.accountName),
      accountType: p.accountType || '',
      currency: p.currency || 'USD',
      isActive: p.isActive ? 'checked' : ''
    }, this.makeTypeSelected(p.accountType)))
  },
  async saveForm() {
    var id = document.getElementById('coaFormId').value
    var payload = {
      accountCode: document.getElementById('coaFormCode').value,
      accountName: document.getElementById('coaFormName').value,
      accountType: document.getElementById('coaFormType').value,
      currency: document.getElementById('coaFormCurrency').value,
      isActive: document.getElementById('coaFormIsActive').checked
    }
    try {
      if (id) { await window.chartOfAccountService.update(id, payload) }
      else { await window.chartOfAccountService.create(payload) }
      app.toast('Account saved', 'success')
      document.getElementById('content').innerHTML = this.render()
    } catch (e) { app.toast('Error: ' + e.message, 'error') }
    return false
  },
  async toggleActive(id) {
    try {
      await window.chartOfAccountService.toggleActive(id)
      document.getElementById('content').innerHTML = this.render()
    } catch (e) { app.toast('Error: ' + e.message, 'error') }
  }
}
