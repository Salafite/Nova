window.NovaModules = window.NovaModules || {}; window.NovaModules['customers'] = {
  render() {
    var search = this.searchTerm || ''
    var list = window.customerService.getAll()
    var filtered = search ? list.filter(function(c) { return c.name.toLowerCase().indexOf(search) > -1 || (c.email || '').toLowerCase().indexOf(search) > -1 }) : list
    var rows = filtered.map(function(c) {
      var initials = (c.name || 'C').substring(0,2).toUpperCase();
      var colors = ['primary', 'secondary', 'tertiary', 'error'];
      var colorIdx = c.id ? c.id % colors.length : 0;
      var avatarColor = colors[colorIdx];

      var group = c.group || 'Retail';
      var groupBadge = group === 'Enterprise' ? 'bg-secondary-container text-on-secondary-container' : 
                       (group === 'Wholesale' ? 'bg-surface-container-highest text-on-surface-variant' : 
                       'bg-primary-container text-on-primary-container');

      var balance = c.balance || 0;
      var limit = c.creditLimit || 500;
      var isOverdue = balance > limit;
      var statusColor = isOverdue ? 'error' : (balance === 0 ? 'on-surface-variant' : 'secondary');
      var statusText = isOverdue ? 'Overdue' : (balance === 0 ? 'Dormant' : 'Active');
      var balanceColor = isOverdue ? 'text-error font-bold' : 'text-on-surface';

      return `
<tr class="hover:bg-primary-container/5 transition-colors group cursor-pointer">
<td class="p-md"><input class="rounded border-outline text-primary focus:ring-primary/20" type="checkbox"/></td>
<td class="p-md">
<div class="flex items-center gap-md">
<div class="w-10 h-10 rounded-full bg-surface-container-high flex items-center justify-center text-${avatarColor} font-bold">${initials}</div>
<div>
<div class="font-title-md text-title-md text-on-surface leading-none">${escapeHtml(c.name)}</div>
<div class="text-[12px] text-on-surface-variant mt-1">Ref: CUST-${c.id}</div>
</div>
</div>
</td>
<td class="p-md">
<span class="px-sm py-1 ${groupBadge} rounded text-xs font-medium">${escapeHtml(group)}</span>
</td>
<td class="p-md">
<div class="text-body-md text-on-surface">${escapeHtml(c.email || '-')}</div>
<div class="text-xs text-on-surface-variant">${escapeHtml(c.phone || '-')}</div>
</td>
<td class="p-md">
<div class="flex items-center gap-xs text-${statusColor}">
<span class="w-2 h-2 rounded-full bg-${statusColor}"></span>
<span class="text-xs font-medium">${statusText}</span>
</div>
</td>
<td class="p-md text-right rtl:text-left font-data-mono text-data-mono ${balanceColor}">
    $${balance.toFixed(2)}
</td>
<td class="p-md text-center opacity-0 group-hover:opacity-100 transition-opacity">
<div class="flex items-center justify-end gap-1">
<button class="p-1 hover:bg-surface-variant rounded-full text-primary" onclick="controllers.customers.showEditForm('${c.id}')"><span class="material-symbols-outlined text-[20px]">edit</span></button>
<button class="p-1 hover:bg-error-container rounded-full text-error" onclick="controllers.customers.deleteCustomer('${c.id}')"><span class="material-symbols-outlined text-[20px]">delete</span></button>
</div>
</td>
</tr>`
    }).join('')
    return renderHtml('models/customer/list', { rows: rows, count: filtered.length })
  },
  mount() { controllers.customers = this; var s = document.getElementById('customerSearch'); if (s) s.value = this.searchTerm || '' },
  search(q) { this.searchTerm = q.toLowerCase(); document.getElementById('content').innerHTML = this.render() },
  showAddForm() {
    document.getElementById('content').innerHTML = renderHtml('models/customer/form', {
      title: 'Add', id: '', name: '', email: '', phone: '', creditLimit: '500'
    })
  },
  showEditForm(id) {
    var c = window.customerService.getById(id)
    if (!c) return
    document.getElementById('content').innerHTML = renderHtml('models/customer/form', {
      title: 'Edit', id: c.id, name: escapeHtml(c.name), email: escapeHtml(c.email || ''), phone: escapeHtml(c.phone || ''), creditLimit: c.creditLimit || 500
    })
  },
  async saveForm() {
    var id = document.getElementById('customerFormId').value
    var name = document.getElementById('customerFormName').value
    var email = document.getElementById('customerFormEmail').value
    var phone = document.getElementById('customerFormPhone').value
    var creditLimit = parseFloat(document.getElementById('customerFormCreditLimit').value) || 500
    try {
      if (id) {
        await window.customerService.update(id, name, email, phone, creditLimit)
      } else {
        await window.customerService.add(name, email, phone, creditLimit)
      }
      document.getElementById('content').innerHTML = this.render()
    } catch (e) {
      app.toast('Error saving customer: ' + e.message, 'error')
    }
    return false
  },
  async deleteCustomer(id) {
    if (!confirm('Delete customer?')) return
    try {
      await window.customerService.remove(id)
      document.getElementById('content').innerHTML = this.render()
    } catch (e) {
      app.toast('Error deleting customer: ' + e.message, 'error')
    }
  }
}
