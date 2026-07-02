window.NovaModules = window.NovaModules || {}; window.NovaModules['documents'] = {
  render() {
    var search = this.searchTerm || ''
    var items = window.documentService.getAll()
    var filtered = search ? items.filter(function(d) { return (d.name || '').toLowerCase().indexOf(search) > -1 || (d.type || '').toLowerCase().indexOf(search) > -1 }) : items
    var rows = filtered.map(function(d) {
      var statusBadge = d.status === 'Published' ? '<span class="px-sm py-xs bg-secondary-container text-on-secondary-container rounded text-[11px] font-bold uppercase">Published</span>' : '<span class="px-sm py-xs bg-surface-container-high text-on-surface-variant rounded text-[11px] font-bold uppercase">' + escapeHtml(d.status || 'Draft') + '</span>'
      var sizeStr = d.size > 1048576 ? (d.size / 1048576).toFixed(1) + ' MB' : (d.size > 1024 ? (d.size / 1024).toFixed(1) + ' KB' : (d.size || 0) + ' B')
      return '<tr class="hover:bg-primary/5 transition-colors group">' +
             '<td class="px-lg py-md font-body-md font-semibold text-primary">' + escapeHtml(d.name) + '</td>' +
             '<td class="px-lg py-md text-body-md text-on-surface-variant">' + escapeHtml(d.type || '-') + '</td>' +
             '<td class="px-lg py-md text-body-md font-data-mono text-on-surface-variant">' + sizeStr + '</td>' +
             '<td class="px-lg py-md text-body-md text-on-surface-variant">' + escapeHtml(d.uploadedBy || '-') + '</td>' +
             '<td class="px-lg py-md text-body-md text-on-surface-variant">' + escapeHtml(d.uploadedAt || '-') + '</td>' +
             '<td class="px-lg py-md">' + statusBadge + '</td>' +
             '</tr>'
    }).join('')
    return renderHtml('screens/document_management', {
      documentRows: rows,
      totalDocuments: items.length,
      totalSize: window.documentService.getTotalSize() > 1048576 ? (window.documentService.getTotalSize() / 1048576).toFixed(1) + ' MB' : (window.documentService.getTotalSize() > 1024 ? (window.documentService.getTotalSize() / 1024).toFixed(1) + ' KB' : window.documentService.getTotalSize() + ' B'),
      publishedDocs: items.filter(function(d) { return d.status === 'Published' }).length
    })
  },
  mount() { controllers.documents = this; var s = document.getElementById('documentSearch'); if (s) s.value = this.searchTerm || '' },
  search(q) { this.searchTerm = q.toLowerCase(); document.getElementById('content').innerHTML = this.render() },
  showCreateForm() {
    document.getElementById('content').innerHTML = renderHtml('models/product/form', {
      title: 'Upload Document', id: '', name: '', type: 'PDF', status: 'Draft'
    })
  },
  async saveForm() {
    try {
      await window.documentService.create({
        name: document.getElementById('inspectionFormProduct') ? document.getElementById('inspectionFormProduct').value : 'New Document',
        type: 'PDF',
        size: 0,
        status: 'Draft'
      })
      app.toast('Document uploaded', 'success')
      document.getElementById('content').innerHTML = this.render()
    } catch (e) {
      app.toast('Error uploading document: ' + e.message, 'error')
    }
    return false
  },
  async deleteItem(id) {
    if (!confirm('Delete this document?')) return
    try {
      await window.documentService.remove(id)
      document.getElementById('content').innerHTML = this.render()
    } catch (e) {
      app.toast('Error deleting document: ' + e.message, 'error')
    }
  }
}
