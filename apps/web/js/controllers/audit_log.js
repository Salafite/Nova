window.NovaModules = window.NovaModules || {}; window.NovaModules['audit_log'] = {
  _actionBadge(action) {
    var map = { INSERT: 'bg-secondary/10 text-secondary border border-secondary/20', UPDATE: 'bg-primary/10 text-primary border border-primary/20', DELETE: 'bg-error/10 text-error border border-error/20' }
    var cls = map[action] || 'bg-surface-container text-on-surface-variant border border-outline-variant'
    return '<span class="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-bold uppercase ' + cls + '">' + escapeHtml(action) + '</span>'
  },
  _entryRow(e) {
    return '<tr class="hover:bg-primary/5 transition-colors group cursor-pointer" onclick="controllers.audit_log.showDetail(' + e.id + ')">' +
      '<td class="px-lg py-md font-body-md text-on-surface-variant">' + escapeHtml(e.tableName || e.table_name || '') + '</td>' +
      '<td class="px-lg py-md font-data-mono text-data-mono">' + (e.recordId || e.record_id || '') + '</td>' +
      '<td class="px-lg py-md">' + this._actionBadge(e.action) + '</td>' +
      '<td class="px-lg py-md font-body-md">' + escapeHtml(e.changedBy || e.changed_by || '-') + '</td>' +
      '<td class="px-lg py-md font-data-mono text-data-mono text-on-surface-variant">' + (e.changedAt || e.changed_at ? new Date(e.changedAt || e.changed_at).toLocaleString() : '') + '</td>' +
      '</tr>'
  },
  _filteredList() {
    var list = window.auditLogService.getAll()
    var tt = (this.searchTable || '').toLowerCase()
    var rr = (this.searchRecord || '').toLowerCase()
    var aa = (this.searchAction || '').toLowerCase()
    if (tt) list = list.filter(function(e) { return (e.tableName || e.table_name || '').toLowerCase().indexOf(tt) > -1 })
    if (rr) list = list.filter(function(e) { return String(e.recordId || e.record_id || '').indexOf(rr) > -1 })
    if (aa) list = list.filter(function(e) { return (e.action || '').toLowerCase().indexOf(aa) > -1 })
    return list
  },
  render() {
    var filtered = this._filteredList()
    var all = window.auditLogService.getAll()
    var counts = window.auditLogService.getActionCounts()
    var rows = filtered.map(this._entryRow.bind(this)).join('')
    return renderHtml('screens/audit_log', {
      total: all.length,
      inserts: counts.INSERT || 0,
      updates: counts.UPDATE || 0,
      deletes: counts.DELETE || 0,
      rows: rows,
      searchTable: this.searchTable || '',
      searchRecord: this.searchRecord || '',
      searchAction: this.searchAction || ''
    })
  },
  mount() {
    controllers.audit_log = this
    var st = document.getElementById('auditSearchTable'); if (st) st.value = this.searchTable || ''
    var sr = document.getElementById('auditSearchRecord'); if (sr) sr.value = this.searchRecord || ''
    var sa = document.getElementById('auditSearchAction'); if (sa) sa.value = this.searchAction || ''
  },
  search(type, value) {
    if (type === 'table') this.searchTable = value
    else if (type === 'record') this.searchRecord = value
    else if (type === 'action') this.searchAction = value
    document.getElementById('content').innerHTML = this.render()
  },
  showDetail(id) {
    var entry = window.auditLogService.getAll().find(function(e) { return e.id === id })
    if (!entry || !entry.changedData && !entry.changed_data) {
      app.toast('No detail data available', 'info')
      return
    }
    var data = entry.changedData || entry.changed_data
    var formatted = '<pre class="text-data-mono text-sm bg-surface-container-low p-lg rounded-lg overflow-x-auto whitespace-pre-wrap">' + escapeHtml(JSON.stringify(data, null, 2)) + '</pre>'
    var overlay = document.createElement('div')
    overlay.className = 'fixed inset-0 z-50 flex items-center justify-center bg-black/30'
    overlay.innerHTML = '<div class="bg-surface-container-lowest rounded-xl shadow-xl max-w-2xl w-full mx-lg max-h-[80vh] flex flex-col"><div class="flex justify-between items-center px-lg py-md border-b border-outline-variant"><h3 class="font-title-md font-bold">Change Detail</h3><button class="material-symbols-outlined text-on-surface-variant hover:text-primary" onclick="this.closest(\'.fixed\').remove()">close</button></div><div class="overflow-y-auto p-lg">' + formatted + '</div></div>'
    overlay.addEventListener('click', function(e) { if (e.target === overlay) overlay.remove() })
    document.body.appendChild(overlay)
  },
  closeDetail() {
    var el = document.querySelector('.fixed.inset-0.z-50')
    if (el) el.remove()
  }
}
