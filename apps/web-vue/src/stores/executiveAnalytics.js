import { defineStore } from 'pinia'
import { api } from '../api/client.js'

/**
 * Format a Date object as YYYY-MM-DD in local time
 * @param {Date} date
 * @returns {string}
 */
function formatDate(date) {
  if (!date || isNaN(date.getTime())) return ''
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}

/**
 * Calculate standard preset date ranges
 * @param {string} preset
 * @returns {{ dateFrom: string, dateTo: string, period: string }}
 */
function calculateDateRange(preset) {
  const now = new Date()
  const today = formatDate(now)

  switch (preset) {
    case 'Today':
    case 'Daily':
      return { dateFrom: today, dateTo: today, period: 'Daily' }

    case 'This Week':
    case 'Weekly': {
      const dayOfWeek = now.getDay()
      const diffToMonday = (dayOfWeek + 6) % 7
      const monday = new Date(now)
      monday.setDate(now.getDate() - diffToMonday)
      return { dateFrom: formatDate(monday), dateTo: today, period: 'Weekly' }
    }

    case 'This Month':
    case 'Monthly': {
      const firstDay = new Date(now.getFullYear(), now.getMonth(), 1)
      return { dateFrom: formatDate(firstDay), dateTo: today, period: 'Monthly' }
    }

    case 'Last Month': {
      const firstDayLastMonth = new Date(now.getFullYear(), now.getMonth() - 1, 1)
      const lastDayLastMonth = new Date(now.getFullYear(), now.getMonth(), 0)
      return {
        dateFrom: formatDate(firstDayLastMonth),
        dateTo: formatDate(lastDayLastMonth),
        period: 'Monthly',
      }
    }

    case 'QTD':
    case 'Quarterly': {
      const currentQuarterMonth = Math.floor(now.getMonth() / 3) * 3
      const firstDayQuarter = new Date(now.getFullYear(), currentQuarterMonth, 1)
      return { dateFrom: formatDate(firstDayQuarter), dateTo: today, period: 'Quarterly' }
    }

    case 'YTD': {
      const firstDayYear = new Date(now.getFullYear(), 0, 1)
      return { dateFrom: formatDate(firstDayYear), dateTo: today, period: 'YTD' }
    }

    default:
      return { dateFrom: '', dateTo: '', period: preset || 'Monthly' }
  }
}

/**
 * Trigger browser file download from Blob or binary buffer
 * @param {Blob|ArrayBuffer} data
 * @param {string} filename
 * @param {string} mimeType
 */
function downloadFile(data, filename, mimeType) {
  const blob = data instanceof Blob ? data : new Blob([data], { type: mimeType })
  const url = window.URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.setAttribute('download', filename)
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  window.URL.revokeObjectURL(url)
}

export const useExecutiveAnalyticsStore = defineStore('executiveAnalytics', {
  state: () => {
    const defaultRange = calculateDateRange('This Month')
    return {
      // Filter state
      filters: {
        preset: 'This Month',
        period: 'Monthly',
        dateFrom: defaultRange.dateFrom,
        dateTo: defaultRange.dateTo,
        categoryId: null,
        productId: null,
        brand: null,
        salesRepId: null,
        customerId: null,
        warehouseId: null,
        deliveryRoute: null,
        quadrant: null,
        minMarginPct: null,
        maxMarginPct: null,
        marginThresholdPct: 15.0,
      },

      // Data state
      summary: null,
      categoryMargins: {
        items: [],
        total_categories: 0,
        total_gross_sales: 0,
        total_gross_profit: 0,
        overall_gross_margin_pct: 0,
        low_margin_count: 0,
      },
      skuMargins: {
        items: [],
        total: 0,
        limit: 50,
        offset: 0,
      },
      trends: {
        period_type: 'Monthly',
        periods: [],
      },
      lowMarginAlerts: {
        count: 0,
        threshold_pct: 15.0,
        categories: [],
        skus: [],
      },
      customerMatrix: {
        summary: {},
        quadrants: {},
        items: [],
        total_customers: 0,
      },
      topCustomers: [],
      unprofitableCustomers: [],
      selectedCustomerDetails: null,
      quadrantPlaybook: null,
      deliverySummary: null,
      warehouseEfficiency: [],
      customerDestinations: [],
      deliveryVariances: [],
      deliveryGauges: null,
      commissionSummaries: [],
      selectedCommissionStatement: null,
      commissionRules: [],
      commissionPayouts: [],

      // Async status
      loading: false,
      loadingTable: false,
      exporting: false,
      error: null,
    }
  },

  getters: {
    // Executive Margin Metrics
    grossSales: (state) => state.summary?.gross_sales ?? 0,
    discountAmount: (state) => state.summary?.discount_amount ?? 0,
    netRevenue: (state) => state.summary?.net_revenue ?? 0,
    cogs: (state) => state.summary?.cogs ?? 0,
    freightCost: (state) => state.summary?.freight_cost ?? 0,
    grossProfit: (state) => state.summary?.gross_profit ?? 0,
    grossMarginPct: (state) => state.summary?.gross_margin_pct ?? 0,
    totalOrders: (state) => state.summary?.total_orders ?? 0,
    priorPeriodGrowthPct: (state) => state.summary?.prior_period_growth?.margin_pct_growth ?? 0,

    // Status helpers
    isLowMargin: (state) => (marginPct) =>
      marginPct !== null && marginPct !== undefined && marginPct < state.filters.marginThresholdPct,

    // Quadrant counts
    quadrantCounts: (state) => {
      const q = state.customerMatrix?.quadrants || {}
      return {
        Q1: q.Q1?.customer_count ?? 0,
        Q2: q.Q2?.customer_count ?? 0,
        Q3: q.Q3?.customer_count ?? 0,
        Q4: q.Q4?.customer_count ?? 0,
      }
    },

    // Route Delivery Performance
    onTimeDeliveryRate: (state) => state.deliverySummary?.overall_on_time_rate_pct ?? 0,
    routeCompletionRate: (state) => state.deliverySummary?.route_completion_rate_pct ?? 0,
    totalDeliveries: (state) => state.deliverySummary?.total_deliveries ?? 0,
    delayedDeliveries: (state) => state.deliverySummary?.delayed_deliveries ?? 0,
  },

  actions: {
    // -------------------------------------------------------------------------
    // Filter Management
    // -------------------------------------------------------------------------

    /**
     * Set date preset filter (e.g., 'This Month', 'Last Month', 'QTD', 'YTD', 'Custom')
     */
    setPeriodPreset(preset) {
      this.filters.preset = preset
      if (preset !== 'Custom') {
        const range = calculateDateRange(preset)
        this.filters.dateFrom = range.dateFrom
        this.filters.dateTo = range.dateTo
        this.filters.period = range.period
      } else {
        this.filters.period = 'Custom'
      }
    },

    /**
     * Set custom date range
     */
    setDateRange(dateFrom, dateTo) {
      this.filters.preset = 'Custom'
      this.filters.period = 'Custom'
      this.filters.dateFrom = dateFrom
      this.filters.dateTo = dateTo
    },

    /**
     * Update partial filter parameters
     */
    setFilters(partialFilters) {
      this.filters = { ...this.filters, ...partialFilters }
    },

    /**
     * Reset filters to initial defaults
     */
    resetFilters() {
      const defaultRange = calculateDateRange('This Month')
      this.filters = {
        preset: 'This Month',
        period: 'Monthly',
        dateFrom: defaultRange.dateFrom,
        dateTo: defaultRange.dateTo,
        categoryId: null,
        productId: null,
        brand: null,
        salesRepId: null,
        customerId: null,
        warehouseId: null,
        deliveryRoute: null,
        quadrant: null,
        minMarginPct: null,
        maxMarginPct: null,
        marginThresholdPct: 15.0,
      }
    },

    /**
     * Internal helper to build clean query parameter dictionary
     */
    _buildFilterParams(overrides = {}) {
      const params = {}
      const src = { ...this.filters, ...overrides }

      if (src.period) params.period = src.period
      if (src.dateFrom) params.date_from = src.dateFrom
      if (src.dateTo) params.date_to = src.dateTo
      if (src.categoryId) params.category_id = src.categoryId
      if (src.productId) params.product_id = src.productId
      if (src.brand) params.brand = src.brand
      if (src.salesRepId) params.sales_rep_id = src.salesRepId
      if (src.customerId) params.customer_id = src.customerId
      if (src.warehouseId) params.warehouse_id = src.warehouseId
      if (src.deliveryRoute) params.delivery_route = src.deliveryRoute
      if (src.quadrant) params.quadrant = src.quadrant
      if (src.minMarginPct !== null && src.minMarginPct !== undefined) params.min_margin_pct = src.minMarginPct
      if (src.maxMarginPct !== null && src.maxMarginPct !== undefined) params.max_margin_pct = src.maxMarginPct

      return params
    },

    // -------------------------------------------------------------------------
    // API Data Fetching Actions
    // -------------------------------------------------------------------------

    /**
     * Fetch executive gross margin KPI summary
     */
    async fetchSummary() {
      try {
        const res = await api.get('/bi/executive/summary', {
          params: this._buildFilterParams(),
        })
        this.summary = res.data
        return res.data
      } catch (err) {
        console.error('Failed to fetch executive margin summary:', err)
        this.error = err.message || 'Failed to fetch margin summary'
        throw err
      }
    },

    /**
     * Fetch category margin breakdown
     */
    async fetchCategoryMargins() {
      try {
        const res = await api.get('/bi/executive/categories', {
          params: this._buildFilterParams(),
        })
        this.categoryMargins = res.data || {
          items: [],
          total_categories: 0,
          total_gross_sales: 0,
          total_gross_profit: 0,
          overall_gross_margin_pct: 0,
          low_margin_count: 0,
        }
        return res.data
      } catch (err) {
        console.error('Failed to fetch category margins:', err)
        throw err
      }
    },

    /**
     * Fetch SKU margin line items with pagination
     */
    async fetchSkuMargins(options = {}) {
      this.loadingTable = true
      try {
        const params = this._buildFilterParams({
          limit: options.limit || this.skuMargins.limit || 50,
          offset: options.offset !== undefined ? options.offset : this.skuMargins.offset || 0,
          ...options,
        })
        if (options.limit) params.limit = options.limit
        if (options.offset !== undefined) params.offset = options.offset

        const res = await api.get('/bi/executive/skus', { params })
        this.skuMargins = res.data || { items: [], total: 0, limit: 50, offset: 0 }
        return res.data
      } catch (err) {
        console.error('Failed to fetch SKU margins:', err)
        throw err
      } finally {
        this.loadingTable = false
      }
    },

    /**
     * Fetch period margin trends for charting
     */
    async fetchTrends(periodType = 'Monthly', periodsCount = 12) {
      try {
        const params = this._buildFilterParams()
        params.period_type = periodType
        params.periods_count = periodsCount
        const res = await api.get('/bi/executive/trends', { params })
        this.trends = res.data || { period_type: periodType, periods: [] }
        return res.data
      } catch (err) {
        console.error('Failed to fetch margin trends:', err)
        throw err
      }
    },

    /**
     * Fetch low margin alerts
     */
    async fetchLowMarginAlerts(thresholdPct = 15.0) {
      try {
        const params = this._buildFilterParams()
        params.threshold_pct = thresholdPct
        const res = await api.get('/bi/executive/alerts', { params })
        this.lowMarginAlerts = res.data || { count: 0, threshold_pct: thresholdPct, categories: [], skus: [] }
        return res.data
      } catch (err) {
        console.error('Failed to fetch low margin alerts:', err)
        throw err
      }
    },

    /**
     * Fetch 4-quadrant customer profitability matrix
     */
    async fetchCustomerMatrix(quadrant = null, marginThresholdPct = null) {
      try {
        const params = this._buildFilterParams()
        if (quadrant) params.quadrant = quadrant
        if (marginThresholdPct !== null) params.margin_threshold_pct = marginThresholdPct
        else if (this.filters.marginThresholdPct) params.margin_threshold_pct = this.filters.marginThresholdPct

        const res = await api.get('/bi/executive/customer-matrix', { params })
        this.customerMatrix = res.data || { summary: {}, quadrants: {}, items: [], total_customers: 0 }
        return res.data
      } catch (err) {
        console.error('Failed to fetch customer profitability matrix:', err)
        throw err
      }
    },

    /**
     * Fetch top profitable customers ranking
     */
    async fetchTopCustomers(limit = 10) {
      try {
        const params = this._buildFilterParams()
        params.limit = limit
        const res = await api.get('/bi/executive/customers/top', { params })
        this.topCustomers = res.data || []
        return res.data
      } catch (err) {
        console.error('Failed to fetch top customers:', err)
        throw err
      }
    },

    /**
     * Fetch lowest-margin / unprofitable customer accounts
     */
    async fetchUnprofitableCustomers(limit = 10, thresholdPct = 10.0) {
      try {
        const params = this._buildFilterParams()
        params.limit = limit
        params.threshold_pct = thresholdPct
        const res = await api.get('/bi/executive/customers/unprofitable', { params })
        this.unprofitableCustomers = res.data || []
        return res.data
      } catch (err) {
        console.error('Failed to fetch unprofitable customers:', err)
        throw err
      }
    },

    /**
     * Fetch individual customer profitability profile & details
     */
    async fetchCustomerDetails(customerId) {
      try {
        const params = this._buildFilterParams()
        const res = await api.get(`/bi/executive/customers/${customerId}`, { params })
        this.selectedCustomerDetails = res.data
        return res.data
      } catch (err) {
        console.error(`Failed to fetch details for customer #${customerId}:`, err)
        throw err
      }
    },

    /**
     * Fetch quadrant strategic playbook guidelines
     */
    async fetchQuadrantPlaybook(quadrantCode) {
      try {
        const res = await api.get(`/bi/executive/quadrants/${quadrantCode}/playbook`)
        this.quadrantPlaybook = res.data
        return res.data
      } catch (err) {
        console.error(`Failed to fetch playbook for quadrant ${quadrantCode}:`, err)
        throw err
      }
    },

    /**
     * Fetch delivery route fulfillment and efficiency summary
     */
    async fetchDeliverySummary() {
      try {
        const res = await api.get('/bi/executive/delivery/summary', {
          params: this._buildFilterParams(),
        })
        this.deliverySummary = res.data
        return res.data
      } catch (err) {
        console.error('Failed to fetch delivery fulfillment summary:', err)
        throw err
      }
    },

    /**
     * Fetch warehouse dispatch efficiency breakdown
     */
    async fetchWarehouseEfficiency() {
      try {
        const res = await api.get('/bi/executive/delivery/warehouses', {
          params: this._buildFilterParams(),
        })
        this.warehouseEfficiency = res.data || []
        return res.data
      } catch (err) {
        console.error('Failed to fetch warehouse delivery efficiency:', err)
        throw err
      }
    },

    /**
     * Fetch delivery metrics by customer destination
     */
    async fetchCustomerDestinations(limit = 50) {
      try {
        const params = this._buildFilterParams()
        params.limit = limit
        const res = await api.get('/bi/executive/delivery/destinations', { params })
        this.customerDestinations = res.data || []
        return res.data
      } catch (err) {
        console.error('Failed to fetch customer destinations:', err)
        throw err
      }
    },

    /**
     * Fetch line items with delivery quantity variances
     */
    async fetchDeliveryVariances(limit = 100) {
      try {
        const params = this._buildFilterParams()
        params.limit = limit
        const res = await api.get('/bi/executive/delivery/variances', { params })
        this.deliveryVariances = res.data || []
        return res.data
      } catch (err) {
        console.error('Failed to fetch delivery variances:', err)
        throw err
      }
    },

    /**
     * Fetch delivery target gauges
     */
    async fetchDeliveryGauges() {
      try {
        const res = await api.get('/bi/executive/delivery/gauges', {
          params: this._buildFilterParams(),
        })
        this.deliveryGauges = res.data
        return res.data
      } catch (err) {
        console.error('Failed to fetch delivery KPI gauges:', err)
        throw err
      }
    },

    /**
     * Fetch sales representative commission summary balances
     */
    async fetchCommissionSummaries(salesRepId = null) {
      try {
        const params = {}
        if (this.filters.dateFrom) params.period_start = this.filters.dateFrom
        if (this.filters.dateTo) params.period_end = this.filters.dateTo
        if (salesRepId || this.filters.salesRepId) {
          params.sales_rep_id = salesRepId || this.filters.salesRepId
        }

        const res = await api.get('/sales/commission/summaries', { params })
        this.commissionSummaries = res.data || []
        return res.data
      } catch (err) {
        console.error('Failed to fetch commission summaries:', err)
        throw err
      }
    },

    /**
     * Fetch detailed sales rep commission statement
     */
    async fetchCommissionStatement(salesRepId, ruleId = null, includePending = true) {
      try {
        const params = { sales_rep_id: salesRepId, include_pending: includePending }
        if (this.filters.dateFrom) params.period_start = this.filters.dateFrom
        if (this.filters.dateTo) params.period_end = this.filters.dateTo
        if (ruleId) params.rule_id = ruleId

        const res = await api.get('/sales/commission/statement', { params })
        this.selectedCommissionStatement = res.data
        return res.data
      } catch (err) {
        console.error(`Failed to fetch commission statement for rep #${salesRepId}:`, err)
        throw err
      }
    },

    /**
     * Fetch commission configuration rules
     */
    async fetchCommissionRules(salesRepId = null, isActive = true) {
      try {
        const params = { limit: 100, offset: 0 }
        if (salesRepId) params.sales_rep_id = salesRepId
        if (isActive !== null) params.is_active = isActive

        const res = await api.get('/sales/commission/rules', { params })
        this.commissionRules = res.data?.items || []
        return res.data
      } catch (err) {
        console.error('Failed to fetch commission rules:', err)
        throw err
      }
    },

    /**
     * Fetch commission payout records
     */
    async fetchCommissionPayouts(salesRepId = null, status = null) {
      try {
        const params = { limit: 100, offset: 0 }
        if (salesRepId) params.sales_rep_id = salesRepId
        if (status) params.status = status

        const res = await api.get('/sales/commission/payouts', { params })
        this.commissionPayouts = res.data?.items || []
        return res.data
      } catch (err) {
        console.error('Failed to fetch commission payouts:', err)
        throw err
      }
    },

    /**
     * Load all primary executive analytics dashboard modules in parallel
     */
    async loadAllExecutiveData() {
      this.loading = true
      this.error = null
      try {
        await Promise.allSettled([
          this.fetchSummary(),
          this.fetchCategoryMargins(),
          this.fetchCustomerMatrix(),
          this.fetchTrends(),
          this.fetchDeliverySummary(),
          this.fetchCommissionSummaries(),
          this.fetchLowMarginAlerts(),
        ])
      } catch (err) {
        console.error('Failed to load full executive dashboard:', err)
        this.error = err.message || 'Failed to load executive dashboard data'
      } finally {
        this.loading = false
      }
    },

    // -------------------------------------------------------------------------
    // Report Export Triggers (PDF, Excel, CSV)
    // -------------------------------------------------------------------------

    /**
     * Trigger PDF Financial Review Report Download
     */
    async exportPdf(confidentialityNotice = 'CONFIDENTIAL — BOARD & BANK REVIEW ONLY') {
      this.exporting = true
      try {
        const params = this._buildFilterParams()
        if (confidentialityNotice) params.confidentiality_notice = confidentialityNotice

        const res = await api.get('/bi/executive/export/pdf', {
          params,
          responseType: 'blob',
        })
        const timestamp = new Date().toISOString().slice(0, 10)
        const filename = `Nova_Executive_Margin_Report_${timestamp}.pdf`
        downloadFile(res.data, filename, 'application/pdf')
        return true
      } catch (err) {
        console.error('Failed to export executive PDF report:', err)
        throw err
      } finally {
        this.exporting = false
      }
    },

    /**
     * Trigger Multi-Tab Excel Financial Model Download
     */
    async exportExcel(confidentialityNotice = 'CONFIDENTIAL - BOARD & EXECUTIVE REVIEW ONLY') {
      this.exporting = true
      try {
        const params = this._buildFilterParams()
        if (confidentialityNotice) params.confidentiality_notice = confidentialityNotice

        const res = await api.get('/bi/executive/export/excel', {
          params,
          responseType: 'blob',
        })
        const timestamp = new Date().toISOString().slice(0, 10)
        const filename = `Nova_Executive_Financial_Model_${timestamp}.xlsx`
        downloadFile(
          res.data,
          filename,
          'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        return true
      } catch (err) {
        console.error('Failed to export executive Excel report:', err)
        throw err
      } finally {
        this.exporting = false
      }
    },

    /**
     * Trigger CSV Category Margin Summary Download
     */
    async exportCsv() {
      this.exporting = true
      try {
        const params = this._buildFilterParams()
        const res = await api.get('/bi/executive/export/csv', {
          params,
          responseType: 'blob',
        })
        const timestamp = new Date().toISOString().slice(0, 10)
        const filename = `Nova_Executive_Category_Margins_${timestamp}.csv`
        downloadFile(res.data, filename, 'text/csv')
        return true
      } catch (err) {
        console.error('Failed to export category margin CSV:', err)
        throw err
      } finally {
        this.exporting = false
      }
    },
  },
})
