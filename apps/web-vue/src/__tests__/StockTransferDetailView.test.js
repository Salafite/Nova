import { mount, flushPromises } from '@vue/test-utils'
import { vi, describe, it, expect, beforeEach, afterEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import StockTransferDetailView from '../views/warehouse/StockTransferDetailView.vue'
import { api } from '../api/client.js'

// Mock api
vi.mock('../api/client.js', () => ({
  api: {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    delete: vi.fn(),
    interceptors: { request: { use: vi.fn() }, response: { use: vi.fn() } },
  },
  CONFIG: { apiBase: 'http://test.local' },
}))

// Mock vue-router
const mockPush = vi.fn()
vi.mock('vue-router', () => ({
  useRoute: () => ({ params: { id: '1' } }),
  useRouter: () => ({ push: mockPush }),
}))

// Mock useWebSocket
vi.mock('../composables/useWebSocket.js', () => ({
  useWebSocket: () => ({ on: vi.fn(), send: vi.fn(), close: vi.fn() }),
}))

// Mock useToast
const mockToast = vi.fn()
vi.mock('../composables/useToast.js', () => ({
  useToast: () => ({ show: mockToast }),
}))

describe('StockTransferDetailView (Multi-Warehouse Transfer Execution)', () => {
  let pinia
  let wrapper

  const sampleTransfer = {
    id: 1,
    transfer_number: 'TRF-20260826-0001',
    source_warehouse_id: 1,
    source_warehouse_name: 'Central Distribution Hub',
    destination_warehouse_id: 2,
    destination_warehouse_name: 'Regional Branch North',
    status: 'In Transit',
    transfer_date: '2026-08-26',
    expected_delivery_date: '2026-08-28',
    carrier: 'FastFreight Logistics',
    tracking_number: 'FF-883921',
    dispatched_at: '2026-08-26T10:00:00Z',
    dispatched_by: 1,
    dispatched_by_name: 'Logistics Lead',
    received_at: null,
    received_by: null,
    received_by_name: null,
    total_requested_qty: 100,
    total_dispatched_qty: 100,
    total_received_qty: 0,
    total_lost_qty: 0,
    lines_count: 2,
    notes: 'Urgent cold storage replenishment',
    lines: [
      {
        id: 11,
        transfer_id: 1,
        product_id: 101,
        product_code: 'SKU-DAIRY-01',
        product_name: 'Fresh Milk 1L',
        uom_name: 'Carton',
        qty_requested: 60,
        qty_dispatched: 60,
        qty_received: 0,
        qty_lost: 0,
        batch_id: 201,
        batch_number: 'LOT-MILK-202608',
        line_number: 1,
      },
      {
        id: 12,
        transfer_id: 1,
        product_id: 102,
        product_code: 'SKU-CHEESE-02',
        product_name: 'Artisan Cheddar 500g',
        uom_name: 'Case',
        qty_requested: 40,
        qty_dispatched: 40,
        qty_received: 0,
        qty_lost: 0,
        batch_id: 202,
        batch_number: 'LOT-CHED-202608',
        line_number: 2,
      },
    ],
  }

  const sampleWarehouses = [
    { id: 1, name: 'Central Distribution Hub' },
    { id: 2, name: 'Regional Branch North' },
  ]

  const sampleProducts = [
    { id: 101, sku: 'SKU-DAIRY-01', name: 'Fresh Milk 1L' },
    { id: 102, sku: 'SKU-CHEESE-02', name: 'Artisan Cheddar 500g' },
  ]

  beforeEach(() => {
    pinia = createPinia()
    setActivePinia(pinia)
    vi.clearAllMocks()

    api.get.mockImplementation((url) => {
      if (url === '/T0108I/1/detail') return Promise.resolve({ data: JSON.parse(JSON.stringify(sampleTransfer)) })
      if (url === '/T0008I/') return Promise.resolve({ data: sampleWarehouses })
      if (url === '/T0003I/') return Promise.resolve({ data: sampleProducts })
      return Promise.resolve({ data: [] })
    })
  })

  afterEach(() => {
    if (wrapper) {
      wrapper.unmount()
      wrapper = null
    }
  })

  function createWrapper() {
    wrapper = mount(StockTransferDetailView, {
      global: {
        plugins: [pinia],
        stubs: {
          SkeletonCard: true,
          ErrorState: true,
          Teleport: true,
        },
      },
    })
    return wrapper
  }

  it('renders transfer document details, routes, and timeline', async () => {
    const w = createWrapper()
    await flushPromises()

    expect(w.text()).toContain('TRF-20260826-0001')
    expect(w.text()).toContain('Central Distribution Hub')
    expect(w.text()).toContain('Regional Branch North')
    expect(w.text()).toContain('FastFreight Logistics')
    expect(w.text()).toContain('FF-883921')
    expect(w.text()).toContain('Fresh Milk 1L')
    expect(w.text()).toContain('Artisan Cheddar 500g')
    expect(w.text()).toContain('LOT-MILK-202608')

    // Timeline step state for In Transit
    expect(w.text()).toContain('Order Created')
    expect(w.text()).toContain('Dispatched (In Transit)')
    expect(w.text()).toContain('Received & Verified')
  })

  it('opens receive modal and completes receiving with transit damage discrepancy', async () => {
    api.post.mockResolvedValueOnce({
      data: {
        ...sampleTransfer,
        status: 'Partially Received',
        total_received_qty: 95,
        total_lost_qty: 5,
        lines: [
          {
            ...sampleTransfer.lines[0],
            qty_received: 55,
            qty_lost: 5,
            loss_reason: 'Transit Damage',
            loss_notes: '5 cartons damaged due to rough transit',
          },
          {
            ...sampleTransfer.lines[1],
            qty_received: 40,
            qty_lost: 0,
          },
        ],
      },
    })

    const w = createWrapper()
    await flushPromises()

    // Click Receive Transfer button
    const recBtn = w.findAll('button').find(b => b.text().includes('Receive Transfer'))
    expect(recBtn).toBeDefined()
    await recBtn.trigger('click')
    await flushPromises()

    // Verify modal is open
    expect(w.text()).toContain('Receive Stock Transfer')

    // Adjust line 1 received qty from 60 to 55
    const recInputs = w.findAll('.rec-qty-input')
    expect(recInputs.length).toBe(2)
    await recInputs[0].setValue(55)
    await recInputs[0].trigger('input')
    await flushPromises()

    // Select loss reason
    const lossReasonSelects = w.findAll('.receive-table select')
    expect(lossReasonSelects.length).toBe(2)
    await lossReasonSelects[0].setValue('Transit Damage')
    await flushPromises()

    // Submit receive form
    const recForm = w.find('form.modal-body')
    await recForm.trigger('submit.prevent')
    await flushPromises()

    expect(api.post).toHaveBeenCalledWith('/T0108I/1/receive', expect.objectContaining({
      lines: expect.arrayContaining([
        expect.objectContaining({
          line_id: 11,
          qty_received: 55,
          qty_lost: 5,
          loss_reason: 'Transit Damage',
        }),
      ]),
      losses: expect.arrayContaining([
        expect.objectContaining({
          line_id: 11,
          qty_lost: 5,
          loss_reason: 'Transit Damage',
        }),
      ]),
    }))
  })

  it('handles "Receive All in Full" action', async () => {
    const w = createWrapper()
    await flushPromises()

    const recBtn = w.findAll('button').find(b => b.text().includes('Receive Transfer'))
    await recBtn.trigger('click')
    await flushPromises()

    // First change to non-full
    let recInputs = w.findAll('.rec-qty-input')
    await recInputs[0].setValue(30)
    await recInputs[0].trigger('input')
    await flushPromises()

    // Click "Receive All in Full"
    const fullBtn = w.findAll('button').find(b => b.text().includes('Receive All in Full'))
    expect(fullBtn).toBeDefined()
    await fullBtn.trigger('click')
    await flushPromises()

    // Verify inputs reset to full dispatched qty
    recInputs = w.findAll('.rec-qty-input')
    expect(recInputs[0].element.value).toBe('60')
    expect(recInputs[1].element.value).toBe('40')
  })

  it('handles rapid barcode scanning in receive modal', async () => {
    const w = createWrapper()
    await flushPromises()

    const recBtn = w.findAll('button').find(b => b.text().includes('Receive Transfer'))
    await recBtn.trigger('click')
    await flushPromises()

    // Reset quantities to 0 for scan-to-count
    const resetBtn = w.findAll('button').find(b => b.text().includes('Reset for Scan-to-Count'))
    expect(resetBtn).toBeDefined()
    await resetBtn.trigger('click')
    await flushPromises()

    let recInputs = w.findAll('.rec-qty-input')
    expect(recInputs[0].element.value).toBe('0')

    // Scan SKU-DAIRY-01
    const barcodeInput = w.find('.barcode-input')
    expect(barcodeInput.exists()).toBe(true)
    await barcodeInput.setValue('SKU-DAIRY-01')
    await barcodeInput.trigger('keydown.enter')
    await flushPromises()

    // Verify quantity incremented to 1 and scan feedback shown
    recInputs = w.findAll('.rec-qty-input')
    expect(recInputs[0].element.value).toBe('1')
    expect(w.find('.scan-feedback.success').exists()).toBe(true)
    expect(w.text()).toContain('Fresh Milk 1L')

    // Scan invalid barcode
    await barcodeInput.setValue('INVALID-BARCODE-999')
    await barcodeInput.trigger('keydown.enter')
    await flushPromises()

    expect(w.find('.scan-feedback.error').exists()).toBe(true)
    expect(w.text()).toContain("No matching product, barcode, or lot number found for 'INVALID-BARCODE-999'")
  })

  it('handles "Reset for Scan-to-Count" action in receive modal', async () => {
    const w = createWrapper()
    await flushPromises()

    const recBtn = w.findAll('button').find(b => b.text().includes('Receive Transfer'))
    await recBtn.trigger('click')
    await flushPromises()

    const resetBtn = w.findAll('button').find(b => b.text().includes('Reset for Scan-to-Count'))
    await resetBtn.trigger('click')
    await flushPromises()

    const recInputs = w.findAll('.rec-qty-input')
    expect(recInputs[0].element.value).toBe('0')
    expect(recInputs[1].element.value).toBe('0')

    const lostInputs = w.findAll('.lost-qty-input')
    expect(lostInputs[0].element.value).toBe('60')
    expect(lostInputs[1].element.value).toBe('40')
  })

  it('opens cancel modal and submits cancellation', async () => {
    api.post.mockResolvedValueOnce({
      data: {
        ...sampleTransfer,
        status: 'Cancelled',
      },
    })

    const w = createWrapper()
    await flushPromises()

    // Click header cancel button
    const cancelBtn = w.find('.header-actions .btn-danger-outline')
    expect(cancelBtn.exists()).toBe(true)
    await cancelBtn.trigger('click')
    await flushPromises()

    // Cancellation modal opened
    expect(w.text()).toContain('Cancel Stock Transfer')

    // Submit cancellation via modal confirm button
    const confirmCancelBtn = w.find('.modal-dialog .btn-danger')
    expect(confirmCancelBtn.exists()).toBe(true)
    await confirmCancelBtn.trigger('click')
    await flushPromises()

    expect(api.post).toHaveBeenCalledWith('/T0108I/1/cancel', expect.objectContaining({
      reason: expect.any(String),
    }))
  })

  it('opens dispatch modal when transfer is in Draft status and submits dispatch', async () => {
    api.get.mockImplementation((url) => {
      if (url === '/T0108I/1/detail') return Promise.resolve({
        data: {
          ...sampleTransfer,
          status: 'Draft',
          dispatched_at: null,
          dispatched_by: null,
          total_dispatched_qty: 0,
        }
      })
      if (url === '/T0008I/') return Promise.resolve({ data: sampleWarehouses })
      if (url === '/T0003I/') return Promise.resolve({ data: sampleProducts })
      return Promise.resolve({ data: [] })
    })

    api.post.mockResolvedValueOnce({
      data: {
        ...sampleTransfer,
        status: 'In Transit',
        dispatched_at: '2026-08-26T12:00:00Z',
      }
    })

    const w = createWrapper()
    await flushPromises()

    const dispatchBtn = w.findAll('button').find(b => b.text().includes('Dispatch Transfer'))
    expect(dispatchBtn).toBeDefined()
    await dispatchBtn.trigger('click')
    await flushPromises()

    expect(w.text()).toContain('Dispatch Stock Transfer')

    const form = w.find('form.modal-body')
    await form.trigger('submit.prevent')
    await flushPromises()

    expect(api.post).toHaveBeenCalledWith('/T0108I/1/dispatch', expect.objectContaining({
      carrier: expect.any(String),
      lines: expect.arrayContaining([
        expect.objectContaining({
          line_id: 11,
          qty_dispatched: 60,
        }),
      ]),
    }))
  })

  it('renders transit loss discrepancy banner when total_lost_qty > 0', async () => {
    api.get.mockImplementation((url) => {
      if (url === '/T0108I/1/detail') return Promise.resolve({
        data: {
          ...sampleTransfer,
          status: 'Received',
          total_received_qty: 95,
          total_lost_qty: 5,
          lines: [
            {
              ...sampleTransfer.lines[0],
              qty_received: 55,
              qty_lost: 5,
              loss_reason: 'Transit Damage',
              loss_notes: 'Broken seal during transit',
            },
          ],
        }
      })
      return Promise.resolve({ data: [] })
    })

    const w = createWrapper()
    await flushPromises()

    expect(w.find('.discrepancy-banner').exists()).toBe(true)
    expect(w.text()).toContain('Transit Discrepancies / Losses Detected')
    expect(w.text()).toContain('5 units lost/damaged')
    expect(w.text()).toContain('Transit Damage')
  })

  it('renders cancelled banner when status is Cancelled', async () => {
    api.get.mockImplementation((url) => {
      if (url === '/T0108I/1/detail') return Promise.resolve({
        data: {
          ...sampleTransfer,
          status: 'Cancelled',
          notes: 'Customer duplicate order cancelled',
        }
      })
      return Promise.resolve({ data: [] })
    })

    const w = createWrapper()
    await flushPromises()

    expect(w.find('.cancelled-banner').exists()).toBe(true)
    expect(w.text()).toContain('Stock Transfer Cancelled')
    expect(w.text()).toContain('Customer duplicate order cancelled')
  })

  it('allows adding and removing line items on Draft transfers', async () => {
    api.get.mockImplementation((url) => {
      if (url === '/T0108I/1/detail') return Promise.resolve({
        data: {
          ...sampleTransfer,
          status: 'Draft',
        }
      })
      if (url === '/T0008I/') return Promise.resolve({ data: sampleWarehouses })
      if (url === '/T0003I/') return Promise.resolve({ data: sampleProducts })
      return Promise.resolve({ data: [] })
    })

    api.post.mockResolvedValueOnce({ data: { id: 13, transfer_id: 1, product_id: 101, qty_requested: 25 } })
    api.delete.mockResolvedValueOnce({ data: {} })

    const w = createWrapper()
    await flushPromises()

    // Add item button in header
    const addBtn = w.find('.header-actions button')
    expect(addBtn.text()).toContain('Add Item')
    await addBtn.trigger('click')
    await flushPromises()

    expect(w.text()).toContain('Add Transfer Line Item')

    // Submit line form
    const lineForm = w.find('.modal-dialog form')
    await lineForm.trigger('submit.prevent')
    await flushPromises()

    expect(api.post).toHaveBeenCalledWith('/T0108I/1/lines', expect.objectContaining({
      transfer_id: 1,
      qty_requested: expect.any(Number),
    }))

    // Click delete line item button
    const deleteBtn = w.find('.actions-group-cell .btn-icon-danger')
    expect(deleteBtn.exists()).toBe(true)
    await deleteBtn.trigger('click')
    await flushPromises()

    expect(w.text()).toContain('Remove Item')

    const confirmDeleteBtn = w.find('.modal-dialog .btn-danger')
    await confirmDeleteBtn.trigger('click')
    await flushPromises()

    expect(api.delete).toHaveBeenCalledWith('/T0108I/1/lines/11')
  })
})
