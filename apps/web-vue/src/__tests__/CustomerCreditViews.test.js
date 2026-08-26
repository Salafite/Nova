import { mount, flushPromises } from '@vue/test-utils'
import { vi, describe, it, expect, beforeEach, afterEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import CustomersView from '../views/customers/CustomersView.vue'
import CustomerDetailView from '../views/customers/CustomerDetailView.vue'
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
let currentRouteId = 1
vi.mock('vue-router', () => ({
  useRouter: () => ({ push: mockPush }),
  useRoute: () => ({ params: { id: currentRouteId } }),
}))

// Mock useToast
const mockToast = vi.fn()
vi.mock('../composables/useToast.js', () => ({
  useToast: () => ({ show: mockToast }),
}))

describe('CustomersView & CustomerDetailView (Credit Limits & Delinquent Indicators)', () => {
  let pinia

  const sampleCustomers = [
    {
      id: 1,
      name: 'Acme Corp',
      group_name: 'Corporate',
      phone: '555-0100',
      email: 'acme@example.com',
      credit_limit: 10000.0,
      balance: 2000.0,
      is_active: true,
    },
    {
      id: 2,
      name: 'High Utilization Inc',
      group_name: 'Wholesale',
      phone: '555-0200',
      email: 'high@example.com',
      credit_limit: 10000.0,
      balance: 8500.0,
      is_active: true,
    },
    {
      id: 3,
      name: 'Delinquent Trader Ltd',
      group_name: 'Retail',
      phone: '555-0300',
      email: 'delinquent@example.com',
      credit_limit: 5000.0,
      balance: 6500.0,
      is_active: true,
    },
    {
      id: 4,
      name: 'Cash Only Store',
      group_name: 'Retail',
      phone: '555-0400',
      email: 'cash@example.com',
      credit_limit: 0.0,
      balance: 0.0,
      is_active: true,
    },
  ]

  const customer1CreditStatus = {
    customer_id: 1,
    customer_name: 'Acme Corp',
    credit_limit: 10000.0,
    balance: 2000.0,
    available_credit: 8000.0,
    raw_available_credit: 8000.0,
    credit_limit_exceeded: false,
    is_credit_limit_enforced: true,
    overdue_invoices_count: 0,
    overdue_invoices_amount: 0.0,
    has_overdue_invoices: false,
    overdue_invoices: [],
    is_delinquent: false,
    on_hold: false,
    has_hold_orders: false,
    hold_orders_count: 0,
    hold_reasons: [],
  }

  const customer3DelinquentStatus = {
    customer_id: 3,
    customer_name: 'Delinquent Trader Ltd',
    credit_limit: 5000.0,
    balance: 6500.0,
    available_credit: 0.0,
    raw_available_credit: -1500.0,
    credit_limit_exceeded: true,
    is_credit_limit_enforced: true,
    overdue_invoices_count: 2,
    overdue_invoices_amount: 4000.0,
    has_overdue_invoices: true,
    overdue_invoices: [
      {
        id: 101,
        invoice_number: 'INV-101',
        issue_date: '2026-06-01',
        due_date: '2026-07-01',
        total_amount: 2500.0,
        days_overdue: 55,
        status: 'Unpaid',
      },
      {
        id: 102,
        invoice_number: 'INV-102',
        issue_date: '2026-06-15',
        due_date: '2026-07-15',
        total_amount: 1500.0,
        days_overdue: 41,
        status: 'Unpaid',
      },
    ],
    is_delinquent: true,
    on_hold: true,
    has_hold_orders: true,
    hold_orders_count: 2,
    hold_reasons: [
      'Customer credit limit exceeded: Balance $6,500.00 > Limit $5,000.00',
      'Customer has 2 invoices overdue by >30 days (total overdue: $4,000.00)',
    ],
  }

  const sampleAging = {
    customer_id: 1,
    customer_name: 'Acme Corp',
    balance: 2000.0,
    aging: {
      current: 1500.0,
      '30': 500.0,
      '60': 0.0,
      '90_plus': 0.0,
      total_outstanding: 2000.0,
      total_paid: 10000.0,
    },
  }

  const sampleInvoices = [
    {
      id: 10,
      invoice_number: 'INV-2026-001',
      partner_id: 1,
      issue_date: '2026-08-01',
      due_date: '2026-08-31',
      total_amount: 1500.0,
      status: 'Unpaid',
    },
    {
      id: 11,
      invoice_number: 'INV-2026-002',
      partner_id: 1,
      issue_date: '2026-07-01',
      due_date: '2026-07-31',
      total_amount: 500.0,
      status: 'Unpaid',
    },
  ]

  const samplePayments = [
    {
      id: 20,
      payment_date: '2026-08-10',
      partner_id: 1,
      amount: 3000.0,
      payment_method: 'Bank Transfer',
      reference: 'TXN-9988',
      status: 'Completed',
    },
  ]

  beforeEach(() => {
    pinia = createPinia()
    setActivePinia(pinia)
    vi.clearAllMocks()

    api.get.mockImplementation((url) => {
      if (url === '/T0010I/') {
        return Promise.resolve({ data: JSON.parse(JSON.stringify(sampleCustomers)) })
      }
      if (url === '/T0010I/1') {
        return Promise.resolve({ data: JSON.parse(JSON.stringify(sampleCustomers[0])) })
      }
      if (url === '/T0010I/1/credit-status') {
        return Promise.resolve({ data: JSON.parse(JSON.stringify(customer1CreditStatus)) })
      }
      if (url === '/T0010I/1/aging') {
        return Promise.resolve({ data: JSON.parse(JSON.stringify(sampleAging)) })
      }
      if (url === '/T0010I/1/invoices') {
        return Promise.resolve({ data: JSON.parse(JSON.stringify(sampleInvoices)) })
      }
      if (url === '/T0010I/1/payments') {
        return Promise.resolve({ data: JSON.parse(JSON.stringify(samplePayments)) })
      }
      if (url === '/T0010I/3') {
        return Promise.resolve({ data: JSON.parse(JSON.stringify(sampleCustomers[2])) })
      }
      if (url === '/T0010I/3/credit-status') {
        return Promise.resolve({ data: JSON.parse(JSON.stringify(customer3DelinquentStatus)) })
      }
      if (url === '/T0010I/3/aging') {
        return Promise.resolve({
          data: {
            customer_id: 3,
            customer_name: 'Delinquent Trader Ltd',
            balance: 6500.0,
            aging: {
              current: 500.0,
              '30': 2000.0,
              '60': 2500.0,
              '90_plus': 1500.0,
              total_outstanding: 6500.0,
              total_paid: 5000.0,
            },
          },
        })
      }
      if (url === '/T0010I/3/invoices') {
        return Promise.resolve({ data: JSON.parse(JSON.stringify(customer3DelinquentStatus.overdue_invoices)) })
      }
      if (url === '/T0010I/3/payments') {
        return Promise.resolve({ data: [] })
      }
      return Promise.resolve({ data: [] })
    })
  })

  describe('CustomersView', () => {
    it('renders customer list with credit utilization, over-limit count, and status badges', async () => {
      const wrapper = mount(CustomersView, {
        global: {
          plugins: [pinia],
          stubs: {
            SkeletonTable: true,
            ErrorState: true,
            ConfirmDialog: true,
          },
        },
      })

      await flushPromises()

      // Customer rows rendered
      expect(wrapper.text()).toContain('Acme Corp')
      expect(wrapper.text()).toContain('High Utilization Inc')
      expect(wrapper.text()).toContain('Delinquent Trader Ltd')
      expect(wrapper.text()).toContain('Cash Only Store')

      // Over limit stat count (Delinquent Trader Ltd balance $6500 > limit $5000)
      const overLimitStat = wrapper.find('.stat-card-risk')
      expect(overLimitStat.exists()).toBe(true)
      expect(overLimitStat.text()).toContain('1')

      // Credit utilization percentages
      expect(wrapper.text()).toContain('20%')
      expect(wrapper.text()).toContain('85%')
      expect(wrapper.text()).toContain('130%')
      expect(wrapper.text()).toContain('Over Limit')
      expect(wrapper.text()).toContain('Near Limit')
    })

    it('filters customers by credit status dropdown', async () => {
      const wrapper = mount(CustomersView, {
        global: {
          plugins: [pinia],
          stubs: {
            SkeletonTable: true,
            ErrorState: true,
            ConfirmDialog: true,
          },
        },
      })

      await flushPromises()

      // Select 'over-limit'
      const creditSelect = wrapper.findAll('select')[1]
      await creditSelect.setValue('over-limit')
      await flushPromises()

      expect(wrapper.text()).toContain('Delinquent Trader Ltd')
      expect(wrapper.text()).not.toContain('Acme Corp')
      expect(wrapper.text()).not.toContain('High Utilization Inc')
      expect(wrapper.text()).not.toContain('Cash Only Store')

      // Select 'near-limit'
      await creditSelect.setValue('near-limit')
      await flushPromises()

      expect(wrapper.text()).toContain('High Utilization Inc')
      expect(wrapper.text()).not.toContain('Acme Corp')
      expect(wrapper.text()).not.toContain('Delinquent Trader Ltd')

      // Select 'unlimited'
      await creditSelect.setValue('unlimited')
      await flushPromises()

      expect(wrapper.text()).toContain('Cash Only Store')
      expect(wrapper.text()).not.toContain('Acme Corp')
    })
  })

  describe('CustomerDetailView', () => {
    it('renders customer credit standing, utilization bar, and aging for healthy account', async () => {
      const wrapper = mount(CustomerDetailView, {
        global: {
          plugins: [pinia],
          stubs: {
            SkeletonCard: true,
            ErrorState: true,
          },
        },
      })

      await flushPromises()

      expect(api.get).toHaveBeenCalledWith('/T0010I/1')
      expect(api.get).toHaveBeenCalledWith('/T0010I/1/credit-status')
      expect(api.get).toHaveBeenCalledWith('/T0010I/1/aging')

      expect(wrapper.text()).toContain('Acme Corp')
      expect(wrapper.text()).toContain('Good Standing')
      expect(wrapper.text()).toContain('$10,000.00')
      expect(wrapper.text()).toContain('$2,000.00')
      expect(wrapper.text()).toContain('$8,000.00') // Available credit
      expect(wrapper.text()).toContain('20%') // Utilization
      expect(wrapper.find('.delinquent-banner').exists()).toBe(false)
    })

    it('renders delinquent alert banner, overdue invoices, and hold orders notice for delinquent account', async () => {
      currentRouteId = 3
      const wrapper = mount(CustomerDetailView, {
        global: {
          plugins: [pinia],
          stubs: {
            SkeletonCard: true,
            ErrorState: true,
          },
        },
      })

      await flushPromises()

      expect(api.get).toHaveBeenCalledWith('/T0010I/3')
      expect(api.get).toHaveBeenCalledWith('/T0010I/3/credit-status')

      expect(wrapper.text()).toContain('Delinquent Trader Ltd')
      expect(wrapper.text()).toContain('Financial Hold')
      
      // Delinquent banner rendered with hold reasons
      const banner = wrapper.find('.delinquent-banner')
      expect(banner.exists()).toBe(true)
      expect(banner.text()).toContain('Delinquent Account & Credit Hold Notice')
      expect(banner.text()).toContain('Customer credit limit exceeded')
      expect(banner.text()).toContain('Customer has 2 invoices overdue by >30 days')
      expect(banner.text()).toContain('2 active sales order(s) currently held')

      // Utilization 130% Exceeded
      expect(wrapper.text()).toContain('130%')
      expect(wrapper.text()).toContain('Exceeded')

      // Overdue invoices tab badges
      expect(wrapper.text()).toContain('>30d Overdue')
      expect(wrapper.text()).toContain('INV-101')
      expect(wrapper.text()).toContain('INV-102')
    })
  })
})
