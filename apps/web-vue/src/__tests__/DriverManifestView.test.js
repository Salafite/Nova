import { mount, flushPromises } from '@vue/test-utils'
import { vi, describe, it, expect, beforeEach, afterEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import DriverManifestView from '../views/sales/DriverManifestView.vue'
import { api } from '../api/client.js'

// Mock api client
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
  useRouter: () => ({ push: mockPush }),
  useRoute: () => ({ params: { id: '5' } }),
}))

// Mock useToast
const mockToast = vi.fn()
vi.mock('../composables/useToast.js', () => ({
  useToast: () => ({ show: mockToast }),
}))

describe('DriverManifestView.vue', () => {
  let pinia
  let wrapper

  const sampleManifest = {
    run_id: 5,
    run_code: 'RUN-2026-005',
    run_date: '2026-09-05',
    zone_name: 'Downtown East Zone',
    driver_name: 'Carlos Driver',
    vehicle_code: 'TRK-02',
    vehicle_name: 'Refrigerated Van 2',
    status: 'In Transit',
    total_weight: 580.0,
    stops: [
      {
        id: 501,
        stop_sequence: 1,
        sales_order_id: 201,
        sales_order_number: 'SO-2026-008',
        customer_name: 'Eastside Bistro',
        delivery_address: '789 Main St, Eastside',
        contact_person: 'Manager Bob',
        contact_phone: '+1-555-0199',
        item_count: 5,
        weight_kg: 210.0,
        status: 'Pending',
        delivery_notes: 'Ring doorbell at rear loading dock',
      },
      {
        id: 502,
        stop_sequence: 2,
        sales_order_id: 202,
        sales_order_number: 'SO-2026-009',
        customer_name: 'Grand Hotel & Suites',
        delivery_address: '100 Hotel Blvd',
        contact_person: 'Chef Mario',
        contact_phone: '+1-555-0200',
        item_count: 10,
        weight_kg: 370.0,
        status: 'Pending',
        delivery_notes: 'Deliver directly to kitchen receiver',
      },
    ],
  }

  beforeEach(() => {
    pinia = createPinia()
    setActivePinia(pinia)
    vi.clearAllMocks()

    api.get.mockImplementation((url) => {
      if (url.includes('/manifest')) {
        return Promise.resolve({ data: JSON.parse(JSON.stringify(sampleManifest)) })
      }
      return Promise.resolve({ data: [] })
    })

    api.put.mockResolvedValue({ data: { status: 'updated' } })
  })

  afterEach(() => {
    if (wrapper) {
      wrapper.unmount()
      wrapper = null
    }
  })

  function createWrapper() {
    wrapper = mount(DriverManifestView, {
      global: {
        plugins: [pinia],
        stubs: {
          SkeletonTable: true,
          ErrorState: true,
        },
      },
    })
    return wrapper
  }

  it('renders driver manifest header and run details', async () => {
    const w = createWrapper()
    await flushPromises()

    expect(w.text()).toContain('Driver Delivery Manifest')
    expect(w.text()).toContain('RUN-2026-005')
    expect(w.text()).toContain('Downtown East Zone Route')
    expect(w.text()).toContain('Carlos Driver')
    expect(w.text()).toContain('TRK-02')
    expect(w.text()).toContain('In Transit')
  })

  it('renders sequential daily drop-offs with customer contact and address details', async () => {
    const w = createWrapper()
    await flushPromises()

    expect(w.text()).toContain('STOP #1')
    expect(w.text()).toContain('Eastside Bistro')
    expect(w.text()).toContain('789 Main St, Eastside')
    expect(w.text()).toContain('+1-555-0199')
    expect(w.text()).toContain('Ring doorbell at rear loading dock')

    expect(w.text()).toContain('STOP #2')
    expect(w.text()).toContain('Grand Hotel & Suites')
    expect(w.text()).toContain('100 Hotel Blvd')
    expect(w.text()).toContain('+1-555-0200')
  })

  it('allows driver to update stop status', async () => {
    const w = createWrapper()
    await flushPromises()

    const selects = w.findAll('.stop-status-actions select')
    expect(selects.length).toBe(2)
    await selects[0].setValue('Delivered')
    await selects[0].trigger('change')
    await flushPromises()

    expect(api.put).toHaveBeenCalledWith(
      expect.stringContaining('/stops/501/status?status=Delivered')
    )
    expect(mockToast).toHaveBeenCalledWith('Stop #1 status updated to Delivered')
  })

  it('triggers window.print when print button clicked', async () => {
    const spyPrint = vi.spyOn(window, 'print').mockImplementation(() => {})
    const w = createWrapper()
    await flushPromises()

    const printBtn = w.find('.header-bar .btn-secondary')
    await printBtn.trigger('click')

    expect(spyPrint).toHaveBeenCalled()
    spyPrint.mockRestore()
  })
})
