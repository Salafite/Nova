window.NovaModules = window.NovaModules || {}; window.NovaModules['hr'] = {
  render() {
    var search = this.searchTerm || ''
    var deptSearch = this.deptSearchTerm || ''
    var employees = window.employeeService.getAll()
    var departments = window.employeeService.getDepartments()
    var filteredEmps = search ? employees.filter(function(e) { return (e.name || '').toLowerCase().indexOf(search) > -1 || (e.email || '').toLowerCase().indexOf(search) > -1 || (e.department || '').toLowerCase().indexOf(search) > -1 }) : employees
    var filteredDepts = deptSearch ? departments.filter(function(d) { return (d.name || '').toLowerCase().indexOf(deptSearch) > -1 || (d.head || '').toLowerCase().indexOf(deptSearch) > -1 }) : departments
    var employeeRows = filteredEmps.map(function(e) {
      var statusBadge = e.status === 'Active' ? '<span class="px-sm py-xs bg-secondary/10 text-secondary rounded text-[11px] font-medium uppercase">Active</span>' : '<span class="px-sm py-xs bg-surface-container-highest text-on-surface-variant rounded text-[11px] font-medium uppercase">' + escapeHtml(e.status || 'Inactive') + '</span>'
      return '<tr class="hover:bg-primary/5 transition-colors group">' +
             '<td class="px-lg py-md font-body-md font-semibold text-on-surface">' + escapeHtml(e.name) + '</td>' +
             '<td class="px-lg py-md text-body-md text-on-surface-variant">' + escapeHtml(e.department || '-') + '</td>' +
             '<td class="px-lg py-md text-body-md text-on-surface-variant">' + escapeHtml(e.designation || '-') + '</td>' +
             '<td class="px-lg py-md text-body-md text-on-surface-variant">' + escapeHtml(e.email || '-') + '</td>' +
             '<td class="px-lg py-md text-center">' + statusBadge + '</td>' +
             '<td class="px-lg py-md text-center opacity-0 group-hover:opacity-100 transition-opacity">' +
             '<div class="flex items-center justify-center gap-1">' +
             '<button class="p-1 hover:bg-surface-variant rounded-full text-primary" onclick="controllers.hr.showEditForm(' + e.id + ')"><span class="material-symbols-outlined text-[20px]">edit</span></button>' +
             '<button class="p-1 hover:bg-error-container rounded-full text-error" onclick="controllers.hr.deleteEmployee(' + e.id + ')"><span class="material-symbols-outlined text-[20px]">delete</span></button>' +
             '</div></td></tr>'
    }).join('')
    var departmentRows = filteredDepts.map(function(d) {
      return '<tr class="hover:bg-primary/5 transition-colors">' +
             '<td class="px-lg py-md font-body-md font-semibold text-on-surface">' + escapeHtml(d.name) + '</td>' +
             '<td class="px-lg py-md text-body-md text-on-surface-variant">' + escapeHtml(d.head || '-') + '</td>' +
             '<td class="px-lg py-md text-center font-data-mono">' + (d.employee_count || 0) + '</td></tr>'
    }).join('')
    return renderHtml('screens/hrms_foundation', {
      employeeRows: employeeRows,
      departmentRows: departmentRows,
      employeeCount: employees.length,
      departmentCount: departments.length,
      activeContracts: employees.filter(function(e) { return e.status === 'Active' }).length
    })
  },
  mount() { controllers.hr = this; var s = document.getElementById('hrSearch'); if (s) s.value = this.searchTerm || ''; var ds = document.getElementById('deptSearch'); if (ds) ds.value = this.deptSearchTerm || '' },
  search(q) { this.searchTerm = q.toLowerCase(); document.getElementById('content').innerHTML = this.render() },
  deptSearch(q) { this.deptSearchTerm = q.toLowerCase(); document.getElementById('content').innerHTML = this.render() },
  async refresh() { await window.employeeService.load(); document.getElementById('content').innerHTML = this.render() },
  showCreateForm() {
    var depts = window.employeeService.getDepartments()
    var deptOptions = depts.map(function(d) { return '<option value="' + escapeHtml(d.name) + '">' + escapeHtml(d.name) + '</option>' }).join('')
    document.getElementById('content').innerHTML =
      '<div class="max-w-2xl mx-auto bg-surface-container-lowest border border-outline-variant rounded-xl p-lg shadow-sm">' +
      '<h3 class="font-title-md text-title-md font-bold mb-lg">Add Employee</h3>' +
      '<form onsubmit="return controllers.hr.saveForm()">' +
      '<input type="hidden" id="empFormId" value="" />' +
      '<div class="grid grid-cols-1 md:grid-cols-2 gap-md mb-md">' +
      '<div class="flex flex-col gap-xs"><label class="font-label-sm text-label-sm font-bold text-on-surface-variant uppercase">Name</label><input id="empFormName" required class="w-full bg-surface border border-outline-variant rounded-lg px-3 py-2 text-body-md focus:ring-2 focus:ring-primary/20" /></div>' +
      '<div class="flex flex-col gap-xs"><label class="font-label-sm text-label-sm font-bold text-on-surface-variant uppercase">Email</label><input id="empFormEmail" type="email" required class="w-full bg-surface border border-outline-variant rounded-lg px-3 py-2 text-body-md focus:ring-2 focus:ring-primary/20" /></div>' +
      '<div class="flex flex-col gap-xs"><label class="font-label-sm text-label-sm font-bold text-on-surface-variant uppercase">Phone</label><input id="empFormPhone" class="w-full bg-surface border border-outline-variant rounded-lg px-3 py-2 text-body-md focus:ring-2 focus:ring-primary/20" /></div>' +
      '<div class="flex flex-col gap-xs"><label class="font-label-sm text-label-sm font-bold text-on-surface-variant uppercase">Department</label><select id="empFormDept" class="w-full bg-surface border border-outline-variant rounded-lg px-3 py-2 text-body-md focus:ring-2 focus:ring-primary/20">' + deptOptions + '</select></div>' +
      '<div class="flex flex-col gap-xs"><label class="font-label-sm text-label-sm font-bold text-on-surface-variant uppercase">Designation</label><input id="empFormDesig" class="w-full bg-surface border border-outline-variant rounded-lg px-3 py-2 text-body-md focus:ring-2 focus:ring-primary/20" /></div>' +
      '<div class="flex flex-col gap-xs"><label class="font-label-sm text-label-sm font-bold text-on-surface-variant uppercase">Hire Date</label><input id="empFormHireDate" type="date" class="w-full bg-surface border border-outline-variant rounded-lg px-3 py-2 text-body-md focus:ring-2 focus:ring-primary/20" /></div>' +
      '</div>' +
      '<div class="flex gap-sm mt-lg"><button type="submit" class="bg-primary text-on-primary px-lg py-sm rounded-lg font-label-md press-effect">Save</button>' +
      '<button type="button" class="bg-surface border border-outline-variant text-on-surface-variant px-lg py-sm rounded-lg font-label-md press-effect" onclick="controllers.hr.render()">Cancel</button></div>' +
      '</form></div>'
  },
  showEditForm(id) {
    var e = window.employeeService.getById(id)
    if (!e) return
    var depts = window.employeeService.getDepartments()
    var deptOptions = depts.map(function(d) { return '<option value="' + escapeHtml(d.name) + '"' + (d.name === e.department ? ' selected' : '') + '>' + escapeHtml(d.name) + '</option>' }).join('')
    document.getElementById('content').innerHTML =
      '<div class="max-w-2xl mx-auto bg-surface-container-lowest border border-outline-variant rounded-xl p-lg shadow-sm">' +
      '<h3 class="font-title-md text-title-md font-bold mb-lg">Edit Employee</h3>' +
      '<form onsubmit="return controllers.hr.saveForm()">' +
      '<input type="hidden" id="empFormId" value="' + e.id + '" />' +
      '<div class="grid grid-cols-1 md:grid-cols-2 gap-md mb-md">' +
      '<div class="flex flex-col gap-xs"><label class="font-label-sm text-label-sm font-bold text-on-surface-variant uppercase">Name</label><input id="empFormName" value="' + escapeHtml(e.name) + '" required class="w-full bg-surface border border-outline-variant rounded-lg px-3 py-2 text-body-md focus:ring-2 focus:ring-primary/20" /></div>' +
      '<div class="flex flex-col gap-xs"><label class="font-label-sm text-label-sm font-bold text-on-surface-variant uppercase">Email</label><input id="empFormEmail" type="email" value="' + escapeHtml(e.email || '') + '" required class="w-full bg-surface border border-outline-variant rounded-lg px-3 py-2 text-body-md focus:ring-2 focus:ring-primary/20" /></div>' +
      '<div class="flex flex-col gap-xs"><label class="font-label-sm text-label-sm font-bold text-on-surface-variant uppercase">Phone</label><input id="empFormPhone" value="' + escapeHtml(e.phone || '') + '" class="w-full bg-surface border border-outline-variant rounded-lg px-3 py-2 text-body-md focus:ring-2 focus:ring-primary/20" /></div>' +
      '<div class="flex flex-col gap-xs"><label class="font-label-sm text-label-sm font-bold text-on-surface-variant uppercase">Department</label><select id="empFormDept" class="w-full bg-surface border border-outline-variant rounded-lg px-3 py-2 text-body-md focus:ring-2 focus:ring-primary/20">' + deptOptions + '</select></div>' +
      '<div class="flex flex-col gap-xs"><label class="font-label-sm text-label-sm font-bold text-on-surface-variant uppercase">Designation</label><input id="empFormDesig" value="' + escapeHtml(e.designation || '') + '" class="w-full bg-surface border border-outline-variant rounded-lg px-3 py-2 text-body-md focus:ring-2 focus:ring-primary/20" /></div>' +
      '<div class="flex flex-col gap-xs"><label class="font-label-sm text-label-sm font-bold text-on-surface-variant uppercase">Hire Date</label><input id="empFormHireDate" type="date" value="' + escapeHtml(e.hire_date || '') + '" class="w-full bg-surface border border-outline-variant rounded-lg px-3 py-2 text-body-md focus:ring-2 focus:ring-primary/20" /></div>' +
      '</div>' +
      '<div class="flex gap-sm mt-lg"><button type="submit" class="bg-primary text-on-primary px-lg py-sm rounded-lg font-label-md press-effect">Save</button>' +
      '<button type="button" class="bg-surface border border-outline-variant text-on-surface-variant px-lg py-sm rounded-lg font-label-md press-effect" onclick="controllers.hr.render()">Cancel</button></div>' +
      '</form></div>'
  },
  async saveForm() {
    var id = document.getElementById('empFormId').value
    var payload = {
      name: document.getElementById('empFormName').value,
      email: document.getElementById('empFormEmail').value,
      phone: document.getElementById('empFormPhone').value,
      department: document.getElementById('empFormDept').value,
      designation: document.getElementById('empFormDesig').value,
      hire_date: document.getElementById('empFormHireDate').value,
      status: 'Active'
    }
    try {
      if (id) { await window.employeeService.update(id, payload) } else { await window.employeeService.create(payload) }
      app.toast('Employee saved', 'success')
      document.getElementById('content').innerHTML = this.render()
    } catch (e) { app.toast('Error saving employee: ' + e.message, 'error') }
    return false
  },
  async deleteEmployee(id) {
    if (!confirm('Delete this employee?')) return
    try { await window.employeeService.remove(id); app.toast('Employee deleted', 'success'); document.getElementById('content').innerHTML = this.render() } catch (e) { app.toast('Error deleting: ' + e.message, 'error') }
  }
}
