import { setActivePinia, createPinia } from 'pinia'
import { useExecutiveAnalyticsStore } from '../stores/executiveAnalytics.js'
import { api } from '../api/client.js'
import { vi, describe, it, expect, beforeEach } from 'vitest'

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

describe('executiveAnalytics store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
    // Mock window.URL createObjectURL and revokeObjectURL
    if (typeof window !== 'undefined') {
      window.URL.createObjectURL = vi.fn(() => 'blob:mock-url')
      window.URL.revokeObjectURL = vi.fn()
    }
  })

  it('initializes with default date presets and empty data state', () => {
    const store = useExecutiveAnalyticsStore()
    expect(store.filters.preset).toBe('This Month')
    expect(store.filters.period).toBe('Monthly')
    expect(store.filters.marginThresholdPct).toBe(15.0)
    expect(store.summary).toBeNull()
    expect(store.categoryMargins.items).toEqual([])
    expect(store.skuMargins.items).toEqual([])
    expect(store.loading).toBe(false)
  })

  it('setPeriodPreset updates date range and period', () => {
    const store = useExecutiveAnalyticsStore()
    store.setPeriodPreset('YTD')
    expect(store.filters.preset).toBe('YTD')
    expect(store.filters.period).toBe('YTD')
    expect(store.filters.dateFrom).toMatch(/^\d{4}-01-01$/)

    store.setPeriodPreset('Today')
    expect(store.filters.preset).toBe('Today')
    expect(store.filters.period).toBe('Daily')
  })

  it('setDateRange sets custom dates and sets period to Custom', () => {
    const store = useExecutiveAnalyticsStore()
    store.setDateRange('2026-01-01', '2026-06-30')
    expect(store.filters.preset).toBe('Custom')
    expect(store.filters.period).toBe('Custom')
    expect(store.filters.dateFrom).toBe('2026-01-01')
    expect(store.filters.dateTo).toBe('2026-06-30')
  })

  it('fetchSummary retrieves and populates executive margin summary', async () => {
    const mockSummary = {
      gross_sales: 100000.0,
      discount_amount: 5000.0,
      net_revenue: 95000.0,
      cogs: 60000.0,
      freight_cost: 3000.0,
      gross_profit: 32000.0,
      gross_margin_pct: 33.68,
      total_orders: 140,
    }
    api.get.mockResolvedValue({ data: mockSummary })
    const store = useExecutiveAnalyticsStore()

    const result = await store.fetchSummary()
    expect(api.get).toHaveBeenCalledWith('/bi/executive/summary', expect.any(Object))
    expect(result).toEqual(mockSummary)
    expect(store.summary).toEqual(mockSummary)
    expect(store.grossProfit).toBe(32000.0)
    expect(store.grossMarginPct).toBe(33.68)
    expect(store.netRevenue).toBe(95000.0)
  })

  it('fetchCategoryMargins retrieves category breakdown', async () => {
    const mockCategories = {
      items: [{ category_name: 'Bakery', gross_profit: 15000, gross_margin_pct: 25.0 }],
      total_categories: 1,
      total_gross_sales: 60000,
    }
    api.get.mockResolvedValue({ data: mockCategories })
    const store = useExecutiveAnalyticsStore()

    const result = await store.fetchCategoryMargins()
    expect(api.get).toHaveBeenCalledWith('/bi/executive/categories', expect.any(Object))
    expect(result).toEqual(mockCategories)
    expect(store.categoryMargins.items.length).toBe(1)
  })

  it('fetchCustomerMatrix retrieves quadrant matrix data', async () => {
    const mockMatrix = {
      summary: { total_customers: 20 },
      quadrants: {
        Q1: { quadrant_name: 'Core Stars', customer_count: 8 },
        Q2: { quadrant_name: 'Volume Risks', customer_count: 4 },
        Q3: { quadrant_name: 'High Potential', customer_count: 5 },
        Q4: { quadrant_name: 'Unprofitable', customer_count: 3 },
      },
      items: [],
    }
    api.get.mockResolvedValue({ data: mockMatrix })
    const store = useExecutiveAnalyticsStore()

    await store.fetchCustomerMatrix()
    expect(api.get).toHaveBeenCalledWith('/bi/executive/customer-matrix', expect.any(Object))
    expect(store.quadrantCounts.Q1).toBe(8)
    expect(store.quadrantCounts.Q2).toBe(4)
    expect(store.quadrantCounts.Q4).toBe(3)
  })

  it('fetchDeliverySummary retrieves delivery fulfillment KPIs', async () => {
    const mockDelivery = {
      total_deliveries: 450,
      on_time_deliveries: 420,
      overall_on_time_rate_pct: 93.33,
      route_completion_rate_pct: 98.0,
      delayed_deliveries: 30,
    }
    api.get.mockResolvedValue({ data: mockDelivery })
    const store = useExecutiveAnalyticsStore()

    await store.fetchDeliverySummary()
    expect(api.get).toHaveBeenCalledWith('/bi/executive/delivery/summary', expect.any(Object))
    expect(store.onTimeDeliveryRate).toBe(93.33)
    expect(store.routeCompletionRate).toBe(98.0)
    expect(store.totalDeliveries).toBe(450)
  })

  it('fetchCommissionSummaries retrieves sales rep commission balances', async () => {
    const mockCommissions = [
      { sales_rep_id: 1, sales_rep_name: 'Sarah Smith', total_commission: 4200.0, paid_commission: 3000.0 },
    ]
    api.get.mockResolvedValue({ data: mockCommissions })
    const store = useExecutiveAnalyticsStore()

    await store.fetchCommissionSummaries()
    expect(api.get).toHaveBeenCalledWith('/sales/commission/summaries', expect.any(Object))
    expect(store.commissionSummaries).toEqual(mockCommissions)
  })

  it('exportPdf triggers file download stream', async () => {
    const mockBlob = new Blob(['%PDF-1.4 mock content'], { type: 'application/pdf' })
    api.get.mockResolvedValue({ data: mockBlob })
    const store = useExecutiveAnalyticsStore()

    const res = await store.exportPdf()
    expect(api.get).toHaveBeenCalledWith('/bi/executive/export/pdf', {
      params: expect.objectContaining({
        confidentiality_notice: 'CONFIDENTIAL — BOARD & BANK REVIEW ONLY',
      }),
      responseType: 'blob',
    })
    expect(res).toBe(true)
    expect(store.exporting).toBe(false)
  })

  it('exportExcel triggers Excel download stream', async () => {
    const mockBlob = new Blob(['mock excel'], { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' })
    api.get.mockResolvedValue({ data: mockBlob })
    const store = useExecutiveAnalyticsStore()

    const res = await store.exportExcel()
    expect(api.get).toHaveBeenCalledWith('/bi/executive/export/excel', {
      params: expect.objectContaining({
        confidentiality_notice: 'CONFIDENTIAL - BOARD & EXECUTIVE REVIEW ONLY',
      }),
      responseType: 'blob',
    })
    expect(res).toBe(true)
    expect(store.exporting).toBe(false)
  })
})
