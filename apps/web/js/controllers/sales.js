window.NovaModules = window.NovaModules || {}; window.NovaModules['sales'] = {
  render() {
    var search = this.searchTerm || ''
    var invoices = window.salesService.searchInvoices(search)
    var rows = invoices.map(function(inv) {
      return '<tr class="row-hover transition-colors cursor-pointer hover:bg-surface-container-low">' +
             '<td class="px-md py-md font-data-mono text-data-mono font-medium text-primary">#' + escapeHtml(inv.id) + '</td>' +
             '<td class="px-md py-md font-body-md">' + escapeHtml(inv.customer) + '</td>' +
             '<td class="px-md py-md font-body-md">' + escapeHtml(inv.date) + '</td>' +
             '<td class="px-md py-md font-body-md">' + (inv.items ? inv.items.length : 0) + '</td>' +
             '<td class="px-md py-md font-data-mono text-data-mono font-bold">$' + inv.total.toFixed(2) + '</td>' +
             '<td class="px-md py-md">' + Badge.orderStatus(inv.status) + '</td>' +
             '<td class="px-md py-md text-right"><button class="action-btn material-symbols-outlined text-on-surface-variant hover:text-primary p-xs rounded-full hover:bg-surface-container-high transition-colors" onclick="controllers.sales.viewDetails(\'' + inv.id + '\')">visibility</button></td>' +
             '</tr>'
    }).join('')
    return renderHtml('models/salesorder/list', { rows: rows })
  },
  mount() { controllers.sales = this; var s = document.getElementById('salesSearch'); if (s) s.value = this.searchTerm || '' },
  search(q) { this.searchTerm = q.toLowerCase(); document.getElementById('content').innerHTML = this.render() },
  viewDetails(id) {
    var inv = window.salesService.getInvoice(id)
    if (!inv) return
    var itemRows = (inv.items || []).map(function(item) {
      return '<tr><td>' + escapeHtml(item.name) + '</td><td>' + (item.qty || 1) + '</td><td>$' + (item.price || 0).toFixed(2) + '</td></tr>'
    }).join('') || '<tr><td colspan="3" style="color:var(--color-text-secondary)">No items</td></tr>'
    document.getElementById('content').innerHTML = renderHtml('models/salesorder/detail', {
      id: escapeHtml(inv.id), customer: escapeHtml(inv.customer), date: escapeHtml(inv.date),
      status: escapeHtml(inv.status), total: inv.total.toFixed(2), itemRows: itemRows
    })
  },
  showCreateForm() {
    var priceLists = window.priceListService.getAll()
    var taxRates = window.taxRateService.getAll()
    var customers = window.customerService.getAll ? window.customerService.getAll() : []
    var plOptions = priceLists.map(function(p) { return '<option value="' + p.id + '">' + escapeHtml(p.name) + '</option>' }).join('')
    var trOptions = taxRates.map(function(r) { return '<option value="' + r.id + '">' + escapeHtml(r.name) + ' (' + r.rate + '%)</option>' }).join('')
    document.getElementById('content').innerHTML = renderHtml('screens/sales_order_form', {
      priceListOptions: plOptions,
      taxRateOptions: trOptions
    })
    var custSelect = document.getElementById('soCustomer')
    if (custSelect) {
      custSelect.innerHTML = '<option value="">Select customer...</option>' +
        customers.map(function(c) { return '<option value="' + c.id + '">' + escapeHtml(c.name) + '</option>' }).join('')
    }
  },
  addLine() {
    var tbody = document.getElementById('soLinesBody')
    var idx = tbody.children.length
    var tr = document.createElement('tr')
    tr.innerHTML = '<td><input type="text" class="so-product-name w-full bg-surface border border-outline-variant rounded px-2 py-1 text-body-sm" placeholder="Product name"></td>' +
      '<td><select class="so-product-id w-full bg-surface border border-outline-variant rounded px-2 py-1 text-body-sm" onchange="controllers.sales.onProductSelect(this)"><option value="">Select...</option></select></td>' +
      '<td><input type="number" class="so-qty w-full bg-surface border border-outline-variant rounded px-2 py-1 text-body-sm" value="1" min="1" onchange="controllers.sales.recalc()" oninput="controllers.sales.recalc()"></td>' +
      '<td><input type="number" class="so-unit-price w-full bg-surface border border-outline-variant rounded px-2 py-1 text-body-sm" value="0" min="0" step="0.01" onchange="controllers.sales.recalc()" oninput="controllers.sales.recalc()"></td>' +
      '<td class="so-line-total font-data-mono text-data-mono text-right">$0.00</td>' +
      '<td><button type="button" class="material-symbols-outlined text-error hover:bg-error-container rounded-full p-xs" onclick="this.closest(\'tr\').remove();controllers.sales.recalc()">remove_circle</button></td>'
    tbody.appendChild(tr)
    this._loadProductSelect(tr.querySelector('.so-product-id'))
  },
  _loadProductSelect(select) {
    var products = window.productService.getAll ? window.productService.getAll() : []
    products.forEach(function(p) {
      var opt = document.createElement('option')
      opt.value = p.id
      opt.textContent = (p.name || '') + ' (SKU: ' + (p.sku || '') + ')'
      select.appendChild(opt)
    })
  },
  async onProductSelect(select) {
    var tr = select.closest('tr')
    var priceInput = tr.querySelector('.so-unit-price')
    var nameInput = tr.querySelector('.so-product-name')
    var pid = parseInt(select.value)
    if (!pid) return
    var product = null
    var products = window.productService.getAll ? window.productService.getAll() : []
    for (var i = 0; i < products.length; i++) { if (products[i].id == pid) { product = products[i]; break } }
    if (product) {
      if (!nameInput.value) nameInput.value = product.name || ''
      var plSelect = document.getElementById('soPriceList')
      var plId = plSelect ? parseInt(plSelect.value) : null
      if (plId) {
        try {
          var plApi = new ApiClient('T0084I')
          var items = await plApi.list({ price_list_id: plId, product_id: pid })
          if (items && items.length > 0) {
            priceInput.value = items[0].unit_price || 0
            this.recalc()
            return
          }
        } catch (e) {}
      }
      if (product.price) priceInput.value = product.price
    }
    this.recalc()
  },
  recalc() {
    var tbody = document.getElementById('soLinesBody')
    var subtotal = 0
    var rows = tbody.querySelectorAll('tr')
    rows.forEach(function(tr) {
      var qty = parseFloat(tr.querySelector('.so-qty').value) || 0
      var price = parseFloat(tr.querySelector('.so-unit-price').value) || 0
      var lineTotal = qty * price
      tr.querySelector('.so-line-total').textContent = '$' + lineTotal.toFixed(2)
      subtotal += lineTotal
    })
    document.getElementById('soSubtotal').textContent = '$' + subtotal.toFixed(2)
    var taxRateSelect = document.getElementById('soTaxRate')
    var taxPct = 0
    if (taxRateSelect) {
      var selectedId = parseInt(taxRateSelect.value)
      if (selectedId) {
        var rates = window.taxRateService.getAll()
        for (var i = 0; i < rates.length; i++) {
          if (rates[i].id == selectedId) { taxPct = rates[i].rate || 0; break }
        }
      }
    }
    var tax = subtotal * taxPct / 100
    var grandTotal = subtotal + tax
    document.getElementById('soTax').textContent = '$' + tax.toFixed(2)
    document.getElementById('soGrandTotal').textContent = '$' + grandTotal.toFixed(2)
  },
  async saveOrder() {
    var customerId = parseInt(document.getElementById('soCustomer').value)
    if (!customerId) { app.toast('Please select a customer', 'error'); return }
    var lines = []
    var tbody = document.getElementById('soLinesBody')
    var rowEls = tbody.querySelectorAll('tr')
    var valid = true
    rowEls.forEach(function(tr, i) {
      var name = tr.querySelector('.so-product-name').value.trim()
      if (!name) { valid = false; return }
      lines.push({
        product_id: parseInt(tr.querySelector('.so-product-id').value) || null,
        product_name: name,
        qty: parseFloat(tr.querySelector('.so-qty').value) || 1,
        unit_price: parseFloat(tr.querySelector('.so-unit-price').value) || 0,
        line_number: i + 1
      })
    })
    if (!valid) { app.toast('All lines need a product name', 'error'); return }
    if (lines.length === 0) { app.toast('Add at least one line item', 'error'); return }
    var orderData = {
      order_number: 'SO-' + String(Date.now()).slice(-6),
      customer_id: customerId,
      price_list_id: parseInt(document.getElementById('soPriceList').value) || null,
      tax_rate_id: parseInt(document.getElementById('soTaxRate').value) || null,
      payment_term_id: parseInt(document.getElementById('soPaymentTerm').value) || null
    }
    try {
      var result = await window.salesService.createWithLines(orderData, lines)
      app.toast('Sales order created: ' + (result.order_number || result.id), 'success')
      document.getElementById('content').innerHTML = this.render()
    } catch (e) { app.toast('Error: ' + e.message, 'error') }
  }
}
