window.NovaModules = window.NovaModules || {}; window.NovaModules['admin'] = {
  render() {
    var rows = window.adminService.getUsers().map(function(u) {
      return '<tr class="hover:bg-primary/5 transition-colors group">' +
               '<td class="px-lg py-md font-body-md font-semibold text-primary">' + escapeHtml(u.username) + '</td>' +
               '<td class="px-lg py-md text-body-md text-on-surface-variant">' + escapeHtml(u.email || u.username + '@novaerp.local') + '</td>' +
               '<td class="px-lg py-md text-body-md">' + escapeHtml(u.role) + '</td>' +
               '<td class="px-lg py-md text-center">' + Badge.userRole('Active') + '</td>' +
             '</tr>'
    }).join('')
    return renderHtml('screens/admin', { userRows: rows })
  },
  mount() { controllers.admin = this },
  showCreateForm() {
    document.getElementById('content').innerHTML = renderHtml('models/user/form', {})
  },
  async saveForm() {
    var username = document.getElementById('userFormUsername').value
    var pass = document.getElementById('userFormPassword').value
    var role = document.getElementById('userFormRole').value
    try {
      await window.adminService.create(username, pass, role)
      app.toast('User Created', 'success')
    } catch (e) {
      app.toast('Error creating user: ' + e.message, 'error')
    }
    document.getElementById('content').innerHTML = this.render()
    return false
  }
}
