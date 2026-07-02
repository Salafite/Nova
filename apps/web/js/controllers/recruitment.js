window.NovaModules = window.NovaModules || {}; window.NovaModules['recruitment'] = {
  render() {
    var search = this.searchTerm || ''
    var items = window.recruitmentService.getAll()
    var filtered = search ? items.filter(function(r) { return (r.candidate || '').toLowerCase().indexOf(search) > -1 || (r.position || '').toLowerCase().indexOf(search) > -1 || (r.stage || '').toLowerCase().indexOf(search) > -1 }) : items
    var rows = filtered.map(function(r) {
      var stageBadge = r.stage === 'Hired' ? '<span class="px-sm py-xs bg-secondary/10 text-secondary rounded text-[11px] font-medium uppercase">Hired</span>' :
                       (r.stage === 'Interview' ? '<span class="px-sm py-xs bg-primary/10 text-primary rounded text-[11px] font-medium uppercase">Interview</span>' :
                       (r.stage === 'Offer' ? '<span class="px-sm py-xs bg-warning/10 text-warning rounded text-[11px] font-medium uppercase">Offer</span>' :
                       '<span class="px-sm py-xs bg-surface-container-highest text-on-surface-variant rounded text-[11px] font-medium uppercase">' + escapeHtml(r.stage) + '</span>'))
      var statusBadge = r.status === 'Active' ? '<span class="px-sm py-xs bg-secondary/10 text-secondary rounded text-[11px] font-medium uppercase">Active</span>' : '<span class="px-sm py-xs bg-surface-container-highest text-on-surface-variant rounded text-[11px] font-medium uppercase">' + escapeHtml(r.status) + '</span>'
      return '<tr class="hover:bg-primary/5 transition-colors group">' +
             '<td class="px-lg py-md font-body-md font-semibold text-on-surface">' + escapeHtml(r.candidate) + '</td>' +
             '<td class="px-lg py-md text-body-md text-on-surface-variant">' + escapeHtml(r.position) + '</td>' +
             '<td class="px-lg py-md">' + stageBadge + '</td>' +
             '<td class="px-lg py-md text-body-md text-on-surface-variant">' + escapeHtml(r.applied_date) + '</td>' +
             '<td class="px-lg py-md text-center">' + statusBadge + '</td>' +
             '<td class="px-lg py-md text-center opacity-0 group-hover:opacity-100 transition-opacity">' +
             '<div class="flex items-center justify-center gap-1">' +
             '<button class="p-1 hover:bg-surface-variant rounded-full text-primary" onclick="controllers.recruitment.showEditForm(' + r.id + ')"><span class="material-symbols-outlined text-[20px]">edit</span></button>' +
             '<button class="p-1 hover:bg-error-container rounded-full text-error" onclick="controllers.recruitment.deleteCandidate(' + r.id + ')"><span class="material-symbols-outlined text-[20px]">delete</span></button>' +
             '</div></td></tr>'
    }).join('')
    var activeCount = items.filter(function(r) { return r.status === 'Active' }).length
    var interviewCount = items.filter(function(r) { return r.stage === 'Interview' }).length
    var hiredCount = items.filter(function(r) { return r.status === 'Hired' }).length
    return renderHtml('screens/recruitment___onboarding', {
      rows: rows,
      activeCount: activeCount,
      interviewCount: interviewCount,
      hiredCount: hiredCount
    })
  },
  mount() { controllers.recruitment = this; var s = document.getElementById('recSearch'); if (s) s.value = this.searchTerm || '' },
  search(q) { this.searchTerm = q.toLowerCase(); document.getElementById('content').innerHTML = this.render() },
  async refresh() { document.getElementById('content').innerHTML = this.render() },
  showCreateForm() {
    document.getElementById('content').innerHTML =
      '<div class="max-w-2xl mx-auto bg-surface-container-lowest border border-outline-variant rounded-xl p-lg shadow-sm">' +
      '<h3 class="font-title-md text-title-md font-bold mb-lg">New Application</h3>' +
      '<form onsubmit="return controllers.recruitment.saveForm()">' +
      '<input type="hidden" id="recFormId" value="" />' +
      '<div class="grid grid-cols-1 md:grid-cols-2 gap-md mb-md">' +
      '<div class="flex flex-col gap-xs"><label class="font-label-sm text-label-sm font-bold text-on-surface-variant uppercase">Candidate Name</label><input id="recFormCandidate" required class="w-full bg-surface border border-outline-variant rounded-lg px-3 py-2 text-body-md focus:ring-2 focus:ring-primary/20" /></div>' +
      '<div class="flex flex-col gap-xs"><label class="font-label-sm text-label-sm font-bold text-on-surface-variant uppercase">Position</label><input id="recFormPosition" required class="w-full bg-surface border border-outline-variant rounded-lg px-3 py-2 text-body-md focus:ring-2 focus:ring-primary/20" /></div>' +
      '<div class="flex flex-col gap-xs"><label class="font-label-sm text-label-sm font-bold text-on-surface-variant uppercase">Stage</label><select id="recFormStage" class="w-full bg-surface border border-outline-variant rounded-lg px-3 py-2 text-body-md focus:ring-2 focus:ring-primary/20"><option value="Applied">Applied</option><option value="Screening">Screening</option><option value="Interview">Interview</option><option value="Offer">Offer</option><option value="Hired">Hired</option></select></div>' +
      '<div class="flex flex-col gap-xs"><label class="font-label-sm text-label-sm font-bold text-on-surface-variant uppercase">Applied Date</label><input id="recFormDate" type="date" required class="w-full bg-surface border border-outline-variant rounded-lg px-3 py-2 text-body-md focus:ring-2 focus:ring-primary/20" /></div>' +
      '</div>' +
      '<div class="flex gap-sm mt-lg"><button type="submit" class="bg-primary text-on-primary px-lg py-sm rounded-lg font-label-md press-effect">Save</button>' +
      '<button type="button" class="bg-surface border border-outline-variant text-on-surface-variant px-lg py-sm rounded-lg font-label-md press-effect" onclick="controllers.recruitment.render()">Cancel</button></div>' +
      '</form></div>'
  },
  showEditForm(id) {
    var r = window.recruitmentService.getById(id)
    if (!r) return
    var stageOpts = ['Applied', 'Screening', 'Interview', 'Offer', 'Hired'].map(function(s) { return '<option value="' + s + '"' + (s === r.stage ? ' selected' : '') + '>' + s + '</option>' }).join('')
    document.getElementById('content').innerHTML =
      '<div class="max-w-2xl mx-auto bg-surface-container-lowest border border-outline-variant rounded-xl p-lg shadow-sm">' +
      '<h3 class="font-title-md text-title-md font-bold mb-lg">Edit Application</h3>' +
      '<form onsubmit="return controllers.recruitment.saveForm()">' +
      '<input type="hidden" id="recFormId" value="' + r.id + '" />' +
      '<div class="grid grid-cols-1 md:grid-cols-2 gap-md mb-md">' +
      '<div class="flex flex-col gap-xs"><label class="font-label-sm text-label-sm font-bold text-on-surface-variant uppercase">Candidate Name</label><input id="recFormCandidate" value="' + escapeHtml(r.candidate) + '" required class="w-full bg-surface border border-outline-variant rounded-lg px-3 py-2 text-body-md focus:ring-2 focus:ring-primary/20" /></div>' +
      '<div class="flex flex-col gap-xs"><label class="font-label-sm text-label-sm font-bold text-on-surface-variant uppercase">Position</label><input id="recFormPosition" value="' + escapeHtml(r.position) + '" required class="w-full bg-surface border border-outline-variant rounded-lg px-3 py-2 text-body-md focus:ring-2 focus:ring-primary/20" /></div>' +
      '<div class="flex flex-col gap-xs"><label class="font-label-sm text-label-sm font-bold text-on-surface-variant uppercase">Stage</label><select id="recFormStage" class="w-full bg-surface border border-outline-variant rounded-lg px-3 py-2 text-body-md focus:ring-2 focus:ring-primary/20">' + stageOpts + '</select></div>' +
      '<div class="flex flex-col gap-xs"><label class="font-label-sm text-label-sm font-bold text-on-surface-variant uppercase">Applied Date</label><input id="recFormDate" type="date" value="' + escapeHtml(r.applied_date) + '" required class="w-full bg-surface border border-outline-variant rounded-lg px-3 py-2 text-body-md focus:ring-2 focus:ring-primary/20" /></div>' +
      '</div>' +
      '<div class="flex gap-sm mt-lg"><button type="submit" class="bg-primary text-on-primary px-lg py-sm rounded-lg font-label-md press-effect">Save</button>' +
      '<button type="button" class="bg-surface border border-outline-variant text-on-surface-variant px-lg py-sm rounded-lg font-label-md press-effect" onclick="controllers.recruitment.render()">Cancel</button></div>' +
      '</form></div>'
  },
  async saveForm() {
    var id = document.getElementById('recFormId').value
    var payload = {
      candidate: document.getElementById('recFormCandidate').value,
      position: document.getElementById('recFormPosition').value,
      stage: document.getElementById('recFormStage').value,
      applied_date: document.getElementById('recFormDate').value,
      status: 'Active'
    }
    try {
      if (id) {
        var existing = window.recruitmentService.getById(id)
        if (existing && payload.stage === 'Hired') payload.status = 'Hired'
        await window.recruitmentService.update(id, payload)
      } else {
        await window.recruitmentService.create(payload)
      }
      app.toast('Application saved', 'success')
      document.getElementById('content').innerHTML = this.render()
    } catch (e) { app.toast('Error saving: ' + e.message, 'error') }
    return false
  },
  async deleteCandidate(id) {
    if (!confirm('Delete this application?')) return
    try { await window.recruitmentService.remove(id); app.toast('Application deleted', 'success'); document.getElementById('content').innerHTML = this.render() } catch (e) { app.toast('Error deleting: ' + e.message, 'error') }
  }
}
