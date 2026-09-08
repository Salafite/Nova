import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import PurchaseReturnsView from '../views/purchasing/PurchaseReturnsView.vue'
import SupplierReturnSlipModal from '../components/purchasing/SupplierReturnSlipModal.vue'
import PhotoLightboxModal from '../components/PhotoLightboxModal.vue'
import { api } from '../api/client.js'

vi.mock('../api/client.js', () => ({
  api: {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    delete: vi.fn(),
  },
}))

const mockToast = vi.fn()
vi.mock('../composables/useToast.js', () => ({
  useToast: () => ({
    show: mockToast,
  }),
}))

const mockSuppliers = [
  { id: 1, name: 'Apex Agriculture', company_name: 'Apex Agriculture Ltd' },
  { id: 2, name: 'Pacific Coast Produce', company_name: 'Pacific Coast Produce Inc' },
]

const mockOrders = [
  { id: 101, order_number: 'PO-2026-001', supplier_id: 1 },
  { id: 102, order_number: 'PO-2026-002', supplier_id: 2 },
]

const mockGoodsReceipts = [
  { id: 501, receipt_number: 'GRN-2026-001', purchase_order_id: 101, supplier_id: 1, receipt_date: '2026-09-01' },
]

const mockGoodsReceiptLines = [
  {
    id: 1,
    receipt_id: 501,
    product_id: 10,
    product_name: 'Organic Honeycrisp Apples',
    qty_ordered: 50,
    qty_received: 50,
    batch_number: 'LOT-APP-2026-01',
    expiry_date: '2026-10-15',
  },
]

const mockProducts = [
  { id: 10, name: 'Organic Honeycrisp Apples', sku: 'SKU-APP-01', cost_price: 45.00 },
  { id: 11, name: 'Organic Valencia Oranges', sku: 'SKU-ORG-02', cost_price: 35.00 },
]

const mockBatches = [
  { id: 1, product_id: 10, batch_number: 'LOT-APP-2026-01', quantity: 100, expiry_date: '2026-10-15' },
  { id: 2, product_id: 11, batch_number: 'LOT-ORG-2026-99', quantity: 60, expiry_date: '2026-11-20' },
]

const mockReturns = [
  {
    id: 1,
    return_number: 'RMA-20260908-001',
    supplier_id: 1,
    purchase_order_id: 101,
    goods_receipt_id: 501,
    return_date: '2026-09-08',
    status: 'Draft',
    total_amount: 900.00,
    reason: 'Damaged fruit pallets upon unloading',
    reason_code: 'damaged',
    notes: 'Driver was present during inspection',
    debit_memo_id: null,
    approved_at: null,
    lines: [
      {
        id: 10,
        return_id: 1,
        line_number: 1,
        product_id: 10,
        product_name: 'Organic Honeycrisp Apples',
        qty: 20,
        unit_price: 45.00,
        line_total: 900.00,
        batch_number: 'LOT-APP-2026-01',
        expiry_date: '2026-10-15',
        reason_code: 'damaged',
        disposition: 'Return to Vendor',
        quarantine_status: 'Quarantine',
      },
    ],
    attachments: [
      {
        id: 'att-1',
        filename: 'damaged_boxes.jpg',
        url: 'https://example.com/damaged_boxes.jpg',
        description: 'Crushed corners on pallet 2',
      },
    ],
  },
  {
    id: 2,
    return_number: 'RMA-20260908-002',
    supplier_id: 2,
    purchase_order_id: 102,
    goods_receipt_id: null,
    return_date: '2026-09-07',
    status: 'Approved',
    total_amount: 350.00,
    reason: 'Expired inventory received',
    reason_code: 'expired',
    notes: 'Approved for debit credit',
    debit_memo_id: 88,
    approved_at: '2026-09-07T14:00:00Z',
    approved_by: 1,
    approved_by_name: 'Marcus Supervisor',
    lines: [
      {
        id: 20,
        return_id: 2,
        line_number: 1,
        product_id: 11,
        product_name: 'Organic Valencia Oranges',
        qty: 10,
        unit_price: 35.00,
        line_total: 350.00,
        batch_number: 'LOT-ORG-2026-99',
        expiry_date: '2026-08-30',
        reason_code: 'expired',
        disposition: 'Return to Vendor',
        quarantine_status: 'Quarantine',
      },
    ],
    attachments: [],
  },
  {
    id: 3,
    return_number: 'RMA-20260908-003',
    supplier_id: 1,
    purchase_order_id: null,
    goods_receipt_id: null,
    return_date: '2026-09-05',
    status: 'Returned',
    total_amount: 200.00,
    reason: 'Carrier picked up rejected items',
    reason_code: 'rejected',
    notes: 'Dispatched with transport carrier',
    debit_memo_id: 77,
    approved_at: '2026-09-05T09:00:00Z',
    lines: [],
    attachments: [],
  },
]

describe('PurchaseReturnsView.vue - RMA Lifecycle & Supplier Debit Memo Frontend (Phase 8)', () => {
  let pinia
  let wrapper

  beforeEach(() => {
    pinia = createPinia()
    setActivePinia(pinia)
    vi.clearAllMocks()

    api.get.mockImplementation((url) => {
      if (url === '/T0081I/') {
        return Promise.resolve({ data: JSON.parse(JSON.stringify(mockReturns)) })
      }
      if (url.includes('/T0081I/1/details')) {
        return Promise.resolve({ data: JSON.parse(JSON.stringify(mockReturns[0])) })
      }
      if (url.includes('/T0081I/2/details')) {
        return Promise.resolve({ data: JSON.parse(JSON.stringify(mockReturns[1])) })
      }
      if (url === '/T0011I/' || url === '/T0103I/') {
        return Promise.resolve({ data: JSON.parse(JSON.stringify(mockSuppliers)) })
      }
      if (url === '/T0014I/') {
        return Promise.resolve({ data: JSON.parse(JSON.stringify(mockOrders)) })
      }
      if (url === '/T0075I/') {
        return Promise.resolve({ data: JSON.parse(JSON.stringify(mockGoodsReceipts)) })
      }
      if (url === '/T0076I/') {
        return Promise.resolve({ data: JSON.parse(JSON.stringify(mockGoodsReceiptLines)) })
      }
      if (url === '/T0003I/') {
        return Promise.resolve({ data: JSON.parse(JSON.stringify(mockProducts)) })
      }
      if (url === '/T0088I/') {
        return Promise.resolve({ data: JSON.parse(JSON.stringify(mockBatches)) })
      }
      return Promise.resolve({ data: [] })
    })

    api.post.mockResolvedValue({ data: { id: 99, return_number: 'RMA-NEW-99', success: true } })
    api.put.mockResolvedValue({ data: { success: true } })
    api.delete.mockResolvedValue({ data: { success: true } })
  })

  afterEach(() => {
    if (wrapper) {
      wrapper.unmount()
      wrapper = null
    }
    document.body.innerHTML = ''
  })

  function createWrapper() {
    wrapper = mount(PurchaseReturnsView, {
      global: {
        plugins: [pinia],
        stubs: {
          'router-link': {
            template: '<a><slot /></a>',
          },
          SupplierReturnSlipModal: true,
          PhotoLightboxModal: true,
        },
      },
    })
    return wrapper
  }

  it('renders page header, navigation hub, and KPI summary cards with computed metrics', async () => {
    const w = createWrapper()
    await flushPromises()

    expect(w.text()).toContain('Vendor Returns (RMA) & Debit Memos')
    expect(w.text()).toContain('Total RMAs')
    expect(w.text()).toContain('3') // Total: 3 returns

    expect(w.text()).toContain('Pending Approval')
    expect(w.text()).toContain('1') // Draft: 1

    expect(w.text()).toContain('Approved & Quarantined')
    expect(w.text()).toContain('1') // Approved: 1

    expect(w.text()).toContain('Completed')
    expect(w.text()).toContain('1') // Returned: 1

    expect(w.text()).toContain('Total Debit Claims')
    expect(w.text()).toContain('$1450.00') // 900 + 350 + 200
  })

  it('renders RMA data table with supplier name, source references, claim amounts, debit memo badges, and statuses', async () => {
    const w = createWrapper()
    await flushPromises()

    // Table rows
    expect(w.text()).toContain('RMA-20260908-001')
    expect(w.text()).toContain('Apex Agriculture')
    expect(w.text()).toContain('PO-2026-001')
    expect(w.text()).toContain('GRN #501')
    expect(w.text()).toContain('$900.00')
    expect(w.text()).toContain('Draft')

    // Approved return with Debit Memo
    expect(w.text()).toContain('RMA-20260908-002')
    expect(w.text()).toContain('Pacific Coast Produce')
    expect(w.text()).toContain('DM #88')
    expect(w.text()).toContain('$350.00')
    expect(w.text()).toContain('Approved')
  })

  it('filters returns by status tabs (Draft, Approved, Returned, Cancelled)', async () => {
    const w = createWrapper()
    await flushPromises()

    const tabs = w.findAll('.filter-tab')
    // Tabs: All (0), Draft (1), Approved (2), Returned (3), Cancelled (4)
    expect(tabs.length).toBe(5)

    // Click Draft tab
    await tabs[1].trigger('click')
    await flushPromises()

    expect(w.text()).toContain('RMA-20260908-001')
    expect(w.text()).not.toContain('RMA-20260908-002')
    expect(w.text()).not.toContain('RMA-20260908-003')

    // Click Approved tab
    await tabs[2].trigger('click')
    await flushPromises()

    expect(w.text()).not.toContain('RMA-20260908-001')
    expect(w.text()).toContain('RMA-20260908-002')
    expect(w.text()).not.toContain('RMA-20260908-003')
  })

  it('filters returns by search query matching RMA number, supplier, or reason', async () => {
    const w = createWrapper()
    await flushPromises()

    const searchInput = w.find('.search-input')
    await searchInput.setValue('Pacific')
    await flushPromises()

    expect(w.text()).toContain('RMA-20260908-002')
    expect(w.text()).not.toContain('RMA-20260908-001')

    // Clear search
    await searchInput.setValue('')
    await flushPromises()
    expect(w.text()).toContain('RMA-20260908-001')
    expect(w.text()).toContain('RMA-20260908-002')
  })

  it('opens RMA creation modal and populates multi-line items with product selection and auto-batching', async () => {
    const w = createWrapper()
    await flushPromises()

    // Click "New Return (RMA)"
    const newBtn = w.find('.page-actions .btn-primary')
    await newBtn.trigger('click')
    await flushPromises()

    expect(w.find('.modal-xl').exists()).toBe(true)
    expect(w.text()).toContain('1. Return Header & References')
    expect(w.text()).toContain('2. Itemized Return Lines & Batches')
    expect(w.text()).toContain('3. Inspection Photos & Evidence')

    // Select Supplier 1
    const supplierSelect = w.find('select[required]')
    await supplierSelect.setValue('1')
    await flushPromises()

    // Select product for line 0
    const productSelect = w.find('.lines-editor-table select')
    await productSelect.setValue('10') // Organic Honeycrisp Apples
    await flushPromises()

    // Line unit price should be auto pre-filled
    const unitPriceInput = w.findAll('.lines-editor-table input[type="number"]')[1]
    expect(unitPriceInput.element.value).toBe('45')

    // Click Auto Batch button in lines header
    const autoBatchBtn = w.findAll('.lines-actions button')[0]
    await autoBatchBtn.trigger('click')
    await flushPromises()

    const batchInput = w.find('.lines-editor-table .batch-text-input')
    expect(batchInput.element.value).toContain('LOT-')
  })

  it('imports line items directly from selected Goods Receipt (GRN)', async () => {
    const w = createWrapper()
    await flushPromises()

    // Open add modal
    await w.find('.page-actions .btn-primary').trigger('click')
    await flushPromises()

    // Set GRN #501
    const grnSelect = w.find('.grn-select-wrap select')
    await grnSelect.setValue('501')
    await flushPromises()

    // Click Import GRN button
    const importBtn = w.find('.btn-import-grn')
    await importBtn.trigger('click')
    await flushPromises()

    // Check lines were imported
    expect(mockToast).toHaveBeenCalledWith(
      expect.stringContaining('Imported'),
      'success'
    )
    const lineRows = w.findAll('.lines-editor-table tbody tr')
    expect(lineRows.length).toBe(1)
  })

  it('adds inspection photo by direct URL in RMA creation modal', async () => {
    const w = createWrapper()
    await flushPromises()

    await w.find('.page-actions .btn-primary').trigger('click')
    await flushPromises()

    const urlInput = w.find('.url-input-bar input[type="text"]')
    await urlInput.setValue('https://example.com/crushed_carton.jpg')

    const descInput = w.find('.photo-desc-input')
    await descInput.setValue('Broken wooden pallet and crushed carton')

    const addUrlBtn = w.find('.url-input-bar button')
    await addUrlBtn.trigger('click')
    await flushPromises()

    expect(w.text()).toContain('crushed_carton.jpg')
    expect(w.find('.photos-upload-grid').exists()).toBe(true)
  })

  it('saves new RMA and submits POST requests to /T0081I/ and /T0082I/bulk', async () => {
    const w = createWrapper()
    await flushPromises()

    await w.find('.page-actions .btn-primary').trigger('click')
    await flushPromises()

    // Set supplier
    const supplierSelect = w.find('select[required]')
    await supplierSelect.setValue('1')
    await flushPromises()

    // Line 0 product
    const productSelect = w.find('.lines-editor-table select')
    await productSelect.setValue('10')
    await flushPromises()

    // Set qty
    const qtyInput = w.findAll('.lines-editor-table input[type="number"]')[0]
    await qtyInput.setValue('5')
    await flushPromises()

    // Click Save & Create RMA
    const saveBtn = w.findAll('.modal-footer-btns button')[1]
    await saveBtn.trigger('click')
    await flushPromises()

    expect(api.post).toHaveBeenCalledWith('/T0081I/', expect.objectContaining({
      supplier_id: 1,
      status: 'Draft',
    }))

    expect(api.post).toHaveBeenCalledWith('/T0082I/bulk', expect.objectContaining({
      return_id: 99,
      lines: expect.arrayContaining([
        expect.objectContaining({
          product_id: 10,
          qty: 5,
        }),
      ]),
    }))

    expect(mockToast).toHaveBeenCalledWith(
      expect.stringContaining('created'),
      'success'
    )
  })

  it('opens details modal and displays full RMA breakdown, batch numbers, and debit memo link', async () => {
    const w = createWrapper()
    await flushPromises()

    // Click RMA link in table on first RMA
    const rmaLink = w.findAll('.rma-link')[0]
    await rmaLink.trigger('click')
    await flushPromises()

    expect(api.get).toHaveBeenCalledWith('/T0081I/1/details')
    expect(w.find('.modal-content.modal-lg').exists()).toBe(true)
    expect(w.text()).toContain('Return Merchandise Authorization')
    expect(w.text()).toContain('RMA-20260908-001')
    expect(w.text()).toContain('Organic Honeycrisp Apples')
    expect(w.text()).toContain('LOT-APP-2026-01')
    expect(w.text()).toContain('DAMAGED')
    expect(w.text()).toContain('Damaged fruit pallets upon unloading')
  })

  it('opens RMA approval modal and submits POST request to /T0081I/{id}/approve with debit memo and quarantine flags', async () => {
    const w = createWrapper()
    await flushPromises()

    // Click Approve button on Draft RMA
    const approveBtn = w.find('.btn-icon-approve')
    await approveBtn.trigger('click')
    await flushPromises()

    expect(w.find('.modal-content').exists()).toBe(true)
    expect(w.text()).toContain('Approve Purchase Return (RMA)')
    expect(w.text()).toContain('Supplier Debit Memo (T0090)')
    expect(w.text()).toContain('Inventory Quarantine (T0088 / T0064)')

    // Click Confirm & Approve RMA
    const confirmApproveBtn = w.find('.modal-actions .btn-success')
    await confirmApproveBtn.trigger('click')
    await flushPromises()

    expect(api.post).toHaveBeenCalledWith('/T0081I/1/approve', {
      create_debit_memo: true,
      quarantine_inventory: true,
      notes: null,
    })

    expect(mockToast).toHaveBeenCalledWith(
      expect.stringContaining('approved'),
      'success'
    )
  })

  it('completes return for Approved RMA and calls /T0081I/{id}/complete-return', async () => {
    const w = createWrapper()
    await flushPromises()

    // Click Complete Return button on Approved RMA
    const completeBtn = w.find('.btn-icon-complete')
    await completeBtn.trigger('click')
    await flushPromises()

    expect(api.post).toHaveBeenCalledWith('/T0081I/2/complete-return')
    expect(mockToast).toHaveBeenCalledWith(
      expect.stringContaining('completed'),
      'success'
    )
  })

  it('cancels RMA when providing cancellation reason', async () => {
    const w = createWrapper()
    await flushPromises()

    const cancelBtn = w.findAll('.btn-icon-warning')[0]
    await cancelBtn.trigger('click')
    await flushPromises()

    expect(w.text()).toContain('Cancel Purchase Return (RMA)')

    // Type cancellation reason
    const textarea = w.find('.modal-body textarea')
    await textarea.setValue('Supplier requested replacement instead of return')
    await flushPromises()

    // Click Confirm Cancel
    const confirmCancelBtn = w.find('.modal-actions .btn-danger')
    await confirmCancelBtn.trigger('click')
    await flushPromises()

    expect(api.post).toHaveBeenCalledWith('/T0081I/1/cancel', {
      reason: 'Supplier requested replacement instead of return',
    })
    expect(mockToast).toHaveBeenCalledWith(
      expect.stringContaining('cancelled'),
      'success'
    )
  })

  it('opens printable Supplier Return Slip modal when clicking print button', async () => {
    const w = createWrapper()
    await flushPromises()

    const printBtn = w.findAll('.btn-icon-print')[0]
    await printBtn.trigger('click')
    await flushPromises()

    const slipModal = w.findComponent({ name: 'SupplierReturnSlipModal' })
    expect(slipModal.exists()).toBe(true)
    expect(slipModal.props('show')).toBe(true)
    expect(slipModal.props('returnId')).toBe(1)
  })
})
