window.DynamicScreen = class DynamicScreen {
  constructor(config) {
    this.config = config
    this._data = []
    this._searchTerm = ''
    this._sortKey = ''
    this._sortDir = 1
    this._loaded = false
    this._moduleName = config.module || ''
    this._entityName = config.entityName || 'Record'
    this._primaryKey = config.primaryKey || 'id'
    this._fields = config.fields || []
    this._columns = config.columns || []
    this._stats = config.stats || []
    this._filters = config.filters || []
    this._buildPayload = config.buildPayload || function(data) { return data }
    this._searchFields = config.searchFields || this._fields.map(function(f) { return f.key })

    if (config.service) {
      this._dataSource = 'service'
      this._serviceKey = typeof config.service === 'string' ? config.service : null
      this._service = typeof config.service === 'string' ? null : config.service
    } else if (config.api) {
      this._dataSource = 'api'
      this._api = config.api
    } else if (config.table) {
      this._dataSource = 'api'
      this._api = new ApiClient(config.table)
    } else {
      this._dataSource = 'none'
    }
  }

  async load() {
    if (this._dataSource === 'service') {
      var svc = this._service || (this._serviceKey ? window[this._serviceKey] : null)
      this._service = svc
      if (svc && svc.load) await svc.load()
      this._data = svc ? (svc.getAll() || []) : []
    } else if (this._dataSource === 'api' && this._api) {
      try { this._data = await this._api.list() || [] } catch (e) { this._data = [] }
    }
    this._loaded = true
  }

  getAll() { return this._data }

  _filtered() {
    var q = (this._searchTerm || '').toLowerCase()
    if (!q) return this._data
    var pk = this._primaryKey
    return this._data.filter(function(row) {
      return this._searchFields.some(function(k) {
        var v = row[k]
        return v != null && String(v).toLowerCase().indexOf(q) > -1
      })
    }, this)
  }

  _sorted(arr) {
    if (!this._sortKey) return arr
    var k = this._sortKey; var d = this._sortDir
    return arr.slice().sort(function(a, b) {
      var av = a[k], bv = b[k]
      if (av == null) av = ''; if (bv == null) bv = ''
      if (typeof av === 'number') return (av - bv) * d
      return String(av).localeCompare(String(bv)) * d
    })
  }

  _sortLink(key, label) {
    var arrow = ''
    if (this._sortKey === key) arrow = this._sortDir === 1 ? ' ▲' : ' ▼'
    return '<a href="#" class="sort-link" data-sort="' + key + '" onclick="return app.loadModule(\'' + this._moduleName + '\')">' + label + arrow + '</a>'
  }

  _cellHtml(col, row) {
    var val = row[col.key]
    if (col.render) return col.render(val, row)
    if (val == null || val === '') return '<span class="text-on-surface-variant/40">-</span>'
    return escapeHtml(String(val))
  }

  _rowHtml(row) {
    var pk = row[this._primaryKey]
    var editFn = 'controllers.' + this._moduleName + '.showEditForm(' + JSON.stringify(pk) + ')'
    var delFn = 'controllers.' + this._moduleName + '.deleteRecord(' + JSON.stringify(pk) + ')'
    var cells = this._columns.map(function(col) {
      var tdClass = col.align === 'right' ? ' class="text-right"' : col.align === 'center' ? ' class="text-center"' : ''
      return '<td' + tdClass + '>' + this._cellHtml(col, row) + '</td>'
    }, this).join('')
    var actions = '<td class="text-center whitespace-nowrap">' +
      '<button class="p-1 hover:bg-surface-variant/50 rounded text-primary" onclick="' + editFn + '"><span class="material-symbols-outlined text-[18px]">edit</span></button>' +
      '<button class="p-1 hover:bg-error-container rounded text-error" onclick="' + delFn + '"><span class="material-symbols-outlined text-[18px]">delete</span></button>' +
      '</td>'
    return '<tr class="hover:bg-primary-container/5 transition-colors group">' + cells + actions + '</tr>'
  }

  _statsHtml() {
    if (!this._stats.length) return ''
    var html = this._stats.map(function(s) {
      var val = typeof s.value === 'function' ? s.value(this._data) : (s.value || 0)
      return '<div class="stat-card"><div class="stat-value">' + val + '</div><div class="stat-label">' + s.label + '</div></div>'
    }, this).join('')
    return '<div class="grid grid-cols-2 lg:grid-cols-4 gap-md mb-lg">' + html + '</div>'
  }

  render() {
    var filtered = this._filtered()
    var sorted = this._sorted(filtered)
    var rows = sorted.map(function(r) { return this._rowHtml(r) }, this).join('')
    var thClass = 'px-md py-md text-left font-label-md text-label-md text-on-surface-variant uppercase tracking-wider border-b border-outline-variant'
    var headers = this._columns.map(function(col) {
      return '<th class="' + thClass + '">' + this._sortLink(col.key, col.label) + '</th>'
    }, this).join('')
    headers += '<th class="' + thClass + ' text-center">Actions</th>'

    var addBtn = '<button class="bg-primary text-on-primary font-title-md text-title-md py-sm px-lg rounded flex items-center gap-sm press-effect hover:bg-primary-container transition-all" onclick="controllers.' + this._moduleName + '.showAddForm()"><span class="material-symbols-outlined">add</span> Add ' + this._entityName + '</button>'

    var searchHtml = this.config.hideSearch ? '' :
      '<div class="flex items-center gap-md mb-lg"><input class="w-full max-w-sm px-md py-sm bg-surface-container-low border border-outline-variant rounded focus:border-primary focus:ring-0 transition-all outline-none text-body-md" id="' + this._moduleName + 'Search" placeholder="Search ' + this._entityName + '..." onkeyup="controllers.' + this._moduleName + '.search(this.value)" type="text"/></div>'

    return this._statsHtml() + searchHtml +
      '<div class="surface-card rounded-xl overflow-hidden border border-outline-variant">' +
      '<div class="flex items-center justify-between px-lg py-md border-b border-outline-variant bg-surface-container-lowest"><h2 class="font-title-md text-title-md text-on-surface font-semibold">' + this.config.title + '</h2>' + addBtn + '</div>' +
      '<div class="overflow-x-auto"><table class="w-full"><thead>' + headers + '</thead><tbody>' + (rows || '<tr><td colspan="99" class="text-center py-xl text-on-surface-variant">No ' + this._entityName + ' found</td></tr>') + '</tbody></table></div></div>'
  }

  mount() {
    controllers[this._moduleName] = this
    var s = document.getElementById(this._moduleName + 'Search')
    if (s) s.value = this._searchTerm || ''
  }

  search(q) { this._searchTerm = q; document.getElementById('content').innerHTML = this.render() }

  _formField(field) {
    var id = this._moduleName + 'Form_' + field.key
    var val = field.value != null ? escapeHtml(String(field.value)) : (field.default != null ? escapeHtml(String(field.default)) : '')
    var label = '<label class="block font-label-md text-label-md text-on-surface-variant uppercase tracking-wider mb-xs" for="' + id + '">' + field.label + (field.required ? ' <span class="text-error">*</span>' : '') + '</label>'
    var input = ''
    if (field.type === 'select' || field.options) {
      var opts = (field.options || []).map(function(o) {
        var optVal = typeof o === 'object' ? o.value : o
        var optLabel = typeof o === 'object' ? o.label : o
        var sel = String(optVal) === val ? ' selected' : ''
        return '<option value="' + escapeHtml(String(optVal)) + '"' + sel + '>' + escapeHtml(String(optLabel)) + '</option>'
      }).join('')
      input = '<select class="w-full px-md py-sm bg-surface-container-low border border-outline-variant rounded focus:border-primary focus:ring-0 outline-none text-body-md" id="' + id + '">' + opts + '</select>'
    } else if (field.type === 'textarea') {
      input = '<textarea class="w-full px-md py-sm bg-surface-container-low border border-outline-variant rounded focus:border-primary focus:ring-0 outline-none text-body-md" id="' + id + '">' + val + '</textarea>'
    } else {
      var type = field.type || 'text'
      input = '<input class="w-full px-md py-sm bg-surface-container-low border border-outline-variant rounded focus:border-primary focus:ring-0 outline-none text-body-md" id="' + id + '" type="' + type + '" value="' + val + '"' + (field.step ? ' step="' + field.step + '"' : '') + (field.required ? ' required' : '') + '/>'
    }
    return '<div class="space-y-xs">' + label + input + '</div>'
  }

  _formHtml(title, id, fields) {
    return '<div class="max-w-2xl mx-auto">' +
      '<div class="surface-card rounded-xl overflow-hidden border border-outline-variant">' +
      '<div class="flex items-center justify-between px-lg py-md border-b border-outline-variant bg-surface-container-lowest"><h2 class="font-title-md text-title-md text-on-surface font-semibold">' + title + '</h2></div>' +
      '<form class="p-lg space-y-lg" onsubmit="return controllers.' + this._moduleName + '.saveForm()">' +
      '<input type="hidden" id="' + this._moduleName + 'FormId" value="' + (id || '') + '"/>' +
      fields +
      '<div class="flex items-center gap-md pt-md border-t border-outline-variant">' +
      '<button type="submit" class="bg-primary text-on-primary font-title-md text-title-md py-sm px-lg rounded press-effect hover:bg-primary-container transition-all">Save</button>' +
      '<button type="button" class="bg-surface-container-low text-on-surface-variant font-title-md text-title-md py-sm px-lg rounded border border-outline-variant press-effect hover:bg-surface-container-high transition-all" onclick="app.loadModule(\'' + this._moduleName + '\')">Cancel</button>' +
      '</div></form></div></div>'
  }

  showAddForm() {
    var fields = this._fields.map(function(f) {
      f.value = f.default ?? ''
      return this._formField(f)
    }, this).join('')
    document.getElementById('content').innerHTML = this._formHtml('Add ' + this._entityName, '', fields)
  }

  showEditForm(id) {
    var record = this._data.find(function(r) { return r[this._primaryKey] == id }, this)
    if (!record) return
    var fields = this._fields.map(function(f) {
      f.value = record[f.key] ?? ''
      return this._formField(f)
    }, this).join('')
    document.getElementById('content').innerHTML = this._formHtml('Edit ' + this._entityName, id, fields)
  }

  _getSvc() {
    return this._service || (this._serviceKey ? window[this._serviceKey] : null)
  }

  async saveForm() {
    var id = document.getElementById(this._moduleName + 'FormId').value
    var data = {}
    this._fields.forEach(function(f) {
      var el = document.getElementById(this._moduleName + 'Form_' + f.key)
      if (!el) return
      data[f.key] = el.type === 'number' ? parseFloat(el.value) || 0 : el.value
    }, this)
    if (data[this._primaryKey] == null) delete data[this._primaryKey]
    var payload = this._buildPayload(data, !!id)
    var svc = this._getSvc()
    try {
      if (id) {
        if (this._dataSource === 'api' && this._api) await this._api.update(id, payload)
        else if (svc) await svc.update(id, payload)
      } else {
        if (this._dataSource === 'api' && this._api) await this._api.create(payload)
        else if (svc) await svc.add(payload)
      }
      await this.load()
      document.getElementById('content').innerHTML = this.render()
    } catch (e) {
      app.toast('Error saving: ' + e.message, 'error')
    }
    return false
  }

  async deleteRecord(id) {
    if (!confirm('Delete this ' + this._entityName + '?')) return
    var svc = this._getSvc()
    try {
      if (this._dataSource === 'api' && this._api) await this._api.delete(id)
      else if (svc) await svc.remove(id)
      await this.load()
      document.getElementById('content').innerHTML = this.render()
    } catch (e) {
      app.toast('Error deleting: ' + e.message, 'error')
    }
  }
}
