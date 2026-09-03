import { mount, flushPromises } from '@vue/test-utils'
import { vi, describe, it, expect, beforeEach, afterEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import GoodsReceiptView from '../views/purchasing/GoodsReceiptView.vue'
import { api } from '../api/client.js'

// Mock api
vi.mock('../api/client.js', () => ({
  api: {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    delete: vi.fn(),
    interceptors: { request: { use: vi.fn() }, response: { use: vi.fn() } }
  },
  CONFIG: { apiBase: 'http://test.local' }
}))

// Mock useToast
const mockToast = vi.fn()
vi.mock('../composables/useToast.js', () => ({
  useToast: () => ({ show: mockToast })
}))

describe('GoodsReceiptView - Barcode Matching & Receiving Quantity Increment (Subtask 3-2)', () => {
  let pinia
  let wrapper

  const sampleProducts = [
    { id: 101, name: 'Wireless Barcode Scanner', sku: 'SKU-SCAN-01', barcode: '0123456789012', gtin: '00123456789012' },
    { id: 102, name: 'Thermal Label Printer', sku: 'SKU-PRN-02', barcode: '9876543210987', gtin: '009876543210987' },
    { id: 103, name: 'Rugged Warehouse Handheld', sku: 'SKU-HND-03', barcode: '5554443332221', gtin: '005554443332221' }
  ]

  const sampleSuppliers = [
    { id: 1, name: 'Apex Tech Solutions', company_name: 'Apex Tech' }
  ]

  const sampleWarehouses = [
    { id: 1, name: 'Central Logistics Center' }
  ]

  const sampleReceipts = [
    {
      id: 1,
      receipt_number: 'GRN-2026-001',
      purchase_order_id: 501,
      supplier_id: 1,
      warehouse_id: 1,
      receipt_date: '2026-09-02',
      status: 'Draft',
      notes: 'Initial test draft receipt'
    }
  ]

  const sampleReceiptLines = [
    {
      id: 1,
      receipt_id: 1,
      product_id: 101,
      product_name: 'Wireless Barcode Scanner',
      qty_ordered: 10,
      qty_received: 2,
      batch_number: 'LOT-2026-01',
      line_number: 1
    }
  ]

  beforeEach(() => {
    pinia = createPinia()
    setActivePinia(pinia)
    vi.clearAllMocks()

    api.get.mockImplementation((url) => {
      if (url.includes('/T0075I/')) {
        return Promise.resolve({ data: JSON.parse(JSON.stringify(sampleReceipts)) })
      }
      if (url.includes('/T0103I/') || url.includes('/T0011I/')) {
        return Promise.resolve({ data: JSON.parse(JSON.stringify(sampleSuppliers)) })
      }
      if (url.includes('/T0008I/')) {
        return Promise.resolve({ data: JSON.parse(JSON.stringify(sampleWarehouses)) })
      }
      if (url.includes('/T0003I/')) {
        return Promise.resolve({ data: JSON.parse(JSON.stringify(sampleProducts)) })
      }
      if (url.includes('/T0076I/')) {
        return Promise.resolve({ data: JSON.parse(JSON.stringify(sampleReceiptLines)) })
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
    wrapper = mount(GoodsReceiptView, {
      attachTo: document.body,
      global: {
        plugins: [pinia]
      }
    })
    return wrapper
  }

  it('loads and renders goods receipts list and summary stats', async () => {
    const w = createWrapper()
    await flushPromises()

    expect(w.text()).toContain('Goods Receipt')
    expect(w.text()).toContain('GRN-2026-001')
    expect(w.text()).toContain('Apex Tech Solutions')
    expect(w.text()).toContain('Central Logistics Center')
  })

  it('increments receiving quantity when scanning a matching product barcode in open modal', async () => {
    const w = createWrapper()
    await flushPromises()

    // Click edit on the existing receipt
    const editBtn = w.find('button[title="Edit"]')
    await editBtn.trigger('click')
    await flushPromises()

    expect(w.find('.modal-lg').exists()).toBe(true)

    // Scanner input in card
    const scannerInput = w.find('.scanner-input')
    await scannerInput.setValue('0123456789012') // Barcode for Wireless Barcode Scanner (id 101)
    await scannerInput.trigger('keydown.enter')
    await flushPromises()

    // Line 0 (product_id 101) qty_received should increment from 2 to 3
    const qtyInputs = w.findAll('.lines-editor-table input[type="number"]')
    // qty_ordered is first number input (10), qty_received is second (now 3)
    expect(qtyInputs[1].element.value).toBe('3')

    // Toast notification triggered
    expect(mockToast).toHaveBeenCalledWith(
      expect.stringContaining('Received 1x Wireless Barcode Scanner (Total: 3)'),
      'success'
    )
  })

  it('increments receiving quantity on consecutive scans of the same item barcode', async () => {
    const w = createWrapper()
    await flushPromises()

    const editBtn = w.find('button[title="Edit"]')
    await editBtn.trigger('click')
    await flushPromises()

    const scannerInput = w.find('.scanner-input')
    // Scan twice
    await scannerInput.setValue('0123456789012')
    await scannerInput.trigger('keydown.enter')
    await flushPromises()

    await scannerInput.setValue('0123456789012')
    await scannerInput.trigger('keydown.enter')
    await flushPromises()

    const qtyInputs = w.findAll('.lines-editor-table input[type="number"]')
    // 2 initial + 1 + 1 = 4
    expect(qtyInputs[1].element.value).toBe('4')
  })

  it('adds a new line item when scanning a product barcode that is not yet in draft receipt lines', async () => {
    const w = createWrapper()
    await flushPromises()

    const editBtn = w.find('button[title="Edit"]')
    await editBtn.trigger('click')
    await flushPromises()

    // Scan Thermal Label Printer barcode (9876543210987) which is product 102 (not in current lines)
    const scannerInput = w.find('.scanner-input')
    await scannerInput.setValue('9876543210987')
    await scannerInput.trigger('keydown.enter')
    await flushPromises()

    // Lines in editor table should now be 2
    const lineRows = w.findAll('.lines-editor-table tbody tr')
    expect(lineRows.length).toBe(2)

    expect(mockToast).toHaveBeenCalledWith(
      expect.stringContaining('Added Thermal Label Printer to receipt'),
      'success'
    )
  })

  it('opens edit modal and increments line item quantity when scanning barcode while receipt row is expanded', async () => {
    const w = createWrapper()
    await flushPromises()

    // Expand first receipt row
    const expandBtn = w.find('.btn-toggle')
    await expandBtn.trigger('click')
    await flushPromises()

    expect(w.find('.expand-row').exists()).toBe(true)

    // Scan barcode for item in expanded draft receipt
    const scannerInput = w.find('.scanner-input')
    await scannerInput.setValue('0123456789012')
    await scannerInput.trigger('keydown.enter')
    await flushPromises()

    // Modal should be opened automatically and line incremented from 2 to 3
    expect(w.find('.modal-lg').exists()).toBe(true)
    const qtyInputs = w.findAll('.lines-editor-table input[type="number"]')
    expect(qtyInputs[1].element.value).toBe('3')
  })

  it('starts a new draft receipt modal pre-populated with product when scanning barcode from main list view', async () => {
    const w = createWrapper()
    await flushPromises()

    // Main view (no modal open, no row expanded)
    const scannerInput = w.find('.scanner-input')
    await scannerInput.setValue('5554443332221') // Rugged Warehouse Handheld (SKU-HND-03)
    await scannerInput.trigger('keydown.enter')
    await flushPromises()

    // New receipt modal should open
    expect(w.find('.modal-lg').exists()).toBe(true)

    // First line should be Rugged Warehouse Handheld with qty_received 1
    const qtyInputs = w.findAll('.lines-editor-table input[type="number"]')
    expect(qtyInputs[1].element.value).toBe('1')
    expect(mockToast).toHaveBeenCalledWith(
      expect.stringContaining('Started new receipt with Rugged Warehouse Handheld'),
      'success'
    )
  })

  it('matches product by SKU when scanned', async () => {
    const w = createWrapper()
    await flushPromises()

    const editBtn = w.find('button[title="Edit"]')
    await editBtn.trigger('click')
    await flushPromises()

    const scannerInput = w.find('.scanner-input')
    await scannerInput.setValue('SKU-SCAN-01')
    await scannerInput.trigger('keydown.enter')
    await flushPromises()

    const qtyInputs = w.findAll('.lines-editor-table input[type="number"]')
    expect(qtyInputs[1].element.value).toBe('3')
  })

  it('triggers rejection audio-visual feedback and warning modal when an unrecognized barcode is scanned', async () => {
    const w = createWrapper()
    await flushPromises()

    const scannerInput = w.find('.scanner-input')
    await scannerInput.setValue('UNKNOWN-INVALID-BARCODE-999')
    await scannerInput.trigger('keydown.enter')
    await flushPromises()

    // Error toast triggered
    expect(mockToast).toHaveBeenCalledWith(
      expect.stringContaining('Unrecognized goods receipt barcode: UNKNOWN-INVALID-BARCODE-999'),
      'error'
    )

    // Red flash class added to scanner card
    expect(w.find('.scanner-card.flash-error').exists()).toBe(true)

    // Teleported mismatch warning modal rendered in document body
    const mismatchModal = document.body.querySelector('.modal-dialog-warning')
    expect(mismatchModal).not.toBeNull()
    expect(mismatchModal.textContent).toContain('Barcode Scan Mismatch Warning')
    expect(mismatchModal.textContent).toContain('UNKNOWN-INVALID-BARCODE-999')
    expect(mismatchModal.textContent).toContain('Inbound goods receipt entry prevented')
  })

  it('allows picker to acknowledge and dismiss the mismatch warning modal', async () => {
    const w = createWrapper()
    await flushPromises()

    const scannerInput = w.find('.scanner-input')
    await scannerInput.setValue('INVALID-SCAN-777')
    await scannerInput.trigger('keydown.enter')
    await flushPromises()

    let mismatchModal = document.body.querySelector('.modal-dialog-warning')
    expect(mismatchModal).not.toBeNull()

    // Click dismiss button inside teleported modal
    const dismissBtn = document.body.querySelector('.btn-danger-action')
    dismissBtn.click()
    await flushPromises()

    mismatchModal = document.body.querySelector('.modal-dialog-warning')
    expect(mismatchModal).toBeNull()
  })
})


describe('GoodsReceiptView - Audio-Visual Rejection Feedback for Unrecognized Barcodes (Subtask 3-4)', () => {
  let pinia
  let wrapper

  const sampleProducts = [
    { id: 101, name: 'Wireless Barcode Scanner', sku: 'SKU-SCAN-01', barcode: '0123456789012', gtin: '00123456789012' }
  ]

  const sampleReceipts = [
    {
      id: 1,
      receipt_number: 'GRN-2026-001',
      status: 'Draft'
    }
  ]

  beforeEach(() => {
    pinia = createPinia()
    setActivePinia(pinia)
    vi.clearAllMocks()

    api.get.mockImplementation((url) => {
      if (url.includes('/T0075I/')) {
        return Promise.resolve({ data: JSON.parse(JSON.stringify(sampleReceipts)) })
      }
      if (url.includes('/T0003I/')) {
        return Promise.resolve({ data: JSON.parse(JSON.stringify(sampleProducts)) })
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
    wrapper = mount(GoodsReceiptView, {
      attachTo: document.body,
      global: {
        plugins: [pinia]
      }
    })
    return wrapper
  }

  it('triggers error toast, red visual flash, error buzzer sound, and warning modal on scanning unrecognized barcode in main view', async () => {
    const w = createWrapper()
    await flushPromises()

    const scannerInput = w.find('.scanner-input')
    const invalidCode = 'UNKNOWN-BARCODE-999'

    await scannerInput.setValue(invalidCode)
    await scannerInput.trigger('keydown.enter')
    await flushPromises()

    // 1. Error toast notification triggered
    expect(mockToast).toHaveBeenCalledWith(
      expect.stringContaining(`Unrecognized goods receipt barcode: ${invalidCode}`),
      'error'
    )

    // 2. Scanner card gets visual error flash class
    const scannerCard = w.find('.scanner-card')
    expect(scannerCard.classes()).toContain('flash-error')

    // 3. Teleported mismatch modal appears in document body
    const modalTitle = document.body.querySelector('.modal-title')
    expect(modalTitle).not.toBeNull()
    expect(modalTitle.textContent).toContain('Barcode Scan Mismatch Warning')

    const scannedCodeElement = document.body.querySelector('.scanned-code-box code')
    expect(scannedCodeElement).not.toBeNull()
    expect(scannedCodeElement.textContent).toBe(invalidCode)

    // 4. Click acknowledge & dismiss button closes modal
    const dismissBtn = document.body.querySelector('.btn-danger-action')
    expect(dismissBtn).not.toBeNull()
    dismissBtn.click()
    await flushPromises()

    expect(document.body.querySelector('.modal-dialog-warning')).toBeNull()
  })

  it('triggers rejection feedback and mismatch warning modal when scanning unrecognized code inside open receipt modal without modifying lines', async () => {
    const w = createWrapper()
    await flushPromises()

    // Open edit modal
    const editBtn = w.find('button[title="Edit"]')
    await editBtn.trigger('click')
    await flushPromises()

    const initialLineCount = w.findAll('.lines-editor-table tbody tr').length

    // Scan invalid barcode inside open modal
    const scannerInput = w.find('.scanner-input')
    const invalidCode = 'INVALID-LOT-777'

    await scannerInput.setValue(invalidCode)
    await scannerInput.trigger('keydown.enter')
    await flushPromises()

    // Error toast triggered
    expect(mockToast).toHaveBeenCalledWith(
      expect.stringContaining(`Unrecognized goods receipt barcode: ${invalidCode}`),
      'error'
    )

    // Line count should remain unchanged
    const currentLineCount = w.findAll('.lines-editor-table tbody tr').length
    expect(currentLineCount).toBe(initialLineCount)

    // Warning modal displayed in body
    const scannedCodeElement = document.body.querySelector('.scanned-code-box code')
    expect(scannedCodeElement).not.toBeNull()
    expect(scannedCodeElement.textContent).toBe(invalidCode)
  })
})


describe('GoodsReceiptView - GS1-128 Batch & Expiry Auto-Population (Subtask 3-3)', () => {
  let pinia
  let wrapper

  const sampleProducts = [
    { id: 101, name: 'Wireless Barcode Scanner', sku: 'SKU-SCAN-01', barcode: '0123456789012', gtin: '00123456789012' },
    { id: 102, name: 'Thermal Label Printer', sku: 'SKU-PRN-02', barcode: '9876543210987', gtin: '009876543210987' }
  ]

  const sampleSuppliers = [{ id: 1, name: 'Apex Tech Solutions' }]
  const sampleWarehouses = [{ id: 1, name: 'Central Logistics Center' }]
  const sampleReceipts = [{ id: 1, receipt_number: 'GRN-2026-001', supplier_id: 1, warehouse_id: 1, status: 'Draft' }]
  const sampleReceiptLines = [
    { id: 1, receipt_id: 1, product_id: 101, product_name: 'Wireless Barcode Scanner', qty_ordered: 10, qty_received: 2, batch_number: '', manufacturing_date: '', expiry_date: '' }
  ]

  beforeEach(() => {
    pinia = createPinia()
    setActivePinia(pinia)
    vi.clearAllMocks()

    api.get.mockImplementation((url) => {
      if (url.includes('/T0075I/')) return Promise.resolve({ data: JSON.parse(JSON.stringify(sampleReceipts)) })
      if (url.includes('/T0103I/') || url.includes('/T0011I/')) return Promise.resolve({ data: JSON.parse(JSON.stringify(sampleSuppliers)) })
      if (url.includes('/T0008I/')) return Promise.resolve({ data: JSON.parse(JSON.stringify(sampleWarehouses)) })
      if (url.includes('/T0003I/')) return Promise.resolve({ data: JSON.parse(JSON.stringify(sampleProducts)) })
      if (url.includes('/T0076I/')) return Promise.resolve({ data: JSON.parse(JSON.stringify(sampleReceiptLines)) })
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
    wrapper = mount(GoodsReceiptView, {
      attachTo: document.body,
      global: { plugins: [pinia] }
    })
    return wrapper
  }

  it('auto-populates batch number, manufacturing date, and expiry date on existing line when GS1-128 is scanned', async () => {
    const w = createWrapper()
    await flushPromises()

    // Open edit modal
    await w.find('button[title="Edit"]').trigger('click')
    await flushPromises()

    // GS1-128 scan: GTIN (01) 00123456789012, Batch (10) BATCH-GS1-99, Expiry (17) 281231, Mfg (11) 260115
    const gs1Code = '(01)00123456789012(10)BATCH-GS1-99(17)281231(11)260115'
    const scannerInput = w.find('.scanner-input')
    await scannerInput.setValue(gs1Code)
    await scannerInput.trigger('keydown.enter')
    await flushPromises()

    // Check batch_number input
    const batchInput = w.find('.lines-editor-table .batch-input')
    expect(batchInput.element.value).toBe('BATCH-GS1-99')

    // Check date inputs (manufacturing_date & expiry_date)
    const dateInputs = w.findAll('.lines-editor-table input[type="date"]')
    expect(dateInputs[0].element.value).toBe('2026-01-15') // Mfg Date (11) 260115
    expect(dateInputs[1].element.value).toBe('2028-12-31') // Expiry Date (17) 281231

    // Check qty_received incremented from 2 to 3
    const qtyInputs = w.findAll('.lines-editor-table input[type="number"]')
    expect(qtyInputs[1].element.value).toBe('3')
  })

  it('auto-populates batch and expiry dates when adding a new line via GS1-128 barcode scan', async () => {
    const w = createWrapper()
    await flushPromises()

    await w.find('button[title="Edit"]').trigger('click')
    await flushPromises()

    // Scan GS1-128 for Product 102 (Thermal Label Printer GTIN 009876543210987) with Lot BATCH-PRN-01 and Expiry 270630
    const gs1Code = '(01)009876543210987(10)BATCH-PRN-01(17)270630'
    const scannerInput = w.find('.scanner-input')
    await scannerInput.setValue(gs1Code)
    await scannerInput.trigger('keydown.enter')
    await flushPromises()

    // Line 2 should be added
    const lineRows = w.findAll('.lines-editor-table tbody tr')
    expect(lineRows.length).toBe(2)

    const batchInputs = w.findAll('.lines-editor-table .batch-input')
    expect(batchInputs[1].element.value).toBe('BATCH-PRN-01')

    const line2Dates = lineRows[1].findAll('input[type="date"]')
    expect(line2Dates[1].element.value).toBe('2027-06-30')
  })

  it('auto-populates GS1-128 batch and expiry dates on line 0 when starting new receipt from main list view', async () => {
    const w = createWrapper()
    await flushPromises()

    const gs1Code = '(01)009876543210987(10)NEW-RECEIPT-LOT(17)290515'
    const scannerInput = w.find('.scanner-input')
    await scannerInput.setValue(gs1Code)
    await scannerInput.trigger('keydown.enter')
    await flushPromises()

    expect(w.find('.modal-lg').exists()).toBe(true)

    const batchInput = w.find('.lines-editor-table .batch-input')
    expect(batchInput.element.value).toBe('NEW-RECEIPT-LOT')

    const dateInputs = w.findAll('.lines-editor-table input[type="date"]')
    expect(dateInputs[1].element.value).toBe('2029-05-15')
  })
})


describe('GoodsReceiptView - Camera Scanner, Sound Toggle, Manual Scan & Saving Workflow (Subtask 5-4)', () => {
  let pinia
  let wrapper

  const sampleProducts = [
    { id: 101, name: 'Wireless Barcode Scanner', sku: 'SKU-SCAN-01', barcode: '0123456789012', gtin: '00123456789012' }
  ]

  const sampleReceipts = [
    { id: 1, receipt_number: 'GRN-2026-001', supplier_id: 1, warehouse_id: 1, status: 'Draft' }
  ]

  const sampleReceiptLines = [
    { id: 1, receipt_id: 1, product_id: 101, product_name: 'Wireless Barcode Scanner', qty_ordered: 10, qty_received: 2, batch_number: 'LOT-1', manufacturing_date: '', expiry_date: '' }
  ]

  beforeEach(() => {
    pinia = createPinia()
    setActivePinia(pinia)
    vi.clearAllMocks()

    api.get.mockImplementation((url) => {
      if (url.includes('/T0075I/')) return Promise.resolve({ data: JSON.parse(JSON.stringify(sampleReceipts)) })
      if (url.includes('/T0003I/')) return Promise.resolve({ data: JSON.parse(JSON.stringify(sampleProducts)) })
      if (url.includes('/T0076I/')) return Promise.resolve({ data: JSON.parse(JSON.stringify(sampleReceiptLines)) })
      return Promise.resolve({ data: [] })
    })

    api.put.mockResolvedValue({ data: { success: true } })
    api.post.mockResolvedValue({ data: { id: 2, success: true } })
  })

  afterEach(() => {
    if (wrapper) {
      wrapper.unmount()
      wrapper = null
    }
    document.body.innerHTML = ''
  })

  function createWrapper() {
    wrapper = mount(GoodsReceiptView, {
      attachTo: document.body,
      global: { plugins: [pinia] }
    })
    return wrapper
  }

  it('opens camera scanner modal when clicking top header Camera Scan button', async () => {
    const w = createWrapper()
    await flushPromises()

    const cameraBtn = w.find('button[title="Open Camera Barcode Scanner"]')
    await cameraBtn.trigger('click')
    await flushPromises()

    // CameraBarcodeScannerModal should now be visible in body teleport
    const cameraModal = document.body.querySelector('.scanner-modal-container')
    expect(cameraModal).not.toBeNull()
  })

  it('triggers handleBarcodeScan when CameraBarcodeScannerModal emits scan event', async () => {
    const w = createWrapper()
    await flushPromises()

    // Open edit modal first
    await w.find('button[title="Edit"]').trigger('click')
    await flushPromises()

    const CameraModalComp = w.findComponent({ name: 'CameraBarcodeScannerModal' })
    expect(CameraModalComp.exists()).toBe(true)

    // Emit scan event from CameraBarcodeScannerModal for product 101 barcode
    await CameraModalComp.vm.$emit('scan', { raw: '0123456789012', gtin: '00123456789012' }, '0123456789012')
    await flushPromises()

    // Qty received should increment to 3
    const qtyInputs = w.findAll('.lines-editor-table input[type="number"]')
    expect(qtyInputs[1].element.value).toBe('3')
  })

  it('triggers manual global scan when clicking Scan / Verify button', async () => {
    const w = createWrapper()
    await flushPromises()

    const scannerInput = w.find('.scanner-input')
    await scannerInput.setValue('0123456789012')

    // Find Scan / Verify button next to scanner input
    const verifyBtn = w.find('.scanner-card button.btn-primary')
    await verifyBtn.trigger('click')
    await flushPromises()

    // Since main view scan with matching product starts new receipt
    expect(w.find('.modal-lg').exists()).toBe(true)
    const qtyInputs = w.findAll('.lines-editor-table input[type="number"]')
    expect(qtyInputs[1].element.value).toBe('1')
  })

  it('toggles sound mute state when clicking mute button in scanner card', async () => {
    const w = createWrapper()
    await flushPromises()

    const soundBtn = w.find('.scanner-card .btn-icon')
    expect(soundBtn.text()).toContain('volume_up')

    await soundBtn.trigger('click')
    await flushPromises()

    expect(soundBtn.text()).toContain('volume_off')
  })

  it('saves modified goods receipt lines and sends PUT request to backend API', async () => {
    const w = createWrapper()
    await flushPromises()

    // Edit receipt 1
    await w.find('button[title="Edit"]').trigger('click')
    await flushPromises()

    // Scan item barcode to increment qty
    const scannerInput = w.find('.scanner-input')
    await scannerInput.setValue('0123456789012')
    await scannerInput.trigger('keydown.enter')
    await flushPromises()

    // Click Save Receipt button
    const saveBtn = w.find('.modal-footer .btn-primary')
    await saveBtn.trigger('click')
    await flushPromises()

    // API put called for receipt line and header
    expect(api.put).toHaveBeenCalledWith('/T0076I/1', expect.objectContaining({
      qty_received: 3
    }))
    expect(api.put).toHaveBeenCalledWith('/T0075I/1', expect.objectContaining({
      status: 'Draft'
    }))
  })
})


