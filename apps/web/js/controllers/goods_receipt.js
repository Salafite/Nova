window.NovaModules = window.NovaModules || {}; window.NovaModules['goods_receipt'] = {
  render() {
    var search = this.searchTerm || ''
    var items = window.goodsReceiptService.getAll()
    var filtered = search ? items.filter(function(r) { return (r.receiptNumber || '').toLowerCase().indexOf(search) > -1 || String(r.purchaseOrderId || '').indexOf(search) > -1 }) : items
    var rows = filtered.map(function(r) {
      var statusBadge = r.status === 'Completed' ? 'bg-secondary/10 text-secondary border border-secondary/20' :
        (r.status === 'Cancelled' ? 'bg-error/10 text-error border border-error/20' :
        'bg-surface-container text-on-surface-variant border border-outline-variant')
      var completeBtn = r.status === 'Draft' ? '<button class="text-secondary font-label-md text-label-md hover:underline" onclick="controllers.goods_receipt.completeReceipt(' + r.id + ')">Complete</button> | ' : ''
      return '<tr class="hover:bg-primary/5 transition-colors group">' +
        '<td class="px-lg py-md font-data-mono text-data-mono font-bold text-primary">' + escapeHtml(r.receiptNumber) + '</td>' +
        '<td class="px-lg py-md font-body-md font-medium">' + escapeHtml(String(r.purchaseOrderId || '-')) + '</td>' +
        '<td class="px-lg py-md font-body-md text-on-surface-variant">' + escapeHtml(r.receiptDate || '-') + '</td>' +
        '<td class="px-lg py-md"><span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-[11px] font-bold uppercase ' + statusBadge + '">' + escapeHtml(r.status) + '</span></td>' +
        '<td class="px-lg py-md text-center">' + completeBtn +
        '<button class="text-error font-label-md text-label-md hover:underline" onclick="controllers.goods_receipt.cancelReceipt(' + r.id + ')">Cancel</button></td>' +
        '<td class="px-lg py-md text-right opacity-0 group-hover:opacity-100 transition-opacity">' +
        '<button class="p-1 hover:bg-surface-variant rounded-full text-primary" onclick="controllers.goods_receipt.showEditForm(' + r.id + ')"><span class="material-symbols-outlined text-[20px]">edit</span></button>' +
        '<button class="p-1 hover:bg-error-container rounded-full text-error" onclick="controllers.goods_receipt.deleteReceipt(' + r.id + ')"><span class="material-symbols-outlined text-[20px]">delete</span></button>' +
        '</td></tr>'
    }).join('')
    return renderHtml('screens/goods_receipt', { rows: rows, count: filtered.length, draftCount: items.filter(function(r) { return r.status === 'Draft' }).length, completedCount: items.filter(function(r) { return r.status === 'Completed' }).length })
  },
  mount() { controllers.goods_receipt = this; var s = document.getElementById('grnSearch'); if (s) s.value = this.searchTerm || '' },
  async refresh() { await window.goodsReceiptService.load(); document.getElementById('content').innerHTML = this.render() },
  search(q) { this.searchTerm = q.toLowerCase(); document.getElementById('content').innerHTML = this.render() },
  showCreateForm() {
    var today = new Date().toISOString().slice(0,10)
    document.getElementById('content').innerHTML = renderHtml('screens/goods_receipt_form', { title: 'New Goods Receipt Note', id: '', receiptNumber: 'GRN-' + String(window.goodsReceiptService.getAll().length + 1).padStart(3, '0'), purchaseOrderId: '', receiptDate: today, warehouseId: '', notes: '' })
  },
  showEditForm(id) {
    var r = window.goodsReceiptService.getById(id)
    if (!r) return
    document.getElementById('content').innerHTML = renderHtml('screens/goods_receipt_form', {
      title: 'Edit Goods Receipt Note', id: r.id, receiptNumber: escapeHtml(r.receiptNumber),
      purchaseOrderId: r.purchaseOrderId, receiptDate: r.receiptDate, warehouseId: r.warehouseId, notes: escapeHtml(r.notes || '')
    })
  },
  async saveForm() {
    var id = document.getElementById('grnFormId').value
    var payload = {
      receiptNumber: document.getElementById('grnFormNumber').value,
      purchaseOrderId: parseInt(document.getElementById('grnFormPO').value) || null,
      receiptDate: document.getElementById('grnFormDate').value,
      warehouseId: parseInt(document.getElementById('grnFormWarehouse').value) || null,
      notes: document.getElementById('grnFormNotes').value || null
    }
    if (!payload.receiptDate) { app.toast('Receipt date is required', 'error'); return false }
    try {
      if (id) { await window.goodsReceiptService.update(id, payload) }
      else { await window.goodsReceiptService.create(payload) }
      app.toast('Goods receipt saved', 'success')
      document.getElementById('content').innerHTML = this.render()
    } catch (e) { app.toast('Error: ' + e.message, 'error') }
    return false
  },
  async completeReceipt(id) {
    if (!confirm('Complete this goods receipt?')) return
    try {
      await window.goodsReceiptService.update(id, { status: 'Completed' })
      app.toast('Goods receipt completed', 'success')
      document.getElementById('content').innerHTML = this.render()
    } catch (e) { app.toast('Error: ' + e.message, 'error') }
  },
  async cancelReceipt(id) {
    if (!confirm('Cancel this goods receipt?')) return
    try {
      await window.goodsReceiptService.update(id, { status: 'Cancelled' })
      app.toast('Goods receipt cancelled', 'success')
      document.getElementById('content').innerHTML = this.render()
    } catch (e) { app.toast('Error: ' + e.message, 'error') }
  },
  async deleteReceipt(id) {
    if (!confirm('Delete goods receipt?')) return
    try { await window.goodsReceiptService.remove(id); document.getElementById('content').innerHTML = this.render() }
    catch (e) { app.toast('Error deleting: ' + e.message, 'error') }
  }
}
