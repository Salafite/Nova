import { mount, flushPromises } from '@vue/test-utils'
import { vi, describe, it, expect, beforeEach, afterEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import PickListDetailView from '../views/warehouse/PickListDetailView.vue'
import { useScanFeedback } from '../composables/useScanFeedback.js'
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
    useScanFeedback().flashState.value = null

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

  it('performs real-time barcode lookup and increments item pick quantity on valid scan with success feedback', async () => {
    api.post.mockResolvedValue({
      data: {
        id: 11,
        qty_picked: 1,
        picked_batch_id: 301,
        picked_batch_number: 'BATCH-CW-001',
        catch_weight_actual: 40.0,
      }
    })

    const w = createWrapper()
    await flushPromises()

    const scanInput = w.find('.scanner-input')
    expect(scanInput.exists()).toBe(true)

    // Type valid product ID / barcode '501' (Cheddar Cheese Block)
    await scanInput.setValue('501')
    await scanInput.trigger('keyup.enter')
    await flushPromises()

    expect(api.post).toHaveBeenCalledWith(
      '/T0101I/1/pick-item/11',
      expect.objectContaining({
        qty_picked: 1,
      })
    )
    expect(mockToast).toHaveBeenCalledWith(expect.stringContaining('Scanned 501 - picked line #1'), 'success')
  })

  it('triggers warning feedback when scanning an item that is already fully picked', async () => {
    const w = createWrapper()
    await flushPromises()

    // Item 502 (line 2) is already fully picked (qty_picked: 5, qty_ordered: 5)
    const scanInput = w.find('.scanner-input')
    await scanInput.setValue('502')
    await scanInput.trigger('keyup.enter')
    await flushPromises()

    expect(mockToast).toHaveBeenCalledWith(expect.stringContaining('is already fully picked'), 'warning')
  })

  it('rejects mismatched barcode scan with error feedback, opens warning modal, and prevents staging', async () => {
    const w = createWrapper()
    await flushPromises()

    const scanInput = w.find('.scanner-input')
    expect(scanInput.exists()).toBe(true)

    // Scan an unallocated/unknown barcode
    await scanInput.setValue('UNKNOWN-BARCODE-999')
    await scanInput.trigger('keyup.enter')
    await flushPromises()

    // 1. Error toast / feedback triggered
    expect(mockToast).toHaveBeenCalledWith(
      expect.stringContaining('Barcode scan mismatch: "UNKNOWN-BARCODE-999" is not in this pick list!'),
      'error'
    )

    // 2. Mismatch warning modal teleported to document.body
    const modal = document.body.querySelector('.modal-overlay')
    expect(modal).toBeTruthy()
    expect(document.body.textContent).toContain('Barcode Scan Mismatch Warning')
    expect(document.body.textContent).toContain('Unrecognized or Mismatched Item')
    expect(document.body.textContent).toContain('UNKNOWN-BARCODE-999')
    expect(document.body.textContent).toContain('Item staging prevented to avoid wrong item shipment.')

    // 3. Click Acknowledge & Dismiss button
    const dismissBtn = document.body.querySelector('.btn-danger-action')
    expect(dismissBtn).toBeTruthy()
    dismissBtn.click()
    await flushPromises()

    // Modal dismissed
    expect(document.body.querySelector('.modal-dialog-warning')).toBeNull()

    // 4. Verify no item pick API post call was made
    expect(api.post).not.toHaveBeenCalledWith(
      expect.stringContaining('/pick-item/'),
      expect.anything()
    )
  })

  it('validates GS1-128 barcode with valid GTIN, allocated FEFO batch, and unexpired date', async () => {
    api.post.mockResolvedValue({
      data: {
        id: 11,
        qty_picked: 1,
        picked_batch_id: 301,
        picked_batch_number: 'BATCH-CW-001',
        catch_weight_actual: 40.0,
      }
    })

    const w = createWrapper()
    await flushPromises()

    const scanInput = w.find('.scanner-input')
    // GS1-128 formatted barcode: product ID 501, allocated batch BATCH-CW-001, expiry 2026-12-31
    await scanInput.setValue('(01)501(10)BATCH-CW-001(17)261231')
    await scanInput.trigger('keyup.enter')
    await flushPromises()

    expect(api.post).toHaveBeenCalledWith(
      '/T0101I/1/pick-item/11',
      expect.objectContaining({
        qty_picked: 1,
        picked_batch_id: 301,
        picked_batch_number: 'BATCH-CW-001'
      })
    )
    expect(mockToast).toHaveBeenCalledWith(expect.stringContaining('picked line #1'), 'success')
  })

  it('rejects GS1-128 barcode scan with EXPIRED expiration date and prevents picking', async () => {
    const w = createWrapper()
    await flushPromises()

    const scanInput = w.find('.scanner-input')
    // GS1-128 formatted barcode with expired date AI(17)200101 (2020-01-01)
    await scanInput.setValue('(01)501(10)BATCH-CW-001(17)200101')
    await scanInput.trigger('keyup.enter')
    await flushPromises()

    // Error feedback toast
    expect(mockToast).toHaveBeenCalledWith(
      expect.stringContaining('Scanned batch is EXPIRED (2020-01-01)! Cannot pick expired items.'),
      'error'
    )

    // Warning modal displayed
    const modal = document.body.querySelector('.modal-overlay')
    expect(modal).toBeTruthy()
    expect(document.body.textContent).toContain('Expired: 2020-01-01')

    // No pick API call made
    expect(api.post).not.toHaveBeenCalledWith(
      expect.stringContaining('/pick-item/'),
      expect.anything()
    )
  })

  it('rejects GS1-128 barcode scan with unallocated batch number not in stock for item', async () => {
    const w = createWrapper()
    await flushPromises()

    const scanInput = w.find('.scanner-input')
    // GS1-128 barcode with unallocated batch number UNALLOCATED-LOT-999
    await scanInput.setValue('(01)501(10)UNALLOCATED-LOT-999(17)261231')
    await scanInput.trigger('keyup.enter')
    await flushPromises()

    // Error feedback toast
    expect(mockToast).toHaveBeenCalledWith(
      expect.stringContaining('Scanned lot "UNALLOCATED-LOT-999" is not allocated or available in warehouse stock for Cheddar Cheese Block (Nominal 20kg)!'),
      'error'
    )

    // Warning modal displayed
    const modal = document.body.querySelector('.modal-overlay')
    expect(modal).toBeTruthy()
    expect(document.body.textContent).toContain('Unallocated Lot: UNALLOCATED-LOT-999')

    // No pick API call made
    expect(api.post).not.toHaveBeenCalledWith(
      expect.stringContaining('/pick-item/'),
      expect.anything()
    )
  })

  it('supports alternative available batch selection with FEFO warning notice on GS1 scan', async () => {
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
            { id: 305, batch_number: 'BATCH-ALT-005', expiry_date: '2027-01-01', quantity: 50 }
          ]
        })
      }
      return Promise.resolve({ data: [] })
    })

    api.post.mockResolvedValue({
      data: {
        id: 11,
        qty_picked: 1,
        picked_batch_id: 305,
        picked_batch_number: 'BATCH-ALT-005',
        catch_weight_actual: 40.0,
      }
    })

    const w = createWrapper()
    await flushPromises()

    const scanInput = w.find('.scanner-input')
    // Scan alternative batch BATCH-ALT-005
    await scanInput.setValue('(01)501(10)BATCH-ALT-005(17)270101')
    await scanInput.trigger('keyup.enter')
    await flushPromises()

    // Warning notice for FEFO override
    expect(mockToast).toHaveBeenCalledWith(
      expect.stringContaining('FEFO Warning: Scanned lot "BATCH-ALT-005" overrides allocated lot "BATCH-CW-001".'),
      'warning'
    )

    // Pick API call includes alternative batch id 305 and batch number BATCH-ALT-005
    expect(api.post).toHaveBeenCalledWith(
      '/T0101I/1/pick-item/11',
      expect.objectContaining({
        qty_picked: 1,
        picked_batch_id: 305,
        picked_batch_number: 'BATCH-ALT-005'
      })
    )
  })

  it('toggles audio mute button and updates scan sound state', async () => {
    const w = createWrapper()
    await flushPromises()

    const muteBtn = w.find('button[title*="audio"]')
    expect(muteBtn.exists()).toBe(true)
    expect(muteBtn.find('.material-symbols-outlined').text()).toBe('volume_up')

    // Click mute button
    await muteBtn.trigger('click')
    await flushPromises()

    // Icon updates to volume_off
    expect(muteBtn.find('.material-symbols-outlined').text()).toBe('volume_off')
  })

  it('opens camera scanner modal and processes scanned barcode from camera modal', async () => {
    api.post.mockResolvedValue({
      data: {
        id: 11,
        qty_picked: 1,
        picked_batch_id: 301,
        picked_batch_number: 'BATCH-CW-001',
      }
    })

    const w = createWrapper()
    await flushPromises()

    // Click camera scan button
    const cameraBtn = w.find('.btn-camera-trigger')
    expect(cameraBtn.exists()).toBe(true)
    await cameraBtn.trigger('click')
    await flushPromises()

    // CameraBarcodeScannerModal component exists
    const modalComp = w.findComponent({ name: 'CameraBarcodeScannerModal' })
    expect(modalComp.exists()).toBe(true)
    expect(modalComp.props('modelValue')).toBe(true)

    // Emit scan event from camera modal
    await modalComp.vm.$emit('scan', null, '501')
    await flushPromises()

    expect(api.post).toHaveBeenCalledWith(
      '/T0101I/1/pick-item/11',
      expect.objectContaining({
        qty_picked: 1
      })
    )
  })

  it('handles hardware USB/Bluetooth barcode scanner rapid keydown buffer and triggers pick', async () => {
    api.post.mockResolvedValue({
      data: {
        id: 11,
        qty_picked: 1,
        picked_batch_id: 301,
        picked_batch_number: 'BATCH-CW-001',
      }
    })

    const w = createWrapper()
    await flushPromises()

    // Simulate rapid hardware scanner key strokes: '5', '0', '1', 'Enter'
    const now = Date.now()
    window.dispatchEvent(new KeyboardEvent('keydown', { key: '5', timeStamp: now }))
    window.dispatchEvent(new KeyboardEvent('keydown', { key: '0', timeStamp: now + 5 }))
    window.dispatchEvent(new KeyboardEvent('keydown', { key: '1', timeStamp: now + 10 }))
    window.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter', timeStamp: now + 15 }))
    await flushPromises()

    expect(api.post).toHaveBeenCalledWith(
      '/T0101I/1/pick-item/11',
      expect.objectContaining({
        qty_picked: 1
      })
    )
  })

  it('applies flash-success state on valid scan and flash-error on mismatch scan', async () => {
    api.post.mockResolvedValue({
      data: {
        id: 11,
        qty_picked: 1,
      }
    })

    const w = createWrapper()
    await flushPromises()

    const scanCard = w.find('.scanner-card')
    expect(scanCard.classes()).not.toContain('flash-success')
    expect(scanCard.classes()).not.toContain('flash-error')

    // Set initial pickQty to 0 so scan increments to 1 instead of hitting fully picked warning
    const pickInputs = w.findAll('.pick-input')
    await pickInputs[0].setValue(0)

    // 1. Scan valid barcode '501'
    const scanInput = w.find('.scanner-input')
    await scanInput.setValue('501')
    await scanInput.trigger('keyup.enter')
    await flushPromises()
    await w.vm.$nextTick()

    expect(scanCard.classes()).toContain('flash-success')

    // 2. Scan mismatched barcode
    await scanInput.setValue('WRONG-BARCODE-000')
    await scanInput.trigger('keyup.enter')
    await flushPromises()
    await w.vm.$nextTick()

    expect(scanCard.classes()).toContain('flash-error')
  })
})



