window.NovaModules = window.NovaModules || {}; window.NovaModules['tenant'] = {
  render() {
    var search = this.searchTerm || ''
    var items = window.tenantService.getAll()
    var filtered = search ? items.filter(function(t) { return (t.name || '').toLowerCase().indexOf(search) > -1 || (t.domain || '').toLowerCase().indexOf(search) > -1 }) : items
    var rows = filtered.map(function(t) {
      var planBadge = t.plan === 'Enterprise' ? '<span class="px-sm py-xs bg-primary-container text-primary rounded text-[11px] font-bold uppercase">Enterprise</span>' : (t.plan === 'Professional' ? '<span class="px-sm py-xs bg-secondary-container text-on-secondary-container rounded text-[11px] font-bold uppercase">Professional</span>' : '<span class="px-sm py-xs bg-surface-container-high text-on-surface-variant rounded text-[11px] font-bold uppercase">' + escapeHtml(t.plan || 'Free') + '</span>')
      var statusBadge = t.status === 'Active' ? '<span class="px-sm py-xs bg-secondary-container text-on-secondary-container rounded text-[11px] font-bold uppercase">Active</span>' : '<span class="px-sm py-xs bg-surface-container-high text-on-surface-variant rounded text-[11px] font-bold uppercase">' + escapeHtml(t.status || 'Inactive') + '</span>'
      return '<tr class="hover:bg-primary/5 transition-colors group">' +
             '<td class="px-lg py-md font-body-md font-semibold text-primary">' + escapeHtml(t.name) + '</td>' +
             '<td class="px-lg py-md text-body-md text-on-surface-variant font-data-mono">' + escapeHtml(t.domain || '-') + '</td>' +
             '<td class="px-lg py-md">' + planBadge + '</td>' +
             '<td class="px-lg py-md">' + statusBadge + '</td>' +
             '<td class="px-lg py-md text-body-md font-data-mono">' + (t.usersCount || 0) + '</td>' +
             '<td class="px-lg py-md text-body-md text-on-surface-variant">' + escapeHtml(t.createdAt || '-') + '</td>' +
             '</tr>'
    }).join('')
    return renderHtml('screens/multi_tenant_architecture', {
      tenantRows: rows,
      totalTenants: items.length,
      activeTenants: window.tenantService.getActiveCount(),
      totalUsers: items.reduce(function(s, t) { return s + (t.usersCount || 0) }, 0)
    })
  },
  mount() { controllers.tenant = this; var s = document.getElementById('tenantSearch'); if (s) s.value = this.searchTerm || '' },
  search(q) { this.searchTerm = q.toLowerCase(); document.getElementById('content').innerHTML = this.render() },
  showCreateForm() {
    document.getElementById('content').innerHTML = renderHtml('models/product/form', {
      title: 'New Tenant', id: '', name: '', domain: '', plan: 'Free', status: 'Active'
    })
  },
  async saveForm() {
    try {
      await window.tenantService.create({
        name: document.getElementById('inspectionFormProduct') ? document.getElementById('inspectionFormProduct').value : 'New Tenant',
        domain: '',
        plan: 'Free',
        status: 'Active'
      })
      app.toast('Tenant created', 'success')
      document.getElementById('content').innerHTML = this.render()
    } catch (e) {
      app.toast('Error creating tenant: ' + e.message, 'error')
    }
    return false
  },
  async deleteItem(id) {
    if (!confirm('Delete this tenant?')) return
    try {
      await window.tenantService.remove(id)
      document.getElementById('content').innerHTML = this.render()
    } catch (e) {
      app.toast('Error deleting tenant: ' + e.message, 'error')
    }
  }
}
