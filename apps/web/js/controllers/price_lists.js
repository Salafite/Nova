window.NovaModules = window.NovaModules || {}; window.NovaModules['price_lists'] = {
  render() {
    var search = this.searchTerm || ''
    var items = window.priceListService.getAll()
    var filtered = search ? items.filter(function(p) { return p.name.toLowerCase().indexOf(search) > -1 || (p.code || '').toLowerCase().indexOf(search) > -1 }) : items
    var rows = filtered.map(function(p) {
      var activeBadge = p.isActive ? 'bg-secondary/10 text-secondary border border-secondary/20' : 'bg-surface-variant/50 text-on-surface-variant border border-outline-variant'
      var activeLabel = p.isActive ? 'Active' : 'Inactive'
      var defaultBadge = p.isDefault ? ' <span class="bg-primary/10 text-primary border border-primary/20 text-[10px] px-1.5 py-0.5 rounded font-bold">DEFAULT</span>' : ''
      return '<tr class="hover:bg-primary/5 transition-colors group">' +
        '<td class="px-lg py-md font-semibold text-on-surface">' + escapeHtml(p.name) + defaultBadge + '</td>' +
        '<td class="px-lg py-md font-data-mono text-data-mono font-bold text-primary">' + escapeHtml(p.code) + '</td>' +
        '<td class="px-lg py-md font-body-md">' + escapeHtml(p.currency || 'USD') + '</td>' +
        '<td class="px-lg py-md"><span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-[11px] font-bold uppercase ' + activeBadge + '">' + activeLabel + '</span></td>' +
        '<td class="px-lg py-md text-right opacity-0 group-hover:opacity-100 transition-opacity">' +
        '<button class="p-1 hover:bg-surface-variant rounded-full text-primary" onclick="controllers.price_lists.showEditForm(' + p.id + ')"><span class="material-symbols-outlined text-[20px]">edit</span></button>' +
        '<button class="p-1 hover:bg-surface-variant rounded-full text-on-surface-variant" onclick="controllers.price_lists.toggleActive(' + p.id + ')"><span class="material-symbols-outlined text-[20px]">' + (p.isActive ? 'toggle_off' : 'toggle_on') + '</span></button>' +
        '</td></tr>'
    }).join('')
    return renderHtml('screens/price_lists', {
      rows: rows, count: filtered.length,
      total: items.length,
      active: items.filter(function(p) { return p.isActive }).length,
      defaultCount: items.filter(function(p) { return p.isDefault }).length
    })
  },
  mount() { controllers.price_lists = this; var s = document.getElementById('priceListSearch'); if (s) s.value = this.searchTerm || '' },
  search(q) { this.searchTerm = q.toLowerCase(); document.getElementById('content').innerHTML = this.render() },
  refresh() { this.render(); document.getElementById('content').innerHTML = this.render() },
  showCreateForm() {
    document.getElementById('content').innerHTML = renderHtml('screens/price_lists_form', {
      title: 'New Price List', id: '', name: '', code: '', description: '', currency: 'USD', isDefault: ''
    })
  },
  showEditForm(id) {
    var p = window.priceListService.getById(id)
    if (!p) return
    document.getElementById('content').innerHTML = renderHtml('screens/price_lists_form', {
      title: 'Edit Price List', id: p.id,
      name: escapeHtml(p.name), code: escapeHtml(p.code),
      description: escapeHtml(p.description || ''),
      currency: p.currency || 'USD',
      isDefault: p.isDefault ? 'checked' : ''
    })
  },
  async saveForm() {
    var id = document.getElementById('priceListFormId').value
    var payload = {
      name: document.getElementById('priceListFormName').value,
      code: document.getElementById('priceListFormCode').value,
      description: document.getElementById('priceListFormDescription').value,
      currency: document.getElementById('priceListFormCurrency').value,
      isDefault: document.getElementById('priceListFormIsDefault').checked
    }
    try {
      if (id) { await window.priceListService.update(id, payload) }
      else { await window.priceListService.create(payload) }
      app.toast('Price list saved', 'success')
      document.getElementById('content').innerHTML = this.render()
    } catch (e) { app.toast('Error: ' + e.message, 'error') }
    return false
  },
  async toggleActive(id) {
    try {
      await window.priceListService.toggleActive(id)
      document.getElementById('content').innerHTML = this.render()
    } catch (e) { app.toast('Error: ' + e.message, 'error') }
  }
}
