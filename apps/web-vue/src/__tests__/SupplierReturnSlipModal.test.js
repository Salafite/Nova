import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
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

vi.mock('../composables/useToast.js', () => ({
  useToast: () => ({
    show: vi.fn(),
  }),
}))

const mockSlipData = {
  return_id: 101,
  return_number: 'RMA-20260908-001',
  return_date: '2026-09-08',
  status: 'Approved',
  company_name: 'Nova Wholesale Distribution Hub',
  company_address: '100 Logistics Blvd, Dock Area B',
  company_phone: '+1 (800) 555-NOVA',
  supplier_id: 12,
  supplier_name: 'Fresh Harvest Farms Ltd',
  supplier_code: 'SUP-0012',
  supplier_contact: 'John Miller',
  supplier_phone: '+1 555-987-6543',
  supplier_email: 'returns@freshharvest.com',
  supplier_address: '450 Agro Way, Salinas, CA',
  purchase_order_id: 201,
  po_number: 'PO-2026-089',
  goods_receipt_id: 301,
  grn_number: 'GRN-301-2026',
  debit_memo_id: 401,
  debit_memo_number: 'DM-2026-0045',
  total_amount: 1250.00,
  currency: 'USD',
  reason: 'Severe temperature excursion during transit',
  notes: 'Driver was present during inspection and acknowledged spoiled pallets.',
  approved_at: '2026-09-08T10:30:00Z',
  approved_by_name: 'Marcus Dock Supervisor',
  lines: [
    {
      id: 1,
      line_number: 1,
      product_id: 50,
      product_name: 'Organic Strawberries 1lb',
      qty: 25,
      uom: 'Cases',
      unit_price: 30.00,
      line_total: 750.00,
      batch_number: 'LOT-STR-2026-01',
      expiry_date: '2026-09-15',
      reason_code: 'damaged',
      reason_label: 'Damaged in Transit',
      quarantine_status: 'Quarantine',
      disposition: 'Return to Vendor',
      photos: [],
    },
    {
      id: 2,
      line_number: 2,
      product_id: 51,
      product_name: 'Organic Blueberries 6oz',
      qty: 20,
      uom: 'Trays',
      unit_price: 25.00,
      line_total: 500.00,
      batch_number: 'LOT-BLU-2026-02',
      expiry_date: '2026-09-18',
      reason_code: 'qc_failed',
      reason_label: 'QC Inspection Failed',
      quarantine_status: 'Quarantine',
      disposition: 'Return to Vendor',
      photos: [],
    },
  ],
  attachments: [
    {
      id: 'att-1',
      filename: 'pallet_crushed_dock4.jpg',
      description: 'Crushed strawberry pallets upon trailer opening',
      url: 'https://images.example.com/dock/pallet_damage.jpg',
    },
    {
      id: 'att-2',
      filename: 'temp_recorder_log.jpg',
      description: 'Temp log showing 18C inside refrigerated truck',
      data_base64: 'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==',
    },
  ],
  acknowledgment_text:
    'Received the returned merchandise listed above in the condition stated. Supplier acknowledgment verifies debit memo claims.',
}

describe('SupplierReturnSlipModal.vue - Printable Return Slip & Evidence Gallery (Phase 7)', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
    api.get.mockResolvedValue({ data: mockSlipData })
  })

  it('renders return slip with company header, document title, and RMA number', async () => {
    const wrapper = mount(SupplierReturnSlipModal, {
      props: {
        show: true,
        returnId: 101,
      },
    })

    await flushPromises()

    expect(wrapper.text()).toContain('Nova Wholesale Distribution Hub')
    expect(wrapper.text()).toContain('VENDOR RETURN MERCHANDISE SLIP')
    expect(wrapper.text()).toContain('RMA-20260908-001')
    expect(wrapper.text()).toContain('Approved')
  })

  it('displays supplier details, cross-references (PO, GRN), and linked debit memo credit amount', async () => {
    const wrapper = mount(SupplierReturnSlipModal, {
      props: {
        show: true,
        returnId: 101,
      },
    })

    await flushPromises()

    // Supplier Info
    expect(wrapper.text()).toContain('Fresh Harvest Farms Ltd')
    expect(wrapper.text()).toContain('SUP-0012')
    expect(wrapper.text()).toContain('John Miller')

    // Document References
    expect(wrapper.text()).toContain('PO-2026-089')
    expect(wrapper.text()).toContain('GRN-301-2026')
    expect(wrapper.text()).toContain('DM-2026-0045')
    expect(wrapper.text()).toContain('$1250.00')
  })

  it('renders itemized return lines table with batch numbers, expiry dates, and reason codes', async () => {
    const wrapper = mount(SupplierReturnSlipModal, {
      props: {
        show: true,
        returnId: 101,
      },
    })

    await flushPromises()

    expect(wrapper.text()).toContain('Organic Strawberries 1lb')
    expect(wrapper.text()).toContain('LOT-STR-2026-01')
    expect(wrapper.text()).toContain('Exp: 2026-09-15')
    expect(wrapper.text()).toContain('Damaged in Transit')

    expect(wrapper.text()).toContain('Organic Blueberries 6oz')
    expect(wrapper.text()).toContain('LOT-BLU-2026-02')
    expect(wrapper.text()).toContain('QC Inspection Failed')

    // Totals line
    expect(wrapper.text()).toContain('45') // Total qty (25 + 20)
    expect(wrapper.text()).toContain('$1250.00')
  })

  it('renders accounting debit memo statement card', async () => {
    const wrapper = mount(SupplierReturnSlipModal, {
      props: {
        show: true,
        returnId: 101,
      },
    })

    await flushPromises()

    expect(wrapper.text()).toContain('Automated Supplier Debit Memo Accounting Notice')
    expect(wrapper.text()).toContain('$1250.00')
  })

  it('renders inspection photos gallery with thumbnails and click-to-lightbox trigger', async () => {
    const wrapper = mount(SupplierReturnSlipModal, {
      props: {
        show: true,
        returnId: 101,
      },
    })

    await flushPromises()

    const photoCards = wrapper.findAll('.photo-card')
    expect(photoCards.length).toBe(2)
    expect(wrapper.text()).toContain('pallet_crushed_dock4.jpg')
    expect(wrapper.text()).toContain('temp_recorder_log.jpg')

    // Clicking first photo opens lightbox
    await photoCards[0].trigger('click')
    expect(wrapper.findComponent(PhotoLightboxModal).exists()).toBe(true)
    expect(wrapper.findComponent(PhotoLightboxModal).props('show')).toBe(true)
  })

  it('renders driver and carrier acknowledgment sign-off section with dual signature blocks', async () => {
    const wrapper = mount(SupplierReturnSlipModal, {
      props: {
        show: true,
        returnId: 101,
      },
    })

    await flushPromises()

    const signoffSection = wrapper.find('.signoff-section')
    expect(signoffSection.exists()).toBe(true)
    expect(signoffSection.text()).toContain('1. Warehouse Quality / Dock Inspector')
    expect(signoffSection.text()).toContain('2. Driver / Carrier Representative Acknowledgment')
    expect(signoffSection.text()).toContain('Marcus Dock Supervisor')
    expect(signoffSection.text()).toContain('Carrier / Transport Co')
    expect(signoffSection.text()).toContain('Driver Printed Name')
    expect(signoffSection.text()).toContain('Truck / Trailer / BOL #')
  })

  it('triggers window.print when clicking Print Slip button', async () => {
    const printSpy = vi.spyOn(window, 'print').mockImplementation(() => {})

    const wrapper = mount(SupplierReturnSlipModal, {
      props: {
        show: true,
        returnId: 101,
      },
    })

    await flushPromises()

    const printBtn = wrapper.find('.btn-print')
    await printBtn.trigger('click')

    expect(printSpy).toHaveBeenCalled()
    printSpy.mockRestore()
  })

  it('toggles photos visibility in printed document via checkbox', async () => {
    const wrapper = mount(SupplierReturnSlipModal, {
      props: {
        show: true,
        returnId: 101,
      },
    })

    await flushPromises()

    const photosSection = wrapper.find('.photos-section')
    expect(photosSection.classes()).not.toContain('hide-in-print')

    // Uncheck photos in print
    const toggleInput = wrapper.find('.toggle-photos-label input[type="checkbox"]')
    await toggleInput.setValue(false)

    expect(wrapper.find('.photos-section').classes()).toContain('hide-in-print')
  })
})
