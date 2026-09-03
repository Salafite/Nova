import { mount, flushPromises } from '@vue/test-utils'
import { vi, describe, it, expect, beforeEach, afterEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import PickListDetailView from '../views/warehouse/PickListDetailView.vue'
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

// Mock useToast
const mockToast = vi.fn()
vi.mock('../composables/useToast.js', () => ({
  useToast: () => ({ show: mockToast }),
}))

describe('PickListDetailView (Catch-Weight & Dual UOM)', () => {
  let pinia
  let wrapper

  const samplePickListDetail = {
    id: 1,
    pick_list_number: 'PL-2026-0001',
    sales_order_id: 101,
    warehouse_id: 1,
    status: 'In Progress',
    notes: null,
    progress_pct: 50,
    has_discrepancies: false,
    discrepancy_count: 0,
    items: [
      {
        id: 11,
        pick_list_id: 1,
        sales_order_line_id: 201,
        product_id: 501,
        product_name: 'Cheddar Cheese Block (Nominal 20kg)',
        qty_ordered: 2,
        qty_picked: 0,
        line_number: 1,
        batch_id: 301,
        batch_number: 'BATCH-CW-001',
        expiry_date: '2026-12-31',
        picked_batch_id: null,
        picked_batch_number: null,
        catch_weight_actual: null,
        catch_weight_uom: 'kg',
        nominal_weight: 40.0,
        tolerance_pct: 10.0,
        tolerance_variance_pct: null,
        tolerance_status: 'Not Applicable',
        supervisor_approved: false,
        supervisor_approved_by: null,
        supervisor_approved_at: null,
        supervisor_notes: null,
        is_catch_weight: true,
      },
      {
        id: 12,
        pick_list_id: 1,
        sales_order_line_id: 202,
        product_id: 502,
        product_name: 'Standard Canned Olive Oil',
        qty_ordered: 5,
        qty_picked: 5,
        line_number: 2,
        batch_id: 302,
        batch_number: 'BATCH-STD-002',
        expiry_date: '2027-06-30',
        picked_batch_id: 302,
        picked_batch_number: 'BATCH-STD-002',
        catch_weight_actual: null,
        catch_weight_uom: null,
        nominal_weight: null,
        tolerance_pct: null,
        tolerance_variance_pct: null,
        tolerance_status: 'Not Applicable',
        supervisor_approved: false,
        supervisor_approved_by: null,
        supervisor_approved_at: null,
        supervisor_notes: null,
        is_catch_weight: false,
      }
    ]
  }

  const sampleWarehouses = [
    { id: 1, name: 'Main Distribution Center', is_active: true }
  ]

  beforeEach(() => {
    pinia = createPinia()
    setActivePinia(pinia)
    vi.clearAllMocks()

    api.get.mockImplementation((url) => {
      if (url.includes('/T0101I/1/detail')) {
        return Promise.resolve({ data: JSON.parse(JSON.stringify(samplePickListDetail)) })
      }
      if (url.includes('/T0008I/')) {
        return Promise.resolve({ data: sampleWarehouses })
      }
      if (url.includes('/available-batches')) {
        return Promise.resolve({ data: [] })
      }
      return Promise.resolve({ data: [] })
    })
  })

  afterEach(() => {
    if (wrapper) {
      wrapper.unmount()
      wrapper = null
    }
    document.body.innerHTML = ''
  })

  function createWrapper() {
    wrapper = mount(PickListDetailView, {
      attachTo: document.body,
      global: {
        plugins: [pinia]
      }
    })
    return wrapper
  }

  it('renders pick list header with Dual UOM badge and summary stats', async () => {
    const w = createWrapper()
    await flushPromises()

    expect(w.text()).toContain('PL-2026-0001')
    expect(w.text()).toContain('FEFO Picking')
    expect(w.text()).toContain('Dual UOM / Catch-Weight')
    expect(w.text()).toContain('Main Distribution Center')
  })

  it('renders catch weight item with Catch Weight badge, nominal weight and tolerance', async () => {
    const w = createWrapper()
    await flushPromises()

    expect(w.text()).toContain('Cheddar Cheese Block')
    expect(w.text()).toContain('Catch Weight')
    expect(w.text()).toContain('Nominal: 40.00 kg')
    expect(w.text()).toContain('Tol: ±10%')
    expect(w.text()).toContain('Standard (Fixed)')
  })

  it('shows live within-tolerance calculation when valid scale weight is entered', async () => {
    const w = createWrapper()
    await flushPromises()

    // Find scale weight input for catch-weight line (id: 11)
    const scaleInputs = w.findAll('.scale-input')
    expect(scaleInputs.length).toBeGreaterThan(0)

    // Set scale weight to 42.0 kg (+5% on 40kg nominal, within ±10%)
    await scaleInputs[0].setValue(42.0)

    expect(w.text()).toContain('+5.00%')
    expect(w.text()).toContain('Within Tol.')
    expect(w.find('.badge-tolerance-within').exists()).toBe(true)
    expect(w.find('.discrepancy-banner').exists()).toBe(false)
  })

  it('shows live out-of-tolerance warning and banner when scale weight exceeds tolerance', async () => {
    const w = createWrapper()
    await flushPromises()

    const scaleInputs = w.findAll('.scale-input')
    // Set scale weight to 46.0 kg (+15% on 40kg nominal, exceeds ±10%)
    await scaleInputs[0].setValue(46.0)

    expect(w.text()).toContain('+15.00%')
    expect(w.text()).toContain('Out of Tol.')
    expect(w.find('.badge-tolerance-out').exists()).toBe(true)
    expect(w.find('.discrepancy-banner').exists()).toBe(true)
    expect(w.text()).toContain('Catch-Weight Tolerance Discrepancy Detected')
  })

  it('submits scale weight and catch weight parameters on savePick', async () => {
    api.post.mockResolvedValue({
      data: {
        id: 11,
        qty_picked: 2,
        picked_batch_id: 301,
        picked_batch_number: 'BATCH-CW-001',
        catch_weight_actual: 41.5,
        catch_weight_uom: 'kg',
        nominal_weight: 40.0,
        tolerance_pct: 10.0,
        tolerance_variance_pct: 3.75,
        tolerance_status: 'Within Tolerance',
        supervisor_approved: false,
      }
    })

    const w = createWrapper()
    await flushPromises()

    const pickInputs = w.findAll('.pick-input')
    await pickInputs[0].setValue(2)

    const scaleInputs = w.findAll('.scale-input')
    await scaleInputs[0].setValue(41.5)

    const pickBtns = w.findAll('.btn-pick')
    await pickBtns[0].trigger('click')
    await flushPromises()

    expect(api.post).toHaveBeenCalledWith(
      '/T0101I/1/pick-item/11',
      expect.objectContaining({
        qty_picked: 2,
        catch_weight_actual: 41.5,
        catch_weight_uom: 'kg',
        nominal_weight: 40.0,
        tolerance_pct: 10.0,
      })
    )
    expect(mockToast).toHaveBeenCalledWith(expect.stringContaining('Line #1 pick recorded'), 'success')
  })

  it('opens supervisor approval modal and posts tolerance approval', async () => {
    api.post.mockResolvedValue({ data: { success: true } })

    const w = createWrapper()
    await flushPromises()

    // Trigger out of tolerance scale weight
    const scaleInputs = w.findAll('.scale-input')
    await scaleInputs[0].setValue(48.0) // +20% variance

    // Click Approve button in discrepancy banner
    const approveBtn = w.find('.discrepancy-banner button')
    expect(approveBtn.exists()).toBe(true)
    await approveBtn.trigger('click')
    await flushPromises()

    // Teleported modal check in document.body
    const modal = document.body.querySelector('.modal-overlay')
    expect(modal).toBeTruthy()
    expect(document.body.textContent).toContain('Supervisor Tolerance Approval')
    expect(document.body.textContent).toContain('+20.00%')

    // Fill supervisor ID and notes
    const supervisorInput = document.body.querySelector('input[placeholder="Enter supervisor username or employee ID"]')
    supervisorInput.value = 'SUP-99'
    supervisorInput.dispatchEvent(new Event('input'))

    const notesTextarea = document.body.querySelector('textarea')
    notesTextarea.value = 'Approved customer 48kg special pack'
    notesTextarea.dispatchEvent(new Event('input'))

    // Submit approval
    const confirmApproveBtn = document.body.querySelector('.modal-footer .btn-warning')
    confirmApproveBtn.click()
    await flushPromises()

    expect(api.post).toHaveBeenCalledWith(
      '/T0101I/1/approve-tolerance',
      expect.objectContaining({
        supervisor_id: 'SUP-99',
        supervisor_notes: 'Approved customer 48kg special pack',
      })
    )
    expect(mockToast).toHaveBeenCalledWith(expect.stringContaining('approved successfully'), 'success')
  })

  it('displays FEFO suggested lots and expiration dates in items table', async () => {
    const w = createWrapper()
    await flushPromises()

    expect(w.text()).toContain('BATCH-CW-001')
    expect(w.text()).toContain('BATCH-STD-002')
    expect(w.text()).toContain('Suggested Lot (FEFO)')
  })

  it('supports picker lot selection override from available batches and manual lot scan', async () => {
    api.get.mockImplementation((url) => {
      if (url.includes('/T0101I/1/detail')) {
        return Promise.resolve({ data: JSON.parse(JSON.stringify(samplePickListDetail)) })
      }
      if (url.includes('/T0008I/')) {
        return Promise.resolve({ data: sampleWarehouses })
      }
      if (url.includes('/available-batches')) {
        return Promise.resolve({
          data: [
            { id: 301, batch_number: 'BATCH-CW-001', expiry_date: '2026-12-31', quantity: 100 },
            { id: 309, batch_number: 'BATCH-ALT-999', expiry_date: '2026-10-15', quantity: 50 }
          ]
        })
      }
      return Promise.resolve({ data: [] })
    })

    const w = createWrapper()
    await flushPromises()

    // Test dropdown lot selection
    const lotSelects = w.findAll('.lot-select')
    expect(lotSelects.length).toBeGreaterThan(0)
    await lotSelects[0].setValue('309')
    await flushPromises()

    expect(w.text()).toContain('Picked Lot: BATCH-ALT-999')
    expect(w.text()).toContain('OVERRIDE')

    // Test manual lot scan override input
    const batchInput = w.find('.batch-input')
    await batchInput.setValue('BATCH-SCAN-777')
    const applyBtn = w.find('.lot-controls .btn-icon')
    await applyBtn.trigger('click')
    await flushPromises()

    expect(w.text()).toContain('Picked Lot: BATCH-SCAN-777')
  })

  it('supports global barcode scanning to match lot and pick item', async () => {
    api.get.mockImplementation((url) => {
      if (url.includes('/T0101I/1/detail')) {
        return Promise.resolve({ data: JSON.parse(JSON.stringify(samplePickListDetail)) })
      }
      if (url.includes('/T0008I/')) {
        return Promise.resolve({ data: sampleWarehouses })
      }
      if (url.includes('/available-batches')) {
        return Promise.resolve({
          data: [
            { id: 301, batch_number: 'BATCH-CW-001', expiry_date: '2026-12-31', quantity: 100 }
          ]
        })
      }
      return Promise.resolve({ data: [] })
    })

    api.post.mockResolvedValue({
      data: {
        id: 11,
        qty_picked: 2,
        picked_batch_id: 301,
        picked_batch_number: 'BATCH-CW-001',
        tolerance_status: 'Not Applicable'
      }
    })

    const w = createWrapper()
    await flushPromises()

    const scannerInput = w.find('.scanner-input')
    await scannerInput.setValue('BATCH-CW-001')
    await scannerInput.trigger('keyup.enter')
    await flushPromises()

    expect(api.post).toHaveBeenCalledWith(
      '/T0101I/1/pick-item/11',
      expect.objectContaining({
        qty_picked: 2,
        picked_batch_id: 301,
        picked_batch_number: 'BATCH-CW-001'
      })
    )
    expect(mockToast).toHaveBeenCalledWith(expect.stringContaining('Scanned code matched'), 'success')
  })
})

