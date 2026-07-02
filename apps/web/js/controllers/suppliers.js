window.NovaModules = window.NovaModules || {}; window.NovaModules['suppliers'] = {
  render() {
    var search = this.searchTerm || ''
    var list = window.supplierService.getAll()
    var filtered = search ? list.filter(function(s) { return s.name.toLowerCase().indexOf(search) > -1 || (s.email || '').toLowerCase().indexOf(search) > -1 }) : list
    var rows = filtered.map(function(s) {
      var initials = (s.name || 'S').substring(0,2).toUpperCase();
      return '<tr class="hover:bg-primary-container/5 transition-colors group">' +
               '<td class="py-md px-md">' +
                 '<div class="flex items-center gap-sm">' +
                   '<div class="w-8 h-8 rounded bg-primary/10 flex items-center justify-center text-primary font-bold text-[12px]">' + initials + '</div>' +
                   '<div>' +
                     '<div class="font-semibold text-on-surface">' + escapeHtml(s.name) + '</div>' +
                     '<div class="text-[11px] text-outline">ID: SUP-' + s.id + '</div>' +
                   '</div>' +
                 '</div>' +
               '</td>' +
               '<td class="py-md px-md">' +
                 '<div class="text-body-md">' + escapeHtml(s.email || '-') + '</div>' +
                 '<div class="text-[11px] text-outline">' + escapeHtml(s.phone || '-') + '</div>' +
               '</td>' +
               '<td class="py-md px-md">' +
                 '<div class="font-data-mono text-data-mono text-primary">' + escapeHtml(s.paymentTerms || 'Net 30') + '</div>' +
               '</td>' +
               '<td class="py-md px-md text-right rtl:text-left">' +
                 '<div class="flex items-center justify-end gap-xs opacity-0 group-hover:opacity-100 transition-opacity">' +
                   '<button class="p-1.5 hover:bg-primary-container/10 text-primary rounded transition-all" onclick="controllers.suppliers.showEditForm(\'' + s.id + '\')"><span class="material-symbols-outlined text-[20px]">edit</span></button>' +
                   '<button class="p-1.5 hover:bg-error-container text-error rounded transition-all" onclick="controllers.suppliers.deleteSupplier(\'' + s.id + '\')"><span class="material-symbols-outlined text-[20px]">delete</span></button>' +
                 '</div>' +
               '</td>' +
             '</tr>'
    }).join('')
    return renderHtml('models/supplier/list', { rows: rows })
  },
  mount() { controllers.suppliers = this; var s = document.getElementById('supplierSearch'); if (s) s.value = this.searchTerm || '' },
  search(q) { this.searchTerm = q.toLowerCase(); document.getElementById('content').innerHTML = this.render() },
  showAddForm() {
    document.getElementById('content').innerHTML = renderHtml('models/supplier/form', {
      title: 'Add', id: '', name: '', email: '', phone: '', paymentTerms: 'Net 30'
    })
  },
  showEditForm(id) {
    var s = window.supplierService.getById(id)
    if (!s) return
    document.getElementById('content').innerHTML = renderHtml('models/supplier/form', {
      title: 'Edit', id: s.id, name: escapeHtml(s.name), email: escapeHtml(s.email || ''), phone: escapeHtml(s.phone || ''), paymentTerms: escapeHtml(s.paymentTerms || 'Net 30')
    })
  },
  async saveForm() {
    var id = document.getElementById('supplierFormId').value
    var name = document.getElementById('supplierFormName').value
    var email = document.getElementById('supplierFormEmail').value
    var phone = document.getElementById('supplierFormPhone').value
    var terms = document.getElementById('supplierFormTerms').value
    try {
      if (id) {
        await window.supplierService.update(id, name, email, phone, terms)
      } else {
        await window.supplierService.add(name, email, phone, terms)
      }
      document.getElementById('content').innerHTML = this.render()
    } catch (e) {
      app.toast('Error saving supplier: ' + e.message, 'error')
    }
    return false
  },
  async deleteSupplier(id) {
    if (!confirm('Delete supplier?')) return
    try {
      await window.supplierService.remove(id)
      document.getElementById('content').innerHTML = this.render()
    } catch (e) {
      app.toast('Error deleting supplier: ' + e.message, 'error')
    }
  }
}
