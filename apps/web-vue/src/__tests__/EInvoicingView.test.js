import { mount, flushPromises } from '@vue/test-utils'
import { vi, describe, it, expect, beforeEach, afterEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import EInvoicingView from '../views/accounting/EInvoicingView.vue'
import FiscalSettingsView from '../views/accounting/FiscalSettingsView.vue'
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
  useRoute: () => ({ params: {} }),
  useRouter: () => ({ push: mockPush }),
}))

// Mock useToast
const mockToast = vi.fn()
vi.mock('../composables/useToast.js', () => ({
  useToast: () => ({ show: mockToast }),
}))

describe('EInvoicingView & Fiscal Authority Web UI', () => {
  let pinia
  let wrapper

  const sampleInvoices = [
    {
      id: 1,
      invoice_number: 'INV-2026-0001',
      invoice_type: 'Sales',
      partner_id: 10,
      issue_date: '2026-09-01',
      total_amount: 1150.0,
      tax_amount: 150.0,
      status: 'Paid',
    },
    {
      id: 2,
      invoice_number: 'INV-2026-0002',
      invoice_type: 'Simplified',
      partner_id: 11,
      issue_date: '2026-09-02',
      total_amount: 575.0,
      tax_amount: 75.0,
      status: 'Unpaid',
    },
    {
      id: 3,
      invoice_number: 'INV-2026-0003',
      invoice_type: 'Sales',
      partner_id: 10,
      issue_date: '2026-09-03',
      total_amount: 2300.0,
      tax_amount: 300.0,
      status: 'Unpaid',
    },
  ]

  const sampleClearanceRecords = [
    {
      id: 101,
      invoice_id: 1,
      clearance_status: 'CLEARED',
      clearance_uuid: 'uuid-cleared-123456789',
      invoice_hash: 'hash-abc1234567890',
      subtype: '0100000',
    },
    {
      id: 102,
      invoice_id: 2,
      clearance_status: 'REPORTED',
      clearance_uuid: 'uuid-reported-987654321',
      invoice_hash: 'hash-def9876543210',
      subtype: '0200000',
    },
    {
      id: 103,
      invoice_id: 3,
      clearance_status: 'REJECTED',
      clearance_uuid: null,
      invoice_hash: null,
      subtype: '0100000',
    },
  ]

  const sampleCustomers = [
    { id: 10, name: 'Acme Corp Trading', tax_id: '300011122200003' },
    { id: 11, name: 'Global Tech Retail', tax_id: '300033344400003' },
  ]

  const sampleFiscalProfiles = [
    {
      id: 1,
      profile_name: 'Saudi ZATCA Production Profile',
      authority_code: 'ZATCA',
      seller_name: 'Nova Global Trading LLC',
      seller_name_ar: 'شركة نوفا للتجارة العامة',
      tax_id: '300012345600003',
      commercial_registration_number: '1010123456',
      building_number: '1234',
      street_name: 'King Fahd Road',
      district: 'Al Olaya',
      city: 'Riyadh',
      postal_code: '12211',
      country_code: 'SA',
      environment: 'Production',
      is_active: true,
      is_default: true,
      private_key: '-----BEGIN EC PRIVATE KEY-----\nMIG...',
      public_key: '-----BEGIN PUBLIC KEY-----\nMFk...',
    },
    {
      id: 2,
      profile_name: 'ZATCA Sandbox Test Profile',
      authority_code: 'ZATCA',
      seller_name: 'Nova Sandbox Entity',
      tax_id: '399999999900003',
      environment: 'Sandbox',
      is_active: false,
      is_default: false,
    },
  ]

  beforeEach(() => {
    pinia = createPinia()
    setActivePinia(pinia)
    vi.clearAllMocks()

    api.get.mockImplementation((url) => {
      if (url.includes('/T0090I/') && url.includes('/qr-code')) {
        return Promise.resolve({
          data: {
            invoice_id: 1,
            seller_name: 'Nova Global Trading LLC',
            vat_number: '300012345600003',
            timestamp: '2026-09-01T12:00:00Z',
            total_amount: 1150.0,
            vat_total: 150.0,
            qr_code_base64: 'AQxOb3ZhIFRyYWRpbmcCCzMwMDAxMjM0NTYw',
            qr_code_image: 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAA...',
            invoice_hash: '5d41402abc4b2a76b9719d911017c592',
            signature: 'MEQCID1234567890abcdef...',
          },
        })
      }
      if (url.includes('/T0090I/') && url.includes('/fiscal-pdf')) {
        return Promise.resolve({ data: new Blob(['%PDF-1.4 mock'], { type: 'application/pdf' }) })
      }
      if (url.includes('/T0090I/')) {
        return Promise.resolve({ data: JSON.parse(JSON.stringify(sampleInvoices)) })
      }
      if (url.includes('/T0124I/')) {
        return Promise.resolve({ data: JSON.parse(JSON.stringify(sampleClearanceRecords)) })
      }
      if (url.includes('/T0125I/')) {
        return Promise.resolve({ data: JSON.parse(JSON.stringify(sampleFiscalProfiles)) })
      }
      if (url.includes('/T0010I/')) {
        return Promise.resolve({ data: JSON.parse(JSON.stringify(sampleCustomers)) })
      }
      return Promise.resolve({ data: [] })
    })

    api.post.mockImplementation((url) => {
      if (url.includes('/generate-xml/')) {
        return Promise.resolve({
          data: {
            invoice_id: 1,
            ubl_xml: '<?xml version="1.0" encoding="UTF-8"?><Invoice xmlns="urn:oasis:names:specification:ubl:schema:xsd:Invoice-2"><ID>INV-2026-0001</ID></Invoice>',
          },
        })
      }
      if (url.includes('/clearance')) {
        return Promise.resolve({
          data: {
            invoice_id: 1,
            status: 'CLEARED',
            clearance_uuid: 'uuid-cleared-new-999',
            clearance_timestamp: '2026-09-05T09:00:00Z',
            environment: 'Sandbox',
            message: 'Invoice cleared successfully by ZATCA',
          },
        })
      }
      if (url.includes('/generate-keypair')) {
        return Promise.resolve({
          data: {
            private_key: '-----BEGIN EC PRIVATE KEY-----\nMIG2AgEAMBAGByqGSM49AgEGBSuBBAAiBIGeMIGbAgEBBDCG...',
            public_key: '-----BEGIN PUBLIC KEY-----\nMFkwEwYHKoZIzj0CAQYIKoZIzj0DAQcDQgAE...',
            algorithm: 'ECDSA_secp256k1',
          },
        })
      }
      return Promise.resolve({ data: { id: 99, success: true } })
    })

    api.put.mockResolvedValue({ data: { success: true } })
    api.delete.mockResolvedValue({ data: { success: true } })
  })

  afterEach(() => {
    if (wrapper) {
      wrapper.unmount()
      wrapper = null
    }
  })

  it('renders EInvoicingView with statistics, records table, and clearance status badges', async () => {
    wrapper = mount(EInvoicingView, {
      global: { plugins: [pinia] },
    })
    await flushPromises()

    expect(wrapper.text()).toContain('e-Invoicing & Fiscal Clearance')
    expect(wrapper.text()).toContain('Total e-Invoices')
    expect(wrapper.text()).toContain('Cleared (B2B)')
    expect(wrapper.text()).toContain('Reported (B2C)')

    // Check table rows
    expect(wrapper.text()).toContain('INV-2026-0001')
    expect(wrapper.text()).toContain('Acme Corp Trading')
    expect(wrapper.text()).toContain('CLEARED')
    expect(wrapper.text()).toContain('INV-2026-0002')
    expect(wrapper.text()).toContain('REPORTED')
    expect(wrapper.text()).toContain('INV-2026-0003')
    expect(wrapper.text()).toContain('REJECTED')
  })

  it('filters records by clearance status and search query', async () => {
    wrapper = mount(EInvoicingView, {
      global: { plugins: [pinia] },
    })
    await flushPromises()

    // Filter by CLEARED status
    const statusSelect = wrapper.findAll('select')[0]
    await statusSelect.setValue('CLEARED')
    await statusSelect.trigger('change')
    await flushPromises()

    expect(wrapper.text()).toContain('INV-2026-0001')
    expect(wrapper.text()).not.toContain('INV-2026-0002')
    expect(wrapper.text()).not.toContain('INV-2026-0003')

    // Search query filter
    await statusSelect.setValue('All')
    const searchInput = wrapper.find('.search-input')
    await searchInput.setValue('Global Tech')
    await flushPromises()

    expect(wrapper.text()).toContain('INV-2026-0002')
    expect(wrapper.text()).not.toContain('INV-2026-0001')
  })

  it('opens QR code preview modal and displays decoded TLV tags', async () => {
    wrapper = mount(EInvoicingView, {
      global: { plugins: [pinia] },
    })
    await flushPromises()

    // Click on QR code button for first record
    const qrButtons = wrapper.findAll('button[title*="QR"]')
    expect(qrButtons.length).toBeGreaterThan(0)
    await qrButtons[0].trigger('click')
    await flushPromises()

    expect(wrapper.find('.modal-overlay').exists()).toBe(true)
    expect(wrapper.text()).toContain('Tax Authority QR Code Preview')
    expect(wrapper.text()).toContain('Nova Global Trading LLC')
    expect(wrapper.text()).toContain('300012345600003')
    expect(wrapper.text()).toContain('$1150.00')
    expect(wrapper.text()).toContain('Tag 1')
    expect(wrapper.text()).toContain('Tag 2')
    expect(wrapper.text()).toContain('Tag 3')
    expect(wrapper.text()).toContain('Tag 4')
    expect(wrapper.text()).toContain('Tag 5')
  })

  it('opens UBL XML inspector modal and renders generated XML document', async () => {
    wrapper = mount(EInvoicingView, {
      global: { plugins: [pinia] },
    })
    await flushPromises()

    // Click XML inspect button
    const xmlButtons = wrapper.findAll('button[title*="XML"]')
    expect(xmlButtons.length).toBeGreaterThan(0)
    await xmlButtons[0].trigger('click')
    await flushPromises()

    expect(wrapper.find('.modal-overlay').exists()).toBe(true)
    expect(wrapper.text()).toContain('OASIS UBL 2.1 XML Document Inspector')
    expect(wrapper.text()).toContain('<Invoice xmlns=')
    expect(wrapper.text()).toContain('INV-2026-0001')
  })

  it('submits invoice for clearance and opens result modal', async () => {
    wrapper = mount(EInvoicingView, {
      global: { plugins: [pinia] },
    })
    await flushPromises()

    const submitButtons = wrapper.findAll('.btn-action-submit')
    expect(submitButtons.length).toBeGreaterThan(0)
    await submitButtons[0].trigger('click')
    await flushPromises()

    expect(api.post).toHaveBeenCalledWith('/T0090I/3/clearance')
    expect(mockToast).toHaveBeenCalledWith(expect.stringContaining('submitted'), 'success')
    expect(wrapper.text()).toContain('Fiscal Authority Clearance Status')
    expect(wrapper.text()).toContain('Invoice cleared successfully')
  })

  it('renders FiscalSettingsView with active profile and creates a new profile', async () => {
    const fiscalWrapper = mount(FiscalSettingsView, {
      global: { plugins: [pinia] },
    })
    await flushPromises()

    expect(fiscalWrapper.text()).toContain('Fiscal Authority Profiles & Tax Credentials')
    expect(fiscalWrapper.text()).toContain('Saudi ZATCA Production Profile')
    expect(fiscalWrapper.text()).toContain('300012345600003')
    expect(fiscalWrapper.text()).toContain('ZATCA')
    expect(fiscalWrapper.text()).toContain('Production')

    // Open create modal
    const addBtn = fiscalWrapper.find('header .btn-primary')
    await addBtn.trigger('click')
    await flushPromises()

    expect(fiscalWrapper.find('.modal-overlay').exists()).toBe(true)
    expect(fiscalWrapper.text()).toContain('New Fiscal Profile')

    // Fill form
    const textInputs = fiscalWrapper.findAll('input[type="text"]')
    // Profile Name is first text input
    await textInputs[0].setValue('PEPPOL European Profile')
    // Seller Name English is second text input
    await textInputs[1].setValue('Nova Europe BV')
    // Tax ID is 4th text input (after Arabic name)
    await textInputs[3].setValue('NL123456789B01')

    const saveBtn = fiscalWrapper.find('.modal-actions .btn-primary')
    await saveBtn.trigger('click')
    await flushPromises()

    expect(api.post).toHaveBeenCalledWith('/T0125I/', expect.objectContaining({
      profile_name: 'PEPPOL European Profile',
      seller_name: 'Nova Europe BV',
      tax_id: 'NL123456789B01',
    }))
    expect(mockToast).toHaveBeenCalledWith(expect.stringContaining('created'), 'success')
  })

  it('generates new ECDSA keypair in FiscalSettingsView', async () => {
    const fiscalWrapper = mount(FiscalSettingsView, {
      global: { plugins: [pinia] },
    })
    await flushPromises()

    // Click Generate Keypair header button
    const keyBtn = fiscalWrapper.find('header .btn-outline')
    await keyBtn.trigger('click')
    await flushPromises()

    expect(api.post).toHaveBeenCalledWith('/T0125I/generate-keypair')
    expect(fiscalWrapper.find('.modal-overlay').exists()).toBe(true)
    expect(fiscalWrapper.text()).toContain('ECDSA secp256k1 Keypair Generator')
    const textareas = fiscalWrapper.findAll('.key-textarea')
    expect(textareas.length).toBeGreaterThan(0)
    expect(textareas[0].element.value).toContain('BEGIN EC PRIVATE KEY')
  })
})
