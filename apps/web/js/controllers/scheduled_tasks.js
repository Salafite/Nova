window.NovaModules = window.NovaModules || {}; window.NovaModules['scheduled_tasks'] = {
  _statusBadge(status) {
    var map = { Idle: 'bg-surface-container text-on-surface-variant border border-outline-variant', Running: 'bg-warning/10 text-warning border border-warning/20', Failed: 'bg-error/10 text-error border border-error/20', Completed: 'bg-secondary/10 text-secondary border border-secondary/20' }
    var cls = map[status] || map.Idle
    return '<span class="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-bold uppercase ' + cls + '">' + escapeHtml(status) + '</span>'
  },
  _taskRow(t) {
    var canRun = t.status === 'Idle' || t.status === 'Failed'
    return '<tr class="hover:bg-primary/5 transition-colors group">' +
      '<td class="px-lg py-md font-body-md font-semibold text-primary">' + escapeHtml(t.taskName) + '</td>' +
      '<td class="px-lg py-md text-body-md text-on-surface-variant">' + escapeHtml(t.taskType) + '</td>' +
      '<td class="px-lg py-md font-data-mono text-data-mono text-on-surface-variant">' + escapeHtml(t.cronExpression) + '</td>' +
      '<td class="px-lg py-md font-data-mono text-data-mono text-on-surface-variant">' + (t.lastRunAt ? new Date(t.lastRunAt).toLocaleString() : '-') + '</td>' +
      '<td class="px-lg py-md font-data-mono text-data-mono text-on-surface-variant">' + (t.nextRunAt ? new Date(t.nextRunAt).toLocaleString() : '-') + '</td>' +
      '<td class="px-lg py-md">' + this._statusBadge(t.status) + '</td>' +
      '<td class="px-lg py-md text-center">' +
        (canRun ? '<button class="p-1 hover:bg-primary-container rounded text-primary" onclick="controllers.scheduled_tasks.runTask(' + t.id + ')" title="Run Now"><span class="material-symbols-outlined text-[18px]">play_arrow</span></button>' : '') +
        '<button class="p-1 hover:bg-primary-container rounded text-primary" onclick="controllers.scheduled_tasks.editTask(' + t.id + ')" title="Edit"><span class="material-symbols-outlined text-[18px]">edit</span></button>' +
        '<button class="p-1 hover:bg-error-container rounded text-error" onclick="controllers.scheduled_tasks.deleteTask(' + t.id + ')" title="Delete"><span class="material-symbols-outlined text-[18px]">delete</span></button>' +
      '</td></tr>'
  },
  render() {
    var list = window.scheduledTaskService.getAll()
    var total = list.length
    var active = window.scheduledTaskService.getActiveCount()
    var running = window.scheduledTaskService.getRunningCount()
    var rows = list.map(this._taskRow.bind(this)).join('')
    return renderHtml('screens/scheduled_tasks', {
      total: total,
      active: active,
      running: running,
      rows: rows
    })
  },
  mount() { controllers.scheduled_tasks = this },
  showAddForm() {
    document.getElementById('content').innerHTML = renderHtml('screens/scheduled_tasks_form', {
      title: 'Add Scheduled Task', id: '', taskName: '', taskType: 'EmailReport', cronExpression: '', description: '', config: '', isActive: 'checked'
    })
  },
  editTask(id) {
    var t = window.scheduledTaskService.getAll().find(function(x) { return x.id === id })
    if (!t) return
    document.getElementById('content').innerHTML = renderHtml('screens/scheduled_tasks_form', {
      title: 'Edit Scheduled Task', id: t.id, taskName: escapeHtml(t.taskName), taskType: escapeHtml(t.taskType), cronExpression: escapeHtml(t.cronExpression), description: escapeHtml(t.description || ''), config: JSON.stringify(t.config || {}, null, 2), isActive: t.isActive ? 'checked' : ''
    })
    var sel = document.getElementById('taskFormType')
    if (sel) sel.value = t.taskType
  },
  async saveForm() {
    var id = document.getElementById('taskFormId').value
    var data = {
      taskName: document.getElementById('taskFormName').value,
      taskType: document.getElementById('taskFormType').value,
      cronExpression: document.getElementById('taskFormCron').value,
      description: document.getElementById('taskFormDesc').value
    }
    var configEl = document.getElementById('taskFormConfig')
    if (configEl && configEl.value) {
      try { data.config = JSON.parse(configEl.value) } catch(e) { app.toast('Invalid JSON in config', 'error'); return }
    }
    data.isActive = document.getElementById('taskFormActive') ? document.getElementById('taskFormActive').checked : true
    try {
      if (id) {
        await window.scheduledTaskService.update(Number(id), data)
        app.toast('Task updated', 'success')
      } else {
        await window.scheduledTaskService.create(data)
        app.toast('Task created', 'success')
      }
      document.getElementById('content').innerHTML = this.render()
    } catch (e) { app.toast('Error: ' + e.message, 'error') }
  },
  async deleteTask(id) {
    if (!confirm('Delete this scheduled task?')) return
    try {
      await window.scheduledTaskService.remove(id)
      document.getElementById('content').innerHTML = this.render()
    } catch (e) { app.toast('Error: ' + e.message, 'error') }
  },
  async runTask(id) {
    try {
      await window.scheduledTaskService.runNow(id)
      document.getElementById('content').innerHTML = this.render()
      app.toast('Task queued for execution', 'success')
    } catch (e) { app.toast('Error: ' + e.message, 'error') }
  }
}
