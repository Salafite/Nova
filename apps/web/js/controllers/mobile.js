window.NovaModules = window.NovaModules || {}; window.NovaModules['mobile'] = {
  render() {
    var devices = window.mobileApiService.getAll()
    var logs = window.mobileApiService.getSyncLogs()
    var deviceRows = devices.map(function(d) {
      var statusBadge = d.status === 'Active' ? '<span class="px-sm py-xs bg-secondary/10 text-secondary rounded text-[11px] font-medium uppercase">Active</span>' : '<span class="px-sm py-xs bg-surface-container-highest text-on-surface-variant rounded text-[11px] font-medium uppercase">' + escapeHtml(d.status || 'Inactive') + '</span>'
      return '<tr class="hover:bg-primary/5 transition-colors group">' +
               '<td class="px-lg py-md font-data-mono text-data-mono">' + escapeHtml(d.device_id || d.id) + '</td>' +
               '<td class="px-lg py-md font-body-md font-semibold">' + escapeHtml(d.device_name || '-') + '</td>' +
               '<td class="px-lg py-md text-body-md text-on-surface-variant">' + escapeHtml(d.user || '-') + '</td>' +
               '<td class="px-lg py-md text-body-md text-on-surface-variant">' + escapeHtml(d.last_sync || '-') + '</td>' +
               '<td class="px-lg py-md text-center">' + statusBadge + '</td>' +
               '<td class="px-lg py-md text-center opacity-0 group-hover:opacity-100 transition-opacity">' +
               '<button class="p-1 hover:bg-error-container rounded-full text-error" onclick="controllers.mobile.deleteDevice(\'' + d.id + '\')"><span class="material-symbols-outlined text-[20px]">delete</span></button></td>' +
             '</tr>'
    }).join('')
    var syncRows = logs.map(function(l) {
      var syncStatus = l.status === 'Success' ? '<span class="px-sm py-xs bg-secondary/10 text-secondary rounded text-[11px] font-medium uppercase">Success</span>' : '<span class="px-sm py-xs bg-error-container text-error rounded text-[11px] font-medium uppercase">' + escapeHtml(l.status || 'Failed') + '</span>'
      return '<tr class="hover:bg-primary/5 transition-colors">' +
               '<td class="px-lg py-md font-data-mono text-data-mono text-sm">' + escapeHtml(l.timestamp || '-') + '</td>' +
               '<td class="px-lg py-md text-body-md">' + escapeHtml(l.device || '-') + '</td>' +
               '<td class="px-lg py-md text-body-md text-on-surface-variant">' + escapeHtml(l.action || '-') + '</td>' +
               '<td class="px-lg py-md text-center">' + syncStatus + '</td>' +
             '</tr>'
    }).join('')
    return renderHtml('screens/mobile_foundation', {
      deviceRows: deviceRows,
      syncRows: syncRows,
      deviceCount: devices.length,
      syncCount: logs.length
    })
  },
  mount() { controllers.mobile = this },
  search(q) { this.searchTerm = q.toLowerCase(); document.getElementById('content').innerHTML = this.render() },
  showCreateForm() {
    document.getElementById('content').innerHTML =
      '<div class="max-w-2xl mx-auto bg-surface-container-lowest border border-outline-variant rounded-xl p-lg shadow-sm">' +
      '<h3 class="font-title-md text-title-md font-bold mb-lg">Register Device</h3>' +
      '<form onsubmit="return controllers.mobile.saveForm()">' +
      '<div class="grid grid-cols-1 md:grid-cols-2 gap-md mb-md">' +
      '<div class="flex flex-col gap-xs"><label class="font-label-sm text-label-sm font-bold text-on-surface-variant uppercase">Device Name</label><input id="mobileFormName" required class="w-full bg-surface border border-outline-variant rounded-lg px-3 py-2 text-body-md focus:ring-2 focus:ring-primary/20" /></div>' +
      '<div class="flex flex-col gap-xs"><label class="font-label-sm text-label-sm font-bold text-on-surface-variant uppercase">Device ID</label><input id="mobileFormDeviceId" required class="w-full bg-surface border border-outline-variant rounded-lg px-3 py-2 text-body-md focus:ring-2 focus:ring-primary/20" /></div>' +
      '<div class="flex flex-col gap-xs"><label class="font-label-sm text-label-sm font-bold text-on-surface-variant uppercase">User</label><input id="mobileFormUser" class="w-full bg-surface border border-outline-variant rounded-lg px-3 py-2 text-body-md focus:ring-2 focus:ring-primary/20" /></div>' +
      '</div>' +
      '<div class="flex gap-sm mt-lg"><button type="submit" class="bg-primary text-on-primary px-lg py-sm rounded-lg font-label-md press-effect">Register</button>' +
      '<button type="button" class="bg-surface border border-outline-variant text-on-surface-variant px-lg py-sm rounded-lg font-label-md press-effect" onclick="controllers.mobile.render()">Cancel</button></div>' +
      '</form></div>'
  },
  async saveForm() {
    var payload = {
      device_name: document.getElementById('mobileFormName').value,
      device_id: document.getElementById('mobileFormDeviceId').value,
      user: document.getElementById('mobileFormUser').value,
      status: 'Active',
      last_sync: new Date().toISOString()
    }
    try {
      await window.mobileApiService.create(payload)
      app.toast('Device registered', 'success')
      document.getElementById('content').innerHTML = this.render()
    } catch (e) {
      app.toast('Error registering device: ' + e.message, 'error')
    }
    return false
  },
  async deleteDevice(id) {
    if (!confirm('Unregister this device?')) return
    try {
      await window.mobileApiService.remove(id)
      app.toast('Device removed', 'success')
      document.getElementById('content').innerHTML = this.render()
    } catch (e) {
      app.toast('Error removing device: ' + e.message, 'error')
    }
  }
}
