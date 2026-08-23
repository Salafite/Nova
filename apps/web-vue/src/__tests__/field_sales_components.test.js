import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import SyncStatusBadge from '../components/mobile/SyncStatusBadge.vue'
import CustomerSelectCard from '../components/mobile/CustomerSelectCard.vue'
import FastCatalogSearch from '../components/mobile/FastCatalogSearch.vue'
import MobileCartDrawer from '../components/mobile/MobileCartDrawer.vue'
import ConflictResolutionModal from '../components/mobile/ConflictResolutionModal.vue'
import FieldSalesMobileView from '../views/mobile/FieldSalesMobileView.vue'
import { useFieldSalesStore } from '../stores/fieldSales.js'

// Mock fake-indexeddb
import 'fake-indexeddb/auto'

import { catalogSearch } from '../services/catalogSearch.js'

describe('Field Sales Mobile UI Components', () => {
  let pinia
  let store

  beforeEach(() => {
    pinia = createPinia()
    setActivePinia(pinia)
    store = useFieldSalesStore()

    // Mock store products & customers
    const mockProducts = [
      { id: 1, name: 'Whole Milk 1L', sku: 'MILK-001', barcode: '123456789012', price: 3.5, stock_quantity: 50, category: 'Dairy', uom_code: 'BTL' },
      { id: 2, name: 'Cheddar Cheese 250g', sku: 'CHZ-002', barcode: '234567890123', price: 6.0, stock_quantity: 5, category: 'Dairy', uom_code: 'PKG' },
      { id: 3, name: 'Sourdough Bread', sku: 'BRD-003', barcode: '345678901234', price: 4.25, stock_quantity: 0, category: 'Bakery', uom_code: 'LOAF' }
    ]
    store.products = mockProducts
    store.totalProductsCount = 3
    catalogSearch.buildIndex(mockProducts)
    store.categories = catalogSearch.getCategories()
    store.warehouses = [
      { id: 1, name: 'Main Distribution Center' }
    ]
    store.customers = [
      {
        id: 10,
        name: 'Metro Supermarket',
        group_name: 'Key Accounts',
        phone: '555-1234',
        city: 'Metropolis',
        credit_limit: 10000,
        balance: 2500,
        available_credit: 7500,
        payment_term_id: 1,
        recent_orders: [
          {
            order_id: 101,
            order_number: 'SO-2026-001',
            order_date: '2026-08-20',
            total_amount: 150.0,
            lines: [{ product_id: 1, product_name: 'Whole Milk 1L', qty: 20 }]
          }
        ]
      }
    ]
    store.customerRecentOrders = store.customers[0].recent_orders
  })

  describe('SyncStatusBadge', () => {
    it('renders online status correctly', () => {
      store.isOnline = true
      store.isSyncing = false
      const wrapper = mount(SyncStatusBadge, { global: { plugins: [pinia] } })
      expect(wrapper.text()).toContain('Online')
      expect(wrapper.find('.pulse-online').exists()).toBe(true)
    })

    it('renders offline and queued count when offline with pending orders', () => {
      store.isOnline = false
      store.pendingCount = 3
      const wrapper = mount(SyncStatusBadge, { global: { plugins: [pinia] } })
      expect(wrapper.text()).toContain('Offline')
      expect(wrapper.find('.badge-pending').text()).toContain('3')
    })

    it('toggles diagnostic popover on click', async () => {
      const wrapper = mount(SyncStatusBadge, { global: { plugins: [pinia] } })
      expect(wrapper.find('.details-popover').exists()).toBe(false)
      await wrapper.find('.status-pill').trigger('click')
      expect(wrapper.find('.details-popover').exists()).toBe(true)
      expect(wrapper.text()).toContain('Sync Diagnostics')
    })
  })

  describe('CustomerSelectCard', () => {
    it('renders search input when no customer selected', () => {
      store.selectedCustomer = null
      const wrapper = mount(CustomerSelectCard, { global: { plugins: [pinia] } })
      expect(wrapper.find('.customer-search-input').exists()).toBe(true)
      expect(wrapper.text()).toContain('Metro Supermarket')
    })

    it('renders customer financial profile when customer is selected', () => {
      store.selectedCustomer = store.customers[0]
      const wrapper = mount(CustomerSelectCard, { global: { plugins: [pinia] } })
      expect(wrapper.find('.customer-name-heading').text()).toBe('Metro Supermarket')
      expect(wrapper.text()).toContain('Credit Limit')
      expect(wrapper.text()).toContain('$10,000.00')
      expect(wrapper.text()).toContain('$7,500.00')
      expect(wrapper.text()).toContain('Recent Orders (1)')
    })
  })

  describe('FastCatalogSearch', () => {
    it('renders search bar, category pills, and product items', () => {
      const wrapper = mount(FastCatalogSearch, { global: { plugins: [pinia] } })
      expect(wrapper.find('.catalog-search-input').exists()).toBe(true)
      expect(wrapper.text()).toContain('All Products')
      expect(wrapper.text()).toContain('Dairy')
      expect(wrapper.text()).toContain('Bakery')
      expect(wrapper.text()).toContain('Whole Milk 1L')
      expect(wrapper.text()).toContain('Cheddar Cheese 250g')
    })

    it('filters products when search query is typed', async () => {
      const wrapper = mount(FastCatalogSearch, { global: { plugins: [pinia] } })
      const searchInput = wrapper.find('.catalog-search-input')
      await searchInput.setValue('Cheese')
      expect(store.searchQuery).toBe('Cheese')
    })
  })

  describe('MobileCartDrawer', () => {
    it('renders empty cart state when no lines present', () => {
      store.draft.lines = []
      const wrapper = mount(MobileCartDrawer, {
        props: { isOpen: true },
        global: { plugins: [pinia] }
      })
      expect(wrapper.text()).toContain('Your draft order is empty')
    })

    it('renders cart line items and totals when items in draft', () => {
      store.selectedCustomer = store.customers[0]
      store.draft.lines = [
        {
          line_number: 1,
          product_id: 1,
          sku: 'MILK-001',
          name: 'Whole Milk 1L',
          qty: 2,
          unit_price: 3.5,
          discount_pct: 0,
          tax_rate: 0,
          subtotal: 7.0,
          tax_amount: 0,
          total: 7.0
        }
      ]
      store.draft.subtotal = 7.0
      store.draft.grand_total = 7.0

      const wrapper = mount(MobileCartDrawer, {
        props: { isOpen: true },
        global: { plugins: [pinia] }
      })
      expect(wrapper.text()).toContain('Whole Milk 1L')
      expect(wrapper.text()).toContain('$7.00')
      expect(wrapper.find('.qty-input').element.value).toBe('2')
    })
  })

  describe('ConflictResolutionModal', () => {
    it('renders conflict details and resolution buttons', () => {
      const order = {
        client_order_uuid: 'uuid-1234-5678',
        customer_name: 'Metro Supermarket',
        order_date: '2026-08-20',
        grand_total: 120.0,
        conflicts: [
          {
            product_id: 3,
            sku: 'BRD-003',
            product_name: 'Sourdough Bread',
            requested_qty: 10,
            available_qty: 0,
            reason: 'OUT_OF_STOCK'
          }
        ]
      }

      const wrapper = mount(ConflictResolutionModal, {
        props: { order },
        global: { plugins: [pinia] }
      })

      expect(wrapper.text()).toContain('Stock Conflict Resolution')
      expect(wrapper.text()).toContain('Sourdough Bread')
      expect(wrapper.text()).toContain('Out of Stock')
      expect(wrapper.text()).toContain('Keep as Backorder')
      expect(wrapper.text()).toContain('Remove from Order')
    })
  })

  describe('FieldSalesMobileView', () => {
    it('mounts and switches between capture and queue tabs', async () => {
      const wrapper = mount(FieldSalesMobileView, {
        global: { plugins: [pinia] }
      })

      expect(wrapper.text()).toContain('Field Sales')
      expect(wrapper.text()).toContain('Order Capture')
      expect(wrapper.text()).toContain('Sync Queue')

      // Switch to Queue tab
      const queueTabBtn = wrapper.findAll('.tab-item')[1]
      await queueTabBtn.trigger('click')
      expect(wrapper.find('.sync-queue-panel').isVisible()).toBe(true)
    })
  })
})
