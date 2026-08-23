import { defineStore } from 'pinia'
import { api } from '../api/client.js'

export const usePortalStore = defineStore('portal', {
  state: () => ({
    // Catalog state
    catalog: [],
    catalogTotal: 0,
    catalogPage: 1,
    catalogLimit: 50,
    categories: [],
    selectedCategory: null,
    searchQuery: '',
    inStockOnly: false,
    catalogLoading: false,
    catalogError: null,

    // Account & ordering cutoff state
    accountSummary: null,
    accountLoading: false,
    accountError: null,
    cutoffStatus: null,
    cutoffLoading: false,

    // Replenishment cart state (persisted in localStorage)
    cart: JSON.parse(localStorage.getItem('portal_cart') || '[]'),

    // Orders state
    orders: [],
    ordersTotal: 0,
    ordersPage: 1,
    ordersLimit: 20,
    ordersFilter: null,
    currentOrder: null,
    ordersLoading: false,
    ordersError: null,

    // Invoices state
    invoices: [],
    invoicesTotal: 0,
    invoicesPage: 1,
    invoicesLimit: 20,
    invoicesFilter: null,
    currentInvoice: null,
    invoicesLoading: false,
    invoicesError: null,

    // Stripe checkout & settlement state
    checkoutSession: null,
    checkoutLoading: false,
    checkoutError: null,
    paymentStatus: null,
  }),

  getters: {
    cartItemCount: state => state.cart.reduce((sum, item) => sum + (Number(item.qty) || 0), 0),
    cartCount: state => state.cart.reduce((sum, item) => sum + (Number(item.qty) || 0), 0),
    cartUniqueItemCount: state => state.cart.length,
    cartSubtotal: state => {
      const total = state.cart.reduce((sum, item) => {
        const price = Number(item.unit_price ?? item.contracted_price ?? item.base_price ?? 0)
        const qty = Number(item.qty || 0)
        return sum + (price * qty)
      }, 0)
      return Math.round(total * 100) / 100
    },
    minOrderAmount: state => state.accountSummary?.min_order_amount || 0,
    meetsMinOrder: state => {
      const min = state.accountSummary?.min_order_amount || 0
      if (min <= 0) return true
      const subtotal = state.cart.reduce((sum, item) => {
        const price = Number(item.unit_price ?? item.contracted_price ?? item.base_price ?? 0)
        return sum + (price * (Number(item.qty) || 0))
      }, 0)
      return subtotal >= min
    },
    meetsMinimumOrder: state => {
      const min = state.accountSummary?.min_order_amount || 0
      if (min <= 0) return true
      const subtotal = state.cart.reduce((sum, item) => {
        const price = Number(item.unit_price ?? item.contracted_price ?? item.base_price ?? 0)
        return sum + (price * (Number(item.qty) || 0))
      }, 0)
      return subtotal >= min
    },
    minOrderDifference: state => {
      const min = state.accountSummary?.min_order_amount || 0
      const subtotal = state.cart.reduce((sum, item) => {
        const price = Number(item.unit_price ?? item.contracted_price ?? item.base_price ?? 0)
        return sum + (price * (Number(item.qty) || 0))
      }, 0)
      return Math.max(0, Math.round((min - subtotal) * 100) / 100)
    },
    minOrderShortfall: state => {
      const min = state.accountSummary?.min_order_amount || 0
      const subtotal = state.cart.reduce((sum, item) => {
        const price = Number(item.unit_price ?? item.contracted_price ?? item.base_price ?? 0)
        return sum + (price * (Number(item.qty) || 0))
      }, 0)
      return Math.max(0, Math.round((min - subtotal) * 100) / 100)
    },
    minOrderProgress: state => {
      const min = state.accountSummary?.min_order_amount || 0
      if (min <= 0) return 100
      const subtotal = state.cart.reduce((sum, item) => {
        const price = Number(item.unit_price ?? item.contracted_price ?? item.base_price ?? 0)
        return sum + (price * (Number(item.qty) || 0))
      }, 0)
      return Math.min(100, Math.round((subtotal / min) * 100))
    },
    isPastCutoff: state => !!state.cutoffStatus?.is_past_cutoff,
    nextDeliveryDate: state => state.cutoffStatus?.next_delivery_date || '',
    unpaidInvoices: state => state.invoices.filter(inv => inv.status !== 'Paid' && inv.status !== 'Cancelled'),
    paidInvoices: state => state.invoices.filter(inv => inv.status === 'Paid'),
    totalUnpaidBalance: state => {
      if (state.accountSummary?.current_balance !== undefined) {
        return Number(state.accountSummary.current_balance) || 0
      }
      return state.invoices
        .filter(inv => inv.status !== 'Paid' && inv.status !== 'Cancelled')
        .reduce((sum, inv) => sum + (Number(inv.balance_due ?? inv.total_amount) || 0), 0)
    },
    allowReorders: state => state.accountSummary?.allow_reorders !== false,
  },

  actions: {
    // ----------------------------------------------------------------------
    // Catalog & Pricing Actions
    // ----------------------------------------------------------------------
    async fetchCatalog(options = {}) {
      this.catalogLoading = true
      this.catalogError = null
      try {
        const params = {
          page: options.page || this.catalogPage,
          limit: options.limit || this.catalogLimit,
        }
        if (options.categoryId !== undefined) {
          this.selectedCategory = options.categoryId
        }
        if (this.selectedCategory !== null && this.selectedCategory !== undefined && this.selectedCategory !== '') {
          params.category_id = this.selectedCategory
        }
        if (options.search !== undefined) {
          this.searchQuery = options.search
        }
        if (this.searchQuery) {
          params.search = this.searchQuery
        }
        if (options.inStockOnly !== undefined) {
          this.inStockOnly = options.inStockOnly
        }
        if (this.inStockOnly) {
          params.in_stock_only = true
        }

        const res = await api.get('/portal/catalog', { params })
        if (res && res.data) {
          this.catalog = res.data.items || []
          this.catalogTotal = res.data.total || 0
          this.categories = res.data.categories || []
          this.catalogPage = res.data.page || 1
          this.catalogLimit = res.data.limit || 50
        }
        return res.data
      } catch (err) {
        this.catalogError = err.response?.data?.detail || err.message || 'Failed to load product catalog'
        return null
      } finally {
        this.catalogLoading = false
      }
    },

    // ----------------------------------------------------------------------
    // Account Summary & Cutoff Actions
    // ----------------------------------------------------------------------
    async fetchAccountSummary() {
      this.accountLoading = true
      this.accountError = null
      try {
        const res = await api.get('/portal/account/summary')
        if (res && res.data) {
          this.accountSummary = res.data
        }
        return res.data
      } catch (err) {
        this.accountError = err.response?.data?.detail || err.message || 'Failed to load account summary'
        return null
      } finally {
        this.accountLoading = false
      }
    },

    async fetchCutoffStatus() {
      this.cutoffLoading = true
      try {
        const res = await api.get('/portal/cutoff-status')
        if (res && res.data) {
          this.cutoffStatus = res.data
        }
        return res.data
      } catch {
        return null
      } finally {
        this.cutoffLoading = false
      }
    },

    // ----------------------------------------------------------------------
    // Replenishment Cart Actions
    // ----------------------------------------------------------------------
    addToCart(product, qty = 1) {
      const quantityToAdd = Number(qty) || 1
      if (quantityToAdd <= 0) return

      const existingIndex = this.cart.findIndex(i => i.product_id === product.id || i.product_id === product.product_id)
      const unitPrice = Number(product.contracted_price ?? product.unit_price ?? product.base_price ?? 0)

      if (existingIndex >= 0) {
        this.cart[existingIndex].qty = Number(this.cart[existingIndex].qty || 0) + quantityToAdd
        if (unitPrice > 0) {
          this.cart[existingIndex].unit_price = unitPrice
        }
      } else {
        this.cart.push({
          product_id: product.id ?? product.product_id,
          product_code: product.product_code ?? '',
          product_name: product.product_name ?? '',
          category_name: product.category_name ?? '',
          uom_name: product.uom_name ?? '',
          unit_price: unitPrice,
          base_price: Number(product.base_price ?? unitPrice),
          is_contracted: !!product.is_contracted,
          discount_percent: Number(product.discount_percent ?? 0),
          qty: quantityToAdd,
          stock_qty: Number(product.stock_qty ?? 0),
          is_in_stock: product.is_in_stock !== false,
          image_url: product.image_url ?? null,
          notes: product.notes ?? '',
        })
      }
      this.saveCart()
    },

    updateCartQty(productId, qty) {
      const parsedQty = Number(qty)
      if (parsedQty <= 0) {
        this.removeFromCart(productId)
        return
      }
      const item = this.cart.find(i => i.product_id === productId)
      if (item) {
        item.qty = parsedQty
        this.saveCart()
      }
    },

    removeFromCart(productId) {
      this.cart = this.cart.filter(i => i.product_id !== productId)
      this.saveCart()
    },

    clearCart() {
      this.cart = []
      this.saveCart()
    },

    saveCart() {
      try {
        localStorage.setItem('portal_cart', JSON.stringify(this.cart))
      } catch {
        // Ignore localStorage quota or private mode issues
      }
    },

    // ----------------------------------------------------------------------
    // Order Placement & Validation Actions
    // ----------------------------------------------------------------------
    async validateCart() {
      try {
        const items = this.cart.map(i => ({
          product_id: i.product_id,
          qty: Number(i.qty),
          notes: i.notes || null,
        }))
        const res = await api.post('/portal/orders/validate', items)
        return res.data
      } catch (err) {
        throw new Error(err.response?.data?.detail || err.message || 'Cart validation failed')
      }
    },

    async submitOrder(payload = {}) {
      try {
        const items = payload.items || this.cart.map(i => ({
          product_id: i.product_id,
          qty: Number(i.qty),
          notes: i.notes || null,
        }))

        const orderData = {
          items,
          warehouse_id: payload.warehouse_id || null,
          requested_delivery_date: payload.requested_delivery_date || null,
          notes: payload.notes || null,
          status: payload.status || 'Confirmed',
        }

        const res = await api.post('/portal/orders', orderData)
        if (res && res.data) {
          // Clear cart on successful order submission
          this.clearCart()
          // Refresh account summary in background
          this.fetchAccountSummary()
          return res.data
        }
        return null
      } catch (err) {
        throw new Error(err.response?.data?.detail || err.message || 'Failed to submit order')
      }
    },

    async fetchOrders(options = {}) {
      this.ordersLoading = true
      this.ordersError = null
      try {
        const params = {
          page: options.page || this.ordersPage,
          limit: options.limit || this.ordersLimit,
        }
        if (options.status) {
          params.status = options.status
          params.status_filter = options.status
        }
        const res = await api.get('/portal/orders', { params })
        if (res && res.data) {
          this.orders = res.data.items || []
          this.ordersTotal = res.data.total || 0
          this.ordersPage = res.data.page || 1
          this.ordersLimit = res.data.limit || 20
        }
        return res.data
      } catch (err) {
        this.ordersError = err.response?.data?.detail || err.message || 'Failed to load order history'
        return null
      } finally {
        this.ordersLoading = false
      }
    },

    updateCartQuantity(productId, qty) {
      return this.updateCartQty(productId, qty)
    },

    loadOrderToCart(order, replace = false) {
      if (replace) {
        this.clearCart()
      }
      const lines = order.lines || []
      let addedCount = 0
      for (const line of lines) {
        const itemQty = Number(line.qty ?? line.quantity ?? 0)
        if (line.product_id && itemQty > 0) {
          this.addToCart({
            id: line.product_id,
            product_id: line.product_id,
            product_code: line.product_code || '',
            product_name: line.product_name || '',
            uom_name: line.uom_name || '',
            unit_price: Number(line.unit_price || 0),
            contracted_price: Number(line.unit_price || 0),
            base_price: Number(line.unit_price || 0),
            is_contracted: true,
          }, itemQty)
          addedCount += 1
        }
      }
      return addedCount
    },

    async createOrder(payload = {}) {
      return this.submitOrder(payload)
    },

    async fetchOrderDetail(orderId) {
      this.ordersLoading = true
      this.ordersError = null
      try {
        const res = await api.get(`/portal/orders/${orderId}`)
        if (res && res.data) {
          this.currentOrder = res.data
        }
        return res.data
      } catch (err) {
        this.ordersError = err.response?.data?.detail || err.message || `Failed to load order #${orderId}`
        return null
      } finally {
        this.ordersLoading = false
      }
    },

    async reorderPastOrder(orderId, payload = {}) {
      try {
        const body = {
          order_id: orderId,
          requested_delivery_date: payload.requested_delivery_date || null,
          notes: payload.notes || null,
          status: payload.status || 'Confirmed',
        }
        const res = await api.post(`/portal/orders/${orderId}/reorder`, body)
        if (res && res.data) {
          this.fetchAccountSummary()
          return res.data
        }
        return null
      } catch (err) {
        throw new Error(err.response?.data?.detail || err.message || `Failed to reorder order #${orderId}`)
      }
    },

    async cancelOrder(orderId, reason = '') {
      try {
        const res = await api.post(`/portal/orders/${orderId}/cancel`, { reason })
        if (res && res.data) {
          this.currentOrder = res.data
          // Update in orders list if present
          const idx = this.orders.findIndex(o => o.id === orderId)
          if (idx >= 0) {
            this.orders[idx] = res.data
          }
          this.fetchAccountSummary()
          return res.data
        }
        return null
      } catch (err) {
        throw new Error(err.response?.data?.detail || err.message || `Failed to cancel order #${orderId}`)
      }
    },

    // ----------------------------------------------------------------------
    // Invoices & Settlement Actions
    // ----------------------------------------------------------------------
    async fetchInvoices(options = {}) {
      this.invoicesLoading = true
      this.invoicesError = null
      try {
        const params = {
          page: options.page || this.invoicesPage,
          limit: options.limit || this.invoicesLimit,
        }
        if (options.status) {
          params.status = options.status
        }
        const res = await api.get('/portal/invoices', { params })
        if (res && res.data) {
          this.invoices = res.data.items || []
          this.invoicesTotal = res.data.total || 0
          this.invoicesPage = res.data.page || 1
          this.invoicesLimit = res.data.limit || 20
        }
        return res.data
      } catch (err) {
        this.invoicesError = err.response?.data?.detail || err.message || 'Failed to load invoices'
        return null
      } finally {
        this.invoicesLoading = false
      }
    },

    async fetchInvoiceDetail(invoiceId) {
      this.invoicesLoading = true
      this.invoicesError = null
      try {
        const res = await api.get(`/portal/invoices/${invoiceId}`)
        if (res && res.data) {
          this.currentInvoice = res.data
        }
        return res.data
      } catch (err) {
        this.invoicesError = err.response?.data?.detail || err.message || `Failed to load invoice #${invoiceId}`
        return null
      } finally {
        this.invoicesLoading = false
      }
    },

    async downloadInvoicePdf(invoiceId) {
      try {
        const res = await api.get(`/portal/invoices/${invoiceId}/pdf`, {
          responseType: 'blob',
        })
        const blob = new Blob([res.data], { type: 'application/pdf' })
        const url = window.URL.createObjectURL(blob)
        const link = document.createElement('a')
        link.href = url
        link.download = `invoice_${invoiceId}.pdf`
        document.body.appendChild(link)
        link.click()
        document.body.removeChild(link)
        window.URL.revokeObjectURL(url)
        return true
      } catch (err) {
        throw new Error(err.response?.data?.detail || err.message || `Failed to download PDF for invoice #${invoiceId}`)
      }
    },

    async createInvoiceCheckoutSession(invoiceId, options = {}) {
      this.checkoutLoading = true
      this.checkoutError = null
      try {
        const origin = window.location.origin
        const body = {
          invoice_id: invoiceId,
          payment_method_types: options.paymentMethodTypes || ['card', 'us_bank_account'],
          success_url: options.successUrl || `${origin}/portal/payment/success?session_id={CHECKOUT_SESSION_ID}&invoice_id=${invoiceId}`,
          cancel_url: options.cancelUrl || `${origin}/portal/invoices`,
        }
        const res = await api.post(`/portal/invoices/${invoiceId}/checkout-session`, body)
        if (res && res.data) {
          this.checkoutSession = res.data
          return res.data
        }
        return null
      } catch (err) {
        this.checkoutError = err.response?.data?.detail || err.message || 'Failed to initialize payment checkout'
        throw new Error(this.checkoutError)
      } finally {
        this.checkoutLoading = false
      }
    },

    async createBalanceCheckoutSession(amount, options = {}) {
      this.checkoutLoading = true
      this.checkoutError = null
      try {
        const origin = window.location.origin
        const body = {
          amount: Number(amount),
          invoice_ids: options.invoiceIds || null,
          payment_method_types: options.paymentMethodTypes || ['card', 'us_bank_account'],
          success_url: options.successUrl || `${origin}/portal/payment/success?session_id={CHECKOUT_SESSION_ID}&type=balance`,
          cancel_url: options.cancelUrl || `${origin}/portal/invoices`,
        }
        const res = await api.post('/portal/settlement/checkout-session', body)
        if (res && res.data) {
          this.checkoutSession = res.data
          return res.data
        }
        return null
      } catch (err) {
        this.checkoutError = err.response?.data?.detail || err.message || 'Failed to initialize balance settlement'
        throw new Error(this.checkoutError)
      } finally {
        this.checkoutLoading = false
      }
    },

    async fetchPaymentSessionStatus(sessionId) {
      try {
        const res = await api.get(`/portal/settlement/session/${sessionId}`)
        if (res && res.data) {
          this.paymentStatus = res.data
          // Refresh account summary and invoices
          this.fetchAccountSummary()
          this.fetchInvoices()
          return res.data
        }
        return null
      } catch (err) {
        throw new Error(err.response?.data?.detail || err.message || 'Failed to verify payment session')
      }
    },
  },
})
