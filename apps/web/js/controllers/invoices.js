window.NovaModules = window.NovaModules || {}; window.NovaModules['invoices'] = {
  render() {
    var search = this.searchTerm || ''
    var items = window.invoiceService.getAll()
    var filtered = search ? items.filter(function(p) { return p.invoiceNumber.toLowerCase().indexOf(search) > -1 || String(p.partnerId).indexOf(search) > -1 }) : items
    var rows = filtered.map(function(p) {
      var statusStyles = { Draft: 'bg-gray-100 text-gray-700 border border-gray-300', Unpaid: 'bg-amber-50 text-amber-700 border border-amber-300', Paid: 'bg-green-50 text-green-700 border border-green-300', Cancelled: 'bg-red-50 text-red-700 border border-red-300' }
      var badges = statusStyles[p.status] || statusStyles.Draft
      return '<tr class="hover:bg-primary/5 transition-colors group">' +
        '<td class="px-lg py-md font-data-mono text-data-mono font-bold text-primary">' + escapeHtml(p.invoiceNumber) + '</td>' +
        '<td class="px-lg py-md">' + escapeHtml(p.invoiceType) + '</td>' +
        '<td class="px-lg py-md">' + escapeHtml(String(p.partnerId)) + '</td>' +
        '<td class="px-lg py-md">' + escapeHtml(p.issueDate) + '</td>' +
        '<td class="px-lg py-md">' + escapeHtml(p.dueDate) + '</td>' +
        '<td class="px-lg py-md font-data-mono font-bold">$' + escapeHtml(Number(p.totalAmount).toFixed(2)) + '</td>' +
        '<td class="px-lg py-md"><span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-[11px] font-bold uppercase ' + badges + '">' + escapeHtml(p.status) + '</span></td>' +
        '<td class="px-lg py-md text-right opacity-0 group-hover:opacity-100 transition-opacity">' +
        '<button class="p-1 hover:bg-surface-variant rounded-full text-primary" onclick="controllers.invoices.showEditForm(' + p.id + ')"><span class="material-symbols-outlined text-[20px]">edit</span></button>' +
        (p.status === 'Unpaid' ? '<button class="p-1 hover:bg-surface-variant rounded-full text-success" onclick="controllers.invoices.payInvoice(' + p.id + ')"><span class="material-symbols-outlined text-[20px]">check_circle</span></button>' : '') +
        (p.status === 'Draft' || p.status === 'Unpaid' ? '<button class="p-1 hover:bg-surface-variant rounded-full text-error" onclick="controllers.invoices.cancelInvoice(' + p.id + ')"><span class="material-symbols-outlined text-[20px]">cancel</span></button>' : '') +
        '</td></tr>'
    }).join('')
    return renderHtml('screens/invoices', {
      rows: rows, count: filtered.length,
      total: items.length,
      unpaid: items.filter(function(p) { return p.status === 'Unpaid' }).length,
      paid: items.filter(function(p) { return p.status === 'Paid' }).length
    })
  },
  mount() { controllers.invoices = this; var s = document.getElementById('invoiceSearch'); if (s) s.value = this.searchTerm || '' },
  search(q) { this.searchTerm = q.toLowerCase(); document.getElementById('content').innerHTML = this.render() },
  refresh() { document.getElementById('content').innerHTML = this.render() },
  showCreateForm() {
    var today = new Date().toISOString().split('T')[0]
    document.getElementById('content').innerHTML = renderHtml('screens/invoices_form', {
      title: 'New Invoice', id: '', invoiceNumber: 'INV-001', invoiceType: 'Sales', partnerId: '', issueDate: today, dueDate: '', totalAmount: '', status: 'Draft', notes: '',
      selSales: 'selected', selPurchase: ''
    })
  },
  showEditForm(id) {
    var p = window.invoiceService.getById(id)
    if (!p) return
    document.getElementById('content').innerHTML = renderHtml('screens/invoices_form', {
      title: 'Edit Invoice', id: p.id,
      invoiceNumber: escapeHtml(p.invoiceNumber), invoiceType: p.invoiceType,
      partnerId: p.partnerId, issueDate: p.issueDate, dueDate: p.dueDate,
      totalAmount: p.totalAmount, status: p.status, notes: escapeHtml(p.notes || ''),
      selSales: p.invoiceType === 'Sales' ? 'selected' : '', selPurchase: p.invoiceType === 'Purchase' ? 'selected' : ''
    })
  },
  async saveForm() {
    var id = document.getElementById('invoiceFormId').value
    var payload = {
      invoiceNumber: document.getElementById('invoiceFormNumber').value,
      invoiceType: document.getElementById('invoiceFormType').value,
      partnerId: parseInt(document.getElementById('invoiceFormPartnerId').value) || 0,
      issueDate: document.getElementById('invoiceFormIssueDate').value,
      dueDate: document.getElementById('invoiceFormDueDate').value,
      totalAmount: parseFloat(document.getElementById('invoiceFormTotalAmount').value) || 0,
      status: document.getElementById('invoiceFormStatus').value,
      notes: document.getElementById('invoiceFormNotes').value
    }
    try {
      if (id) { await window.invoiceService.update(id, payload) }
      else { await window.invoiceService.create(payload) }
      app.toast('Invoice saved', 'success')
      document.getElementById('content').innerHTML = this.render()
    } catch (e) { app.toast('Error: ' + e.message, 'error') }
    return false
  },
  async payInvoice(id) {
    try {
      await window.invoiceService.update(id, { status: 'Paid' })
      app.toast('Invoice marked as Paid', 'success')
      document.getElementById('content').innerHTML = this.render()
    } catch (e) { app.toast('Error: ' + e.message, 'error') }
  },
  async cancelInvoice(id) {
    try {
      await window.invoiceService.update(id, { status: 'Cancelled' })
      app.toast('Invoice cancelled', 'success')
      document.getElementById('content').innerHTML = this.render()
    } catch (e) { app.toast('Error: ' + e.message, 'error') }
  }
}
