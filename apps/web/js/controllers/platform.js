window.NovaModules = window.NovaModules || {}; window.NovaModules['platform'] = {
  render() {
    var items = window.platformService.getAll()
    var rows = items.map(function(s) {
      var statusBadge = s.status === 'Healthy' || s.status === 'Online' ? '<span class="px-sm py-xs bg-secondary-container text-on-secondary-container rounded text-[11px] font-bold uppercase">Healthy</span>' : '<span class="px-sm py-xs bg-error-container text-error rounded text-[11px] font-bold uppercase">' + escapeHtml(s.status || 'Offline') + '</span>'
      return '<tr class="hover:bg-primary/5 transition-colors group">' +
             '<td class="px-lg py-md font-body-md font-semibold text-primary">' + escapeHtml(s.serviceName || s.name || '-') + '</td>' +
             '<td class="px-lg py-md">' + statusBadge + '</td>' +
             '<td class="px-lg py-md text-body-md font-data-mono text-on-surface-variant">' + escapeHtml(s.version || '-') + '</td>' +
             '<td class="px-lg py-md text-body-md font-data-mono text-on-surface-variant">' + escapeHtml(s.uptime || '0%') + '</td>' +
             '<td class="px-lg py-md text-body-md text-on-surface-variant">' + escapeHtml(s.lastChecked || '-') + '</td>' +
             '</tr>'
    }).join('')
    var uptimeValues = items.map(function(s) { return parseFloat(s.uptime) || 0 })
    var avgUptime = uptimeValues.length ? Math.round(uptimeValues.reduce(function(a, b) { return a + b }, 0) / uptimeValues.length) : 100
    return renderHtml('screens/enterprise_platform_completion', {
      serviceRows: rows,
      totalServices: items.length,
      healthyServices: window.platformService.getHealthyCount(),
      platformVersion: window.platformService.getVersion(),
      avgUptime: avgUptime
    })
  },
  mount() { controllers.platform = this }
}
