window.NovaModules = window.NovaModules || {}; window.NovaModules['serial_numbers'] = {
  render() {
    var search = this.searchTerm || ''
    var items = window.serialNumberService.getAll()
    var filtered = search ? items.filter(function(s) {
      return (s.serialNumber || '').toLowerCase().indexOf(search) > -1 || String(s.productId || '').indexOf(search) > -1
    }) : items
    var rows = filtered.map(function(s) {
      var badge = s.status === 'In Stock' ? 'bg-secondary/10 text-secondary border border-secondary/20' :
        (s.status === 'Sold' ? 'bg-primary/10 text-primary border border-primary/20' :
        (s.status === 'Returned' ? 'bg-warning/10 text-warning border border-warning/20' :
        'bg-error/10 text-error border border-error/20'))
      return '<tr class="hover:bg-primary/5 transition-colors group">' +
        '<td class="px-lg py-md font-data-mono text-data-mono font-bold text-primary">' + escapeHtml(s.serialNumber) + '</td>' +
        '<td class="px-lg py-md font-body-md">' + escapeHtml(String(s.productId)) + '</td>' +
        '<td class="px-lg py-md"><span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-[11px] font-bold uppercase ' + badge + '">' + escapeHtml(s.status) + '</span></td>' +
        '<td class="px-lg py-md font-body-md text-on-surface-variant">' + escapeHtml(String(s.warehouseId || '-')) + '</td>' +
        '<td class="px-lg py-md text-right opacity-0 group-hover:opacity-100 transition-opacity">' +
        '<button class="p-1 hover:bg-surface-variant rounded-full text-primary" onclick="controllers.serial_numbers.showEditForm(' + s.id + ')"><span class="material-symbols-outlined text-[20px]">edit</span></button>' +
        '<button class="p-1 hover:bg-error-container rounded-full text-error" onclick="controllers.serial_numbers.deleteSerial(' + s.id + ')"><span class="material-symbols-outlined text-[20px]">delete</span></button>' +
        '</td></tr>'
    }).join('')
    return renderHtml('screens/serial_numbers', {
      rows: rows, count: filtered.length,
      total: items.length,
      inStock: items.filter(function(s) { return s.status === 'In Stock' }).length,
      sold: items.filter(function(s) { return s.status === 'Sold' }).length
    })
  },
  mount() { controllers.serial_numbers = this; var s = document.getElementById('serialSearch'); if (s) s.value = this.searchTerm || '' },
  search(q) { this.searchTerm = q.toLowerCase(); document.getElementById('content').innerHTML = this.render() },
  refresh() { this.render(); document.getElementById('content').innerHTML = this.render() },
  _statusOptions(selected) {
    var opts = ['In Stock','Reserved','Sold','Returned','Scrapped','Lost']
    return opts.map(function(s) { return '<option value="' + s + '"' + (s === selected ? ' selected' : '') + '>' + s + '</option>' }).join('')
  },
  showCreateForm() {
    document.getElementById('content').innerHTML = renderHtml('screens/serial_numbers_form', {
      title: 'New Serial Number', id: '', productId: '', serialNumber: '',
      statusOptions: this._statusOptions('In Stock'), warehouseId: '', notes: ''
    })
  },
  showEditForm(id) {
    var s = window.serialNumberService.getById(id)
    if (!s) return
    document.getElementById('content').innerHTML = renderHtml('screens/serial_numbers_form', {
      title: 'Edit Serial Number', id: s.id,
      productId: s.productId, serialNumber: escapeHtml(s.serialNumber),
      statusOptions: this._statusOptions(s.status), warehouseId: s.warehouseId, notes: escapeHtml(s.notes || '')
    })
  },
  async saveForm() {
    var id = document.getElementById('serialFormId').value
    var payload = {
      productId: parseInt(document.getElementById('serialFormProduct').value) || null,
      serialNumber: document.getElementById('serialFormNumber').value,
      status: document.getElementById('serialFormStatus').value,
      warehouseId: parseInt(document.getElementById('serialFormWarehouse').value) || null,
      notes: document.getElementById('serialFormNotes').value || null
    }
    if (!payload.serialNumber) { app.toast('Serial number is required', 'error'); return false }
    try {
      if (id) { await window.serialNumberService.update(id, payload) }
      else { await window.serialNumberService.create(payload) }
      app.toast('Serial number saved', 'success')
      document.getElementById('content').innerHTML = this.render()
    } catch (e) { app.toast('Error: ' + e.message, 'error') }
    return false
  },
  async deleteSerial(id) {
    if (!confirm('Delete this serial number?')) return
    try { await window.serialNumberService.remove(id); document.getElementById('content').innerHTML = this.render() }
    catch (e) { app.toast('Error deleting: ' + e.message, 'error') }
  }
}
