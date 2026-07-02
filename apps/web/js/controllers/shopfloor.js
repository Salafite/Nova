window.NovaModules = window.NovaModules || {}; window.NovaModules['shopfloor'] = {
  render() {
    var jobs = window.shopfloorService ? window.shopfloorService.getJobs() : []
    var workstations = window.shopfloorService ? window.shopfloorService.getWorkstations() : []
    var jobRows = jobs.map(function(j) {
      return '<tr class="hover:bg-primary-container/5 transition-colors group">' +
               '<td class="px-md py-3 font-data-mono text-data-mono text-primary font-bold">' + escapeHtml(j.id) + '</td>' +
               '<td class="px-md py-3 font-body-md text-body-md font-semibold">' + escapeHtml(j.productName) + '</td>' +
               '<td class="px-md py-3 font-data-mono text-data-mono">' + j.quantity + '</td>' +
               '<td class="px-md py-3"><div class="flex items-center gap-2"><span class="material-symbols-outlined text-outline text-[18px]">precision_manufacturing</span><span class="font-body-md text-body-md">' + escapeHtml(j.workstation || '-') + '</span></div></td>' +
               '<td class="px-md py-3 text-center">' + Badge.shopJobStatus(j.status) + '</td>' +
               '<td class="px-md py-3 text-right">' + Badge.shopJobActions(j.status, j.id) + '</td>' +
             '</tr>'
    }).join('')
    var wsRows = workstations.map(function(w, idx) {
      var status = idx < 3 ? 'Busy' : 'Available'
      return '<tr class="hover:bg-primary-container/5 transition-colors">' +
               '<td class="px-md py-3 font-body-md text-body-md font-medium">' + escapeHtml(w) + '</td>' +
               '<td class="px-md py-3">' + Badge.workstationStatus(status) + '</td>' +
               '<td class="px-md py-3 font-data-mono text-data-mono text-on-surface-variant">' + (idx < 3 ? 'Job-' + (1001 + idx) : '-') + '</td>' +
             '</tr>'
    }).join('')
    var activeWS = window.shopfloorService ? window.shopfloorService.getActiveCount() : 0
    var availableWS = window.shopfloorService ? window.shopfloorService.getAvailableWSCount() : 0
    var pendingJobs = window.shopfloorService ? window.shopfloorService.getPendingCount() : 0
    var completedJobs = window.shopfloorService ? window.shopfloorService.getCompletedCount() : 0

    return renderHtml('screens/shopfloor', {
      jobRows: jobRows,
      workstationRows: wsRows,
      activeWS: activeWS,
      availableWS: availableWS,
      inProgressJobs: activeWS,
      pendingJobs: pendingJobs,
      completedJobs: completedJobs
    })
  },
  mount() { controllers.shopfloor = this },
  showCreateForm() {
    document.getElementById('content').innerHTML = renderHtml('models/job/form', {})
  },
  async saveForm() {
    var productName = document.getElementById('jobFormProduct').value
    var qty = parseInt(document.getElementById('jobFormQty').value)
    var ws = document.getElementById('jobFormWorkstation').value
    try {
      if (window.shopfloorService) {
        await window.shopfloorService.createJob(productName, qty, ws)
        app.toast('Work Order Created', 'success')
      }
      document.getElementById('content').innerHTML = this.render()
    } catch (e) {
      app.toast('Error creating job: ' + e.message, 'error')
    }
    return false
  },
  async completeJob(id) {
    try {
      if (window.shopfloorService) {
        await window.shopfloorService.updateStatus(id, 'Completed')
        app.toast('Job ' + id + ' completed', 'success')
      }
      document.getElementById('content').innerHTML = this.render()
    } catch (e) {
      app.toast('Error completing job: ' + e.message, 'error')
    }
  }
}
