<template>
  <div class="executive-analytics-view" :dir="dir">
    <!-- Top Header & Actions -->
    <div class="page-header">
      <div class="header-titles">
        <div class="title-row">
          <span class="material-symbols-outlined header-icon">query_stats</span>
          <div>
            <h1 class="page-title">{{ t('exec-title', 'Executive Analytics & Margin Optimization') }}</h1>
            <p class="page-subtitle">
              {{ t('exec-subtitle', 'Real-time gross margins, customer profitability matrix, collected-margin commissions, & route fulfillment') }}
            </p>
          </div>
        </div>
      </div>

      <!-- Export & Refresh Toolbar -->
      <div class="header-actions">
        <button class="btn-outline export-btn" :disabled="store.exporting" @click="handleExportPdf">
          <span class="material-symbols-outlined">picture_as_pdf</span>
          <span>{{ store.exporting ? t('exporting', 'Exporting...') : t('export-pdf', 'Export PDF') }}</span>
        </button>

        <button class="btn-outline export-btn" :disabled="store.exporting" @click="handleExportExcel">
          <span class="material-symbols-outlined">table_view</span>
          <span>{{ store.exporting ? t('exporting', 'Exporting...') : t('export-excel', 'Export Excel') }}</span>
        </button>

        <button class="btn-outline export-btn" :disabled="store.exporting" @click="handleExportCsv">
          <span class="material-symbols-outlined">download</span>
          <span>{{ t('export-csv', 'Export CSV') }}</span>
        </button>

        <button class="btn-primary refresh-btn" :disabled="store.loading" @click="refreshData">
          <span class="material-symbols-outlined" :class="{ 'spin-icon': store.loading }">refresh</span>
          <span>{{ store.loading ? t('loading', 'Loading...') : t('refresh', 'Refresh') }}</span>
        </button>
      </div>
    </div>

    <!-- Filters & Period Preset Bar -->
    <div class="filter-bar-card">
      <div class="filter-controls">
        <div class="period-presets">
          <span class="filter-label">{{ t('period', 'Period') }}:</span>
          <div class="preset-pills">
            <button
              v-for="preset in periodPresets"
              :key="preset"
              class="preset-pill"
              :class="{ active: store.filters.preset === preset }"
              @click="selectPreset(preset)"
            >
              {{ preset }}
            </button>
          </div>
        </div>

        <div v-if="store.filters.preset === 'Custom'" class="custom-dates">
          <div class="date-group">
            <label>{{ t('from', 'From') }}</label>
            <input type="date" v-model="customDateFrom" class="date-input" />
          </div>
          <div class="date-group">
            <label>{{ t('to', 'To') }}</label>
            <input type="date" v-model="customDateTo" class="date-input" />
          </div>
          <button class="btn-primary btn-sm" @click="applyCustomDates">
            {{ t('apply', 'Apply') }}
          </button>
        </div>

        <div class="threshold-control">
          <label class="filter-label">{{ t('margin-threshold', 'Target Margin') }}:</label>
          <div class="input-with-suffix">
            <input
              type="number"
              step="0.5"
              min="0"
              max="100"
              v-model.number="tempThreshold"
              @change="updateMarginThreshold"
              class="threshold-input"
            />
            <span class="suffix">%</span>
          </div>
        </div>
      </div>
    </div>

    <!-- Loading State -->
    <div v-if="store.loading && !store.summary" class="loading-container">
      <div class="skeleton-grid">
        <SkeletonCard v-for="i in 6" :key="i" variant="card" />
      </div>
      <div class="skeleton-table-wrap">
        <SkeletonTable />
      </div>
    </div>

    <!-- Error State -->
    <ErrorState v-else-if="store.error && !store.summary" :message="store.error" @retry="refreshData" />

    <!-- Main Dashboard Content -->
    <template v-else>
      <!-- Executive KPI Cards -->
      <div class="kpi-cards-grid">
        <!-- Gross Profit Margin Card -->
        <div class="kpi-card highlight-card" :class="marginHealthClass(store.grossMarginPct)">
          <div class="kpi-head">
            <span class="kpi-label">{{ t('exec-gross-margin', 'Gross Profit Margin') }}</span>
            <span class="material-symbols-outlined kpi-icon">percent</span>
          </div>
          <div class="kpi-value-row">
            <span class="kpi-value">{{ formatPercent(store.grossMarginPct) }}</span>
            <span class="kpi-status-badge" :class="marginHealthClass(store.grossMarginPct)">
              {{ store.grossMarginPct >= store.filters.marginThresholdPct ? t('healthy', 'Target Met') : t('under-target', 'Below Target') }}
            </span>
          </div>
          <div class="kpi-subtext">
            <span>{{ t('target', 'Target') }}: {{ store.filters.marginThresholdPct }}%</span>
            <span v-if="store.priorPeriodGrowthPct" class="trend-badge" :class="store.priorPeriodGrowthPct >= 0 ? 'up' : 'down'">
              {{ store.priorPeriodGrowthPct >= 0 ? '+' : '' }}{{ formatPercent(store.priorPeriodGrowthPct) }} vs prior
            </span>
          </div>
        </div>

        <!-- Gross Profit $ Card -->
        <div class="kpi-card">
          <div class="kpi-head">
            <span class="kpi-label">{{ t('exec-gross-profit', 'Gross Profit') }}</span>
            <span class="material-symbols-outlined kpi-icon text-emerald">monetization_on</span>
          </div>
          <div class="kpi-value-row">
            <span class="kpi-value text-emerald">{{ formatCurrency(store.grossProfit) }}</span>
          </div>
          <div class="kpi-subtext">
            <span>{{ t('net-revenue', 'Net Rev') }}: {{ formatCurrency(store.netRevenue) }}</span>
          </div>
        </div>

        <!-- Net Revenue Card -->
        <div class="kpi-card">
          <div class="kpi-head">
            <span class="kpi-label">{{ t('exec-net-revenue', 'Net Revenue') }}</span>
            <span class="material-symbols-outlined kpi-icon text-blue">payments</span>
          </div>
          <div class="kpi-value-row">
            <span class="kpi-value">{{ formatCurrency(store.netRevenue) }}</span>
          </div>
          <div class="kpi-subtext">
            <span>{{ t('gross-sales', 'Gross Sales') }}: {{ formatCurrency(store.grossSales) }}</span>
          </div>
        </div>

        <!-- Cost of Goods Sold (COGS) -->
        <div class="kpi-card">
          <div class="kpi-head">
            <span class="kpi-label">{{ t('exec-cogs', 'COGS (Product Cost)') }}</span>
            <span class="material-symbols-outlined kpi-icon text-amber">inventory_2</span>
          </div>
          <div class="kpi-value-row">
            <span class="kpi-value">{{ formatCurrency(store.cogs) }}</span>
          </div>
          <div class="kpi-subtext">
            <span>{{ formatPercent(store.netRevenue ? (store.cogs / store.netRevenue) * 100 : 0) }} of Net Revenue</span>
          </div>
        </div>

        <!-- Freight & Delivery Cost -->
        <div class="kpi-card">
          <div class="kpi-head">
            <span class="kpi-label">{{ t('exec-freight', 'Freight & Shipping Cost') }}</span>
            <span class="material-symbols-outlined kpi-icon text-indigo">local_shipping</span>
          </div>
          <div class="kpi-value-row">
            <span class="kpi-value">{{ formatCurrency(store.freightCost) }}</span>
          </div>
          <div class="kpi-subtext">
            <span>{{ formatPercent(store.netRevenue ? (store.freightCost / store.netRevenue) * 100 : 0) }} of Net Revenue</span>
          </div>
        </div>

        <!-- Customer Discounts -->
        <div class="kpi-card">
          <div class="kpi-head">
            <span class="kpi-label">{{ t('exec-discounts', 'Customer Discounts') }}</span>
            <span class="material-symbols-outlined kpi-icon text-rose">sell</span>
          </div>
          <div class="kpi-value-row">
            <span class="kpi-value text-rose">{{ formatCurrency(store.discountAmount) }}</span>
          </div>
          <div class="kpi-subtext">
            <span>{{ t('orders-count', 'Orders') }}: {{ store.totalOrders }}</span>
          </div>
        </div>
      </div>

      <!-- Navigation Tabs -->
      <div class="analytics-tabs-nav">
        <button
          class="tab-btn"
          :class="{ active: activeTab === 'margins' }"
          @click="activeTab = 'margins'"
        >
          <span class="material-symbols-outlined">category</span>
          <span>{{ t('tab-margins', 'Category & SKU Margins') }}</span>
          <span v-if="store.lowMarginAlerts?.count > 0" class="badge-alert">
            {{ store.lowMarginAlerts.count }}
          </span>
        </button>

        <button
          class="tab-btn"
          :class="{ active: activeTab === 'matrix' }"
          @click="activeTab = 'matrix'"
        >
          <span class="material-symbols-outlined">grid_view</span>
          <span>{{ t('tab-customer-matrix', 'Customer Profitability Matrix') }}</span>
          <span class="badge-count">{{ store.customerMatrix?.total_customers || 0 }}</span>
        </button>

        <button
          class="tab-btn"
          :class="{ active: activeTab === 'commissions' }"
          @click="activeTab = 'commissions'"
        >
          <span class="material-symbols-outlined">price_check</span>
          <span>{{ t('tab-commissions', 'Collected Margin Commissions') }}</span>
        </button>

        <button
          class="tab-btn"
          :class="{ active: activeTab === 'fulfillment' }"
          @click="activeTab = 'fulfillment'"
        >
          <span class="material-symbols-outlined">local_shipping</span>
          <span>{{ t('tab-fulfillment', 'Route Fulfillment & Delivery') }}</span>
        </button>
      </div>

      <!-- TAB 1: Category & SKU Margins -->
      <div v-show="activeTab === 'margins'" class="tab-content">
        <!-- Low Margin Alerts Banner -->
        <div v-if="store.lowMarginAlerts?.count > 0" class="alert-banner">
          <span class="material-symbols-outlined alert-banner-icon">warning</span>
          <div class="alert-banner-content">
            <h4 class="alert-banner-title">
              {{ t('low-margin-alert-title', 'Low Margin Alerts Detected') }} ({{ store.lowMarginAlerts.count }} items < {{ store.filters.marginThresholdPct }}%)
            </h4>
            <p class="alert-banner-desc">
              {{ t('low-margin-alert-desc', 'The following product categories or SKUs have realized margins under the required threshold after factoring unit COGS, freight costs, and customer discounts.') }}
            </p>
            <div class="alert-tags">
              <span v-for="cat in (store.lowMarginAlerts.categories || [])" :key="cat.category_name" class="alert-tag">
                {{ cat.category_name }}: <strong>{{ formatPercent(cat.gross_margin_pct) }}</strong>
              </span>
            </div>
          </div>
        </div>

        <!-- Charts Grid -->
        <div class="charts-row">
          <!-- Category Gross Margin Bar Chart -->
          <div class="chart-card">
            <div class="chart-header">
              <h3 class="chart-title">{{ t('category-margin-chart', 'Gross Margin % by Category') }}</h3>
              <span class="chart-sub">{{ t('vs-threshold', 'Red indicates below target threshold') }}</span>
            </div>
            <div class="chart-body">
              <BarChart
                v-if="categoryChartLabels.length"
                :labels="categoryChartLabels"
                :values="categoryChartValues"
                :height="260"
                label="Gross Margin %"
                color="#5d3fd3"
              />
              <div v-else class="empty-chart">{{ t('no-data', 'No category margin data available') }}</div>
            </div>
          </div>

          <!-- Category Profit Contribution Donut Chart -->
          <div class="chart-card">
            <div class="chart-header">
              <h3 class="chart-title">{{ t('category-profit-share', 'Gross Profit Share by Category') }}</h3>
              <span class="chart-sub">{{ t('profit-distribution', 'Total realized profit dollar distribution') }}</span>
            </div>
            <div class="chart-body">
              <DonutChart
                v-if="categoryProfitLabels.length"
                :labels="categoryProfitLabels"
                :values="categoryProfitValues"
                :height="260"
              />
              <div v-else class="empty-chart">{{ t('no-data', 'No category profit data available') }}</div>
            </div>
          </div>
        </div>

        <!-- Category Margins Breakdown Table -->
        <div class="data-section-card">
          <div class="section-header">
            <div class="section-title-wrap">
              <span class="material-symbols-outlined section-icon">inventory</span>
              <h3 class="section-title">{{ t('category-margin-breakdown', 'Product Category Gross Margin Breakdown') }}</h3>
            </div>
            <span class="section-count">
              {{ categoryItems.length }} {{ t('categories', 'Categories') }}
            </span>
          </div>

          <div class="table-responsive">
            <table class="data-table">
              <thead>
                <tr>
                  <th>{{ t('category', 'Category') }}</th>
                  <th class="text-right">{{ t('gross-sales', 'Gross Sales') }}</th>
                  <th class="text-right">{{ t('discounts', 'Discounts') }}</th>
                  <th class="text-right">{{ t('net-revenue', 'Net Revenue') }}</th>
                  <th class="text-right">{{ t('cogs', 'COGS') }}</th>
                  <th class="text-right">{{ t('freight', 'Freight') }}</th>
                  <th class="text-right">{{ t('gross-profit', 'Gross Profit') }}</th>
                  <th class="text-right">{{ t('margin-pct', 'Gross Margin %') }}</th>
                  <th class="text-center">{{ t('status', 'Status') }}</th>
                </tr>
              </thead>
              <tbody>
                <tr v-if="!categoryItems.length">
                  <td colspan="9" class="empty-cell">{{ t('no-records', 'No category data found') }}</td>
                </tr>
                <tr v-for="cat in categoryItems" :key="cat.category_id || cat.category_name">
                  <td class="font-semibold">{{ cat.category_name || 'Unassigned' }}</td>
                  <td class="text-right">{{ formatCurrency(cat.gross_sales) }}</td>
                  <td class="text-right text-rose">{{ formatCurrency(cat.discount_amount) }}</td>
                  <td class="text-right">{{ formatCurrency(cat.net_revenue) }}</td>
                  <td class="text-right">{{ formatCurrency(cat.cogs) }}</td>
                  <td class="text-right">{{ formatCurrency(cat.freight_cost) }}</td>
                  <td class="text-right font-bold text-emerald">{{ formatCurrency(cat.gross_profit) }}</td>
                  <td class="text-right font-bold" :class="marginHealthTextClass(cat.gross_margin_pct)">
                    {{ formatPercent(cat.gross_margin_pct) }}
                  </td>
                  <td class="text-center">
                    <span
                      class="status-pill"
                      :class="cat.gross_margin_pct >= store.filters.marginThresholdPct ? 'pill-healthy' : 'pill-alert'"
                    >
                      {{ cat.gross_margin_pct >= store.filters.marginThresholdPct ? t('healthy', 'Target Met') : t('low-margin', 'Low Margin') }}
                    </span>
                  </td>
                </tr>
              </tbody>
              <tfoot v-if="categoryItems.length">
                <tr class="summary-row">
                  <td class="font-bold">{{ t('total', 'Total') }}</td>
                  <td class="text-right font-bold">{{ formatCurrency(store.summary?.gross_sales) }}</td>
                  <td class="text-right font-bold text-rose">{{ formatCurrency(store.summary?.discount_amount) }}</td>
                  <td class="text-right font-bold">{{ formatCurrency(store.summary?.net_revenue) }}</td>
                  <td class="text-right font-bold">{{ formatCurrency(store.summary?.cogs) }}</td>
                  <td class="text-right font-bold">{{ formatCurrency(store.summary?.freight_cost) }}</td>
                  <td class="text-right font-bold text-emerald">{{ formatCurrency(store.summary?.gross_profit) }}</td>
                  <td class="text-right font-bold">{{ formatPercent(store.summary?.gross_margin_pct) }}</td>
                  <td></td>
                </tr>
              </tfoot>
            </table>
          </div>
        </div>

        <!-- SKU Margins Drill-down Table -->
        <div class="data-section-card">
          <div class="section-header">
            <div class="section-title-wrap">
              <span class="material-symbols-outlined section-icon">barcode_scanner</span>
              <h3 class="section-title">{{ t('sku-margin-drilldown', 'SKU-Level Margin Optimization') }}</h3>
            </div>

            <!-- SKU Filters -->
            <div class="sku-filter-toolbar">
              <div class="search-input-wrap">
                <span class="material-symbols-outlined search-icon">search</span>
                <input
                  type="text"
                  v-model="skuSearch"
                  :placeholder="t('search-sku-placeholder', 'Search SKU or product name...')"
                  class="search-input"
                />
              </div>

              <label class="checkbox-toggle">
                <input type="checkbox" v-model="onlyLowMarginSkus" />
                <span>{{ t('show-low-margin-only', 'Low Margin Only (< 15%)') }}</span>
              </label>
            </div>
          </div>

          <div class="table-responsive">
            <table class="data-table">
              <thead>
                <tr>
                  <th>{{ t('sku-code', 'SKU') }}</th>
                  <th>{{ t('product-name', 'Product Name') }}</th>
                  <th>{{ t('category', 'Category') }}</th>
                  <th class="text-right">{{ t('units-sold', 'Units Sold') }}</th>
                  <th class="text-right">{{ t('avg-price', 'Avg Price') }}</th>
                  <th class="text-right">{{ t('unit-cost', 'Unit Cost') }}</th>
                  <th class="text-right">{{ t('revenue', 'Revenue') }}</th>
                  <th class="text-right">{{ t('gross-profit', 'Gross Profit') }}</th>
                  <th class="text-right">{{ t('margin-pct', 'Margin %') }}</th>
                  <th class="text-center">{{ t('status', 'Status') }}</th>
                </tr>
              </thead>
              <tbody>
                <tr v-if="store.loadingTable">
                  <td colspan="10" class="loading-cell">{{ t('loading', 'Loading SKU margins...') }}</td>
                </tr>
                <tr v-else-if="!filteredSkus.length">
                  <td colspan="10" class="empty-cell">{{ t('no-records', 'No matching SKUs found') }}</td>
                </tr>
                <tr v-for="sku in paginatedSkus" :key="sku.sku || sku.product_id">
                  <td class="font-mono text-xs">{{ sku.sku || '-' }}</td>
                  <td class="font-semibold">{{ sku.product_name || '-' }}</td>
                  <td>{{ sku.category_name || '-' }}</td>
                  <td class="text-right">{{ formatNumber(sku.quantity_sold || sku.units_sold) }}</td>
                  <td class="text-right">{{ formatCurrency(sku.avg_selling_price || sku.unit_price) }}</td>
                  <td class="text-right">{{ formatCurrency(sku.unit_cost || sku.cost_price) }}</td>
                  <td class="text-right">{{ formatCurrency(sku.net_revenue || sku.gross_sales) }}</td>
                  <td class="text-right font-bold text-emerald">{{ formatCurrency(sku.gross_profit) }}</td>
                  <td class="text-right font-bold" :class="marginHealthTextClass(sku.gross_margin_pct)">
                    {{ formatPercent(sku.gross_margin_pct) }}
                  </td>
                  <td class="text-center">
                    <span
                      class="status-pill"
                      :class="sku.gross_margin_pct >= store.filters.marginThresholdPct ? 'pill-healthy' : 'pill-alert'"
                    >
                      {{ sku.gross_margin_pct >= store.filters.marginThresholdPct ? 'Healthy' : 'Low Margin' }}
                    </span>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>

          <!-- Pagination -->
          <div v-if="filteredSkus.length > skuPageSize" class="pagination-bar">
            <span class="page-info">
              Showing {{ (skuPage - 1) * skuPageSize + 1 }} to {{ Math.min(skuPage * skuPageSize, filteredSkus.length) }} of {{ filteredSkus.length }} SKUs
            </span>
            <div class="page-buttons">
              <button class="btn-outline btn-xs" :disabled="skuPage === 1" @click="skuPage--">
                {{ t('previous', 'Previous') }}
              </button>
              <button class="btn-outline btn-xs" :disabled="skuPage >= maxSkuPages" @click="skuPage++">
                {{ t('next', 'Next') }}
              </button>
            </div>
          </div>
        </div>
      </div>

      <!-- TAB 2: Customer Profitability Matrix (4 Quadrants) -->
      <div v-show="activeTab === 'matrix'" class="tab-content">
        <!-- 4 Quadrants Summary Cards Grid -->
        <div class="quadrants-grid">
          <!-- Q1: Core Stars -->
          <div
            class="quadrant-card q1-card"
            :class="{ active: selectedQuadrantFilter === 'Q1' }"
            @click="toggleQuadrantFilter('Q1')"
          >
            <div class="q-header">
              <div class="q-badge q1-badge">Q1: Core Stars</div>
              <span class="material-symbols-outlined q-icon">star</span>
            </div>
            <div class="q-title">High Volume · High Margin</div>
            <div class="q-metrics">
              <div class="q-metric-item">
                <span class="q-label">{{ t('customers', 'Customers') }}</span>
                <span class="q-val">{{ store.customerMatrix?.quadrants?.Q1?.customer_count || 0 }}</span>
              </div>
              <div class="q-metric-item">
                <span class="q-label">{{ t('gross-profit', 'Profit') }}</span>
                <span class="q-val text-emerald">{{ formatCurrency(store.customerMatrix?.quadrants?.Q1?.total_gross_profit || 0) }}</span>
              </div>
            </div>
            <div class="q-desc">Protect relationship, nurture, and provide priority white-glove logistics.</div>
          </div>

          <!-- Q2: Volume Risks -->
          <div
            class="quadrant-card q2-card"
            :class="{ active: selectedQuadrantFilter === 'Q2' }"
            @click="toggleQuadrantFilter('Q2')"
          >
            <div class="q-header">
              <div class="q-badge q2-badge">Q2: Volume Risks</div>
              <span class="material-symbols-outlined q-icon">warning</span>
            </div>
            <div class="q-title">High Volume · Low Margin</div>
            <div class="q-metrics">
              <div class="q-metric-item">
                <span class="q-label">{{ t('customers', 'Customers') }}</span>
                <span class="q-val">{{ store.customerMatrix?.quadrants?.Q2?.customer_count || 0 }}</span>
              </div>
              <div class="q-metric-item">
                <span class="q-label">{{ t('gross-profit', 'Profit') }}</span>
                <span class="q-val text-amber">{{ formatCurrency(store.customerMatrix?.quadrants?.Q2?.total_gross_profit || 0) }}</span>
              </div>
            </div>
            <div class="q-desc">High volume consuming capacity at slim margins. Renegotiate pricing or curb freight subsidies.</div>
          </div>

          <!-- Q3: High Potential -->
          <div
            class="quadrant-card q3-card"
            :class="{ active: selectedQuadrantFilter === 'Q3' }"
            @click="toggleQuadrantFilter('Q3')"
          >
            <div class="q-header">
              <div class="q-badge q3-badge">Q3: High Potential</div>
              <span class="material-symbols-outlined q-icon">trending_up</span>
            </div>
            <div class="q-title">Low Volume · High Margin</div>
            <div class="q-metrics">
              <div class="q-metric-item">
                <span class="q-label">{{ t('customers', 'Customers') }}</span>
                <span class="q-val">{{ store.customerMatrix?.quadrants?.Q3?.customer_count || 0 }}</span>
              </div>
              <div class="q-metric-item">
                <span class="q-label">{{ t('gross-profit', 'Profit') }}</span>
                <span class="q-val text-blue">{{ formatCurrency(store.customerMatrix?.quadrants?.Q3?.total_gross_profit || 0) }}</span>
              </div>
            </div>
            <div class="q-desc">High gross margin accounts with low volume. Prime target for cross-selling and wallet-share growth.</div>
          </div>

          <!-- Q4: Unprofitable / Drain Accounts -->
          <div
            class="quadrant-card q4-card"
            :class="{ active: selectedQuadrantFilter === 'Q4' }"
            @click="toggleQuadrantFilter('Q4')"
          >
            <div class="q-header">
              <div class="q-badge q4-badge">Q4: Drain Accounts</div>
              <span class="material-symbols-outlined q-icon">do_not_disturb_on</span>
            </div>
            <div class="q-title">Low Volume · Low Margin</div>
            <div class="q-metrics">
              <div class="q-metric-item">
                <span class="q-label">{{ t('customers', 'Customers') }}</span>
                <span class="q-val">{{ store.customerMatrix?.quadrants?.Q4?.customer_count || 0 }}</span>
              </div>
              <div class="q-metric-item">
                <span class="q-label">{{ t('gross-profit', 'Profit') }}</span>
                <span class="q-val text-rose">{{ formatCurrency(store.customerMatrix?.quadrants?.Q4?.total_gross_profit || 0) }}</span>
              </div>
            </div>
            <div class="q-desc">Unprofitable orders draining operational resources. Impose minimum order quantities or delivery fees.</div>
          </div>
        </div>

        <!-- Filter Pill Row -->
        <div class="matrix-filter-bar">
          <div class="filter-pills">
            <button
              class="filter-pill"
              :class="{ active: !selectedQuadrantFilter }"
              @click="selectedQuadrantFilter = null"
            >
              All Accounts ({{ store.customerMatrix?.items?.length || 0 }})
            </button>
            <button
              class="filter-pill q1-pill"
              :class="{ active: selectedQuadrantFilter === 'Q1' }"
              @click="selectedQuadrantFilter = 'Q1'"
            >
              Q1: Core Stars ({{ store.customerMatrix?.quadrants?.Q1?.customer_count || 0 }})
            </button>
            <button
              class="filter-pill q2-pill"
              :class="{ active: selectedQuadrantFilter === 'Q2' }"
              @click="selectedQuadrantFilter = 'Q2'"
            >
              Q2: Volume Risks ({{ store.customerMatrix?.quadrants?.Q2?.customer_count || 0 }})
            </button>
            <button
              class="filter-pill q3-pill"
              :class="{ active: selectedQuadrantFilter === 'Q3' }"
              @click="selectedQuadrantFilter = 'Q3'"
            >
              Q3: High Potential ({{ store.customerMatrix?.quadrants?.Q3?.customer_count || 0 }})
            </button>
            <button
              class="filter-pill q4-pill"
              :class="{ active: selectedQuadrantFilter === 'Q4' }"
              @click="selectedQuadrantFilter = 'Q4'"
            >
              Q4: Drain Accounts ({{ store.customerMatrix?.quadrants?.Q4?.customer_count || 0 }})
            </button>
          </div>

          <div class="search-input-wrap">
            <span class="material-symbols-outlined search-icon">search</span>
            <input
              type="text"
              v-model="customerSearch"
              :placeholder="t('search-customer-placeholder', 'Search customer name or code...')"
              class="search-input"
            />
          </div>
        </div>

        <!-- Ranked Customer Profitability Table -->
        <div class="data-section-card">
          <div class="table-responsive">
            <table class="data-table">
              <thead>
                <tr>
                  <th>{{ t('customer', 'Customer') }}</th>
                  <th class="text-center">{{ t('quadrant', 'Quadrant') }}</th>
                  <th class="text-right">{{ t('orders', 'Orders') }}</th>
                  <th class="text-right">{{ t('gross-sales', 'Gross Sales') }}</th>
                  <th class="text-right">{{ t('discounts', 'Discounts') }}</th>
                  <th class="text-right">{{ t('cogs', 'COGS') }}</th>
                  <th class="text-right">{{ t('freight', 'Freight') }}</th>
                  <th class="text-right">{{ t('gross-profit', 'Gross Profit') }}</th>
                  <th class="text-right">{{ t('margin-pct', 'Margin %') }}</th>
                  <th class="text-right">{{ t('aov', 'Avg Order') }}</th>
                  <th class="text-center">{{ t('actions', 'Strategy') }}</th>
                </tr>
              </thead>
              <tbody>
                <tr v-if="!filteredCustomers.length">
                  <td colspan="11" class="empty-cell">{{ t('no-records', 'No customer records match filter') }}</td>
                </tr>
                <tr v-for="c in paginatedCustomers" :key="c.customer_id">
                  <td>
                    <div class="customer-info-cell">
                      <span class="customer-name">{{ c.customer_name }}</span>
                      <span class="customer-code">{{ c.customer_code || `#${c.customer_id}` }}</span>
                    </div>
                  </td>
                  <td class="text-center">
                    <span class="quadrant-tag" :class="`tag-${(c.quadrant || 'Q1').toLowerCase()}`">
                      {{ c.quadrant || 'Q1' }} · {{ c.quadrant_name || 'Star' }}
                    </span>
                  </td>
                  <td class="text-right">{{ c.order_count || c.total_orders || 0 }}</td>
                  <td class="text-right">{{ formatCurrency(c.gross_sales) }}</td>
                  <td class="text-right text-rose">{{ formatCurrency(c.discount_amount) }}</td>
                  <td class="text-right">{{ formatCurrency(c.cogs) }}</td>
                  <td class="text-right">{{ formatCurrency(c.freight_cost) }}</td>
                  <td class="text-right font-bold text-emerald">{{ formatCurrency(c.gross_profit) }}</td>
                  <td class="text-right font-bold" :class="marginHealthTextClass(c.gross_margin_pct)">
                    {{ formatPercent(c.gross_margin_pct) }}
                  </td>
                  <td class="text-right">{{ formatCurrency(c.average_order_value || c.aov) }}</td>
                  <td class="text-center">
                    <button class="btn-outline btn-xs" @click="openCustomerPlaybook(c)">
                      <span class="material-symbols-outlined">menu_book</span>
                      {{ t('playbook', 'Playbook') }}
                    </button>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>

          <!-- Customer Pagination -->
          <div v-if="filteredCustomers.length > customerPageSize" class="pagination-bar">
            <span class="page-info">
              Showing {{ (customerPage - 1) * customerPageSize + 1 }} to {{ Math.min(customerPage * customerPageSize, filteredCustomers.length) }} of {{ filteredCustomers.length }} Customers
            </span>
            <div class="page-buttons">
              <button class="btn-outline btn-xs" :disabled="customerPage === 1" @click="customerPage--">
                {{ t('previous', 'Previous') }}
              </button>
              <button class="btn-outline btn-xs" :disabled="customerPage >= maxCustomerPages" @click="customerPage++">
                {{ t('next', 'Next') }}
              </button>
            </div>
          </div>
        </div>
      </div>

      <!-- TAB 3: Sales Rep Margin Commissions -->
      <div v-show="activeTab === 'commissions'" class="tab-content">
        <!-- Explanatory Callout Banner -->
        <div class="info-callout-card">
          <span class="material-symbols-outlined info-icon">verified</span>
          <div class="info-body">
            <h4 class="info-title">{{ t('collected-margin-policy', 'Collected Gross Margin Commission Policy') }}</h4>
            <p class="info-desc">
              {{ t('collected-margin-policy-desc', 'Sales representative commissions are computed strictly against paid invoices and collected cash (realized gross margin) rather than uncollected top-line bookings. Discount concessions directly reduce the commissionable profit base to align sales incentives with company profitability.') }}
            </p>
          </div>
        </div>

        <!-- Commission Summaries Table -->
        <div class="data-section-card">
          <div class="section-header">
            <div class="section-title-wrap">
              <span class="material-symbols-outlined section-icon">badge</span>
              <h3 class="section-title">{{ t('sales-rep-commission-ledger', 'Sales Representative Margin Commission Ledger') }}</h3>
            </div>
            <button class="btn-outline btn-sm" @click="loadCommissions">
              <span class="material-symbols-outlined">sync</span>
              {{ t('refresh', 'Refresh Ledger') }}
            </button>
          </div>

          <div class="table-responsive">
            <table class="data-table">
              <thead>
                <tr>
                  <th>{{ t('sales-rep', 'Sales Representative') }}</th>
                  <th class="text-right">{{ t('booked-sales', 'Booked Sales') }}</th>
                  <th class="text-right">{{ t('invoices-collected', 'Paid Invoices') }}</th>
                  <th class="text-right">{{ t('realized-margin', 'Collected Gross Margin') }}</th>
                  <th class="text-right">{{ t('effective-margin', 'Margin %') }}</th>
                  <th class="text-right">{{ t('realized-commission', 'Earned Commission') }}</th>
                  <th class="text-right">{{ t('paid-payouts', 'Paid Payouts') }}</th>
                  <th class="text-right">{{ t('pending-commission', 'Pending Balance') }}</th>
                  <th class="text-center">{{ t('action', 'Statement') }}</th>
                </tr>
              </thead>
              <tbody>
                <tr v-if="!store.commissionSummaries?.length">
                  <td colspan="9" class="empty-cell">{{ t('no-commission-data', 'No commission statements found for this period') }}</td>
                </tr>
                <tr v-for="rep in store.commissionSummaries" :key="rep.sales_rep_id">
                  <td>
                    <div class="rep-name-cell">
                      <span class="rep-name">{{ rep.sales_rep_name || `Rep #${rep.sales_rep_id}` }}</span>
                      <span class="rep-code">{{ rep.sales_rep_code || `ID: ${rep.sales_rep_id}` }}</span>
                    </div>
                  </td>
                  <td class="text-right">{{ formatCurrency(rep.total_booked_sales || rep.booked_sales) }}</td>
                  <td class="text-right">{{ formatCurrency(rep.total_invoices_paid || rep.collected_sales) }}</td>
                  <td class="text-right font-bold text-emerald">{{ formatCurrency(rep.total_gross_profit || rep.realized_margin) }}</td>
                  <td class="text-right">{{ formatPercent(rep.effective_margin_pct || rep.margin_pct) }}</td>
                  <td class="text-right font-bold text-indigo">{{ formatCurrency(rep.total_commission || rep.earned_commission) }}</td>
                  <td class="text-right text-emerald">{{ formatCurrency(rep.paid_commission || rep.paid_payouts) }}</td>
                  <td class="text-right font-bold text-amber">{{ formatCurrency(rep.pending_commission || rep.pending_balance) }}</td>
                  <td class="text-center">
                    <button class="btn-outline btn-xs" @click="viewCommissionStatement(rep)">
                      <span class="material-symbols-outlined">receipt_long</span>
                      {{ t('statement', 'Statement') }}
                    </button>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>

      <!-- TAB 4: Route Fulfillment & Delivery Efficiency -->
      <div v-show="activeTab === 'fulfillment'" class="tab-content">
        <!-- Fulfillment Gauges Grid -->
        <div class="gauges-grid">
          <div class="gauge-card">
            <div class="gauge-head">
              <span class="gauge-label">{{ t('otd-rate', 'On-Time Delivery (OTD) Rate') }}</span>
              <span class="material-symbols-outlined gauge-icon text-emerald">schedule</span>
            </div>
            <div class="gauge-value" :class="store.onTimeDeliveryRate >= 95 ? 'text-emerald' : 'text-amber'">
              {{ formatPercent(store.onTimeDeliveryRate) }}
            </div>
            <div class="gauge-progress-bar">
              <div
                class="gauge-progress-fill"
                :style="{
                  width: `${Math.min(100, Math.max(0, store.onTimeDeliveryRate))}%`,
                  backgroundColor: store.onTimeDeliveryRate >= 95 ? '#10b981' : '#f59e0b',
                }"
              ></div>
            </div>
            <div class="gauge-sub">Target: 95.0% On-Time Threshold</div>
          </div>

          <div class="gauge-card">
            <div class="gauge-head">
              <span class="gauge-label">{{ t('route-completion', 'Route Completion Rate') }}</span>
              <span class="material-symbols-outlined gauge-icon text-blue">task_alt</span>
            </div>
            <div class="gauge-value text-blue">
              {{ formatPercent(store.routeCompletionRate) }}
            </div>
            <div class="gauge-progress-bar">
              <div
                class="gauge-progress-fill"
                :style="{
                  width: `${Math.min(100, Math.max(0, store.routeCompletionRate))}%`,
                  backgroundColor: '#3b82f6',
                }"
              ></div>
            </div>
            <div class="gauge-sub">Total Dispatched: {{ store.totalDeliveries }} Deliveries</div>
          </div>

          <div class="gauge-card">
            <div class="gauge-head">
              <span class="gauge-label">{{ t('delayed-deliveries', 'Delayed Deliveries') }}</span>
              <span class="material-symbols-outlined gauge-icon text-rose">warning</span>
            </div>
            <div class="gauge-value text-rose">
              {{ store.delayedDeliveries }}
            </div>
            <div class="gauge-progress-bar">
              <div
                class="gauge-progress-fill"
                :style="{
                  width: `${store.totalDeliveries ? Math.min(100, (store.delayedDeliveries / store.totalDeliveries) * 100) : 0}%`,
                  backgroundColor: '#ef4444',
                }"
              ></div>
            </div>
            <div class="gauge-sub">
              {{ store.totalDeliveries ? formatPercent((store.delayedDeliveries / store.totalDeliveries) * 100) : '0%' }} of all shipments
            </div>
          </div>
        </div>

        <!-- Warehouse Dispatch Efficiency Table -->
        <div class="data-section-card">
          <div class="section-header">
            <div class="section-title-wrap">
              <span class="material-symbols-outlined section-icon">warehouse</span>
              <h3 class="section-title">{{ t('warehouse-dispatch-efficiency', 'Warehouse Dispatch & Logistics Efficiency') }}</h3>
            </div>
          </div>

          <div class="table-responsive">
            <table class="data-table">
              <thead>
                <tr>
                  <th>{{ t('warehouse', 'Warehouse') }}</th>
                  <th class="text-right">{{ t('dispatched-orders', 'Dispatched Orders') }}</th>
                  <th class="text-right">{{ t('delivered-orders', 'Delivered') }}</th>
                  <th class="text-right">{{ t('delayed-orders', 'Delayed') }}</th>
                  <th class="text-right">{{ t('otd-pct', 'OTD %') }}</th>
                  <th class="text-right">{{ t('total-freight', 'Total Freight') }}</th>
                  <th class="text-right">{{ t('cost-per-delivery', 'Avg Cost / Delivery') }}</th>
                </tr>
              </thead>
              <tbody>
                <tr v-if="!store.warehouseEfficiency?.length">
                  <td colspan="7" class="empty-cell">{{ t('no-warehouse-data', 'No warehouse delivery metrics recorded') }}</td>
                </tr>
                <tr v-for="wh in store.warehouseEfficiency" :key="wh.warehouse_id || wh.warehouse_name">
                  <td class="font-semibold">{{ wh.warehouse_name || 'Central Distribution Hub' }}</td>
                  <td class="text-right">{{ wh.total_deliveries || 0 }}</td>
                  <td class="text-right text-emerald">{{ wh.delivered_count || wh.total_deliveries || 0 }}</td>
                  <td class="text-right text-rose">{{ wh.delayed_count || 0 }}</td>
                  <td class="text-right font-bold" :class="wh.on_time_rate_pct >= 95 ? 'text-emerald' : 'text-amber'">
                    {{ formatPercent(wh.on_time_rate_pct) }}
                  </td>
                  <td class="text-right">{{ formatCurrency(wh.total_freight_cost) }}</td>
                  <td class="text-right font-bold">{{ formatCurrency(wh.avg_cost_per_delivery) }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </template>

    <!-- Customer Strategy Playbook Modal -->
    <div v-if="showPlaybookModal" class="modal-backdrop" @click.self="showPlaybookModal = false">
      <div class="modal-card">
        <div class="modal-header">
          <div class="modal-title-wrap">
            <span class="material-symbols-outlined modal-icon">menu_book</span>
            <div>
              <h3 class="modal-title">{{ t('customer-strategy-playbook', 'Customer Strategic Playbook') }}</h3>
              <p class="modal-subtitle">
                {{ selectedCustomerForPlaybook?.customer_name }} ·
                <span class="quadrant-tag" :class="`tag-${(selectedCustomerForPlaybook?.quadrant || 'q1').toLowerCase()}`">
                  {{ selectedCustomerForPlaybook?.quadrant }} ({{ selectedCustomerForPlaybook?.quadrant_name }})
                </span>
              </p>
            </div>
          </div>
          <button class="btn-icon" @click="showPlaybookModal = false">
            <span class="material-symbols-outlined">close</span>
          </button>
        </div>

        <div class="modal-body">
          <!-- Customer Economics Summary -->
          <div class="economics-grid">
            <div class="econ-box">
              <span class="econ-label">Gross Margin %</span>
              <span class="econ-val font-bold" :class="marginHealthTextClass(selectedCustomerForPlaybook?.gross_margin_pct)">
                {{ formatPercent(selectedCustomerForPlaybook?.gross_margin_pct) }}
              </span>
            </div>
            <div class="econ-box">
              <span class="econ-label">Gross Profit $</span>
              <span class="econ-val text-emerald font-bold">{{ formatCurrency(selectedCustomerForPlaybook?.gross_profit) }}</span>
            </div>
            <div class="econ-box">
              <span class="econ-label">Freight Impact</span>
              <span class="econ-val text-indigo">{{ formatCurrency(selectedCustomerForPlaybook?.freight_cost) }}</span>
            </div>
            <div class="econ-box">
              <span class="econ-label">Discounts Given</span>
              <span class="econ-val text-rose">{{ formatCurrency(selectedCustomerForPlaybook?.discount_amount) }}</span>
            </div>
          </div>

          <!-- Strategy Guidelines based on Quadrant -->
          <div class="strategy-section">
            <h4 class="strategy-heading">{{ t('recommended-playbook-actions', 'Recommended Leadership Actions') }}</h4>
            <div class="strategy-cards-list">
              <div class="strategy-item">
                <span class="material-symbols-outlined strategy-bullet text-indigo">check_circle</span>
                <div>
                  <strong>{{ getQuadrantGuideline(selectedCustomerForPlaybook?.quadrant).title }}</strong>
                  <p>{{ getQuadrantGuideline(selectedCustomerForPlaybook?.quadrant).description }}</p>
                </div>
              </div>
              <div class="strategy-item">
                <span class="material-symbols-outlined strategy-bullet text-emerald">paid</span>
                <div>
                  <strong>Pricing & Concession Limits</strong>
                  <p>{{ getQuadrantGuideline(selectedCustomerForPlaybook?.quadrant).pricingPolicy }}</p>
                </div>
              </div>
              <div class="strategy-item">
                <span class="material-symbols-outlined strategy-bullet text-amber">local_shipping</span>
                <div>
                  <strong>Freight & Delivery Terms</strong>
                  <p>{{ getQuadrantGuideline(selectedCustomerForPlaybook?.quadrant).deliveryPolicy }}</p>
                </div>
              </div>
            </div>
          </div>
        </div>

        <div class="modal-footer">
          <button class="btn-primary" @click="showPlaybookModal = false">{{ t('close', 'Close') }}</button>
        </div>
      </div>
    </div>

    <!-- Sales Rep Statement Modal -->
    <div v-if="showStatementModal" class="modal-backdrop" @click.self="showStatementModal = false">
      <div class="modal-card modal-lg">
        <div class="modal-header">
          <div class="modal-title-wrap">
            <span class="material-symbols-outlined modal-icon">receipt_long</span>
            <div>
              <h3 class="modal-title">{{ t('commission-statement', 'Commission Statement Detail') }}</h3>
              <p class="modal-subtitle">{{ activeRepForStatement?.sales_rep_name }} · Period: {{ store.filters.dateFrom }} to {{ store.filters.dateTo }}</p>
            </div>
          </div>
          <button class="btn-icon" @click="showStatementModal = false">
            <span class="material-symbols-outlined">close</span>
          </button>
        </div>

        <div class="modal-body">
          <div class="statement-summary-bar">
            <div class="stat-summary-item">
              <span class="stat-summary-lbl">Booked Sales</span>
              <span class="stat-summary-val">{{ formatCurrency(activeRepForStatement?.total_booked_sales || activeRepForStatement?.booked_sales) }}</span>
            </div>
            <div class="stat-summary-item">
              <span class="stat-summary-lbl">Collected Gross Margin</span>
              <span class="stat-summary-val text-emerald">{{ formatCurrency(activeRepForStatement?.total_gross_profit || activeRepForStatement?.realized_margin) }}</span>
            </div>
            <div class="stat-summary-item">
              <span class="stat-summary-lbl">Earned Commission</span>
              <span class="stat-summary-val text-indigo font-bold">{{ formatCurrency(activeRepForStatement?.total_commission || activeRepForStatement?.earned_commission) }}</span>
            </div>
            <div class="stat-summary-item">
              <span class="stat-summary-lbl">Pending Unpaid Balance</span>
              <span class="stat-summary-val text-amber font-bold">{{ formatCurrency(activeRepForStatement?.pending_commission || activeRepForStatement?.pending_balance) }}</span>
            </div>
          </div>

          <div class="table-responsive">
            <table class="data-table">
              <thead>
                <tr>
                  <th>{{ t('invoice-num', 'Invoice #') }}</th>
                  <th>{{ t('customer', 'Customer') }}</th>
                  <th class="text-right">{{ t('invoice-amount', 'Invoice Paid') }}</th>
                  <th class="text-right">{{ t('gross-margin-dollar', 'Gross Margin $') }}</th>
                  <th class="text-right">{{ t('margin-pct', 'Margin %') }}</th>
                  <th class="text-right">{{ t('rate', 'Comm %') }}</th>
                  <th class="text-right">{{ t('commission-earned', 'Commission $') }}</th>
                  <th class="text-center">{{ t('status', 'Status') }}</th>
                </tr>
              </thead>
              <tbody>
                <tr v-if="!store.selectedCommissionStatement?.line_items?.length && !store.selectedCommissionStatement?.invoices?.length">
                  <td colspan="8" class="empty-cell">
                    {{ t('no-invoices-found', 'No individual paid invoice breakdown items found.') }}
                  </td>
                </tr>
                <tr
                  v-for="inv in (store.selectedCommissionStatement?.line_items || store.selectedCommissionStatement?.invoices || [])"
                  :key="inv.invoice_id || inv.invoice_number"
                >
                  <td class="font-mono">{{ inv.invoice_number || `#${inv.invoice_id}` }}</td>
                  <td>{{ inv.customer_name || '-' }}</td>
                  <td class="text-right">{{ formatCurrency(inv.paid_amount || inv.total_amount) }}</td>
                  <td class="text-right font-bold text-emerald">{{ formatCurrency(inv.gross_profit || inv.realized_margin) }}</td>
                  <td class="text-right">{{ formatPercent(inv.margin_pct || inv.gross_margin_pct) }}</td>
                  <td class="text-right">{{ formatPercent(inv.commission_rate_pct || 5.0) }}</td>
                  <td class="text-right font-bold text-indigo">{{ formatCurrency(inv.commission_amount) }}</td>
                  <td class="text-center">
                    <span class="status-pill pill-healthy">Collected</span>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        <div class="modal-footer">
          <button class="btn-primary" @click="showStatementModal = false">{{ t('close', 'Close') }}</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useI18n } from '../../composables/useI18n.js'
import { useToast } from '../../composables/useToast.js'
import { useExecutiveAnalyticsStore } from '../../stores/executiveAnalytics.js'
import SkeletonCard from '../../components/SkeletonCard.vue'
import SkeletonTable from '../../components/SkeletonTable.vue'
import ErrorState from '../../components/ErrorState.vue'
import BarChart from '../../components/charts/BarChart.vue'
import DonutChart from '../../components/charts/DonutChart.vue'

const { t, dir } = useI18n()
const { show: toast } = useToast()
const store = useExecutiveAnalyticsStore()

// Active Tab & Filters
const activeTab = ref('margins')
const periodPresets = ['Today', 'This Week', 'This Month', 'Last Month', 'QTD', 'YTD', 'Custom']
const customDateFrom = ref(store.filters.dateFrom)
const customDateTo = ref(store.filters.dateTo)
const tempThreshold = ref(store.filters.marginThresholdPct || 15.0)

// SKU Drilldown local state
const skuSearch = ref('')
const onlyLowMarginSkus = ref(false)
const skuPage = ref(1)
const skuPageSize = ref(15)

// Customer Matrix local state
const selectedQuadrantFilter = ref(null)
const customerSearch = ref('')
const customerPage = ref(1)
const customerPageSize = ref(15)

// Modal states
const showPlaybookModal = ref(false)
const selectedCustomerForPlaybook = ref(null)
const showStatementModal = ref(false)
const activeRepForStatement = ref(null)

// ---------------------------------------------------------------------------
// Formatting Helpers
// ---------------------------------------------------------------------------
function formatCurrency(val) {
  if (val === null || val === undefined || isNaN(Number(val))) return '$0.00'
  return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(Number(val))
}

function formatPercent(val) {
  if (val === null || val === undefined || isNaN(Number(val))) return '0.0%'
  return `${Number(val).toFixed(1)}%`
}

function formatNumber(val) {
  if (val === null || val === undefined || isNaN(Number(val))) return '0'
  return new Intl.NumberFormat('en-US').format(Number(val))
}

function marginHealthClass(marginPct) {
  if (marginPct === null || marginPct === undefined) return 'neutral'
  return Number(marginPct) >= store.filters.marginThresholdPct ? 'healthy-card' : 'alert-card'
}

function marginHealthTextClass(marginPct) {
  if (marginPct === null || marginPct === undefined) return ''
  return Number(marginPct) >= store.filters.marginThresholdPct ? 'text-emerald' : 'text-rose'
}

// ---------------------------------------------------------------------------
// Computed Data Properties
// ---------------------------------------------------------------------------
const categoryItems = computed(() => store.categoryMargins?.items || [])

const categoryChartLabels = computed(() => {
  return categoryItems.value.map((c) => c.category_name || 'Unassigned')
})

const categoryChartValues = computed(() => {
  return categoryItems.value.map((c) => Number(c.gross_margin_pct || 0))
})

const categoryProfitLabels = computed(() => {
  return categoryItems.value.map((c) => c.category_name || 'Unassigned')
})

const categoryProfitValues = computed(() => {
  return categoryItems.value.map((c) => Number(c.gross_profit || 0))
})

const filteredSkus = computed(() => {
  let list = store.skuMargins?.items || []
  if (skuSearch.value) {
    const q = skuSearch.value.toLowerCase()
    list = list.filter(
      (s) =>
        (s.sku && s.sku.toLowerCase().includes(q)) ||
        (s.product_name && s.product_name.toLowerCase().includes(q)) ||
        (s.category_name && s.category_name.toLowerCase().includes(q))
    )
  }
  if (onlyLowMarginSkus.value) {
    list = list.filter((s) => Number(s.gross_margin_pct || 0) < store.filters.marginThresholdPct)
  }
  return list
})

const maxSkuPages = computed(() => Math.ceil(filteredSkus.value.length / skuPageSize.value) || 1)

const paginatedSkus = computed(() => {
  const start = (skuPage.value - 1) * skuPageSize.value
  return filteredSkus.value.slice(start, start + skuPageSize.value)
})

const filteredCustomers = computed(() => {
  let list = store.customerMatrix?.items || []
  if (selectedQuadrantFilter.value) {
    list = list.filter((c) => c.quadrant === selectedQuadrantFilter.value)
  }
  if (customerSearch.value) {
    const q = customerSearch.value.toLowerCase()
    list = list.filter(
      (c) =>
        (c.customer_name && c.customer_name.toLowerCase().includes(q)) ||
        (c.customer_code && c.customer_code.toLowerCase().includes(q))
    )
  }
  return list
})

const maxCustomerPages = computed(() => Math.ceil(filteredCustomers.value.length / customerPageSize.value) || 1)

const paginatedCustomers = computed(() => {
  const start = (customerPage.value - 1) * customerPageSize.value
  return filteredCustomers.value.slice(start, start + customerPageSize.value)
})

// ---------------------------------------------------------------------------
// Actions & Handlers
// ---------------------------------------------------------------------------
async function refreshData() {
  try {
    await store.loadAllExecutiveData()
    await store.fetchSkuMargins({ limit: 100 })
    toast(t('dashboard-refreshed', 'Executive analytics updated'), 'success')
  } catch (err) {
    toast(t('dashboard-refresh-failed', 'Failed to update dashboard data'), 'error')
  }
}

async function selectPreset(preset) {
  store.setPeriodPreset(preset)
  customDateFrom.value = store.filters.dateFrom
  customDateTo.value = store.filters.dateTo
  await refreshData()
}

async function applyCustomDates() {
  if (!customDateFrom.value || !customDateTo.value) return
  store.setDateRange(customDateFrom.value, customDateTo.value)
  await refreshData()
}

async function updateMarginThreshold() {
  store.filters.marginThresholdPct = tempThreshold.value
  await store.fetchLowMarginAlerts(tempThreshold.value)
}

function toggleQuadrantFilter(q) {
  selectedQuadrantFilter.value = selectedQuadrantFilter.value === q ? null : q
  customerPage.value = 1
}

async function loadCommissions() {
  try {
    await store.fetchCommissionSummaries()
    toast(t('commissions-refreshed', 'Commission ledger refreshed'), 'success')
  } catch (err) {
    toast(t('commissions-error', 'Failed to fetch commissions'), 'error')
  }
}

async function handleExportPdf() {
  try {
    await store.exportPdf()
    toast(t('pdf-exported', 'Executive PDF financial report downloaded'), 'success')
  } catch (err) {
    toast(t('export-pdf-error', 'Failed to generate PDF report'), 'error')
  }
}

async function handleExportExcel() {
  try {
    await store.exportExcel()
    toast(t('excel-exported', 'Executive multi-tab Excel model downloaded'), 'success')
  } catch (err) {
    toast(t('export-excel-error', 'Failed to generate Excel report'), 'error')
  }
}

async function handleExportCsv() {
  try {
    await store.exportCsv()
    toast(t('csv-exported', 'Category margin CSV downloaded'), 'success')
  } catch (err) {
    toast(t('export-csv-error', 'Failed to generate CSV export'), 'error')
  }
}

function openCustomerPlaybook(customer) {
  selectedCustomerForPlaybook.value = customer
  showPlaybookModal.value = true
}

async function viewCommissionStatement(rep) {
  activeRepForStatement.value = rep
  showStatementModal.value = true
  try {
    await store.fetchCommissionStatement(rep.sales_rep_id)
  } catch (err) {
    console.error('Failed to load detailed statement:', err)
  }
}

function getQuadrantGuideline(quadrant) {
  switch (quadrant) {
    case 'Q1':
      return {
        title: 'Protect & Nurture Core Stars',
        description:
          'High volume and high margin driver. Assign dedicated executive account managers and ensure zero-delay priority warehouse fulfillment.',
        pricingPolicy: 'Preserve existing pricing matrix. Strictly cap discount concessions to 3% max.',
        deliveryPolicy: 'Offer complimentary scheduled deliveries with dedicated logistics routing.',
      }
    case 'Q2':
      return {
        title: 'Remediate Volume Risks',
        description:
          'Consuming significant warehouse and route bandwidth at slim margins. Review pricing tiers and renegotiate commodity pass-through clauses.',
        pricingPolicy: 'Implement minimum 4-6% price increase across low-margin SKUs or limit discounts.',
        deliveryPolicy: 'Require full pallet/truckload shipments to eliminate route freight subsidies.',
      }
    case 'Q3':
      return {
        title: 'Expand High Potential Accounts',
        description:
          'Healthy margins with room for volume expansion. Incentivize sales reps with margin multipliers to capture additional SKU category share.',
        pricingPolicy: 'Offer volume rebate thresholds that protect base margin while encouraging larger batch orders.',
        deliveryPolicy: 'Standard route consolidation with bi-weekly scheduled dispatches.',
      }
    case 'Q4':
    default:
      return {
        title: 'Restructure or Eliminate Drain Accounts',
        description:
          'Unprofitable orders eroding net operational margin. Implement stringent minimum order quantities (MOQs) or delivery surcharges.',
        pricingPolicy: 'Eliminate all discretionary customer discounts immediately.',
        deliveryPolicy: 'Enforce mandatory $50+ delivery fee on all orders below $500 threshold.',
      }
  }
}

// ---------------------------------------------------------------------------
// Lifecycle
// ---------------------------------------------------------------------------
onMounted(async () => {
  await refreshData()
})
</script>

<style scoped>
.executive-analytics-view {
  padding-bottom: 40px;
}

/* Page Header */
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 16px;
  margin-bottom: 20px;
}

.title-row {
  display: flex;
  align-items: center;
  gap: 12px;
}

.header-icon {
  font-size: 32px;
  color: var(--color-primary, #5d3fd3);
  background: var(--bg-primary-faded, #e6deff);
  padding: 8px;
  border-radius: 10px;
}

.page-title {
  font-size: 22px;
  font-weight: 700;
  color: var(--text-primary);
  margin: 0;
}

.page-subtitle {
  font-size: 13px;
  color: var(--text-subtle);
  margin-top: 2px;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.export-btn {
  padding: 7px 14px;
  font-size: 12px;
}

.refresh-btn {
  padding: 7px 16px;
  font-size: 12px;
}

.spin-icon {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  100% {
    transform: rotate(360deg);
  }
}

/* Filter Bar */
.filter-bar-card {
  background: var(--bg-surface);
  border: 1px solid var(--border-default);
  border-radius: 10px;
  padding: 12px 16px;
  margin-bottom: 20px;
}

.filter-controls {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 16px;
}

.period-presets {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.filter-label {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.preset-pills {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}

.preset-pill {
  padding: 5px 12px;
  border-radius: 20px;
  border: 1px solid var(--border-input);
  background: var(--bg-surface);
  color: var(--text-secondary);
  font-size: 12px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.15s ease;
}

.preset-pill:hover {
  background: var(--bg-surface-hover);
}

.preset-pill.active {
  background: var(--color-primary, #5d3fd3);
  color: #ffffff;
  border-color: var(--color-primary, #5d3fd3);
}

.custom-dates {
  display: flex;
  align-items: center;
  gap: 8px;
}

.date-group {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  color: var(--text-muted);
}

.date-input {
  padding: 4px 8px;
  border: 1px solid var(--border-input);
  border-radius: 6px;
  font-size: 12px;
  background: var(--bg-surface);
  color: var(--text-primary);
}

.threshold-control {
  display: flex;
  align-items: center;
  gap: 8px;
}

.input-with-suffix {
  position: relative;
  display: inline-flex;
  align-items: center;
}

.threshold-input {
  width: 65px;
  padding: 4px 20px 4px 8px;
  border: 1px solid var(--border-input);
  border-radius: 6px;
  font-size: 12px;
  font-weight: 600;
  background: var(--bg-surface);
  color: var(--text-primary);
  text-align: right;
}

.suffix {
  position: absolute;
  right: 6px;
  font-size: 11px;
  color: var(--text-subtle);
  pointer-events: none;
}

/* Executive KPI Grid */
.kpi-cards-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 14px;
  margin-bottom: 24px;
}

.kpi-card {
  background: var(--bg-surface);
  border: 1px solid var(--border-default);
  border-radius: 10px;
  padding: 16px;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  transition: transform 0.15s, box-shadow 0.15s;
}

.kpi-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
}

.kpi-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.kpi-label {
  font-size: 11px;
  font-weight: 700;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.kpi-icon {
  font-size: 20px;
  color: var(--text-subtle);
}

.kpi-value-row {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  margin-bottom: 6px;
}

.kpi-value {
  font-size: 24px;
  font-weight: 700;
  color: var(--text-primary);
  line-height: 1.1;
}

.kpi-subtext {
  font-size: 11px;
  color: var(--text-subtle);
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.kpi-status-badge {
  font-size: 10px;
  font-weight: 700;
  padding: 2px 6px;
  border-radius: 10px;
  text-transform: uppercase;
}

.kpi-status-badge.healthy-card {
  background: #dcfce7;
  color: #16a34a;
}

.kpi-status-badge.alert-card {
  background: #fee2e2;
  color: #dc2626;
}

.trend-badge {
  font-weight: 600;
}

.trend-badge.up {
  color: #16a34a;
}

.trend-badge.down {
  color: #dc2626;
}

.text-emerald {
  color: #16a34a;
}

.text-blue {
  color: #2563eb;
}

.text-indigo {
  color: #4f46e5;
}

.text-amber {
  color: #d97706;
}

.text-rose {
  color: #e11d48;
}

/* Tabs Navigation */
.analytics-tabs-nav {
  display: flex;
  gap: 8px;
  border-bottom: 2px solid var(--border-default);
  margin-bottom: 20px;
  overflow-x: auto;
}

.tab-btn {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 12px 18px;
  background: transparent;
  border: none;
  border-bottom: 3px solid transparent;
  margin-bottom: -2px;
  color: var(--text-muted);
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  white-space: nowrap;
  transition: all 0.15s;
}

.tab-btn:hover {
  color: var(--color-primary, #5d3fd3);
}

.tab-btn.active {
  color: var(--color-primary, #5d3fd3);
  border-bottom-color: var(--color-primary, #5d3fd3);
}

.badge-alert {
  background: #dc2626;
  color: #ffffff;
  font-size: 10px;
  font-weight: 700;
  padding: 2px 6px;
  border-radius: 10px;
}

.badge-count {
  background: var(--bg-surface-low, #f3f4f6);
  color: var(--text-secondary);
  font-size: 10px;
  font-weight: 700;
  padding: 2px 6px;
  border-radius: 10px;
}

/* Alert Banner */
.alert-banner {
  display: flex;
  align-items: flex-start;
  gap: 14px;
  background: #fef2f2;
  border: 1px solid #fecaca;
  border-radius: 10px;
  padding: 16px;
  margin-bottom: 20px;
}

.alert-banner-icon {
  font-size: 28px;
  color: #dc2626;
  flex-shrink: 0;
}

.alert-banner-title {
  font-size: 14px;
  font-weight: 700;
  color: #991b1b;
  margin-bottom: 4px;
}

.alert-banner-desc {
  font-size: 12px;
  color: #7f1d1d;
  margin-bottom: 8px;
}

.alert-tags {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}

.alert-tag {
  background: #fee2e2;
  border: 1px solid #fca5a5;
  color: #991b1b;
  font-size: 11px;
  padding: 3px 8px;
  border-radius: 4px;
}

/* Charts Grid */
.charts-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
  margin-bottom: 24px;
}

.chart-card {
  background: var(--bg-surface);
  border: 1px solid var(--border-default);
  border-radius: 10px;
  padding: 18px;
}

.chart-header {
  margin-bottom: 14px;
}

.chart-title {
  font-size: 14px;
  font-weight: 700;
  color: var(--text-primary);
  margin-bottom: 2px;
}

.chart-sub {
  font-size: 11px;
  color: var(--text-subtle);
}

.chart-body {
  min-height: 260px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.empty-chart {
  color: var(--text-faint);
  font-size: 13px;
}

/* Data Section Cards & Tables */
.data-section-card {
  background: var(--bg-surface);
  border: 1px solid var(--border-default);
  border-radius: 10px;
  overflow: hidden;
  margin-bottom: 24px;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 14px 18px;
  background: var(--bg-surface-low);
  border-bottom: 1px solid var(--border-default);
  flex-wrap: wrap;
  gap: 12px;
}

.section-title-wrap {
  display: flex;
  align-items: center;
  gap: 8px;
}

.section-icon {
  font-size: 20px;
  color: var(--color-primary, #5d3fd3);
}

.section-title {
  font-size: 14px;
  font-weight: 700;
  color: var(--text-primary);
  margin: 0;
}

.section-count {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-subtle);
}

.sku-filter-toolbar {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.search-input-wrap {
  position: relative;
  display: flex;
  align-items: center;
}

.search-icon {
  position: absolute;
  left: 8px;
  font-size: 18px;
  color: var(--text-subtle);
}

.search-input {
  padding: 6px 10px 6px 30px;
  border: 1px solid var(--border-input);
  border-radius: 6px;
  font-size: 12px;
  background: var(--bg-surface);
  color: var(--text-primary);
  width: 220px;
}

.checkbox-toggle {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: var(--text-secondary);
  cursor: pointer;
}

.table-responsive {
  overflow-x: auto;
}

.data-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 12px;
}

.data-table th {
  background: var(--bg-surface-low);
  padding: 10px 14px;
  font-size: 11px;
  font-weight: 700;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.5px;
  border-bottom: 1px solid var(--border-default);
  text-align: left;
  white-space: nowrap;
}

.data-table td {
  padding: 11px 14px;
  border-bottom: 1px solid var(--border-light);
  color: var(--text-secondary);
  white-space: nowrap;
}

.data-table tbody tr:hover {
  background: var(--bg-surface-hover);
}

.summary-row td {
  background: var(--bg-surface-low);
  border-top: 2px solid var(--border-default);
  border-bottom: none;
}

.empty-cell,
.loading-cell {
  text-align: center;
  padding: 40px 14px;
  color: var(--text-subtle);
  font-size: 13px;
}

.text-right {
  text-align: right;
}

.text-center {
  text-align: center;
}

.font-bold {
  font-weight: 700;
}

.font-semibold {
  font-weight: 600;
}

.font-mono {
  font-family: monospace;
}

/* Status Pills */
.status-pill {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 12px;
  font-size: 10px;
  font-weight: 700;
  text-transform: uppercase;
}

.pill-healthy {
  background: #dcfce7;
  color: #16a34a;
}

.pill-alert {
  background: #fee2e2;
  color: #dc2626;
}

/* Quadrants Grid */
.quadrants-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
  gap: 16px;
  margin-bottom: 20px;
}

.quadrant-card {
  background: var(--bg-surface);
  border: 1px solid var(--border-default);
  border-radius: 10px;
  padding: 16px;
  cursor: pointer;
  transition: all 0.15s ease;
}

.quadrant-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.06);
}

.quadrant-card.active {
  border-width: 2px;
}

.q1-card.active {
  border-color: #10b981;
}

.q2-card.active {
  border-color: #f59e0b;
}

.q3-card.active {
  border-color: #3b82f6;
}

.q4-card.active {
  border-color: #ef4444;
}

.q-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 6px;
}

.q-badge {
  font-size: 11px;
  font-weight: 700;
  padding: 2px 8px;
  border-radius: 4px;
  text-transform: uppercase;
}

.q1-badge {
  background: #dcfce7;
  color: #16a34a;
}

.q2-badge {
  background: #fef3c7;
  color: #d97706;
}

.q3-badge {
  background: #dbeafe;
  color: #2563eb;
}

.q4-badge {
  background: #fee2e2;
  color: #dc2626;
}

.q-icon {
  font-size: 20px;
  color: var(--text-subtle);
}

.q-title {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 10px;
}

.q-metrics {
  display: flex;
  justify-content: space-between;
  background: var(--bg-surface-low);
  padding: 8px 10px;
  border-radius: 6px;
  margin-bottom: 8px;
}

.q-metric-item {
  display: flex;
  flex-direction: column;
}

.q-label {
  font-size: 10px;
  color: var(--text-subtle);
  text-transform: uppercase;
}

.q-val {
  font-size: 14px;
  font-weight: 700;
}

.q-desc {
  font-size: 11px;
  color: var(--text-subtle);
  line-height: 1.4;
}

/* Matrix Filter Bar */
.matrix-filter-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 14px;
  flex-wrap: wrap;
  gap: 12px;
}

.filter-pills {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}

.filter-pill {
  padding: 5px 12px;
  border-radius: 20px;
  border: 1px solid var(--border-input);
  background: var(--bg-surface);
  color: var(--text-secondary);
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
}

.filter-pill.active {
  background: var(--color-primary, #5d3fd3);
  color: #ffffff;
  border-color: var(--color-primary, #5d3fd3);
}

.customer-info-cell {
  display: flex;
  flex-direction: column;
}

.customer-name {
  font-weight: 600;
  color: var(--text-primary);
}

.customer-code {
  font-size: 10px;
  color: var(--text-subtle);
  font-family: monospace;
}

.quadrant-tag {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 10px;
  font-weight: 700;
}

.tag-q1 {
  background: #dcfce7;
  color: #16a34a;
}

.tag-q2 {
  background: #fef3c7;
  color: #d97706;
}

.tag-q3 {
  background: #dbeafe;
  color: #2563eb;
}

.tag-q4 {
  background: #fee2e2;
  color: #dc2626;
}

/* Callout Info Banner */
.info-callout-card {
  display: flex;
  align-items: flex-start;
  gap: 14px;
  background: #eff6ff;
  border: 1px solid #bfdbfe;
  border-radius: 10px;
  padding: 16px;
  margin-bottom: 20px;
}

.info-icon {
  font-size: 28px;
  color: #2563eb;
  flex-shrink: 0;
}

.info-title {
  font-size: 14px;
  font-weight: 700;
  color: #1e40af;
  margin-bottom: 4px;
}

.info-desc {
  font-size: 12px;
  color: #1e3a8a;
  line-height: 1.5;
}

.rep-name-cell {
  display: flex;
  flex-direction: column;
}

.rep-name {
  font-weight: 600;
  color: var(--text-primary);
}

.rep-code {
  font-size: 10px;
  color: var(--text-subtle);
}

/* Gauges Grid */
.gauges-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
  gap: 16px;
  margin-bottom: 24px;
}

.gauge-card {
  background: var(--bg-surface);
  border: 1px solid var(--border-default);
  border-radius: 10px;
  padding: 18px;
}

.gauge-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.gauge-label {
  font-size: 12px;
  font-weight: 700;
  color: var(--text-muted);
  text-transform: uppercase;
}

.gauge-icon {
  font-size: 22px;
}

.gauge-value {
  font-size: 28px;
  font-weight: 800;
  margin-bottom: 8px;
}

.gauge-progress-bar {
  height: 8px;
  background: var(--border-light, #e5e7eb);
  border-radius: 4px;
  overflow: hidden;
  margin-bottom: 8px;
}

.gauge-progress-fill {
  height: 100%;
  border-radius: 4px;
  transition: width 0.6s ease;
}

.gauge-sub {
  font-size: 11px;
  color: var(--text-subtle);
}

/* Pagination Bar */
.pagination-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 18px;
  background: var(--bg-surface-low);
  border-top: 1px solid var(--border-default);
}

.page-info {
  font-size: 12px;
  color: var(--text-subtle);
}

.page-buttons {
  display: flex;
  gap: 6px;
}

.btn-xs {
  padding: 4px 10px !important;
  font-size: 11px !important;
}

.btn-sm {
  padding: 6px 14px !important;
  font-size: 12px !important;
}

/* Modals */
.modal-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.45);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  padding: 20px;
}

.modal-card {
  background: var(--bg-surface);
  border-radius: 12px;
  width: 100%;
  max-width: 600px;
  max-height: 85vh;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  box-shadow: 0 10px 25px rgba(0, 0, 0, 0.2);
}

.modal-lg {
  max-width: 850px;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  padding: 16px 20px;
  background: var(--bg-surface-low);
  border-bottom: 1px solid var(--border-default);
}

.modal-title-wrap {
  display: flex;
  align-items: center;
  gap: 10px;
}

.modal-icon {
  font-size: 24px;
  color: var(--color-primary, #5d3fd3);
}

.modal-title {
  font-size: 16px;
  font-weight: 700;
  color: var(--text-primary);
  margin: 0;
}

.modal-subtitle {
  font-size: 12px;
  color: var(--text-subtle);
  margin-top: 2px;
}

.modal-body {
  padding: 20px;
  overflow-y: auto;
}

.economics-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 10px;
  margin-bottom: 20px;
}

.econ-box {
  background: var(--bg-surface-low);
  border: 1px solid var(--border-light);
  border-radius: 8px;
  padding: 10px;
  display: flex;
  flex-direction: column;
}

.econ-label {
  font-size: 10px;
  color: var(--text-subtle);
  text-transform: uppercase;
}

.econ-val {
  font-size: 15px;
  margin-top: 4px;
}

.strategy-section {
  background: var(--bg-surface-low);
  border-radius: 8px;
  padding: 14px;
}

.strategy-heading {
  font-size: 13px;
  font-weight: 700;
  color: var(--text-primary);
  margin-bottom: 12px;
}

.strategy-cards-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.strategy-item {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  font-size: 12px;
}

.strategy-item p {
  color: var(--text-secondary);
  margin-top: 2px;
}

.strategy-bullet {
  font-size: 18px;
  flex-shrink: 0;
  margin-top: 2px;
}

.statement-summary-bar {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
  background: var(--bg-surface-low);
  border-radius: 8px;
  padding: 14px;
  margin-bottom: 18px;
}

.stat-summary-item {
  display: flex;
  flex-direction: column;
}

.stat-summary-lbl {
  font-size: 10px;
  color: var(--text-subtle);
  text-transform: uppercase;
}

.stat-summary-val {
  font-size: 16px;
  margin-top: 2px;
}

.modal-footer {
  padding: 12px 20px;
  background: var(--bg-surface-low);
  border-top: 1px solid var(--border-default);
  display: flex;
  justify-content: flex-end;
}

/* Skeleton Loading Container */
.loading-container {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.skeleton-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 14px;
}

@media (max-width: 768px) {
  .charts-row {
    grid-template-columns: 1fr;
  }
  .economics-grid,
  .statement-summary-bar {
    grid-template-columns: 1fr 1fr;
  }
}

[dir="rtl"] .search-icon {
  left: auto;
  right: 8px;
}

[dir="rtl"] .search-input {
  padding: 6px 30px 6px 10px;
}

[dir="rtl"] .suffix {
  right: auto;
  left: 6px;
}
</style>
