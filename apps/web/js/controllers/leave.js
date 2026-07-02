window.NovaModules = window.NovaModules || {}; window.NovaModules['leave'] = {
  render() {
    var search = this.searchTerm || ''
    var items = window.leaveService.getAll()
    var filtered = search ? items.filter(function(l) { return (l.employee_name || '').toLowerCase().indexOf(search) > -1 || (l.leave_type || '').toLowerCase().indexOf(search) > -1 || (l.status || '').toLowerCase().indexOf(search) > -1 }) : items
    var rows = filtered.map(function(l) {
      var statusBadge = l.status === 'Approved' ? '<span class="px-sm py-xs bg-secondary/10 text-secondary rounded text-[11px] font-medium uppercase">Approved</span>' :
                        (l.status === 'Rejected' ? '<span class="px-sm py-xs bg-error/10 text-error rounded text-[11px] font-medium uppercase">Rejected</span>' :
                        '<span class="px-sm py-xs bg-surface-container-highest text-on-surface-variant rounded text-[11px] font-medium uppercase">' + escapeHtml(l.status) + '</span>')
      return '<tr class="hover:bg-primary/5 transition-colors group">' +
             '<td class="px-lg py-md font-body-md font-semibold text-on-surface">' + escapeHtml(l.employee_name) + '</td>' +
             '<td class="px-lg py-md text-body-md text-on-surface-variant">' + escapeHtml(l.leave_type) + '</td>' +
             '<td class="px-lg py-md text-body-md text-on-surface-variant">' + escapeHtml(l.start_date) + '</td>' +
             '<td class="px-lg py-md text-body-md text-on-surface-variant">' + escapeHtml(l.end_date) + '</td>' +
             '<td class="px-lg py-md text-center font-data-mono">' + (l.days || 0) + '</td>' +
             '<td class="px-lg py-md text-center">' + statusBadge + '</td>' +
             '<td class="px-lg py-md text-center opacity-0 group-hover:opacity-100 transition-opacity">' +
             '<div class="flex items-center justify-center gap-1">' +
             '<button class="p-1 hover:bg-surface-variant rounded-full text-primary" onclick="controllers.leave.showEditForm(' + l.id + ')"><span class="material-symbols-outlined text-[20px]">edit</span></button>' +
             '<button class="p-1 hover:bg-error-container rounded-full text-error" onclick="controllers.leave.deleteRequest(' + l.id + ')"><span class="material-symbols-outlined text-[20px]">delete</span></button>' +
             '</div></td></tr>'
    }).join('')
    var pendingCount = items.filter(function(l) { return l.status === 'Pending' }).length
    var approvedCount = items.filter(function(l) { return l.status === 'Approved' }).length
    var rejectedCount = items.filter(function(l) { return l.status === 'Rejected' }).length
    return renderHtml('screens/leave_management', {
      rows: rows,
      pendingCount: pendingCount,
      approvedCount: approvedCount,
      rejectedCount: rejectedCount
    })
  },
  mount() { controllers.leave = this; var s = document.getElementById('leaveSearch'); if (s) s.value = this.searchTerm || '' },
  search(q) { this.searchTerm = q.toLowerCase(); document.getElementById('content').innerHTML = this.render() },
  async refresh() { await window.leaveService.load(); document.getElementById('content').innerHTML = this.render() },
  showCreateForm() {
    document.getElementById('content').innerHTML =
      '<div class="max-w-2xl mx-auto bg-surface-container-lowest border border-outline-variant rounded-xl p-lg shadow-sm">' +
      '<h3 class="font-title-md text-title-md font-bold mb-lg">New Leave Request</h3>' +
      '<form onsubmit="return controllers.leave.saveForm()">' +
      '<input type="hidden" id="leaveFormId" value="" />' +
      '<div class="grid grid-cols-1 md:grid-cols-2 gap-md mb-md">' +
      '<div class="flex flex-col gap-xs"><label class="font-label-sm text-label-sm font-bold text-on-surface-variant uppercase">Employee Name</label><input id="leaveFormEmployee" required class="w-full bg-surface border border-outline-variant rounded-lg px-3 py-2 text-body-md focus:ring-2 focus:ring-primary/20" /></div>' +
      '<div class="flex flex-col gap-xs"><label class="font-label-sm text-label-sm font-bold text-on-surface-variant uppercase">Leave Type</label><select id="leaveFormType" class="w-full bg-surface border border-outline-variant rounded-lg px-3 py-2 text-body-md focus:ring-2 focus:ring-primary/20"><option value="Annual">Annual</option><option value="Sick">Sick</option><option value="Personal">Personal</option><option value="Maternity">Maternity</option></select></div>' +
      '<div class="flex flex-col gap-xs"><label class="font-label-sm text-label-sm font-bold text-on-surface-variant uppercase">Start Date</label><input id="leaveFormStart" type="date" required class="w-full bg-surface border border-outline-variant rounded-lg px-3 py-2 text-body-md focus:ring-2 focus:ring-primary/20" /></div>' +
      '<div class="flex flex-col gap-xs"><label class="font-label-sm text-label-sm font-bold text-on-surface-variant uppercase">End Date</label><input id="leaveFormEnd" type="date" required class="w-full bg-surface border border-outline-variant rounded-lg px-3 py-2 text-body-md focus:ring-2 focus:ring-primary/20" /></div>' +
      '<div class="flex flex-col gap-xs col-span-2"><label class="font-label-sm text-label-sm font-bold text-on-surface-variant uppercase">Reason</label><textarea id="leaveFormReason" rows="2" class="w-full bg-surface border border-outline-variant rounded-lg px-3 py-2 text-body-md focus:ring-2 focus:ring-primary/20"></textarea></div>' +
      '</div>' +
      '<div class="flex gap-sm mt-lg"><button type="submit" class="bg-primary text-on-primary px-lg py-sm rounded-lg font-label-md press-effect">Save</button>' +
      '<button type="button" class="bg-surface border border-outline-variant text-on-surface-variant px-lg py-sm rounded-lg font-label-md press-effect" onclick="controllers.leave.render()">Cancel</button></div>' +
      '</form></div>'
  },
  showEditForm(id) {
    var l = window.leaveService.getById(id)
    if (!l) return
    var typeOpts = ['Annual', 'Sick', 'Personal', 'Maternity'].map(function(t) { return '<option value="' + t + '"' + (t === l.leave_type ? ' selected' : '') + '>' + t + '</option>' }).join('')
    document.getElementById('content').innerHTML =
      '<div class="max-w-2xl mx-auto bg-surface-container-lowest border border-outline-variant rounded-xl p-lg shadow-sm">' +
      '<h3 class="font-title-md text-title-md font-bold mb-lg">Edit Leave Request</h3>' +
      '<form onsubmit="return controllers.leave.saveForm()">' +
      '<input type="hidden" id="leaveFormId" value="' + l.id + '" />' +
      '<div class="grid grid-cols-1 md:grid-cols-2 gap-md mb-md">' +
      '<div class="flex flex-col gap-xs"><label class="font-label-sm text-label-sm font-bold text-on-surface-variant uppercase">Employee Name</label><input id="leaveFormEmployee" value="' + escapeHtml(l.employee_name) + '" required class="w-full bg-surface border border-outline-variant rounded-lg px-3 py-2 text-body-md focus:ring-2 focus:ring-primary/20" /></div>' +
      '<div class="flex flex-col gap-xs"><label class="font-label-sm text-label-sm font-bold text-on-surface-variant uppercase">Leave Type</label><select id="leaveFormType" class="w-full bg-surface border border-outline-variant rounded-lg px-3 py-2 text-body-md focus:ring-2 focus:ring-primary/20">' + typeOpts + '</select></div>' +
      '<div class="flex flex-col gap-xs"><label class="font-label-sm text-label-sm font-bold text-on-surface-variant uppercase">Start Date</label><input id="leaveFormStart" type="date" value="' + escapeHtml(l.start_date) + '" required class="w-full bg-surface border border-outline-variant rounded-lg px-3 py-2 text-body-md focus:ring-2 focus:ring-primary/20" /></div>' +
      '<div class="flex flex-col gap-xs"><label class="font-label-sm text-label-sm font-bold text-on-surface-variant uppercase">End Date</label><input id="leaveFormEnd" type="date" value="' + escapeHtml(l.end_date) + '" required class="w-full bg-surface border border-outline-variant rounded-lg px-3 py-2 text-body-md focus:ring-2 focus:ring-primary/20" /></div>' +
      '<div class="flex flex-col gap-xs col-span-2"><label class="font-label-sm text-label-sm font-bold text-on-surface-variant uppercase">Reason</label><textarea id="leaveFormReason" rows="2" class="w-full bg-surface border border-outline-variant rounded-lg px-3 py-2 text-body-md focus:ring-2 focus:ring-primary/20">' + escapeHtml(l.reason || '') + '</textarea></div>' +
      '</div>' +
      '<div class="flex gap-sm mt-lg"><button type="submit" class="bg-primary text-on-primary px-lg py-sm rounded-lg font-label-md press-effect">Save</button>' +
      '<button type="button" class="bg-surface border border-outline-variant text-on-surface-variant px-lg py-sm rounded-lg font-label-md press-effect" onclick="controllers.leave.render()">Cancel</button></div>' +
      '</form></div>'
  },
  async saveForm() {
    var id = document.getElementById('leaveFormId').value
    var start = document.getElementById('leaveFormStart').value
    var end = document.getElementById('leaveFormEnd').value
    var days = 0
    if (start && end) { days = Math.max(1, Math.floor((new Date(end) - new Date(start)) / (1000 * 60 * 60 * 24)) + 1) }
    var payload = {
      employee_name: document.getElementById('leaveFormEmployee').value,
      leave_type: document.getElementById('leaveFormType').value,
      start_date: start,
      end_date: end,
      days: days,
      reason: document.getElementById('leaveFormReason').value,
      status: 'Pending'
    }
    try {
      if (id) { await window.leaveService.update(id, payload) } else { await window.leaveService.create(payload) }
      app.toast('Leave request saved', 'success')
      document.getElementById('content').innerHTML = this.render()
    } catch (e) { app.toast('Error saving request: ' + e.message, 'error') }
    return false
  },
  async deleteRequest(id) {
    if (!confirm('Delete this leave request?')) return
    try { await window.leaveService.remove(id); app.toast('Request deleted', 'success'); document.getElementById('content').innerHTML = this.render() } catch (e) { app.toast('Error deleting: ' + e.message, 'error') }
  }
}
