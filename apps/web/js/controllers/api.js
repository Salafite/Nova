window.NovaModules = window.NovaModules || {}; window.NovaModules['api'] = {
  render() {
    var keys = window.apiGatewayService.getAll()
    var endpoints = window.apiGatewayService.getEndpoints()
    var keyRows = keys.map(function(k) {
      var keyStatus = k.status === 'Active' ? '<span class="px-sm py-xs bg-secondary/10 text-secondary rounded text-[11px] font-medium uppercase">Active</span>' : '<span class="px-sm py-xs bg-surface-container-highest text-on-surface-variant rounded text-[11px] font-medium uppercase">' + escapeHtml(k.status || 'Revoked') + '</span>'
      return '<tr class="hover:bg-primary/5 transition-colors group">' +
               '<td class="px-lg py-md font-body-md font-semibold text-primary">' + escapeHtml(k.name || '-') + '</td>' +
               '<td class="px-lg py-md font-data-mono text-data-mono text-xs">' + escapeHtml(k.key || k.id) + '</td>' +
               '<td class="px-lg py-md text-body-md text-on-surface-variant">' + escapeHtml(k.created || '-') + '</td>' +
               '<td class="px-lg py-md text-body-md text-on-surface-variant">' + escapeHtml(k.last_used || '-') + '</td>' +
               '<td class="px-lg py-md text-center">' + keyStatus + '</td>' +
               '<td class="px-lg py-md text-center opacity-0 group-hover:opacity-100 transition-opacity">' +
               '<button class="p-1 hover:bg-error-container rounded-full text-error" onclick="controllers.api.deleteKey(\'' + k.id + '\')"><span class="material-symbols-outlined text-[20px]">delete</span></button></td>' +
             '</tr>'
    }).join('')
    var endpointRows = endpoints.map(function(e) {
      var methodColor = e.method === 'GET' ? 'text-secondary' : (e.method === 'POST' ? 'text-primary' : (e.method === 'DELETE' ? 'text-error' : 'text-on-surface-variant'))
      return '<tr class="hover:bg-primary/5 transition-colors">' +
               '<td class="px-lg py-md font-data-mono text-data-mono font-bold ' + methodColor + '">' + escapeHtml(e.method || 'GET') + '</td>' +
               '<td class="px-lg py-md font-data-mono text-data-mono text-on-surface-variant">' + escapeHtml(e.path || '-') + '</td>' +
               '<td class="px-lg py-md text-body-md text-on-surface-variant">' + escapeHtml(e.description || '-') + '</td>' +
             '</tr>'
    }).join('')
    return renderHtml('screens/public_api_platform', {
      keyRows: keyRows,
      endpointRows: endpointRows,
      keyCount: keys.length,
      endpointCount: endpoints.length
    })
  },
  mount() { controllers.api = this },
  search(q) { this.searchTerm = q.toLowerCase(); document.getElementById('content').innerHTML = this.render() },
  showCreateForm() {
    document.getElementById('content').innerHTML =
      '<div class="max-w-2xl mx-auto bg-surface-container-lowest border border-outline-variant rounded-xl p-lg shadow-sm">' +
      '<h3 class="font-title-md text-title-md font-bold mb-lg">Create API Key</h3>' +
      '<form onsubmit="return controllers.api.saveForm()">' +
      '<div class="grid grid-cols-1 gap-md mb-md">' +
      '<div class="flex flex-col gap-xs"><label class="font-label-sm text-label-sm font-bold text-on-surface-variant uppercase">Key Name</label><input id="apiFormName" required class="w-full bg-surface border border-outline-variant rounded-lg px-3 py-2 text-body-md focus:ring-2 focus:ring-primary/20" /></div>' +
      '</div>' +
      '<div class="flex gap-sm mt-lg"><button type="submit" class="bg-primary text-on-primary px-lg py-sm rounded-lg font-label-md press-effect">Create</button>' +
      '<button type="button" class="bg-surface border border-outline-variant text-on-surface-variant px-lg py-sm rounded-lg font-label-md press-effect" onclick="controllers.api.render()">Cancel</button></div>' +
      '</form></div>'
  },
  async saveForm() {
    var payload = {
      name: document.getElementById('apiFormName').value,
      key: 'nova_' + Math.random().toString(36).substr(2, 32),
      status: 'Active',
      created: new Date().toISOString(),
      last_used: '-'
    }
    try {
      await window.apiGatewayService.create(payload)
      app.toast('API key created', 'success')
      document.getElementById('content').innerHTML = this.render()
    } catch (e) {
      app.toast('Error creating API key: ' + e.message, 'error')
    }
    return false
  },
  async deleteKey(id) {
    if (!confirm('Revoke this API key?')) return
    try {
      await window.apiGatewayService.remove(id)
      app.toast('API key revoked', 'success')
      document.getElementById('content').innerHTML = this.render()
    } catch (e) {
      app.toast('Error revoking API key: ' + e.message, 'error')
    }
  }
}
