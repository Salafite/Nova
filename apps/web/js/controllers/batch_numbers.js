window.NovaModules = window.NovaModules || {}; window.NovaModules['batch_numbers'] = {
  render() {
    var search = this.searchTerm || ''
    var items = window.batchNumberService.getAll()
    var filtered = search ? items.filter(function(b) {
      return (b.batchNumber || '').toLowerCase().indexOf(search) > -1 || String(b.productId || '').indexOf(search) > -1
    }) : items
    var today = new Date()
    var rows = filtered.map(function(b) {
      var badge = b.status === 'Available' ? 'bg-secondary/10 text-secondary border border-secondary/20' :
        (b.status === 'Partially Used' ? 'bg-warning/10 text-warning border border-warning/20' :
        (b.status === 'Expired' ? 'bg-error/10 text-error border border-error/20' :
        'bg-surface-container text-on-surface-variant border border-outline-variant'))
      var expiryDisplay = b.expiryDate || '-'
      var expiryClass = ''
      if (b.expiryDate) {
        var expiry = new Date(b.expiryDate)
        var diff = Math.ceil((expiry - today) / (1000 * 60 * 60 * 24))
        if (diff < 0) expiryClass = 'text-error font-bold'
        else if (diff <= 30) expiryClass = 'text-warning font-bold'
      }
      return '<tr class="hover:bg-primary/5 transition-colors group">' +
        '<td class="px-lg py-md font-data-mono text-data-mono font-bold text-primary">' + escapeHtml(b.batchNumber) + '</td>' +
        '<td class="px-lg py-md font-body-md">' + escapeHtml(String(b.productId)) + '</td>' +
        '<td class="px-lg py-md font-body-md font-semibold">' + escapeHtml(String(b.quantity)) + '</td>' +
        '<td class="px-lg py-md font-body-md ' + expiryClass + '">' + escapeHtml(expiryDisplay) + '</td>' +
        '<td class="px-lg py-md"><span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-[11px] font-bold uppercase ' + badge + '">' + escapeHtml(b.status) + '</span></td>' +
        '<td class="px-lg py-md text-right opacity-0 group-hover:opacity-100 transition-opacity">' +
        '<button class="p-1 hover:bg-surface-variant rounded-full text-primary" onclick="controllers.batch_numbers.showEditForm(' + b.id + ')"><span class="material-symbols-outlined text-[20px]">edit</span></button>' +
        '<button class="p-1 hover:bg-error-container rounded-full text-error" onclick="controllers.batch_numbers.deleteBatch(' + b.id + ')"><span class="material-symbols-outlined text-[20px]">delete</span></button>' +
        '</td></tr>'
    }).join('')
    return renderHtml('screens/batch_numbers', {
      rows: rows, count: filtered.length,
      total: items.length,
      available: items.filter(function(b) { return b.status === 'Available' }).length,
      depleted: items.filter(function(b) { return b.status === 'Depleted' }).length
    })
  },
  mount() { controllers.batch_numbers = this; var s = document.getElementById('batchSearch'); if (s) s.value = this.searchTerm || '' },
  search(q) { this.searchTerm = q.toLowerCase(); document.getElementById('content').innerHTML = this.render() },
  refresh() { this.render(); document.getElementById('content').innerHTML = this.render() },
  showCreateForm() {
    var today = new Date().toISOString().slice(0,10)
    document.getElementById('content').innerHTML = renderHtml('screens/batch_numbers_form', {
      title: 'New Batch Number', id: '', productId: '', batchNumber: '',
      expiryDate: '', manufacturingDate: today, quantity: '0', warehouseId: '', notes: ''
    })
  },
  showEditForm(id) {
    var b = window.batchNumberService.getById(id)
    if (!b) return
    document.getElementById('content').innerHTML = renderHtml('screens/batch_numbers_form', {
      title: 'Edit Batch Number', id: b.id,
      productId: b.productId, batchNumber: escapeHtml(b.batchNumber),
      expiryDate: b.expiryDate || '', manufacturingDate: b.manufacturingDate || '',
      quantity: b.quantity, warehouseId: b.warehouseId, notes: escapeHtml(b.notes || '')
    })
  },
  async saveForm() {
    var id = document.getElementById('batchFormId').value
    var payload = {
      productId: parseInt(document.getElementById('batchFormProduct').value) || null,
      batchNumber: document.getElementById('batchFormNumber').value,
      expiryDate: document.getElementById('batchFormExpiry').value || null,
      manufacturingDate: document.getElementById('batchFormMfgDate').value || null,
      quantity: parseFloat(document.getElementById('batchFormQty').value) || 0,
      warehouseId: parseInt(document.getElementById('batchFormWarehouse').value) || null,
      notes: document.getElementById('batchFormNotes').value || null
    }
    if (!payload.batchNumber) { app.toast('Batch number is required', 'error'); return false }
    try {
      if (id) { await window.batchNumberService.update(id, payload) }
      else { await window.batchNumberService.create(payload) }
      app.toast('Batch number saved', 'success')
      document.getElementById('content').innerHTML = this.render()
    } catch (e) { app.toast('Error: ' + e.message, 'error') }
    return false
  },
  async deleteBatch(id) {
    if (!confirm('Delete this batch number?')) return
    try { await window.batchNumberService.remove(id); document.getElementById('content').innerHTML = this.render() }
    catch (e) { app.toast('Error deleting: ' + e.message, 'error') }
  }
}
