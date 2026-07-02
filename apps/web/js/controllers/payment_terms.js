window.NovaModules = window.NovaModules || {}; window.NovaModules['payment_terms'] = {
  render() {
    var search = this.searchTerm || ''
    var items = window.paymentTermService.getAll()
    var filtered = search ? items.filter(function(p) { return p.name.toLowerCase().indexOf(search) > -1 || (p.code || '').toLowerCase().indexOf(search) > -1 }) : items
    var rows = filtered.map(function(p) {
      var activeBadge = p.isActive ? 'bg-secondary/10 text-secondary border border-secondary/20' : 'bg-surface-variant/50 text-on-surface-variant border border-outline-variant'
      var activeLabel = p.isActive ? 'Active' : 'Inactive'
      var defaultBadge = p.isDefault ? ' <span class="bg-primary/10 text-primary border border-primary/20 text-[10px] px-1.5 py-0.5 rounded font-bold">DEFAULT</span>' : ''
      return '<tr class="hover:bg-primary/5 transition-colors group">' +
        '<td class="px-lg py-md font-semibold text-on-surface">' + escapeHtml(p.name) + defaultBadge + '</td>' +
        '<td class="px-lg py-md font-data-mono text-data-mono font-bold text-primary">' + escapeHtml(p.code) + '</td>' +
        '<td class="px-lg py-md font-body-md">' + escapeHtml(String(p.dueDays)) + ' days</td>' +
        '<td class="px-lg py-md font-body-md">' + (p.discountPercentage > 0 ? escapeHtml(String(p.discountPercentage)) + '% / ' + escapeHtml(String(p.discountDays)) + 'd' : '-') + '</td>' +
        '<td class="px-lg py-md"><span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-[11px] font-bold uppercase ' + activeBadge + '">' + activeLabel + '</span></td>' +
        '<td class="px-lg py-md text-right opacity-0 group-hover:opacity-100 transition-opacity">' +
        '<button class="p-1 hover:bg-surface-variant rounded-full text-primary" onclick="controllers.payment_terms.showEditForm(' + p.id + ')"><span class="material-symbols-outlined text-[20px]">edit</span></button>' +
        '<button class="p-1 hover:bg-surface-variant rounded-full text-on-surface-variant" onclick="controllers.payment_terms.toggleActive(' + p.id + ')"><span class="material-symbols-outlined text-[20px]">' + (p.isActive ? 'toggle_off' : 'toggle_on') + '</span></button>' +
        '<button class="p-1 hover:bg-surface-variant rounded-full text-primary" onclick="controllers.payment_terms.toggleDefault(' + p.id + ')"><span class="material-symbols-outlined text-[20px]">' + (p.isDefault ? 'star' : 'star_outline') + '</span></button>' +
        '</td></tr>'
    }).join('')
    return renderHtml('screens/payment_terms', {
      rows: rows, count: filtered.length,
      total: items.length,
      active: items.filter(function(p) { return p.isActive }).length,
      defaultCount: items.filter(function(p) { return p.isDefault }).length
    })
  },
  mount() { controllers.payment_terms = this; var s = document.getElementById('paymentTermSearch'); if (s) s.value = this.searchTerm || '' },
  search(q) { this.searchTerm = q.toLowerCase(); document.getElementById('content').innerHTML = this.render() },
  refresh() { document.getElementById('content').innerHTML = this.render() },
  showCreateForm() {
    document.getElementById('content').innerHTML = renderHtml('screens/payment_terms_form', {
      title: 'New Payment Term', id: '', name: '', code: '', description: '', dueDays: '30', discountPercentage: '0', discountDays: '0', isDefault: ''
    })
  },
  showEditForm(id) {
    var p = window.paymentTermService.getById(id)
    if (!p) return
    document.getElementById('content').innerHTML = renderHtml('screens/payment_terms_form', {
      title: 'Edit Payment Term', id: p.id,
      name: escapeHtml(p.name), code: escapeHtml(p.code),
      description: escapeHtml(p.description || ''),
      dueDays: p.dueDays, discountPercentage: p.discountPercentage,
      discountDays: p.discountDays,
      isDefault: p.isDefault ? 'checked' : ''
    })
  },
  async saveForm() {
    var id = document.getElementById('paymentTermFormId').value
    var payload = {
      name: document.getElementById('paymentTermFormName').value,
      code: document.getElementById('paymentTermFormCode').value,
      description: document.getElementById('paymentTermFormDescription').value,
      dueDays: parseInt(document.getElementById('paymentTermFormDueDays').value) || 0,
      discountPercentage: parseFloat(document.getElementById('paymentTermFormDiscountPct').value) || 0,
      discountDays: parseInt(document.getElementById('paymentTermFormDiscountDays').value) || 0,
      isDefault: document.getElementById('paymentTermFormIsDefault').checked
    }
    try {
      if (id) { await window.paymentTermService.update(id, payload) }
      else { await window.paymentTermService.create(payload) }
      app.toast('Payment term saved', 'success')
      document.getElementById('content').innerHTML = this.render()
    } catch (e) { app.toast('Error: ' + e.message, 'error') }
    return false
  },
  async toggleActive(id) {
    try {
      await window.paymentTermService.toggleActive(id)
      document.getElementById('content').innerHTML = this.render()
    } catch (e) { app.toast('Error: ' + e.message, 'error') }
  },
  async toggleDefault(id) {
    try {
      await window.paymentTermService.toggleDefault(id)
      document.getElementById('content').innerHTML = this.render()
    } catch (e) { app.toast('Error: ' + e.message, 'error') }
  }
}
