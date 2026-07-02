window.NovaModules = window.NovaModules || {}; window.NovaModules['payments'] = {
  render() {
    var search = this.searchTerm || ''
    var items = window.paymentService.getAll()
    var filtered = search ? items.filter(function(p) { return (p.reference || '').toLowerCase().indexOf(search) > -1 || String(p.partnerId).indexOf(search) > -1 }) : items
    var rows = filtered.map(function(p) {
      return '<tr class="hover:bg-primary/5 transition-colors group">' +
        '<td class="px-lg py-md font-data-mono text-data-mono font-bold text-primary">' + escapeHtml(p.reference || 'PAY-' + p.id) + '</td>' +
        '<td class="px-lg py-md">' + escapeHtml(p.paymentDate) + '</td>' +
        '<td class="px-lg py-md">' + escapeHtml(String(p.partnerId)) + '</td>' +
        '<td class="px-lg py-md">' + escapeHtml(String(p.invoiceId)) + '</td>' +
        '<td class="px-lg py-md font-data-mono font-bold">$' + escapeHtml(Number(p.amount).toFixed(2)) + '</td>' +
        '<td class="px-lg py-md">' + escapeHtml(p.paymentMethod) + '</td>' +
        '<td class="px-lg py-md"><span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-[11px] font-bold uppercase bg-green-50 text-green-700 border border-green-300">' + escapeHtml(p.status) + '</span></td>' +
        '<td class="px-lg py-md text-right opacity-0 group-hover:opacity-100 transition-opacity">' +
        '<button class="p-1 hover:bg-surface-variant rounded-full text-primary" onclick="controllers.payments.showEditForm(' + p.id + ')"><span class="material-symbols-outlined text-[20px]">edit</span></button>' +
        '</td></tr>'
    }).join('')
    var methodCounts = {}
    items.forEach(function(p) { methodCounts[p.paymentMethod] = (methodCounts[p.paymentMethod] || 0) + 1 })
    var methodStats = Object.keys(methodCounts).map(function(m) {
      return '<div class="bg-surface-container-lowest border border-outline-variant p-lg rounded-xl shadow-sm"><p class="text-on-surface-variant font-label-md text-label-md uppercase tracking-wider">' + escapeHtml(m) + '</p><p class="font-display-lg text-[28px] leading-tight text-on-surface font-bold">' + methodCounts[m] + '</p></div>'
    }).join('') || '<div class="bg-surface-container-lowest border border-outline-variant p-lg rounded-xl shadow-sm col-span-3"><p class="text-on-surface-variant font-label-md text-label-md uppercase tracking-wider">No Payments Yet</p></div>'
    return renderHtml('screens/payments', {
      rows: rows, count: filtered.length,
      total: items.length,
      methodStats: methodStats
    })
  },
  mount() { controllers.payments = this; var s = document.getElementById('paymentSearch'); if (s) s.value = this.searchTerm || '' },
  search(q) { this.searchTerm = q.toLowerCase(); document.getElementById('content').innerHTML = this.render() },
  refresh() { document.getElementById('content').innerHTML = this.render() },
  showCreateForm() {
    var today = new Date().toISOString().split('T')[0]
    document.getElementById('content').innerHTML = renderHtml('screens/payments_form', {
      title: 'New Payment', id: '', paymentDate: today, invoiceId: '', partnerId: '', amount: '', paymentMethod: 'Bank Transfer', reference: '', status: 'Completed', notes: '',
      selCash: '', selBankTransfer: 'selected', selCard: '', selCheck: ''
    })
  },
  showEditForm(id) {
    var p = window.paymentService.getById(id)
    if (!p) return
    document.getElementById('content').innerHTML = renderHtml('screens/payments_form', {
      title: 'Edit Payment', id: p.id,
      paymentDate: p.paymentDate, invoiceId: p.invoiceId,
      partnerId: p.partnerId, amount: p.amount,
      paymentMethod: p.paymentMethod, reference: escapeHtml(p.reference || ''),
      status: p.status, notes: escapeHtml(p.notes || ''),
      selCash: p.paymentMethod === 'Cash' ? 'selected' : '',
      selBankTransfer: p.paymentMethod === 'Bank Transfer' ? 'selected' : '',
      selCard: p.paymentMethod === 'Card' ? 'selected' : '',
      selCheck: p.paymentMethod === 'Check' ? 'selected' : ''
    })
  },
  async saveForm() {
    var id = document.getElementById('paymentFormId').value
    var payload = {
      paymentDate: document.getElementById('paymentFormDate').value,
      invoiceId: parseInt(document.getElementById('paymentFormInvoiceId').value) || 0,
      partnerId: parseInt(document.getElementById('paymentFormPartnerId').value) || 0,
      amount: parseFloat(document.getElementById('paymentFormAmount').value) || 0,
      paymentMethod: document.getElementById('paymentFormMethod').value,
      reference: document.getElementById('paymentFormReference').value,
      status: document.getElementById('paymentFormStatus').value,
      notes: document.getElementById('paymentFormNotes').value
    }
    try {
      if (id) { await window.paymentService.update(id, payload) }
      else { await window.paymentService.create(payload) }
      app.toast('Payment saved', 'success')
      document.getElementById('content').innerHTML = this.render()
    } catch (e) { app.toast('Error: ' + e.message, 'error') }
    return false
  }
}
