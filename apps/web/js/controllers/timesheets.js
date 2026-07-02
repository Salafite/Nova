window.NovaModules = window.NovaModules || {}; window.NovaModules['timesheets'] = {
  render() {
    var search = this.searchTerm || ''
    var items = window.timesheetService.getAll()
    var filtered = search ? items.filter(function(t) { return (t.employeeName || '').toLowerCase().indexOf(search) > -1 || (t.project || '').toLowerCase().indexOf(search) > -1 }) : items
    var rows = filtered.map(function(t) {
      var statusBadge = t.status === 'Approved' ? '<span class="px-sm py-xs bg-secondary-container text-on-secondary-container rounded text-[11px] font-bold uppercase">Approved</span>' : (t.status === 'Pending' || t.status === 'Submitted' ? '<span class="px-sm py-xs bg-warning/10 text-warning rounded text-[11px] font-bold uppercase">Pending</span>' : '<span class="px-sm py-xs bg-surface-container-high text-on-surface-variant rounded text-[11px] font-bold uppercase">' + escapeHtml(t.status || 'Draft') + '</span>')
      var hours = parseFloat(t.hours) || 0
      return '<tr class="hover:bg-primary-container/5 transition-colors group">' +
             '<td class="px-lg py-md"><div class="font-medium text-on-surface">' + escapeHtml(t.employeeName || '-') + '</div></td>' +
             '<td class="px-lg py-md text-body-md text-on-surface-variant">' + escapeHtml(t.project || '-') + '</td>' +
             '<td class="px-lg py-md text-body-md text-on-surface-variant">' + escapeHtml(t.date || '-') + '</td>' +
             '<td class="px-lg py-md font-data-mono text-data-mono text-on-surface">' + hours.toFixed(1) + '</td>' +
             '<td class="px-lg py-md">' + statusBadge + '</td>' +
             '<td class="px-lg py-md text-right"><div class="flex items-center justify-end gap-1">' +
             '<button class="p-1 hover:bg-surface-variant rounded-full text-primary" onclick="controllers.timesheets.approveEntry(\'' + t.id + '\')"><span class="material-symbols-outlined text-[20px]">check</span></button>' +
             '<button class="p-1 hover:bg-error-container rounded-full text-error" onclick="controllers.timesheets.deleteItem(\'' + t.id + '\')"><span class="material-symbols-outlined text-[20px]">delete</span></button>' +
             '</div></td>' +
             '</tr>'
    }).join('')
    return renderHtml('screens/timesheets', {
      timesheetRows: rows,
      totalHours: window.timesheetService.getTotalHours().toFixed(1),
      pendingApproval: window.timesheetService.getPendingCount(),
      billableHours: window.timesheetService.getBillableHours().toFixed(1)
    })
  },
  mount() { controllers.timesheets = this; var s = document.getElementById('timesheetSearch'); if (s) s.value = this.searchTerm || '' },
  search(q) { this.searchTerm = q.toLowerCase(); document.getElementById('content').innerHTML = this.render() },
  showCreateForm() {
    document.getElementById('content').innerHTML = renderHtml('models/inspection/form', {
      title: 'New Timesheet Entry', id: '', employeeName: '', project: '', date: '', hours: '', billable: 'true', status: 'Draft'
    })
  },
  async saveForm() {
    var id = document.getElementById('inspectionFormId') ? document.getElementById('inspectionFormId').value : ''
    try {
      if (id) {
        await window.timesheetService.update(id, { status: 'Submitted' })
      } else {
        await window.timesheetService.create({
          employeeName: document.getElementById('inspectionFormProduct') ? document.getElementById('inspectionFormProduct').value : 'Employee',
          project: '',
          date: new Date().toISOString().split('T')[0],
          hours: 8,
          status: 'Draft',
          billable: true
        })
        app.toast('Timesheet entry created', 'success')
      }
      document.getElementById('content').innerHTML = this.render()
    } catch (e) {
      app.toast('Error saving timesheet entry: ' + e.message, 'error')
    }
    return false
  },
  async approveEntry(id) {
    try {
      await window.timesheetService.update(id, { status: 'Approved' })
      app.toast('Timesheet approved', 'success')
      document.getElementById('content').innerHTML = this.render()
    } catch (e) {
      app.toast('Error approving timesheet: ' + e.message, 'error')
    }
  },
  async deleteItem(id) {
    if (!confirm('Delete this timesheet entry?')) return
    try {
      await window.timesheetService.remove(id)
      document.getElementById('content').innerHTML = this.render()
    } catch (e) {
      app.toast('Error deleting timesheet: ' + e.message, 'error')
    }
  }
}
