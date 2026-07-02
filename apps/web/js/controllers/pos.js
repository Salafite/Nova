var cart = []

function posRenderProductList(list) {
  var el = document.getElementById('posProductList')
  el.innerHTML = list.map(function(item) {
      return '<div class="product-card bg-surface-container-lowest border border-outline-variant rounded p-sm flex flex-col group transition-all hover:border-primary/50 hover:shadow-sm cursor-pointer" onclick="controllers.pos.addToCart(\'' + item.id + '\')">' +
             '<div class="aspect-square bg-surface-container-low rounded mb-sm overflow-hidden relative">' +
             '<div class="w-full h-full flex items-center justify-center bg-surface-variant text-on-surface-variant"><span class="material-symbols-outlined text-[32px]">inventory_2</span></div>' +
             '</div>' +
             '<div class="flex-1">' +
             '<h3 class="font-title-md text-body-md font-semibold text-on-surface line-clamp-1">' + escapeHtml(item.name) + '</h3>' +
             '<p class="font-data-mono text-[11px] text-on-surface-variant mb-xs">SKU: NOVA-' + item.id + '</p>' +
             '<div class="flex items-center justify-between mt-sm">' +
             '<span class="font-data-mono text-primary font-bold">$' + item.price.toFixed(2) + '</span>' +
             '<span class="text-[10px] text-on-secondary px-1.5 py-0.5 bg-secondary rounded">In Stock</span>' +
             '</div>' +
             '</div>' +
             '<button class="mt-md w-full bg-primary-container text-on-primary-container py-2 rounded font-label-md flex items-center justify-center gap-xs group-hover:bg-primary group-hover:text-white transition-all">' +
             '<span class="material-symbols-outlined text-sm">add</span> Add to Cart' +
             '</button>' +
             '</div>'
  }).join('') || '<p class="text-on-surface-variant text-center col-span-full py-xl">No products found</p>'
}

function posRenderCart() {
  var el = document.getElementById('cartItems')
  if (!cart.length) {
    el.innerHTML = '<p class="text-on-surface-variant text-center py-xl">Cart is empty</p>'
    document.getElementById('cartCount').textContent = '0'
    document.getElementById('cartTotal').textContent = '0.00'
    return
  }
  el.innerHTML = cart.map(function(item, idx) {
    return '<div class="flex gap-sm items-center group mb-md">' +
             '<div class="w-16 h-16 bg-surface-container-low rounded border border-outline-variant flex-shrink-0 flex items-center justify-center">' +
             '<span class="material-symbols-outlined text-[24px] text-on-surface-variant">inventory_2</span>' +
             '</div>' +
             '<div class="flex-1 min-w-0">' +
             '<h4 class="font-body-md text-on-surface font-semibold truncate">' + escapeHtml(item.name) + '</h4>' +
             '<p class="font-data-mono text-[11px] text-on-surface-variant">$' + item.price.toFixed(2) + ' / unit</p>' +
             '</div>' +
             '<div class="flex flex-col items-end gap-xs">' +
             '<div class="flex items-center border border-outline-variant rounded bg-surface-container-low" onclick="event.stopPropagation()">' +
             '<button class="w-6 h-6 flex items-center justify-center hover:bg-outline-variant transition-colors" onclick="controllers.pos.decrementFromCart(' + idx + ')"><span class="material-symbols-outlined text-[14px]">remove</span></button>' +
             '<span class="w-8 text-center font-data-mono text-xs">' + String(item.qty).padStart(2, '0') + '</span>' +
             '<button class="w-6 h-6 flex items-center justify-center hover:bg-outline-variant transition-colors" onclick="controllers.pos.addToCart(\'' + item.productId + '\')"><span class="material-symbols-outlined text-[14px]">add</span></button>' +
             '</div>' +
             '<span class="font-data-mono text-primary font-bold">$' + (item.price * item.qty).toFixed(2) + '</span>' +
             '</div>' +
             '</div>'
  }).join('')
  var total = cart.reduce(function(s, item) { return s + item.price * item.qty }, 0)
  var tax = total * 0.05
  document.getElementById('cartCount').textContent = cart.length
  document.getElementById('cartSubtotal').textContent = '$' + total.toFixed(2)
  document.getElementById('cartTax').textContent = '$' + tax.toFixed(2)
  document.getElementById('cartTotalDisplay').textContent = '$' + (total + tax).toFixed(2)
}

window.NovaModules = window.NovaModules || {}; window.NovaModules['pos'] = {
  render() {
    var products = window.productService.getAll()
    var prodListHtml = products.map(function(item) {
      return '<div class="product-card bg-surface-container-lowest border border-outline-variant rounded p-sm flex flex-col group transition-all hover:border-primary/50 hover:shadow-sm cursor-pointer" onclick="controllers.pos.addToCart(\'' + item.id + '\')">' +
             '<div class="aspect-square bg-surface-container-low rounded mb-sm overflow-hidden relative">' +
             '<div class="w-full h-full flex items-center justify-center bg-surface-variant text-on-surface-variant"><span class="material-symbols-outlined text-[32px]">inventory_2</span></div>' +
             '</div>' +
             '<div class="flex-1">' +
             '<h3 class="font-title-md text-body-md font-semibold text-on-surface line-clamp-1">' + escapeHtml(item.name) + '</h3>' +
             '<p class="font-data-mono text-[11px] text-on-surface-variant mb-xs">SKU: NOVA-' + item.id + '</p>' +
             '<div class="flex items-center justify-between mt-sm">' +
             '<span class="font-data-mono text-primary font-bold">$' + item.price.toFixed(2) + '</span>' +
             '<span class="text-[10px] text-on-secondary px-1.5 py-0.5 bg-secondary rounded">In Stock</span>' +
             '</div>' +
             '</div>' +
             '<button class="mt-md w-full bg-primary-container text-on-primary-container py-2 rounded font-label-md flex items-center justify-center gap-xs group-hover:bg-primary group-hover:text-white transition-all">' +
             '<span class="material-symbols-outlined text-sm">add</span> Add to Cart' +
             '</button>' +
             '</div>'
    }).join('') || '<p class="text-on-surface-variant text-center col-span-full py-xl">No products found</p>'
    return renderHtml('screens/pos', {
      productList: prodListHtml,
      cartCount: '0',
      cartItems: '<p class="text-on-surface-variant text-center py-xl">Cart is empty</p>',
      cartTotal: '0.00'
    })
  },
  mount() {
    controllers.pos = this
    cart = []
  },
  search(q) {
    var products = window.productService.getAll()
    var filtered = q ? products.filter(function(p) { return p.name.toLowerCase().indexOf(q.toLowerCase()) > -1 }) : products
    posRenderProductList(filtered)
  },
  addToCart(productId) {
    var product = window.productService.getById(Number(productId))
    if (!product) return
    var existing = cart.find(function(c) { return c.productId === productId })
    if (existing) {
      existing.qty++
    } else {
      cart.push({ productId: product.id, name: product.name, price: product.price, qty: 1 })
    }
    posRenderCart()
  },
  removeFromCart(idx) { cart.splice(idx, 1); posRenderCart() },
  decrementFromCart(idx) {
    if (cart[idx].qty > 1) {
      cart[idx].qty--
    } else {
      cart.splice(idx, 1)
    }
    posRenderCart()
  },
  clearCart() { cart = []; posRenderCart() },
  async checkout() {
    if (!cart.length) return app.toast('Cart is empty', 'error')
    var customer = document.getElementById('customerInput').value || 'Walk-in Customer'
    try {
      await window.posService.checkout(cart, customer)
      app.toast('Sale completed!', 'success')
      cart = []
      posRenderCart()
      document.getElementById('customerInput').value = ''
    } catch (e) {
      app.toast('Checkout failed: ' + e.message, 'error')
    }
  }
}
