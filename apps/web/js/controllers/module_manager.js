window.NovaModules = window.NovaModules || {}; window.NovaModules['module_manager'] = {
  async load() {
    await window.moduleRegistryService.load()
  },

  render() {
    var installed = window.moduleRegistryService.getInstalled()
    var totalInstalled = installed.length
    var totalActive = installed.filter(function(m) { return m.isActive }).length
    var totalAvailable = (this._available || []).length

    var installedRows = installed.map(function(m) {
      var activeBadge = m.isActive
        ? '<span class="inline-flex items-center gap-xs px-sm py-xs rounded-full bg-success/10 text-success text-label-md font-semibold">Active</span>'
        : '<span class="inline-flex items-center gap-xs px-sm py-xs rounded-full bg-surface-container-high text-on-surface-variant text-label-md font-semibold">Disabled</span>'
      var coreBadge = m.isCore ? ' <span class="text-label-sm text-on-surface-variant">(core)</span>' : ''
      var toggleBtn = m.isCore ? '' : (
        m.isActive
          ? '<button class="text-warning hover:text-warning/80 transition-colors press-effect p-xs" onclick="controllers.module_manager.toggleModule(' + m.id + ', false)" title="Disable"><span class="material-symbols-outlined text-[18px]">toggle_off</span></button>'
          : '<button class="text-success hover:text-success/80 transition-colors press-effect p-xs" onclick="controllers.module_manager.toggleModule(' + m.id + ', true)" title="Enable"><span class="material-symbols-outlined text-[18px]">toggle_on</span></button>'
      )
      return '<tr class="hover:bg-primary/5 transition-colors group">' +
        '<td class="px-lg py-md font-body-md font-semibold text-primary">' + escapeHtml(m.name) + coreBadge + '</td>' +
        '<td class="px-lg py-md font-data-mono text-body-md text-on-surface-variant">' + escapeHtml(m.version) + '</td>' +
        '<td class="px-lg py-md text-body-md text-on-surface-variant">' + escapeHtml(m.category || '-') + '</td>' +
        '<td class="px-lg py-md text-center">' + activeBadge + '</td>' +
        '<td class="px-lg py-md text-center"><div class="flex items-center justify-center gap-xs">' + toggleBtn +
        (m.isCore ? '' : '<button class="text-error hover:text-error/80 transition-colors press-effect p-xs" onclick="controllers.module_manager.uninstallModule(' + m.id + ')" title="Uninstall"><span class="material-symbols-outlined text-[18px]">delete</span></button>') +
        '</div></td></tr>'
    }).join('')

    var self = this
    var availableRows = (this._available || []).map(function(a) {
      var alreadyInstalled = installed.some(function(m) { return m.moduleKey === a.module_key })
      var installBtn = alreadyInstalled
        ? '<span class="text-on-surface-variant text-label-md">Installed</span>'
        : '<button class="bg-primary text-on-primary px-md py-xs rounded-lg text-label-md font-semibold active:translate-y-[1px] transition-all press-effect" onclick="controllers.module_manager.installModule(\'' + a.module_key + '\')">Install</button>'
      return '<tr class="hover:bg-primary/5 transition-colors group">' +
        '<td class="px-lg py-md font-body-md font-semibold text-primary">' + escapeHtml(a.name) + '</td>' +
        '<td class="px-lg py-md text-body-md text-on-surface-variant">' + (a.has_controllers ? '<span class="text-success">Yes</span>' : '<span class="text-on-surface-variant">No</span>') + '</td>' +
        '<td class="px-lg py-md text-center">' + installBtn + '</td></tr>'
    }).join('')

    return renderHtml('screens/module_manager', {
      totalInstalled: totalInstalled,
      totalActive: totalActive,
      totalAvailable: totalAvailable,
      installedRows: installedRows || '<tr><td colspan="5" class="px-lg py-md text-body-md text-on-surface-variant text-center">No modules installed yet</td></tr>',
      availableRows: availableRows || '<tr><td colspan="3" class="px-lg py-md text-body-md text-on-surface-variant text-center">Click "Scan for Modules" to discover available modules</td></tr>',
    })
  },

  mount() {
    var self = this
    this._available = []
    window.moduleRegistryService.discover().then(function(available) {
      self._available = available
      var content = document.getElementById('content')
      if (content) content.innerHTML = self.render()
    })
  },

  async discoverModules() {
    var self = this
    this._available = await window.moduleRegistryService.discover()
    document.getElementById('content').innerHTML = this.render()
  },

  async installModule(moduleKey) {
    var result = await window.moduleRegistryService.install(moduleKey)
    if (result.ok) {
      app.toast('Module installed successfully', 'success')
    } else {
      app.toast('Error: ' + (result.error || 'Installation failed'), 'error')
    }
    document.getElementById('content').innerHTML = this.render()
  },

  async uninstallModule(id) {
    if (!confirm('Uninstall this module?')) return
    var result = await window.moduleRegistryService.uninstall(id)
    if (result.ok) {
      app.toast('Module uninstalled', 'success')
    } else {
      app.toast('Error: ' + (result.error || 'Uninstall failed'), 'error')
    }
    document.getElementById('content').innerHTML = this.render()
  },

  async toggleModule(id, active) {
    var result = await window.moduleRegistryService.toggle(id, active)
    if (result.ok) {
      app.toast(active ? 'Module enabled' : 'Module disabled', 'success')
    } else {
      app.toast('Error: ' + (result.error || 'Toggle failed'), 'error')
    }
    document.getElementById('content').innerHTML = this.render()
  }
}
