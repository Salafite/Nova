window.NovaModules = window.NovaModules || {}; window.NovaModules['finance'] = {
  render() {
    var summary = window.financeService.getSummary()
    var transactions = window.financeService.getTransactions()
    var rows = transactions.slice(-10).reverse().map(function(t) {
      var amountColor = t.type === 'Revenue' ? 'text-secondary' : 'text-error'
      var prefix = t.type === 'Revenue' ? '+' : '-'
      return '<tr class="group transition-colors hover:bg-surface-container-low">' +
               '<td class="px-lg py-4 text-on-surface-variant">' + escapeHtml(t.date) + '</td>' +
               '<td class="px-lg py-4"><span class="font-medium">' + escapeHtml(t.description) + '</span></td>' +
               '<td class="px-lg py-4">' + Badge.transactionType(t.type) + '</td>' +
               '<td class="px-lg py-4 text-right font-data-mono font-bold ' + amountColor + '">' + prefix + '$' + t.amount.toFixed(2) + '</td>' +
             '</tr>'
    }).join('')
    return renderHtml('screens/finance', {
      totalRevenue: summary.totalRevenue.toFixed(2),
      totalExpenses: summary.totalExpenses.toFixed(2),
      netProfit: summary.netProfit.toFixed(2),
      pendingInvoices: summary.pendingInvoices,
      transactionRows: rows
    })
  }
}
