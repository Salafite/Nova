window.NovaModules = window.NovaModules || {}; window.NovaModules['quotations'] = {
  render() {
    var search = this.searchTerm || ''
    var items = window.quotationService.getAll()
    var customers = window.customerService ? window.customerService.getAll() : []
    var filtered = search ? items.filter(function(q) { return (q.quoteNumber || '').toLowerCase().indexOf(search) > -1 || (q.customerName || '').toLowerCase().indexOf(search) > -1 }) : items
    var rows = filtered.map(function(q) {
      var customer = customers.find(function(c) { return c.id == q.customerId })
      var customerName = customer ? customer.name : 'Customer #' + q.customerId
      var statusBadge = q.status === 'Accepted' ? 'bg-secondary/10 text-secondary border border-secondary/20' :
        (q.status === 'Converted' ? 'bg-primary/10 text-primary border border-primary/20' :
        (q.status === 'Sent' ? 'bg-warning/10 text-warning border border-warning/20' :
        (q.status === 'Rejected' ? 'bg-error/10 text-error border border-error/20' :
        'bg-surface-container text-on-surface-variant border border-outline-variant')))
      var convertBtn = q.status === 'Accepted' ? '<button class="text-primary font-label-md text-label-md hover:underline" onclick="controllers.quotations.convertToOrder(' + q.id + ')">Convert to Order</button>' : ''
      return '<tr class="hover:bg-primary/5 transition-colors group">' +
        '<td class="px-lg py-md font-data-mono text-data-mono font-bold text-primary">' + escapeHtml(q.quoteNumber) + '</td>' +
        '<td class="px-lg py-md font-body-md">' + escapeHtml(customerName) + '</td>' +
        '<td class="px-lg py-md font-body-md text-on-surface-variant">' + escapeHtml(q.quoteDate || '-') + '</td>' +
        '<td class="px-lg py-md font-body-md text-on-surface-variant">' + escapeHtml(q.validUntil || '-') + '</td>' +
        '<td class="px-lg py-md font-data-mono text-data-mono font-bold text-right">$' + (q.grandTotal || 0).toFixed(2) + '</td>' +
        '<td class="px-lg py-md"><span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-[11px] font-bold uppercase ' + statusBadge + '">' + escapeHtml(q.status) + '</span></td>' +
        '<td class="px-lg py-md text-right">' + convertBtn + '</td>' +
        '<td class="px-lg py-md text-right opacity-0 group-hover:opacity-100 transition-opacity">' +
        '<button class="p-1 hover:bg-surface-variant rounded-full text-primary" onclick="controllers.quotations.showEditForm(' + q.id + ')"><span class="material-symbols-outlined text-[20px]">edit</span></button>' +
        '<button class="p-1 hover:bg-error-container rounded-full text-error" onclick="controllers.quotations.deleteQuote(' + q.id + ')"><span class="material-symbols-outlined text-[20px]">delete</span></button>' +
        '</td></tr>'
    }).join('')
    return renderHtml('screens/quotations', { rows: rows, count: filtered.length, pending: window.quotationService.getPendingCount() })
  },
  mount() { controllers.quotations = this; var s = document.getElementById('quoteSearch'); if (s) s.value = this.searchTerm || '' },
  search(q) { this.searchTerm = q.toLowerCase(); document.getElementById('content').innerHTML = this.render() },
  showCreateForm() {
    document.getElementById('content').innerHTML = renderHtml('screens/quotations_form', { title: 'New Quotation', id: '', quoteNumber: 'QTE-' + String(window.quotationService.getAll().length + 1).padStart(3, '0'), customerId: '', quoteDate: new Date().toISOString().slice(0, 10), validUntil: '', subtotal: '0', tax: '0', grandTotal: '0', notes: '' })
  },
  showEditForm(id) {
    var q = window.quotationService.getById(id)
    if (!q) return
    document.getElementById('content').innerHTML = renderHtml('screens/quotations_form', {
      title: 'Edit Quotation', id: q.id, quoteNumber: escapeHtml(q.quoteNumber), customerId: q.customerId,
      quoteDate: q.quoteDate, validUntil: q.validUntil || '', subtotal: q.subtotal, tax: q.tax, grandTotal: q.grandTotal, notes: escapeHtml(q.notes || '')
    })
  },
  async saveForm() {
    var id = document.getElementById('quoteFormId').value
    var payload = {
      quoteNumber: document.getElementById('quoteFormNumber').value,
      customerId: parseInt(document.getElementById('quoteFormCustomer').value) || 0,
      quoteDate: document.getElementById('quoteFormDate').value,
      validUntil: document.getElementById('quoteFormValid').value || null,
      subtotal: parseFloat(document.getElementById('quoteFormSubtotal').value) || 0,
      tax: parseFloat(document.getElementById('quoteFormTax').value) || 0,
      notes: document.getElementById('quoteFormNotes').value
    }
    try {
      if (id) { await window.quotationService.update(id, payload) }
      else { await window.quotationService.create(payload) }
      app.toast('Quotation saved', 'success')
      document.getElementById('content').innerHTML = this.render()
    } catch (e) { app.toast('Error: ' + e.message, 'error') }
    return false
  },
  async deleteQuote(id) {
    if (!confirm('Delete quotation?')) return
    try { await window.quotationService.remove(id); document.getElementById('content').innerHTML = this.render() }
    catch (e) { app.toast('Error deleting: ' + e.message, 'error') }
  },
  async convertToOrder(id) {
    if (!confirm('Convert this quotation to a sales order?')) return
    try {
      await window.quotationService.convertToOrder(id)
      app.toast('Quotation converted to order', 'success')
      document.getElementById('content').innerHTML = this.render()
    } catch (e) { app.toast('Error converting: ' + e.message, 'error') }
  }
}
