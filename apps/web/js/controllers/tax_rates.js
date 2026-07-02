window.NovaModules = window.NovaModules || {}; window.NovaModules['tax_rates'] = {
  render() {
    var search = this.searchTerm || ''
    var items = window.taxRateService.getAll()
    var filtered = search ? items.filter(function(r) { return (r.name || '').toLowerCase().indexOf(search) > -1 || (r.code || '').toLowerCase().indexOf(search) > -1 }) : items
    var rows = filtered.map(function(r) {
      var isActive = r.isActive
      var badge = isActive ? 'bg-success/10 text-success border border-success/20' : 'bg-error/10 text-error border border-error/20'
      var defaultTag = r.isDefault ? '<span class="text-[10px] ml-1 bg-primary/10 text-primary px-1.5 py-0.5 rounded-full font-bold uppercase">Default</span>' : ''
      return '<tr class="hover:bg-primary/5 transition-colors group">' +
        '<td class="px-lg py-md font-body-md font-medium">' + escapeHtml(r.name) + defaultTag + '</td>' +
        '<td class="px-lg py-md font-data-mono text-data-mono text-primary font-bold">' + escapeHtml(r.code) + '</td>' +
        '<td class="px-lg py-md font-data-mono text-data-mono">' + escapeHtml(String(r.rate)) + '%</td>' +
        '<td class="px-lg py-md font-body-md text-on-surface-variant">' + escapeHtml(r.type) + '</td>' +
        '<td class="px-lg py-md"><span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-[11px] font-bold uppercase ' + badge + '">' + (isActive ? 'Active' : 'Inactive') + '</span></td>' +
        '<td class="px-lg py-md text-right opacity-0 group-hover:opacity-100 transition-opacity">' +
        '<button class="p-1 hover:bg-surface-variant rounded-full text-primary" onclick="controllers.tax_rates.showEditForm(' + r.id + ')"><span class="material-symbols-outlined text-[20px]">edit</span></button>' +
        '<button class="p-1 hover:bg-error-container rounded-full text-error" onclick="controllers.tax_rates.toggleActive(' + r.id + ')"><span class="material-symbols-outlined text-[20px]">' + (isActive ? 'toggle_off' : 'toggle_on') + '</span></button>' +
        '</td></tr>'
    }).join('')
    return renderHtml('screens/tax_rates', { rows: rows, count: filtered.length, activeCount: window.taxRateService.getActiveCount(), defaultCount: window.taxRateService.getDefaultCount() })
  },
  mount() { controllers.tax_rates = this; var s = document.getElementById('txrSearch'); if (s) s.value = this.searchTerm || '' },
  async refresh() { await window.taxRateService.load(); document.getElementById('content').innerHTML = this.render() },
  search(q) { this.searchTerm = q.toLowerCase(); document.getElementById('content').innerHTML = this.render() },
  showCreateForm() {
    document.getElementById('content').innerHTML = renderHtml('screens/tax_rates_form', { title: 'New Tax Rate', id: '', name: '', code: '', rate: '', type: 'Sales', isDefault: '', description: '' })
  },
  showEditForm(id) {
    var r = window.taxRateService.getById(id)
    if (!r) return
    document.getElementById('content').innerHTML = renderHtml('screens/tax_rates_form', {
      title: 'Edit Tax Rate', id: r.id, name: escapeHtml(r.name), code: escapeHtml(r.code),
      rate: r.rate, type: r.type, isDefault: r.isDefault ? 'checked' : '', description: escapeHtml(r.description || '')
    })
  },
  async saveForm() {
    var id = document.getElementById('txrFormId').value
    var payload = {
      name: document.getElementById('txrFormName').value,
      code: document.getElementById('txrFormCode').value,
      rate: parseFloat(document.getElementById('txrFormRate').value) || 0,
      type: document.getElementById('txrFormType').value,
      isDefault: document.getElementById('txrFormDefault').checked,
      description: document.getElementById('txrFormDesc').value || null
    }
    if (!payload.name) { app.toast('Name is required', 'error'); return false }
    if (!payload.code) { app.toast('Code is required', 'error'); return false }
    try {
      if (id) { await window.taxRateService.update(id, payload) }
      else { await window.taxRateService.create(payload) }
      app.toast('Tax rate saved', 'success')
      document.getElementById('content').innerHTML = this.render()
    } catch (e) { app.toast('Error: ' + e.message, 'error') }
    return false
  },
  async toggleActive(id) {
    var r = window.taxRateService.getById(id)
    if (!r) return
    try {
      await window.taxRateService.update(id, { isActive: !r.isActive })
      app.toast('Tax rate ' + (!r.isActive ? 'activated' : 'deactivated'), 'success')
      document.getElementById('content').innerHTML = this.render()
    } catch (e) { app.toast('Error: ' + e.message, 'error') }
  }
}
