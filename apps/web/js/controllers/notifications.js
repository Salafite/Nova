window.NovaModules = window.NovaModules || {}; window.NovaModules['notifications'] = {
  render() {
    var list = window.notificationService.getAll()
    var tt = this.searchTerm || ''
    if (tt) list = list.filter(function(n) { return n.title && n.title.toLowerCase().indexOf(tt) > -1 })
    var total = list.length
    var unread = window.notificationService.getUnreadCount()
    var currentUserId = null
    try { currentUserId = JSON.parse(localStorage.getItem('nova_user') || '{}').id } catch(e) {}
    var rows = list.map(function(n) {
      var iconMap = { Info: 'info', Success: 'check_circle', Warning: 'warning', Error: 'error' }
      var colorMap = { Info: 'text-primary', Success: 'text-secondary', Warning: 'text-warning', Error: 'text-error' }
      var icon = iconMap[n.notificationType] || 'info'
      var color = colorMap[n.notificationType] || 'text-primary'
      var readClass = n.isRead ? 'opacity-60' : 'font-semibold bg-surface-container-low'
      return '<tr class="hover:bg-primary/5 transition-colors group ' + readClass + '">' +
        '<td class="px-lg py-md"><span class="material-symbols-outlined ' + color + '">' + icon + '</span></td>' +
        '<td class="px-lg py-md font-body-md">' + escapeHtml(n.title) + '</td>' +
        '<td class="px-lg py-md text-body-md text-on-surface-variant">' + escapeHtml(n.message || '') + '</td>' +
        '<td class="px-lg py-md"><span class="px-sm py-xs rounded text-[11px] font-bold uppercase bg-surface-container-high ' + color + '">' + escapeHtml(n.notificationType) + '</span></td>' +
        '<td class="px-lg py-md text-body-md text-on-surface-variant">' + (n.referenceType ? escapeHtml(n.referenceType) + ' #' + n.referenceId : '-') + '</td>' +
        '<td class="px-lg py-md font-data-mono text-data-mono text-on-surface-variant">' + (n.createdAt ? new Date(n.createdAt).toLocaleString() : '') + '</td>' +
        '<td class="px-lg py-md text-center">' +
          (n.isRead ? '<span class="text-secondary"><span class="material-symbols-outlined text-[18px]">done</span></span>' :
            '<button class="p-1 hover:bg-primary-container rounded text-primary" onclick="controllers.notifications.markOne(' + n.id + ')"><span class="material-symbols-outlined text-[18px]">mark_email_read</span></button>') +
        '</td></tr>'
    }).join('')
    return renderHtml('screens/notifications', {
      total: total,
      unread: unread,
      rows: rows,
      hasUnread: unread > 0 ? '' : 'hidden',
      currentUserId: currentUserId
    })
  },
  mount() {
    controllers.notifications = this
    var s = document.getElementById('notificationSearch')
    if (s) { var val = this.searchTerm || ''; s.value = val; s.oninput = function() { controllers.notifications.search(this.value) } }
  },
  search(q) {
    this.searchTerm = q.toLowerCase()
    document.getElementById('content').innerHTML = this.render()
  },
  async markOne(id) {
    try {
      await window.notificationService.markRead(id)
      document.getElementById('content').innerHTML = this.render()
    } catch (e) { app.toast('Error: ' + e.message, 'error') }
  },
  async markAll() {
    var currentUserId = null
    try { currentUserId = JSON.parse(localStorage.getItem('nova_user') || '{}').id } catch(e) {}
    if (!currentUserId) return
    try {
      await window.notificationService.markAllRead(currentUserId)
      document.getElementById('content').innerHTML = this.render()
      app.toast('All notifications marked as read', 'success')
    } catch (e) { app.toast('Error: ' + e.message, 'error') }
  }
}
