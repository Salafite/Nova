window.NovaModules = window.NovaModules || {}; window.NovaModules['payroll'] = {
  render() {
    var search = this.searchTerm || ''
    var items = window.payrollService.getAll()
    var filtered = search ? items.filter(function(p) { return (p.employee_name || '').toLowerCase().indexOf(search) > -1 || (p.period || '').toLowerCase().indexOf(search) > -1 || (p.status || '').toLowerCase().indexOf(search) > -1 }) : items
    var rows = filtered.map(function(p) {
      var statusBadge = p.status === 'Paid' ? '<span class="px-sm py-xs bg-secondary/10 text-secondary rounded text-[11px] font-medium uppercase">Paid</span>' :
                        (p.status === 'Processed' ? '<span class="px-sm py-xs bg-primary/10 text-primary rounded text-[11px] font-medium uppercase">Processed</span>' :
                        '<span class="px-sm py-xs bg-surface-container-highest text-on-surface-variant rounded text-[11px] font-medium uppercase">' + escapeHtml(p.status) + '</span>')
      return '<tr class="hover:bg-primary/5 transition-colors group">' +
             '<td class="px-lg py-md font-body-md font-semibold text-on-surface">' + escapeHtml(p.employee_name) + '</td>' +
             '<td class="px-lg py-md text-body-md text-on-surface-variant">' + escapeHtml(p.period) + '</td>' +
             '<td class="px-lg py-md text-right font-data-mono">$' + (p.basic_salary || 0).toFixed(2) + '</td>' +
             '<td class="px-lg py-md text-right font-data-mono">$' + (p.allowances || 0).toFixed(2) + '</td>' +
             '<td class="px-lg py-md text-right font-data-mono text-error">$' + (p.deductions || 0).toFixed(2) + '</td>' +
             '<td class="px-lg py-md text-right font-data-mono font-bold text-on-surface">$' + (p.net_pay || 0).toFixed(2) + '</td>' +
             '<td class="px-lg py-md text-center">' + statusBadge + '</td>' +
             '<td class="px-lg py-md text-center opacity-0 group-hover:opacity-100 transition-opacity">' +
             '<div class="flex items-center justify-center gap-1">' +
             '<button class="p-1 hover:bg-surface-variant rounded-full text-primary" onclick="controllers.payroll.showEditForm(' + p.id + ')"><span class="material-symbols-outlined text-[20px]">edit</span></button>' +
             '<button class="p-1 hover:bg-error-container rounded-full text-error" onclick="controllers.payroll.deleteEntry(' + p.id + ')"><span class="material-symbols-outlined text-[20px]">delete</span></button>' +
             '</div></td></tr>'
    }).join('')
    var totalPayroll = items.reduce(function(s, p) { return s + (p.net_pay || 0) }, 0).toFixed(2)
    var pendingCount = items.filter(function(p) { return p.status === 'Draft' || p.status === 'Pending' }).length
    return renderHtml('screens/payroll_management', {
      rows: rows,
      totalPayroll: totalPayroll,
      employeeCount: items.length,
      pendingCount: pendingCount
    })
  },
  mount() { controllers.payroll = this; var s = document.getElementById('paySearch'); if (s) s.value = this.searchTerm || '' },
  search(q) { this.searchTerm = q.toLowerCase(); document.getElementById('content').innerHTML = this.render() },
  async refresh() { await window.payrollService.load(); document.getElementById('content').innerHTML = this.render() },
  showCreateForm() {
    document.getElementById('content').innerHTML =
      '<div class="max-w-2xl mx-auto bg-surface-container-lowest border border-outline-variant rounded-xl p-lg shadow-sm">' +
      '<h3 class="font-title-md text-title-md font-bold mb-lg">New Payroll Entry</h3>' +
      '<form onsubmit="return controllers.payroll.saveForm()">' +
      '<input type="hidden" id="payFormId" value="" />' +
      '<div class="grid grid-cols-1 md:grid-cols-2 gap-md mb-md">' +
      '<div class="flex flex-col gap-xs"><label class="font-label-sm text-label-sm font-bold text-on-surface-variant uppercase">Employee Name</label><input id="payFormEmployee" required class="w-full bg-surface border border-outline-variant rounded-lg px-3 py-2 text-body-md focus:ring-2 focus:ring-primary/20" /></div>' +
      '<div class="flex flex-col gap-xs"><label class="font-label-sm text-label-sm font-bold text-on-surface-variant uppercase">Period</label><input id="payFormPeriod" placeholder="e.g. June 2026" required class="w-full bg-surface border border-outline-variant rounded-lg px-3 py-2 text-body-md focus:ring-2 focus:ring-primary/20" /></div>' +
      '<div class="flex flex-col gap-xs"><label class="font-label-sm text-label-sm font-bold text-on-surface-variant uppercase">Basic Salary ($)</label><input id="payFormBasic" type="number" step="0.01" value="0" class="w-full bg-surface border border-outline-variant rounded-lg px-3 py-2 text-body-md focus:ring-2 focus:ring-primary/20" /></div>' +
      '<div class="flex flex-col gap-xs"><label class="font-label-sm text-label-sm font-bold text-on-surface-variant uppercase">Allowances ($)</label><input id="payFormAllow" type="number" step="0.01" value="0" class="w-full bg-surface border border-outline-variant rounded-lg px-3 py-2 text-body-md focus:ring-2 focus:ring-primary/20" /></div>' +
      '<div class="flex flex-col gap-xs"><label class="font-label-sm text-label-sm font-bold text-on-surface-variant uppercase">Deductions ($)</label><input id="payFormDeduct" type="number" step="0.01" value="0" class="w-full bg-surface border border-outline-variant rounded-lg px-3 py-2 text-body-md focus:ring-2 focus:ring-primary/20" /></div>' +
      '<div class="flex flex-col gap-xs"><label class="font-label-sm text-label-sm font-bold text-on-surface-variant uppercase">Status</label><select id="payFormStatus" class="w-full bg-surface border border-outline-variant rounded-lg px-3 py-2 text-body-md focus:ring-2 focus:ring-primary/20"><option value="Draft">Draft</option><option value="Processed">Processed</option><option value="Paid">Paid</option></select></div>' +
      '</div>' +
      '<div class="flex gap-sm mt-lg"><button type="submit" class="bg-primary text-on-primary px-lg py-sm rounded-lg font-label-md press-effect">Save</button>' +
      '<button type="button" class="bg-surface border border-outline-variant text-on-surface-variant px-lg py-sm rounded-lg font-label-md press-effect" onclick="controllers.payroll.render()">Cancel</button></div>' +
      '</form></div>'
  },
  showEditForm(id) {
    var p = window.payrollService.getById(id)
    if (!p) return
    var statusOpts = ['Draft', 'Processed', 'Paid'].map(function(s) { return '<option value="' + s + '"' + (s === p.status ? ' selected' : '') + '>' + s + '</option>' }).join('')
    document.getElementById('content').innerHTML =
      '<div class="max-w-2xl mx-auto bg-surface-container-lowest border border-outline-variant rounded-xl p-lg shadow-sm">' +
      '<h3 class="font-title-md text-title-md font-bold mb-lg">Edit Payroll Entry</h3>' +
      '<form onsubmit="return controllers.payroll.saveForm()">' +
      '<input type="hidden" id="payFormId" value="' + p.id + '" />' +
      '<div class="grid grid-cols-1 md:grid-cols-2 gap-md mb-md">' +
      '<div class="flex flex-col gap-xs"><label class="font-label-sm text-label-sm font-bold text-on-surface-variant uppercase">Employee Name</label><input id="payFormEmployee" value="' + escapeHtml(p.employee_name) + '" required class="w-full bg-surface border border-outline-variant rounded-lg px-3 py-2 text-body-md focus:ring-2 focus:ring-primary/20" /></div>' +
      '<div class="flex flex-col gap-xs"><label class="font-label-sm text-label-sm font-bold text-on-surface-variant uppercase">Period</label><input id="payFormPeriod" value="' + escapeHtml(p.period) + '" required class="w-full bg-surface border border-outline-variant rounded-lg px-3 py-2 text-body-md focus:ring-2 focus:ring-primary/20" /></div>' +
      '<div class="flex flex-col gap-xs"><label class="font-label-sm text-label-sm font-bold text-on-surface-variant uppercase">Basic Salary ($)</label><input id="payFormBasic" type="number" step="0.01" value="' + (p.basic_salary || 0) + '" class="w-full bg-surface border border-outline-variant rounded-lg px-3 py-2 text-body-md focus:ring-2 focus:ring-primary/20" /></div>' +
      '<div class="flex flex-col gap-xs"><label class="font-label-sm text-label-sm font-bold text-on-surface-variant uppercase">Allowances ($)</label><input id="payFormAllow" type="number" step="0.01" value="' + (p.allowances || 0) + '" class="w-full bg-surface border border-outline-variant rounded-lg px-3 py-2 text-body-md focus:ring-2 focus:ring-primary/20" /></div>' +
      '<div class="flex flex-col gap-xs"><label class="font-label-sm text-label-sm font-bold text-on-surface-variant uppercase">Deductions ($)</label><input id="payFormDeduct" type="number" step="0.01" value="' + (p.deductions || 0) + '" class="w-full bg-surface border border-outline-variant rounded-lg px-3 py-2 text-body-md focus:ring-2 focus:ring-primary/20" /></div>' +
      '<div class="flex flex-col gap-xs"><label class="font-label-sm text-label-sm font-bold text-on-surface-variant uppercase">Status</label><select id="payFormStatus" class="w-full bg-surface border border-outline-variant rounded-lg px-3 py-2 text-body-md focus:ring-2 focus:ring-primary/20">' + statusOpts + '</select></div>' +
      '</div>' +
      '<div class="flex gap-sm mt-lg"><button type="submit" class="bg-primary text-on-primary px-lg py-sm rounded-lg font-label-md press-effect">Save</button>' +
      '<button type="button" class="bg-surface border border-outline-variant text-on-surface-variant px-lg py-sm rounded-lg font-label-md press-effect" onclick="controllers.payroll.render()">Cancel</button></div>' +
      '</form></div>'
  },
  async saveForm() {
    var id = document.getElementById('payFormId').value
    var basic = parseFloat(document.getElementById('payFormBasic').value) || 0
    var allow = parseFloat(document.getElementById('payFormAllow').value) || 0
    var deduct = parseFloat(document.getElementById('payFormDeduct').value) || 0
    var payload = {
      employee_name: document.getElementById('payFormEmployee').value,
      period: document.getElementById('payFormPeriod').value,
      basic_salary: basic,
      allowances: allow,
      deductions: deduct,
      net_pay: basic + allow - deduct,
      status: document.getElementById('payFormStatus').value
    }
    try {
      if (id) { await window.payrollService.update(id, payload) } else { await window.payrollService.create(payload) }
      app.toast('Payroll entry saved', 'success')
      document.getElementById('content').innerHTML = this.render()
    } catch (e) { app.toast('Error saving entry: ' + e.message, 'error') }
    return false
  },
  async deleteEntry(id) {
    if (!confirm('Delete this payroll entry?')) return
    try { await window.payrollService.remove(id); app.toast('Entry deleted', 'success'); document.getElementById('content').innerHTML = this.render() } catch (e) { app.toast('Error deleting: ' + e.message, 'error') }
  }
}
