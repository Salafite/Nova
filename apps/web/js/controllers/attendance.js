window.NovaModules = window.NovaModules || {}; window.NovaModules['attendance'] = {
  render() {
    var search = this.searchTerm || ''
    var items = window.attendanceService.getAll()
    var filtered = search ? items.filter(function(a) { return (a.employee_name || '').toLowerCase().indexOf(search) > -1 || (a.date || '').indexOf(search) > -1 }) : items
    var rows = filtered.map(function(a) {
      var statusBadge = a.status === 'Present' ? '<span class="px-sm py-xs bg-secondary/10 text-secondary rounded text-[11px] font-medium uppercase">Present</span>' :
                        (a.status === 'Absent' ? '<span class="px-sm py-xs bg-error/10 text-error rounded text-[11px] font-medium uppercase">Absent</span>' :
                        '<span class="px-sm py-xs bg-surface-container-highest text-on-surface-variant rounded text-[11px] font-medium uppercase">' + escapeHtml(a.status) + '</span>')
      return '<tr class="hover:bg-primary/5 transition-colors group">' +
             '<td class="px-lg py-md font-body-md font-semibold text-on-surface">' + escapeHtml(a.employee_name) + '</td>' +
             '<td class="px-lg py-md text-body-md text-on-surface-variant">' + escapeHtml(a.date) + '</td>' +
             '<td class="px-lg py-md font-data-mono">' + escapeHtml(a.clock_in || '-') + '</td>' +
             '<td class="px-lg py-md font-data-mono">' + escapeHtml(a.clock_out || '-') + '</td>' +
             '<td class="px-lg py-md text-center">' + statusBadge + '</td>' +
             '<td class="px-lg py-md text-center opacity-0 group-hover:opacity-100 transition-opacity">' +
             '<div class="flex items-center justify-center gap-1">' +
             '<button class="p-1 hover:bg-surface-variant rounded-full text-primary" onclick="controllers.attendance.showEditForm(' + a.id + ')"><span class="material-symbols-outlined text-[20px]">edit</span></button>' +
             '<button class="p-1 hover:bg-error-container rounded-full text-error" onclick="controllers.attendance.deleteRecord(' + a.id + ')"><span class="material-symbols-outlined text-[20px]">delete</span></button>' +
             '</div></td></tr>'
    }).join('')
    var presentCount = items.filter(function(a) { return a.status === 'Present' }).length
    var absentCount = items.filter(function(a) { return a.status === 'Absent' }).length
    var leaveCount = items.filter(function(a) { return a.status === 'Leave' || a.status === 'On Leave' }).length
    return renderHtml('screens/attendance___time_tracking', {
      rows: rows,
      presentCount: presentCount,
      absentCount: absentCount,
      leaveCount: leaveCount
    })
  },
  mount() { controllers.attendance = this; var s = document.getElementById('attSearch'); if (s) s.value = this.searchTerm || '' },
  search(q) { this.searchTerm = q.toLowerCase(); document.getElementById('content').innerHTML = this.render() },
  async refresh() { await window.attendanceService.load(); document.getElementById('content').innerHTML = this.render() },
  showCreateForm() {
    document.getElementById('content').innerHTML =
      '<div class="max-w-2xl mx-auto bg-surface-container-lowest border border-outline-variant rounded-xl p-lg shadow-sm">' +
      '<h3 class="font-title-md text-title-md font-bold mb-lg">Add Attendance Record</h3>' +
      '<form onsubmit="return controllers.attendance.saveForm()">' +
      '<input type="hidden" id="attFormId" value="" />' +
      '<div class="grid grid-cols-1 md:grid-cols-2 gap-md mb-md">' +
      '<div class="flex flex-col gap-xs"><label class="font-label-sm text-label-sm font-bold text-on-surface-variant uppercase">Employee Name</label><input id="attFormEmployee" required class="w-full bg-surface border border-outline-variant rounded-lg px-3 py-2 text-body-md focus:ring-2 focus:ring-primary/20" /></div>' +
      '<div class="flex flex-col gap-xs"><label class="font-label-sm text-label-sm font-bold text-on-surface-variant uppercase">Date</label><input id="attFormDate" type="date" required class="w-full bg-surface border border-outline-variant rounded-lg px-3 py-2 text-body-md focus:ring-2 focus:ring-primary/20" /></div>' +
      '<div class="flex flex-col gap-xs"><label class="font-label-sm text-label-sm font-bold text-on-surface-variant uppercase">Clock In</label><input id="attFormIn" type="time" class="w-full bg-surface border border-outline-variant rounded-lg px-3 py-2 text-body-md focus:ring-2 focus:ring-primary/20" /></div>' +
      '<div class="flex flex-col gap-xs"><label class="font-label-sm text-label-sm font-bold text-on-surface-variant uppercase">Clock Out</label><input id="attFormOut" type="time" class="w-full bg-surface border border-outline-variant rounded-lg px-3 py-2 text-body-md focus:ring-2 focus:ring-primary/20" /></div>' +
      '<div class="flex flex-col gap-xs"><label class="font-label-sm text-label-sm font-bold text-on-surface-variant uppercase">Status</label><select id="attFormStatus" class="w-full bg-surface border border-outline-variant rounded-lg px-3 py-2 text-body-md focus:ring-2 focus:ring-primary/20"><option value="Present">Present</option><option value="Absent">Absent</option><option value="Leave">On Leave</option></select></div>' +
      '</div>' +
      '<div class="flex gap-sm mt-lg"><button type="submit" class="bg-primary text-on-primary px-lg py-sm rounded-lg font-label-md press-effect">Save</button>' +
      '<button type="button" class="bg-surface border border-outline-variant text-on-surface-variant px-lg py-sm rounded-lg font-label-md press-effect" onclick="controllers.attendance.render()">Cancel</button></div>' +
      '</form></div>'
  },
  showEditForm(id) {
    var a = window.attendanceService.getById(id)
    if (!a) return
    var statusOpts = ['Present', 'Absent', 'Leave'].map(function(s) { return '<option value="' + s + '"' + (s === a.status ? ' selected' : '') + '>' + s + '</option>' }).join('')
    document.getElementById('content').innerHTML =
      '<div class="max-w-2xl mx-auto bg-surface-container-lowest border border-outline-variant rounded-xl p-lg shadow-sm">' +
      '<h3 class="font-title-md text-title-md font-bold mb-lg">Edit Attendance Record</h3>' +
      '<form onsubmit="return controllers.attendance.saveForm()">' +
      '<input type="hidden" id="attFormId" value="' + a.id + '" />' +
      '<div class="grid grid-cols-1 md:grid-cols-2 gap-md mb-md">' +
      '<div class="flex flex-col gap-xs"><label class="font-label-sm text-label-sm font-bold text-on-surface-variant uppercase">Employee Name</label><input id="attFormEmployee" value="' + escapeHtml(a.employee_name) + '" required class="w-full bg-surface border border-outline-variant rounded-lg px-3 py-2 text-body-md focus:ring-2 focus:ring-primary/20" /></div>' +
      '<div class="flex flex-col gap-xs"><label class="font-label-sm text-label-sm font-bold text-on-surface-variant uppercase">Date</label><input id="attFormDate" type="date" value="' + escapeHtml(a.date) + '" required class="w-full bg-surface border border-outline-variant rounded-lg px-3 py-2 text-body-md focus:ring-2 focus:ring-primary/20" /></div>' +
      '<div class="flex flex-col gap-xs"><label class="font-label-sm text-label-sm font-bold text-on-surface-variant uppercase">Clock In</label><input id="attFormIn" type="time" value="' + escapeHtml(a.clock_in || '') + '" class="w-full bg-surface border border-outline-variant rounded-lg px-3 py-2 text-body-md focus:ring-2 focus:ring-primary/20" /></div>' +
      '<div class="flex flex-col gap-xs"><label class="font-label-sm text-label-sm font-bold text-on-surface-variant uppercase">Clock Out</label><input id="attFormOut" type="time" value="' + escapeHtml(a.clock_out || '') + '" class="w-full bg-surface border border-outline-variant rounded-lg px-3 py-2 text-body-md focus:ring-2 focus:ring-primary/20" /></div>' +
      '<div class="flex flex-col gap-xs"><label class="font-label-sm text-label-sm font-bold text-on-surface-variant uppercase">Status</label><select id="attFormStatus" class="w-full bg-surface border border-outline-variant rounded-lg px-3 py-2 text-body-md focus:ring-2 focus:ring-primary/20">' + statusOpts + '</select></div>' +
      '</div>' +
      '<div class="flex gap-sm mt-lg"><button type="submit" class="bg-primary text-on-primary px-lg py-sm rounded-lg font-label-md press-effect">Save</button>' +
      '<button type="button" class="bg-surface border border-outline-variant text-on-surface-variant px-lg py-sm rounded-lg font-label-md press-effect" onclick="controllers.attendance.render()">Cancel</button></div>' +
      '</form></div>'
  },
  async saveForm() {
    var id = document.getElementById('attFormId').value
    var payload = {
      employee_name: document.getElementById('attFormEmployee').value,
      date: document.getElementById('attFormDate').value,
      clock_in: document.getElementById('attFormIn').value,
      clock_out: document.getElementById('attFormOut').value,
      status: document.getElementById('attFormStatus').value
    }
    try {
      if (id) { await window.attendanceService.update(id, payload) } else { await window.attendanceService.create(payload) }
      app.toast('Attendance record saved', 'success')
      document.getElementById('content').innerHTML = this.render()
    } catch (e) { app.toast('Error saving record: ' + e.message, 'error') }
    return false
  },
  async deleteRecord(id) {
    if (!confirm('Delete this record?')) return
    try { await window.attendanceService.remove(id); app.toast('Record deleted', 'success'); document.getElementById('content').innerHTML = this.render() } catch (e) { app.toast('Error deleting: ' + e.message, 'error') }
  }
}
