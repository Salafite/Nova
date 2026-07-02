window.NovaModules = window.NovaModules || {}; window.NovaModules['quality'] = {
  render() {
    var inspections = window.qualityService ? window.qualityService.getInspections() : []
    var passCount = window.qualityService ? window.qualityService.getInspections().filter(function(i) { return i.result === 'Pass' }).length : 0
    var pendingCount = window.qualityService ? window.qualityService.getPendingCount() : 0
    var failCount = window.qualityService ? window.qualityService.getFailCount() : 0
    var insRows = inspections.map(function(ins) {
      var btns = ins.result === 'Pending' ? '<div class="flex items-center justify-center gap-xs"><button class="p-1 hover:bg-secondary-container text-secondary rounded transition-colors" onclick="controllers.quality.passInspection(\'' + escapeHtml(ins.id) + '\')"><span class="material-symbols-outlined text-[18px]">check_circle</span></button> <button class="p-1 hover:bg-error-container text-error rounded transition-colors" onclick="controllers.quality.failInspection(\'' + escapeHtml(ins.id) + '\')"><span class="material-symbols-outlined text-[18px]">cancel</span></button></div>' : ''
      return '<tr class="hover:bg-primary/5 transition-colors group">' +
               '<td class="px-lg py-md font-data-mono text-data-mono text-primary font-bold">' + escapeHtml(ins.id) + '</td>' +
               '<td class="px-lg py-md text-body-md">' + escapeHtml(ins.productName) + '</td>' +
               '<td class="px-lg py-md text-body-md">' + escapeHtml(ins.batch || '-') + '</td>' +
               '<td class="px-lg py-md">' + Badge.inspectionResult(ins.result || 'Pending') + '</td>' +
               '<td class="px-lg py-md text-body-md">' + escapeHtml(ins.inspector) + '</td>' +
               '<td class="px-lg py-md text-body-md text-on-surface-variant">' + escapeHtml(ins.date) + '</td>' +
               '<td class="px-lg py-md text-center">' + btns + '</td>' +
             '</tr>'
    }).join('')
    return renderHtml('screens/quality', {
      inspectionRows: insRows,
      passRate: inspections.length ? Math.round(passCount / inspections.length * 100) : 0,
      totalInspections: inspections.length,
      pendingInspections: pendingCount,
      failedInspections: failCount
    })
  },
  mount() { controllers.quality = this },
  showCreateForm() {
    document.getElementById('content').innerHTML = renderHtml('models/inspection/form', {})
  },
  async saveForm() {
    var productName = document.getElementById('qcFormProduct').value
    var batch = document.getElementById('qcFormBatch').value
    var inspector = document.getElementById('qcFormInspector').value
    try {
      if (window.qualityService) {
        await window.qualityService.createInspection(productName, batch, inspector)
        app.toast('Inspection Created', 'success')
      }
      document.getElementById('content').innerHTML = this.render()
    } catch (e) {
      app.toast('Error creating inspection: ' + e.message, 'error')
    }
    return false
  },
  async passInspection(id) {
    try {
      if (window.qualityService) await window.qualityService.updateResult(id, 'Pass')
      document.getElementById('content').innerHTML = this.render()
    } catch (e) {
      app.toast('Error updating inspection: ' + e.message, 'error')
    }
  },
  async failInspection(id) {
    try {
      if (window.qualityService) await window.qualityService.updateResult(id, 'Fail')
      document.getElementById('content').innerHTML = this.render()
    } catch (e) {
      app.toast('Error updating inspection: ' + e.message, 'error')
    }
  }
}
