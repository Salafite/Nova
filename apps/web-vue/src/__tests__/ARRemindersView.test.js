import { mount, flushPromises } from '@vue/test-utils'
import { vi, describe, it, expect, beforeEach, afterEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import ARRemindersView from '../views/accounting/ARRemindersView.vue'
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

describe('ARRemindersView (AR Collection Rules, Templates & Dispatch)', () => {
  let pinia
  let wrapper

  const sampleRules = [
    {
      id: 1,
      rule_name: '30 Days Overdue Reminder',
      description: 'First reminder with statement',
      trigger_type: 'AGING_THRESHOLD',
      threshold_days: 30,
      frequency: 'WEEKLY',
      channel: 'WHATSAPP',
      template_id: 10,
      min_balance_threshold: 100,
      attach_statement_pdf: true,
      include_payment_link: true,
      exclude_vip: true,
      is_active: true,
    },
    {
      id: 2,
      rule_name: '60 Days Escalation',
      description: 'Second reminder',
      trigger_type: 'AGING_THRESHOLD',
      threshold_days: 60,
      frequency: 'DAILY',
      channel: 'ALL',
      template_id: 11,
      min_balance_threshold: 250,
      attach_statement_pdf: true,
      include_payment_link: true,
      exclude_vip: false,
      is_active: true,
    },
  ]

  const sampleTemplates = [
    {
      id: 10,
      name: 'Standard WhatsApp Reminder',
      template_code: 'TMPL-WA-REMIND30',
      channel: 'WHATSAPP',
      subject: '',
      body_text: 'Dear {customer_name}, your balance of {overdue_amount} is overdue.',
      whatsapp_template_id: 'ar_reminder_30d',
      whatsapp_language_code: 'en_US',
      is_default: true,
      is_active: true,
    },
    {
      id: 11,
      name: 'Escalation Email Notice',
      template_code: 'TMPL-EM-OVERDUE60',
      channel: 'EMAIL',
      subject: 'URGENT: Overdue Account Notice',
      body_text: 'Dear {customer_name}, your account is 60+ days overdue.',
      whatsapp_template_id: '',
      whatsapp_language_code: 'en_US',
      is_default: false,
      is_active: true,
    },
  ]

  const sampleSummary = {
    as_of_date: '2026-09-08',
    total_customers: 25,
    overdue_customers_count: 5,
    total_balance: 15400.0,
    total_overdue: 8200.0,
    current_balance: 7200.0,
    aging_breakdown: {
      current: 7200.0,
      '1_30': 3500.0,
      '31_60': 2700.0,
      '61_90': 1200.0,
      '90_plus': 800.0,
    },
  }

  const sampleCustomers = [
    { id: 101, name: 'Bistro Deluxe', balance: 3500.0, is_vip: false },
    { id: 102, name: 'Seaside Grill', balance: 2700.0, is_vip: true },
  ]

  beforeEach(() => {
    pinia = createPinia()
    setActivePinia(pinia)
    vi.clearAllMocks()

    api.get.mockImplementation((url) => {
      if (url.includes('/accounting/reminder-rules')) {
        return Promise.resolve({ data: JSON.parse(JSON.stringify(sampleRules)) })
      }
      if (url.includes('/accounting/reminder-templates')) {
        return Promise.resolve({ data: JSON.parse(JSON.stringify(sampleTemplates)) })
      }
      if (url.includes('/accounting/reminders/summary')) {
        return Promise.resolve({ data: JSON.parse(JSON.stringify(sampleSummary)) })
      }
      if (url.includes('/T0010I/')) {
        return Promise.resolve({ data: JSON.parse(JSON.stringify(sampleCustomers)) })
      }
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
    wrapper = mount(ARRemindersView, {
      global: {
        plugins: [pinia],
      },
    })
    return wrapper
  }

  it('renders AR reminders view with summary metrics, aging breakdown, and reminder rules list', async () => {
    const w = createWrapper()
    await flushPromises()

    expect(w.text()).toContain('AR Reminders & Statement Dispatch')
    expect(w.text()).toContain('$8,200.00')
    expect(w.text()).toContain('5') // Overdue Accounts count
    expect(w.text()).toContain('30 Days Overdue Reminder')
    expect(w.text()).toContain('60 Days Escalation')
    expect(w.text()).toContain('WHATSAPP')
    expect(w.text()).toContain('Standard WhatsApp Reminder')
  })

  it('switches tabs to Message Templates and displays templates table', async () => {
    const w = createWrapper()
    await flushPromises()

    const tabs = w.findAll('.tab')
    const templatesTab = tabs[1] // Message Templates tab
    await templatesTab.trigger('click')
    await flushPromises()

    expect(w.text()).toContain('TMPL-WA-REMIND30')
    expect(w.text()).toContain('Standard WhatsApp Reminder')
    expect(w.text()).toContain('TMPL-EM-OVERDUE60')
    expect(w.text()).toContain('Escalation Email Notice')
  })

  it('opens rule creation modal and submits new rule to API', async () => {
    api.post.mockResolvedValueOnce({ data: { id: 3, rule_name: '90 Days Final Demand' } })

    const w = createWrapper()
    await flushPromises()

    // Click "New Rule" button
    const addRuleBtn = w.find('button.btn-primary')
    await addRuleBtn.trigger('click')
    await flushPromises()

    expect(w.find('.modal-overlay').exists()).toBe(true)

    // Fill rule name
    const textInputs = w.findAll('.modal-body input[type="text"]')
    await textInputs[0].setValue('90 Days Final Demand')

    // Fill threshold days
    const numInputs = w.findAll('.modal-body input[type="number"]')
    await numInputs[0].setValue(90)

    // Submit rule
    const saveBtn = w.find('.modal-actions .btn-primary')
    await saveBtn.trigger('click')
    await flushPromises()

    expect(api.post).toHaveBeenCalledWith('/accounting/reminder-rules', expect.objectContaining({
      rule_name: '90 Days Final Demand',
      threshold_days: 90,
    }))
    expect(mockToast).toHaveBeenCalledWith('Reminder rule created successfully', 'success')
  })

  it('opens template creation modal, inserts placeholder tag, and saves template', async () => {
    api.post.mockResolvedValueOnce({ data: { id: 12, name: 'Custom Final Notice' } })

    const w = createWrapper()
    await flushPromises()

    // Switch to templates tab
    const tabs = w.findAll('.tab')
    await tabs[1].trigger('click')
    await flushPromises()

    // Click "New Template" button
    const addTmplBtn = w.find('button.btn-primary')
    await addTmplBtn.trigger('click')
    await flushPromises()

    expect(w.find('.modal-overlay').exists()).toBe(true)

    // Set template name
    const nameInput = w.find('.modal-body input[type="text"]')
    await nameInput.setValue('Custom Final Notice')

    // Click placeholder chip '{balance}'
    const varChips = w.findAll('.var-chip')
    const balanceChip = varChips.find(c => c.text().includes('{balance}'))
    if (balanceChip) {
      await balanceChip.trigger('click')
    }

    // Submit template
    const saveBtn = w.find('.modal-actions .btn-primary')
    await saveBtn.trigger('click')
    await flushPromises()

    expect(api.post).toHaveBeenCalledWith('/accounting/reminder-templates', expect.objectContaining({
      name: 'Custom Final Notice',
    }))
    expect(mockToast).toHaveBeenCalledWith('Template created successfully', 'success')
  })

  it('switches to batch evaluation tab and executes batch dry run', async () => {
    const mockBatchResult = {
      total_evaluated: 25,
      total_eligible: 4,
      total_dispatched: 4,
      total_skipped_vip: 1,
      total_skipped_excluded: 0,
      dispatched_communications: [
        {
          customer_id: 101,
          customer_name: 'Bistro Deluxe',
          rule_name: '30 Days Overdue Reminder',
          channel: 'WHATSAPP',
          status: 'READY (DRY RUN)',
        },
      ],
    }
    api.post.mockResolvedValueOnce({ data: mockBatchResult })

    const w = createWrapper()
    await flushPromises()

    // Click Batch Evaluation tab
    const tabs = w.findAll('.tab')
    await tabs[2].trigger('click')
    await flushPromises()

    expect(w.text()).toContain('Run Batch Evaluation')

    // Click Run Batch
    const runBtn = w.find('.batch-container button.btn-primary')
    await runBtn.trigger('click')
    await flushPromises()

    expect(api.post).toHaveBeenCalledWith('/accounting/reminders/run-batch', expect.objectContaining({
      dry_run: true,
    }))
    expect(w.text()).toContain('Bistro Deluxe')
    expect(w.text()).toContain('30 Days Overdue Reminder')
  })

  it('switches to manual dispatch tab and dispatches on-demand reminder', async () => {
    api.post.mockResolvedValueOnce({ data: { success: true, tracking_number: 'COMM-12345' } })

    const w = createWrapper()
    await flushPromises()

    // Click Manual Dispatch tab
    const tabs = w.findAll('.tab')
    await tabs[3].trigger('click')
    await flushPromises()

    expect(w.text()).toContain('Manual Customer Reminder & Statement Dispatch')

    // Select customer
    const selectCustomer = w.find('.dispatch-container select')
    await selectCustomer.setValue(101)

    // Click Send Now
    const sendBtn = w.find('.dispatch-container button.btn-primary')
    await sendBtn.trigger('click')
    await flushPromises()

    expect(api.post).toHaveBeenCalledWith('/accounting/reminders/dispatch', expect.objectContaining({
      customer_id: 101,
      attach_statement_pdf: true,
      include_payment_link: true,
    }))
    expect(mockToast).toHaveBeenCalledWith('Reminder dispatched successfully', 'success')
  })
})
