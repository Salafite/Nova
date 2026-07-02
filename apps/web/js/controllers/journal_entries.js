window.NovaModules = window.NovaModules || {}; window.NovaModules['journal_entries'] = {
  render() {
    var search = this.searchTerm || ''
    var items = window.journalEntryService.getAll()
    var filtered = search ? items.filter(function(p) { return p.reference.toLowerCase().indexOf(search) > -1 || p.description.toLowerCase().indexOf(search) > -1 }) : items
    var rows = filtered.map(function(p) {
      var statusBadge = p.status === 'Posted' ? 'bg-success/10 text-success border border-success/20' : p.status === 'Cancelled' ? 'bg-error/10 text-error border border-error/20' : 'bg-surface-variant/50 text-on-surface-variant border border-outline-variant'
      var actions = ''
      if (p.status === 'Draft') {
        actions = '<button class="p-1 hover:bg-surface-variant rounded-full text-primary" onclick="controllers.journal_entries.showEditForm(' + p.id + ')"><span class="material-symbols-outlined text-[20px]">edit</span></button>' +
          '<button class="p-1 hover:bg-surface-variant rounded-full text-success" onclick="controllers.journal_entries.postJE(' + p.id + ')"><span class="material-symbols-outlined text-[20px]">check_circle</span></button>'
      }
      return '<tr class="hover:bg-primary/5 transition-colors group">' +
        '<td class="px-lg py-md font-data-mono text-data-mono font-bold text-primary">' + escapeHtml(p.reference) + '</td>' +
        '<td class="px-lg py-md font-body-md">' + escapeHtml(p.entryDate) + '</td>' +
        '<td class="px-lg py-md font-semibold text-on-surface">' + escapeHtml(p.description) + '</td>' +
        '<td class="px-lg py-md"><span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-[11px] font-bold uppercase ' + statusBadge + '">' + p.status + '</span></td>' +
        '<td class="px-lg py-md text-right opacity-0 group-hover:opacity-100 transition-opacity">' + actions + '</td></tr>'
    }).join('')
    return renderHtml('screens/journal_entries', {
      rows: rows, count: filtered.length,
      total: items.length,
      draft: items.filter(function(p) { return p.status === 'Draft' }).length,
      posted: items.filter(function(p) { return p.status === 'Posted' }).length
    })
  },
  mount() { controllers.journal_entries = this; var s = document.getElementById('jeSearch'); if (s) s.value = this.searchTerm || '' },
  search(q) { this.searchTerm = q.toLowerCase(); document.getElementById('content').innerHTML = this.render() },
  refresh() { this.render(); document.getElementById('content').innerHTML = this.render() },
  showCreateForm() {
    document.getElementById('content').innerHTML = renderHtml('screens/journal_entries_form', {
      title: 'New Journal Entry', id: '', reference: '', entryDate: new Date().toISOString().split('T')[0], description: ''
    })
  },
  showEditForm(id) {
    var p = window.journalEntryService.getById(id)
    if (!p) return
    document.getElementById('content').innerHTML = renderHtml('screens/journal_entries_form', {
      title: 'Edit Journal Entry', id: p.id,
      reference: escapeHtml(p.reference),
      entryDate: p.entryDate,
      description: escapeHtml(p.description || '')
    })
  },
  async saveForm() {
    var id = document.getElementById('jeFormId').value
    var payload = {
      reference: document.getElementById('jeFormReference').value,
      entryDate: document.getElementById('jeFormDate').value,
      description: document.getElementById('jeFormDescription').value
    }
    try {
      if (id) { await window.journalEntryService.update(id, payload) }
      else { await window.journalEntryService.create(payload) }
      app.toast('Journal entry saved', 'success')
      document.getElementById('content').innerHTML = this.render()
    } catch (e) { app.toast('Error: ' + e.message, 'error') }
    return false
  },
  async postJE(id) {
    try {
      await window.journalEntryService.postJE(id)
      app.toast('Journal entry posted', 'success')
      document.getElementById('content').innerHTML = this.render()
    } catch (e) { app.toast('Error: ' + e.message, 'error') }
  }
}
