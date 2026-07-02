window.Badge = {
  stock(quantity, minStock) {
    var threshold = minStock || 5
    if (quantity <= 0) {
      return '<span class="px-sm py-xs bg-error-container text-error rounded text-[11px] font-medium uppercase">Out of Stock</span>'
    }
    if (quantity <= threshold) {
      return '<span class="px-sm py-xs bg-surface-container-highest text-secondary rounded text-[11px] font-medium uppercase">Low Stock</span>'
    }
    return '<span class="px-sm py-xs bg-surface-container-high text-primary rounded text-[11px] font-medium uppercase">In Stock</span>'
  },

  orderStatus(status) {
    var base = 'inline-flex items-center px-sm py-xs rounded-full bg-surface-container-high text-primary text-[11px] font-bold uppercase'
    return '<span class="' + base + '">' + escapeHtml(status) + '</span>'
  },

  poStatus(status) {
    if (status === 'Received') {
      return '<span class="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-bold uppercase bg-secondary/10 text-secondary border border-secondary/20">Received</span>'
    }
    if (status === 'Pending') {
      return '<span class="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-bold uppercase bg-warning/10 text-warning border border-warning/20">Pending</span>'
    }
    return '<span class="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-bold uppercase bg-surface-container text-on-surface-variant border border-outline-variant">' + escapeHtml(status) + '</span>'
  },

  userRole(role) {
    return '<span class="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-bold uppercase bg-secondary/10 text-secondary border border-secondary/20">' + escapeHtml(role) + '</span>'
  },

  transactionType(type) {
    if (type === 'Revenue') {
      return '<span class="px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-secondary-container text-on-secondary-container">Revenue</span>'
    }
    return '<span class="px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-error-container text-on-error-container">Expense</span>'
  },

  mfgOrderStatus(status) {
    if (status === 'Completed') {
      return '<span class="px-2 py-1 rounded text-[11px] font-bold uppercase tracking-tight bg-secondary-container/20 text-on-secondary-container">Completed</span>'
    }
    if (status === 'In Progress') {
      return '<span class="px-2 py-1 rounded text-[11px] font-bold uppercase tracking-tight bg-primary-container/10 text-primary">In Progress</span>'
    }
    return '<span class="px-2 py-1 rounded text-[11px] font-bold uppercase tracking-tight bg-surface-variant text-on-surface-variant">' + escapeHtml(status) + '</span>'
  },

  mfgStatusActions(status, id, completeHandler) {
    if (status === 'Completed') {
      return '<span class="text-secondary font-label-md text-label-md flex items-center justify-end"><span class="material-symbols-outlined text-[16px] mr-1">check_circle</span>Done</span>'
    }
    return '<button class="bg-primary text-on-primary px-3 py-1 rounded text-label-md font-label-md hover:brightness-110 press-effect transition-all" onclick="' + completeHandler + '">Complete</button>'
  },

  poReceiveActions(status, id) {
    if (status === 'Received') {
      return '<span class="text-secondary font-label-md flex items-center justify-end"><span class="material-symbols-outlined text-[16px] mr-1">check_circle</span>Received</span>'
    }
    return '<button class="bg-primary text-on-primary px-3 py-1 rounded text-label-md font-label-md hover:brightness-110 press-effect transition-all" onclick="controllers.purchasing.receiveOrder(\'' + escapeHtml(id) + '\')">Receive</button>'
  },

  shopJobStatus(status) {
    if (status === 'Completed') {
      return '<span class="inline-flex items-center px-2.5 py-0.5 rounded-full font-label-md text-[11px] font-bold uppercase bg-secondary text-white">Completed</span>'
    }
    if (status === 'In Progress') {
      return '<span class="inline-flex items-center px-2.5 py-0.5 rounded-full font-label-md text-[11px] font-bold uppercase bg-secondary-container text-on-secondary-container">In Progress</span>'
    }
    return '<span class="inline-flex items-center px-2.5 py-0.5 rounded-full font-label-md text-[11px] font-bold uppercase bg-surface-container-highest text-on-surface-variant">' + escapeHtml(status) + '</span>'
  },

  shopJobActions(status, id) {
    if (status === 'Completed') {
      return '<span class="text-secondary font-label-md flex items-center justify-end"><span class="material-symbols-outlined text-[16px] mr-1">check_circle</span>Done</span>'
    }
    return '<button class="bg-primary text-on-primary px-3 py-1 rounded text-[11px] font-bold uppercase hover:brightness-110 transition-all press-effect" onclick="controllers.shopfloor.completeJob(\'' + escapeHtml(id) + '\')">Complete</button>'
  },

  inspectionResult(result, id) {
    var cls = result === 'Pass' ? 'bg-secondary/10 text-secondary border border-secondary/20' :
      (result === 'Fail' ? 'bg-error/10 text-error border border-error/20' :
       'bg-surface-container text-on-surface-variant border border-outline-variant')
    return '<span class="inline-flex items-center px-2 py-0.5 rounded text-label-md font-medium uppercase ' + cls + '">' + escapeHtml(result) + '</span>'
  },

  planStatus(status) {
    var cls = status === 'Released' ? 'bg-secondary/10 text-secondary border border-secondary/20' :
      (status === 'Approved' ? 'bg-warning/10 text-warning border border-warning/20' :
       'bg-surface-container text-on-surface-variant border border-outline-variant')
    return '<span class="inline-flex items-center px-2.5 py-0.5 rounded-full font-label-md text-[11px] font-bold uppercase ' + cls + '">' + escapeHtml(status) + '</span>'
  },

  workstationStatus(status) {
    var sc = status === 'Busy' ? 'text-warning' : 'text-secondary'
    return '<span class="flex items-center gap-xs font-label-md text-label-md font-bold uppercase ' + sc + '"><span class="w-2 h-2 rounded-full bg-current"></span>' + escapeHtml(status) + '</span>'
  }
}
