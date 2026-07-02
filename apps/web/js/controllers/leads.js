window.NovaModules = window.NovaModules || {}; window.NovaModules['leads'] = {
  render() {
    var search = this.searchTerm || ''
    var list = window.leadService.getAll()
    var filtered = search ? list.filter(function(l) {
      var q = search.toLowerCase()
      return (l.firstName || '').toLowerCase().indexOf(q) > -1 || (l.lastName || '').toLowerCase().indexOf(q) > -1 || (l.email || '').toLowerCase().indexOf(q) > -1 || (l.company || '').toLowerCase().indexOf(q) > -1
    }) : list

    var total = list.length
    var newCount = list.filter(function(l) { return l.status === 'New' }).length
    var qualified = list.filter(function(l) { return l.status === 'Qualified' }).length
    var converted = list.filter(function(l) { return l.status === 'Converted' }).length

    var rows = filtered.map(function(l) {
      var name = escapeHtml(l.firstName || '') + ' ' + escapeHtml(l.lastName || '')
      var badgeMap = { 'New': 'primary', 'Contacted': 'warning', 'Qualified': 'success', 'Disqualified': 'error', 'Converted': 'secondary' }
      var badgeColor = badgeMap[l.status] || 'primary'
      return '<tr class="hover:bg-primary-container/5 transition-colors group cursor-pointer">' +
        '<td class="p-md"><div class="font-title-md text-title-md text-on-surface">' + name + '</div></td>' +
        '<td class="p-md text-body-md text-on-surface-variant">' + escapeHtml(l.email || '-') + '</td>' +
        '<td class="p-md text-body-md text-on-surface-variant">' + escapeHtml(l.company || '-') + '</td>' +
        '<td class="p-md"><span class="text-xs text-on-surface-variant">' + escapeHtml(l.source || '-') + '</span></td>' +
        '<td class="p-md"><span class="px-sm py-1 rounded text-xs font-medium bg-' + badgeColor + '-container text-on-' + badgeColor + '-container">' + escapeHtml(l.status) + '</span></td>' +
        '<td class="p-md text-center opacity-0 group-hover:opacity-100 transition-opacity">' +
        '<div class="flex items-center justify-end gap-1">' +
        (l.status === 'New' || l.status === 'Contacted' ? '<button class="p-1 hover:bg-surface-variant rounded-full text-success" onclick="controllers.leads.qualify(' + l.id + ')"><span class="material-symbols-outlined text-[18px]">check_circle</span></button>' : '') +
        (l.status !== 'Converted' && l.status !== 'Disqualified' ? '<button class="p-1 hover:bg-surface-variant rounded-full text-error" onclick="controllers.leads.disqualify(' + l.id + ')"><span class="material-symbols-outlined text-[18px]">cancel</span></button>' : '') +
        '<button class="p-1 hover:bg-surface-variant rounded-full text-primary" onclick="controllers.leads.showEditForm(' + l.id + ')"><span class="material-symbols-outlined text-[18px]">edit</span></button>' +
        '</div></td></tr>'
    }).join('')

    return renderHtml('screens/leads', {
      rows: rows, count: filtered.length,
      total: total, newCount: newCount, qualified: qualified, converted: converted
    })
  },
  mount() { controllers.leads = this; var s = document.getElementById('leadSearch'); if (s) s.value = this.searchTerm || '' },
  search(q) { this.searchTerm = q.toLowerCase(); document.getElementById('content').innerHTML = this.render() },
  showCreateForm() {
    document.getElementById('content').innerHTML = renderHtml('screens/leads_form', {
      title: 'Add Lead', id: '', firstName: '', lastName: '', email: '', phone: '', company: '', title: '', source: 'Website', status: 'New', notes: ''
    })
  },
  showEditForm(id) {
    var l = window.leadService.getById(id)
    if (!l) return
    document.getElementById('content').innerHTML = renderHtml('screens/leads_form', {
      title: 'Edit Lead', id: l.id,
      firstName: escapeHtml(l.firstName || ''), lastName: escapeHtml(l.lastName || ''),
      email: escapeHtml(l.email || ''), phone: escapeHtml(l.phone || ''),
      company: escapeHtml(l.company || ''), title: escapeHtml(l.title || ''),
      source: l.source || 'Website', status: l.status || 'New',
      notes: escapeHtml(l.notes || '')
    })
  },
  async saveForm() {
    var id = document.getElementById('leadFormId').value
    var data = {
      firstName: document.getElementById('leadFormFirstName').value,
      lastName: document.getElementById('leadFormLastName').value,
      email: document.getElementById('leadFormEmail').value,
      phone: document.getElementById('leadFormPhone').value,
      company: document.getElementById('leadFormCompany').value,
      title: document.getElementById('leadFormTitle').value,
      source: document.getElementById('leadFormSource').value,
      status: document.getElementById('leadFormStatus').value,
      notes: document.getElementById('leadFormNotes').value
    }
    try {
      if (id) { await window.leadService.update(data) } else { await window.leadService.add(data) }
      document.getElementById('content').innerHTML = this.render()
    } catch (e) { app.toast('Error: ' + e.message, 'error') }
    return false
  },
  async qualify(id) {
    try { await window.leadService.qualify(id); document.getElementById('content').innerHTML = this.render() }
    catch (e) { app.toast(e.message, 'error') }
  },
  async disqualify(id) {
    try { await window.leadService.disqualify(id); document.getElementById('content').innerHTML = this.render() }
    catch (e) { app.toast(e.message, 'error') }
  }
}
