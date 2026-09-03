<template>
  <div :dir="dir" class="restock-view">
    <!-- Header -->
    <div class="flex justify-between items-center mb-6 flex-wrap gap-4">
      <div>
        <h1 class="page-title flex items-center gap-2">
          <span class="material-symbols-outlined text-primary-500 text-3xl">smart_toy</span>
          {{ t('restock-suggestions-title', 'AI Restock & Supplier Reorder Points') }}
        </h1>
        <p class="page-subtitle">
          {{ t('restock-suggestions-sub', 'Automated supplier reorder queue, pending sales order reservation factoring, and one-click PO generation') }}
        </p>
      </div>
      <div class="flex items-center gap-3">
        <button class="btn-secondary flex items-center gap-2" @click="loadData" :disabled="loading || runningForecast">
          <span class="material-symbols-outlined" :class="{ 'animate-spin': loading }">refresh</span>
          {{ t('refresh', 'Refresh') }}
        </button>
        <button class="btn-secondary flex items-center gap-2" @click="runForecast" :disabled="runningForecast">
          <span class="material-symbols-outlined" :class="{ 'animate-spin': runningForecast }">bolt</span>
          {{ runningForecast ? t('running-forecast', 'Analyzing Demand...') : t('run-ai-forecast', 'Run AI Forecast') }}
        </button>
        <button
          v-if="supplierQueue.length > 0"
          class="btn-primary flex items-center gap-2 bg-emerald-600 hover:bg-emerald-700 text-white"
          @click="approveAllSuppliers"
          :disabled="approvingAll"
        >
          <span class="material-symbols-outlined" :class="{ 'animate-spin': approvingAll }">done_all</span>
          {{ approvingAll ? t('approving-all', 'Generating POs...') : t('approve-all-pos', 'Approve All Supplier Draft POs') }}
        </button>
      </div>
    </div>

    <!-- Navigation Tabs -->
    <div class="nav-cards mb-6">
      <router-link to="/purchasing/requisitions" class="nav-card">
        <span class="material-symbols-outlined nav-icon">receipt_long</span>
        <span class="nav-label">{{ t('pr-title', 'Requisitions') }}</span>
      </router-link>
      <router-link to="/purchasing/rfqs" class="nav-card">
        <span class="material-symbols-outlined nav-icon">request_quote</span>
        <span class="nav-label">{{ t('rfq-title', 'RFQs') }}</span>
      </router-link>
      <router-link to="/purchasing" class="nav-card">
        <span class="material-symbols-outlined nav-icon">receipt</span>
        <span class="nav-label">{{ t('purchase-orders', 'Purchase Orders') }}</span>
      </router-link>
      <router-link to="/purchasing/returns" class="nav-card">
        <span class="material-symbols-outlined nav-icon">assignment_return</span>
        <span class="nav-label">{{ t('returns-title', 'Returns') }}</span>
      </router-link>
      <router-link to="/purchasing/restock-suggestions" class="nav-card nav-card-active">
        <span class="material-symbols-outlined nav-icon">smart_toy</span>
        <span class="nav-label">{{ t('ai-restock', 'AI Restock') }}</span>
      </router-link>
    </div>

    <!-- Feedback Banner -->
    <div v-if="successMsg" class="mb-4 p-4 bg-emerald-50 border border-emerald-200 text-emerald-800 rounded-lg flex justify-between items-center shadow-sm">
      <div class="flex items-center gap-2">
        <span class="material-symbols-outlined text-emerald-600">check_circle</span>
        <span class="font-medium">{{ successMsg }}</span>
      </div>
      <button class="btn-icon text-emerald-600 hover:text-emerald-800" @click="successMsg = ''"><span class="material-symbols-outlined">close</span></button>
    </div>

    <!-- Metric Summary KPI Cards -->
    <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
      <div class="kpi-card">
        <div class="flex justify-between items-start">
          <div>
            <div class="kpi-label">{{ t('supplier-draft-queues', 'Supplier PO Queues') }}</div>
            <div class="kpi-value text-indigo-600">{{ supplierQueue.length }}</div>
          </div>
          <span class="material-symbols-outlined text-indigo-500 text-3xl">local_shipping</span>
        </div>
        <div class="kpi-subtext text-gray-500 mt-2">
          {{ summary.total_items || filteredSuggestions.length }} {{ t('items-grouped', 'at-risk items grouped by supplier') }}
        </div>
      </div>

      <div class="kpi-card">
        <div class="flex justify-between items-start">
          <div>
            <div class="kpi-label">{{ t('at-risk-skus', 'At-Risk SKUs') }}</div>
            <div class="kpi-value text-amber-600">{{ summary.at_risk_count || 0 }}</div>
          </div>
          <span class="material-symbols-outlined text-amber-500 text-3xl">warning</span>
        </div>
        <div class="kpi-subtext text-gray-500 mt-2">
          {{ summary.total_evaluated || 0 }} {{ t('total-evaluated', 'SKUs Evaluated (Factors Pending SOs)') }}
        </div>
      </div>

      <div class="kpi-card">
        <div class="flex justify-between items-start">
          <div>
            <div class="kpi-label">{{ t('critical-stockouts', 'Critical Stockouts') }}</div>
            <div class="kpi-value text-rose-600">{{ summary.critical_count || 0 }}</div>
          </div>
          <span class="material-symbols-outlined text-rose-500 text-3xl">error</span>
        </div>
        <div class="kpi-subtext text-gray-500 mt-2">{{ t('stockout-imminent', 'Depletion before supplier arrival') }}</div>
      </div>

      <div class="kpi-card">
        <div class="flex justify-between items-start">
          <div>
            <div class="kpi-label">{{ t('suggested-spend', 'Suggested Spend') }}</div>
            <div class="kpi-value text-emerald-600">${{ formatMoney(summary.total_estimated_spend || 0) }}</div>
          </div>
          <span class="material-symbols-outlined text-emerald-500 text-3xl">payments</span>
        </div>
        <div class="kpi-subtext text-gray-500 mt-2">{{ formatUnits(summary.total_suggested_qty || 0) }} {{ t('units-total', 'units total') }}</div>
      </div>
    </div>

    <!-- Filter & View Mode Bar -->
    <div class="data-card p-4 mb-6">
      <div class="flex flex-wrap items-center justify-between gap-4">
        <!-- View Switcher Tabs -->
        <div class="flex items-center bg-gray-100 p-1 rounded-lg border border-gray-200">
          <button
            class="px-4 py-2 text-sm font-semibold rounded-md transition-colors flex items-center gap-2"
            :class="viewMode === 'supplier-queue' ? 'bg-white text-primary-700 shadow-sm' : 'text-gray-600 hover:text-gray-900'"
            @click="viewMode = 'supplier-queue'"
          >
            <span class="material-symbols-outlined text-lg">local_shipping</span>
            {{ t('consolidated-supplier-pos', 'Consolidated Supplier PO Queue') }}
            <span class="ml-1 px-2 py-0.5 text-xs font-bold rounded-full" :class="viewMode === 'supplier-queue' ? 'bg-primary-100 text-primary-800' : 'bg-gray-200 text-gray-700'">
              {{ supplierQueue.length }}
            </span>
          </button>
          <button
            class="px-4 py-2 text-sm font-semibold rounded-md transition-colors flex items-center gap-2"
            :class="viewMode === 'sku-suggestions' ? 'bg-white text-primary-700 shadow-sm' : 'text-gray-600 hover:text-gray-900'"
            @click="viewMode = 'sku-suggestions'"
          >
            <span class="material-symbols-outlined text-lg">inventory_2</span>
            {{ t('by-product-sku', 'All SKU Recommendations') }}
            <span class="ml-1 px-2 py-0.5 text-xs font-bold rounded-full" :class="viewMode === 'sku-suggestions' ? 'bg-primary-100 text-primary-800' : 'bg-gray-200 text-gray-700'">
              {{ filteredSuggestions.length }}
            </span>
          </button>
        </div>

        <div class="flex flex-wrap items-center gap-3">
          <!-- Search input -->
          <div class="relative min-w-[220px]">
            <span class="material-symbols-outlined absolute left-3 top-2.5 text-gray-400">search</span>
            <input
              type="text"
              v-model="searchQuery"
              class="form-input pl-9"
              :placeholder="t('search-sku-supplier', 'Search SKU, Product, Supplier...')"
            />
          </div>

          <select v-model.number="filters.days" class="form-input text-sm" @change="loadData">
            <option :value="14">14-Day Velocity</option>
            <option :value="30">30-Day Velocity (Default)</option>
            <option :value="60">60-Day Velocity</option>
            <option :value="90">90-Day Velocity</option>
          </select>

          <select v-model.number="filters.target_coverage_days" class="form-input text-sm" @change="loadData">
            <option :value="15">15-Day Target Coverage</option>
            <option :value="30">30-Day Target Coverage</option>
            <option :value="45">45-Day Target Coverage</option>
            <option :value="60">60-Day Target Coverage</option>
          </select>

          <label class="flex items-center gap-2 cursor-pointer text-sm font-medium text-gray-700 ml-2">
            <input
              type="checkbox"
              v-model="filters.only_at_risk"
              class="rounded text-primary-600 focus:ring-primary-500"
              @change="loadData"
            />
            {{ t('only-at-risk', 'Only restock needed') }}
          </label>
        </div>
      </div>
    </div>

    <!-- Loading and Error States -->
    <SkeletonTable v-if="loading" />
    <ErrorState v-else-if="error" :message="error" @retry="loadData" />

    <!-- VIEW 1: CONSOLIDATED SUPPLIER DRAFT PO QUEUE -->
    <div v-else-if="viewMode === 'supplier-queue'" class="space-y-6">
      <div v-if="!filteredSupplierQueue.length" class="empty-state">
        <span class="material-symbols-outlined empty-icon text-emerald-500">task_alt</span>
        <h3 class="text-lg font-semibold mt-2">{{ t('all-healthy-title', 'No Supplier Reorder Queues Pending') }}</h3>
        <p class="text-gray-500 max-w-md mx-auto mt-1">
          {{ t('all-healthy-msg', 'All evaluated SKUs have sufficient net available stock above safety thresholds. Pending sales order reservations are fully satisfied.') }}
        </p>
        <button class="btn-secondary mt-4" @click="filters.only_at_risk = false; loadData()">
          {{ t('show-all-suppliers', 'Show All Supplier Mappings') }}
        </button>
      </div>

      <div v-for="group in filteredSupplierQueue" :key="group.supplier_id || 'unassigned'" class="data-card overflow-hidden border border-gray-200 shadow-sm">
        <!-- Supplier Header -->
        <div class="p-4 bg-gray-50 border-b border-gray-200 flex flex-wrap items-center justify-between gap-4">
          <div class="flex items-center gap-3">
            <button
              class="btn-icon text-gray-500 hover:text-gray-700"
              @click="toggleSupplierExpand(group.supplier_id)"
              :title="expandedSuppliers[group.supplier_id] ? 'Collapse' : 'Expand'"
            >
              <span class="material-symbols-outlined transition-transform" :class="{ 'rotate-180': expandedSuppliers[group.supplier_id] }">
                expand_more
              </span>
            </button>

            <div>
              <div class="flex items-center gap-2">
                <h3 class="font-bold text-lg text-gray-900">{{ group.supplier_name || 'Unassigned Supplier' }}</h3>
                <span class="badge" :class="urgencyBadge(group.max_urgency)">
                  {{ group.max_urgency }} URGENCY
                </span>
              </div>
              <div class="text-xs text-gray-500 flex items-center gap-3 mt-1">
                <span><strong class="text-gray-700">Lead Time:</strong> {{ group.lead_time_days }} days</span>
                <span>•</span>
                <span><strong class="text-gray-700">Expected Delivery:</strong> {{ group.expected_date }}</span>
                <span>•</span>
                <span><strong class="text-gray-700">Total Items:</strong> {{ group.total_items }} SKUs</span>
              </div>
            </div>
          </div>

          <div class="flex items-center gap-4">
            <div class="text-right">
              <div class="text-xs text-gray-500 uppercase font-semibold">Consolidated Spend</div>
              <div class="text-xl font-bold text-emerald-700">${{ formatMoney(group.total_estimated_cost) }}</div>
              <div class="text-xs text-gray-500">{{ formatUnits(group.total_qty) }} total units</div>
            </div>

            <div class="flex items-center gap-2">
              <button
                class="btn-secondary btn-sm flex items-center gap-1"
                @click="openSupplierEditModal(group)"
                :disabled="actionLoading['sup_' + group.supplier_id]"
              >
                <span class="material-symbols-outlined text-sm">edit</span>
                {{ t('customize', 'Customize PO') }}
              </button>

              <button
                class="btn-primary btn-sm flex items-center gap-1 bg-emerald-600 hover:bg-emerald-700 text-white"
                @click="approveSupplierQueue(group)"
                :disabled="actionLoading['sup_' + group.supplier_id]"
              >
                <span class="material-symbols-outlined text-sm">check_circle</span>
                {{ actionLoading['sup_' + group.supplier_id] ? t('processing', 'Creating...') : t('approve-po', 'Approve Draft PO') }}
              </button>
            </div>
          </div>
        </div>

        <!-- Supplier Line Items Table -->
        <div v-if="expandedSuppliers[group.supplier_id]" class="table-wrap">
          <table class="data-table">
            <thead>
              <tr>
                <th>{{ t('product', 'Product & SKU') }}</th>
                <th>{{ t('urgency', 'Urgency') }}</th>
                <th class="col-num">{{ t('stock-reservation', 'Stock / Pending SO Reservations') }}</th>
                <th class="col-num">{{ t('daily-velocity', '30d Velocity') }}</th>
                <th class="col-num">{{ t('moq', 'MOQ') }}</th>
                <th class="col-num">{{ t('unit-cost', 'Unit Cost') }}</th>
                <th class="col-num">{{ t('suggested-order-qty', 'Suggested Qty') }}</th>
                <th class="col-num">{{ t('estimated-cost', 'Line Total') }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="item in group.items" :key="item.product_id" :class="{ 'bg-rose-50/40': item.urgency === 'CRITICAL', 'bg-amber-50/30': item.urgency === 'HIGH' }">
                <td>
                  <div class="font-semibold text-gray-900">{{ item.product_name }}</div>
                  <div class="text-xs text-gray-500 font-mono">{{ item.sku }}</div>
                </td>
                <td>
                  <span class="badge text-xs" :class="urgencyBadge(item.urgency)">
                    {{ item.urgency }}
                  </span>
                  <div v-if="item.projected_stockout_date" class="text-[11px] text-gray-500 mt-0.5">
                    Stockout: {{ item.projected_stockout_date }}
                  </div>
                </td>
                <td class="col-num">
                  <div class="font-medium text-gray-900">
                    {{ formatUnits(item.available_stock ?? item.net_available_stock ?? 0) }} units Net Avail
                  </div>
                  <div class="text-xs text-gray-500">
                    Stock: {{ formatUnits(item.current_stock || 0) }}
                    <span v-if="item.reserved_qty > 0" class="text-indigo-600 font-semibold">
                      • {{ formatUnits(item.reserved_qty) }} SO Reserved
                    </span>
                  </div>
                  <div class="text-[11px]" :class="item.days_of_inventory <= item.lead_time_days ? 'text-rose-600 font-bold' : 'text-gray-400'">
                    {{ item.days_of_inventory != null ? `${item.days_of_inventory}d supply` : 'N/A' }}
                  </div>
                </td>
                <td class="col-num font-mono text-sm text-gray-700">
                  {{ Number(item.velocity_30d || 0).toFixed(2) }} u/d
                </td>
                <td class="col-num font-mono text-sm text-gray-600">
                  {{ formatUnits(item.min_order_qty || 1) }}
                </td>
                <td class="col-num font-mono text-sm text-gray-800">
                  ${{ Number(item.unit_cost || 0).toFixed(2) }}
                </td>
                <td class="col-num">
                  <div class="font-bold text-primary-700 text-base">{{ formatUnits(item.suggested_order_qty) }}</div>
                  <div v-if="item.suggested_order_qty === item.min_order_qty && item.min_order_qty > 1" class="text-[10px] text-indigo-600 font-medium">
                    (MOQ Enforced)
                  </div>
                </td>
                <td class="col-num font-semibold text-gray-900">
                  ${{ formatMoney(item.estimated_cost) }}
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <!-- VIEW 2: INDIVIDUAL SKU RECOMMENDATIONS TABLE -->
    <div v-else-if="viewMode === 'sku-suggestions'">
      <div v-if="!filteredSuggestions.length" class="empty-state">
        <span class="material-symbols-outlined empty-icon text-emerald-500">task_alt</span>
        <h3 class="text-lg font-semibold mt-2">{{ t('all-healthy-title', 'Inventory is Healthy') }}</h3>
        <p class="text-gray-500 max-w-md mx-auto mt-1">
          {{ t('all-healthy-msg', 'All evaluated SKUs have sufficient inventory above their reorder thresholds and lead-time safety buffers.') }}
        </p>
        <button class="btn-secondary mt-4" @click="filters.only_at_risk = false; loadData()">
          {{ t('show-all-skus', 'Show All Catalog SKUs') }}
        </button>
      </div>

      <div v-else class="data-card overflow-hidden">
        <div class="table-wrap">
          <table class="data-table">
            <thead>
              <tr>
                <th>{{ t('product', 'Product & SKU') }}</th>
                <th>{{ t('urgency', 'Urgency') }}</th>
                <th class="col-num">{{ t('available-stock', 'Stock / Pending SO Reservations') }}</th>
                <th class="col-num">{{ t('daily-velocity', '30d Velocity') }}</th>
                <th>{{ t('supplier', 'Supplier / Lead Time') }}</th>
                <th class="col-num">{{ t('moq', 'MOQ') }}</th>
                <th class="col-num">{{ t('suggested-order-qty', 'Suggested Qty') }}</th>
                <th class="col-num">{{ t('estimated-cost', 'Est. Total') }}</th>
                <th class="text-center">{{ t('actions', 'Actions') }}</th>
              </tr>
            </thead>
            <tbody>
              <template v-for="item in filteredSuggestions" :key="item.product_id">
                <tr :class="{ 'bg-rose-50/40': item.urgency === 'CRITICAL', 'bg-amber-50/30': item.urgency === 'HIGH' }">
                  <td>
                    <div class="font-semibold text-gray-900">{{ item.product_name }}</div>
                    <div class="text-xs text-gray-500 font-mono">{{ item.sku }}</div>
                  </td>
                  <td>
                    <span class="badge" :class="urgencyBadge(item.urgency)">
                      {{ item.urgency }}
                    </span>
                    <div v-if="item.projected_stockout_date" class="text-[11px] text-gray-500 mt-0.5">
                      Stockout: {{ item.projected_stockout_date }}
                    </div>
                  </td>
                  <td class="col-num">
                    <div class="font-medium text-gray-900">
                      {{ formatUnits(item.available_stock ?? item.net_available_stock ?? 0) }} units Net Avail
                    </div>
                    <div class="text-xs text-gray-500">
                      Stock: {{ formatUnits(item.current_stock || 0) }}
                      <span v-if="item.reserved_qty > 0" class="text-indigo-600 font-semibold">
                        • {{ formatUnits(item.reserved_qty) }} SO Reserved
                      </span>
                    </div>
                    <div class="text-xs" :class="item.days_of_inventory <= item.lead_time_days ? 'text-rose-600 font-bold' : 'text-gray-500'">
                      {{ item.days_of_inventory != null ? `${item.days_of_inventory}d supply` : 'N/A' }}
                    </div>
                  </td>
                  <td class="col-num">
                    <div class="font-mono text-sm">{{ Number(item.velocity_30d || 0).toFixed(2) }}</div>
                    <div class="text-[11px] text-gray-400">units/day</div>
                  </td>
                  <td>
                    <div class="text-sm font-medium text-gray-800">{{ item.supplier_name || 'Standard Supplier' }}</div>
                    <div class="text-xs text-gray-500">{{ item.lead_time_days }}d lead time (${{ Number(item.unit_cost || 0).toFixed(2) }}/u)</div>
                  </td>
                  <td class="col-num text-sm text-gray-600 font-mono">
                    {{ formatUnits(item.min_order_qty || 1) }}
                  </td>
                  <td class="col-num">
                    <div class="font-bold text-primary-700 text-base">{{ formatUnits(item.suggested_order_qty) }}</div>
                    <div v-if="item.suggested_order_qty === item.min_order_qty && item.min_order_qty > 1" class="text-[10px] text-indigo-600 font-medium">
                      (MOQ Enforced)
                    </div>
                  </td>
                  <td class="col-num font-semibold text-gray-900">
                    ${{ formatMoney(item.estimated_cost) }}
                  </td>
                  <td class="text-center">
                    <div class="flex items-center justify-center gap-1">
                      <!-- Quick Approve -->
                      <button
                        class="btn-primary btn-sm flex items-center gap-1"
                        @click="approveSuggestion(item)"
                        :disabled="actionLoading[item.product_id]"
                        :title="t('approve-and-create-po', 'Approve Draft PO')"
                      >
                        <span class="material-symbols-outlined text-sm">check</span>
                        <span>{{ t('approve', 'Approve') }}</span>
                      </button>

                      <!-- Edit Order Modal -->
                      <button
                        class="btn-icon"
                        @click="openEditModal(item)"
                        :title="t('edit', 'Edit Restock Quantity')"
                        :aria-label="t('edit')"
                      >
                        <span class="material-symbols-outlined">edit</span>
                      </button>

                      <!-- Expand Rationale -->
                      <button
                        class="btn-icon"
                        @click="toggleRationale(item.product_id)"
                        :title="t('rationale', 'View Decision Rationale')"
                        :aria-label="t('rationale')"
                      >
                        <span class="material-symbols-outlined" :class="{ 'rotate-180': expandedRationale[item.product_id] }">
                          expand_more
                        </span>
                      </button>

                      <!-- Dismiss / Reject -->
                      <button
                        class="btn-icon btn-icon-danger"
                        @click="rejectSuggestion(item)"
                        :title="t('dismiss', 'Dismiss')"
                        :aria-label="t('dismiss')"
                      >
                        <span class="material-symbols-outlined">close</span>
                      </button>
                    </div>
                  </td>
                </tr>

                <!-- Expandable Rationale Row -->
                <tr v-if="expandedRationale[item.product_id]" class="bg-gray-50/80 border-t border-b border-gray-200">
                  <td colspan="9" class="p-4">
                    <div class="bg-white p-4 rounded-lg border border-gray-200 shadow-sm">
                      <div class="flex items-center gap-2 mb-2">
                        <span class="material-symbols-outlined text-primary-600 text-lg">psychology</span>
                        <h4 class="font-semibold text-gray-800 text-sm">{{ t('ai-rationale-title', 'AI Forecasting Decision Rationale') }}</h4>
                      </div>
                      <pre class="text-xs text-gray-700 whitespace-pre-wrap font-sans leading-relaxed">{{ item.rationale }}</pre>
                    </div>
                  </td>
                </tr>
              </template>
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <!-- MODAL 1: CUSTOMIZE CONSOLIDATED SUPPLIER DRAFT PO -->
    <div v-if="showSupplierEditModal" class="modal-overlay" @click.self="closeSupplierEditModal">
      <div class="modal-content max-w-3xl">
        <div class="modal-header">
          <h3 class="font-semibold text-lg flex items-center gap-2">
            <span class="material-symbols-outlined text-primary-600">edit_note</span>
            {{ t('customize-supplier-po', 'Customize Consolidated Supplier Purchase Order') }}
          </h3>
          <button class="btn-icon" @click="closeSupplierEditModal" aria-label="Close">
            <span class="material-symbols-outlined">close</span>
          </button>
        </div>

        <div class="modal-body space-y-4">
          <div class="p-3 bg-gray-50 rounded border border-gray-200 text-sm flex justify-between items-center">
            <div>
              <div class="font-bold text-gray-900 text-base">{{ currentSupplierEdit?.supplier_name || 'Supplier' }}</div>
              <div class="text-xs text-gray-500">
                Lead Time: {{ currentSupplierEdit?.lead_time_days }} days • {{ supplierEditForm.items.length }} line items
              </div>
            </div>
            <div class="text-right">
              <span class="text-xs font-medium text-gray-500">Calculated PO Total:</span>
              <div class="text-xl font-bold text-emerald-700">${{ formatMoney(supplierEditTotal) }}</div>
            </div>
          </div>

          <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div class="form-group">
              <label>{{ t('expected-delivery', 'Expected Delivery Date') }}</label>
              <input
                type="date"
                v-model="supplierEditForm.expected_date"
                class="form-input"
              />
            </div>
            <div class="form-group">
              <label>{{ t('po-notes', 'Purchase Order Notes & Rationale') }}</label>
              <input
                type="text"
                v-model="supplierEditForm.notes"
                class="form-input text-sm"
                placeholder="Custom PO notes or rationale..."
              />
            </div>
          </div>

          <!-- Items Table -->
          <div class="border border-gray-200 rounded-lg overflow-hidden">
            <table class="w-full text-sm text-left">
              <thead class="bg-gray-100 text-xs uppercase font-semibold text-gray-600 border-b border-gray-200">
                <tr>
                  <th class="p-2.5">Product & SKU</th>
                  <th class="p-2.5 text-right w-28">Order Qty</th>
                  <th class="p-2.5 text-right w-28">Unit Price ($)</th>
                  <th class="p-2.5 text-right w-32">Line Total ($)</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-gray-200">
                <tr v-for="it in supplierEditForm.items" :key="it.product_id">
                  <td class="p-2.5">
                    <div class="font-semibold text-gray-800">{{ it.product_name }}</div>
                    <div class="text-xs text-gray-500 font-mono">{{ it.sku }}</div>
                  </td>
                  <td class="p-2.5 text-right">
                    <input
                      type="number"
                      v-model.number="it.qty"
                      min="1"
                      step="1"
                      class="form-input text-right py-1 px-2 text-sm"
                    />
                  </td>
                  <td class="p-2.5 text-right">
                    <input
                      type="number"
                      v-model.number="it.unit_price"
                      min="0"
                      step="0.01"
                      class="form-input text-right py-1 px-2 text-sm"
                    />
                  </td>
                  <td class="p-2.5 text-right font-bold text-gray-900">
                    ${{ formatMoney((it.qty || 0) * (it.unit_price || 0)) }}
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        <div class="modal-footer flex justify-end gap-2">
          <button class="btn-secondary" @click="closeSupplierEditModal">
            {{ t('cancel', 'Cancel') }}
          </button>
          <button
            class="btn-primary bg-emerald-600 hover:bg-emerald-700 text-white"
            @click="submitSupplierEdit"
            :disabled="submittingSupplierEdit || supplierEditTotal <= 0"
          >
            <span class="material-symbols-outlined text-sm">check</span>
            {{ submittingSupplierEdit ? t('saving', 'Creating PO...') : t('confirm-create-po', 'Confirm & Generate Draft PO') }}
          </button>
        </div>
      </div>
    </div>

    <!-- MODAL 2: EDIT SINGLE SKU RESTOCK MODAL -->
    <div v-if="showEditModal" class="modal-overlay" @click.self="closeEditModal">
      <div class="modal-content max-w-lg">
        <div class="modal-header">
          <h3 class="font-semibold text-lg flex items-center gap-2">
            <span class="material-symbols-outlined text-primary-600">edit_note</span>
            {{ t('edit-restock-order', 'Customize Restock Purchase Order') }}
          </h3>
          <button class="btn-icon" @click="closeEditModal" aria-label="Close">
            <span class="material-symbols-outlined">close</span>
          </button>
        </div>

        <div class="modal-body space-y-4">
          <div class="p-3 bg-gray-50 rounded border border-gray-200 text-sm">
            <div class="font-semibold text-gray-900">{{ currentEditItem?.product_name }}</div>
            <div class="text-xs text-gray-500 font-mono">{{ currentEditItem?.sku }}</div>
          </div>

          <div class="form-row flex gap-4">
            <div class="form-group flex-1">
              <label>{{ t('suggested-order-qty', 'Order Quantity') }} <span class="required">*</span></label>
              <input
                type="number"
                v-model.number="editForm.qty"
                min="1"
                step="1"
                required
                class="form-input"
              />
              <span class="text-xs text-gray-500 mt-1 block">
                MOQ: {{ currentEditItem?.min_order_qty || 1 }} units
              </span>
            </div>

            <div class="form-group flex-1">
              <label>{{ t('unit-price', 'Unit Cost ($)') }}</label>
              <input
                type="number"
                v-model.number="editForm.unit_price"
                min="0"
                step="0.01"
                class="form-input"
              />
            </div>
          </div>

          <div class="form-group">
            <label>{{ t('supplier', 'Supplier') }}</label>
            <select v-model.number="editForm.supplier_id" class="form-input">
              <option v-for="s in suppliers" :key="s.id" :value="s.id">
                {{ s.name }}
              </option>
            </select>
          </div>

          <div class="form-group">
            <label>{{ t('expected-date', 'Expected Delivery Date') }}</label>
            <input
              type="date"
              v-model="editForm.expected_date"
              class="form-input"
            />
          </div>

          <div class="form-group">
            <label>{{ t('notes-rationale', 'PO Notes & Rationale') }}</label>
            <textarea
              v-model="editForm.notes"
              rows="3"
              class="form-input font-sans text-xs"
            ></textarea>
          </div>

          <div class="p-3 bg-primary-50 rounded-lg flex justify-between items-center">
            <span class="text-xs font-medium text-primary-800">{{ t('estimated-total', 'Estimated Order Total:') }}</span>
            <span class="text-lg font-bold text-primary-900">
              ${{ formatMoney((editForm.qty || 0) * (editForm.unit_price || 0)) }}
            </span>
          </div>
        </div>

        <div class="modal-footer flex justify-end gap-2">
          <button class="btn-secondary" @click="closeEditModal">
            {{ t('cancel', 'Cancel') }}
          </button>
          <button
            class="btn-primary"
            @click="submitEdit"
            :disabled="submittingEdit || !editForm.qty || editForm.qty <= 0"
          >
            <span class="material-symbols-outlined text-sm">check</span>
            {{ submittingEdit ? t('saving', 'Creating PO...') : t('create-draft-po', 'Create Draft PO') }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from '../../composables/useI18n.js'
import SkeletonTable from '../../components/SkeletonTable.vue'
import ErrorState from '../../components/ErrorState.vue'
import { api } from '../../api/client.js'

const router = useRouter()
const { t, dir } = useI18n()

const viewMode = ref('supplier-queue') // 'supplier-queue' | 'sku-suggestions'
const loading = ref(false)
const runningForecast = ref(false)
const approvingAll = ref(false)
const error = ref('')
const successMsg = ref('')

const suggestions = ref([])
const supplierQueue = ref([])
const suppliers = ref([])
const summary = ref({
  total_evaluated: 0,
  at_risk_count: 0,
  critical_count: 0,
  high_count: 0,
  medium_count: 0,
  total_suggested_qty: 0,
  total_estimated_spend: 0,
  total_suppliers: 0,
  total_items: 0,
})

const searchQuery = ref('')
const actionLoading = reactive({})
const expandedRationale = reactive({})
const expandedSuppliers = reactive({})

const filters = reactive({
  days: 30,
  safety_margin_days: 7,
  target_coverage_days: 30,
  only_at_risk: true,
})

// Single SKU Edit modal state
const showEditModal = ref(false)
const currentEditItem = ref(null)
const submittingEdit = ref(false)
const editForm = reactive({
  qty: 1,
  unit_price: 0,
  supplier_id: 1,
  expected_date: '',
  notes: '',
})

// Supplier PO Edit modal state
const showSupplierEditModal = ref(false)
const currentSupplierEdit = ref(null)
const submittingSupplierEdit = ref(false)
const supplierEditForm = reactive({
  expected_date: '',
  notes: '',
  items: [],
})

const filteredSuggestions = computed(() => {
  if (!searchQuery.value.trim()) return suggestions.value
  const q = searchQuery.value.toLowerCase()
  return suggestions.value.filter(s =>
    (s.product_name && s.product_name.toLowerCase().includes(q)) ||
    (s.sku && s.sku.toLowerCase().includes(q)) ||
    (s.supplier_name && s.supplier_name.toLowerCase().includes(q))
  )
})

const filteredSupplierQueue = computed(() => {
  if (!searchQuery.value.trim()) return supplierQueue.value
  const q = searchQuery.value.toLowerCase()
  return supplierQueue.value.filter(g =>
    (g.supplier_name && g.supplier_name.toLowerCase().includes(q)) ||
    (g.items && g.items.some(it =>
      (it.product_name && it.product_name.toLowerCase().includes(q)) ||
      (it.sku && it.sku.toLowerCase().includes(q))
    ))
  )
})

const supplierEditTotal = computed(() => {
  if (!supplierEditForm.items) return 0
  return supplierEditForm.items.reduce((sum, item) => sum + ((item.qty || 0) * (item.unit_price || 0)), 0)
})

async function loadSuppliers() {
  try {
    const res = await api.get('/T0011I/')
    suppliers.value = Array.isArray(res.data) ? res.data : (res.data?.items || [])
  } catch (e) {
    console.warn('Failed to load suppliers:', e)
  }
}

async function loadData() {
  loading.value = true
  error.value = ''
  try {
    const [resSuggestions, resQueue] = await Promise.all([
      api.get('/purchasing/restock/suggestions', {
        params: {
          days: filters.days,
          safety_margin_days: filters.safety_margin_days,
          target_coverage_days: filters.target_coverage_days,
          only_at_risk: filters.only_at_risk,
        },
      }),
      api.get('/purchasing/restock/supplier-queue', {
        params: {
          days: filters.days,
          safety_margin_days: filters.safety_margin_days,
          target_coverage_days: filters.target_coverage_days,
          only_at_risk: filters.only_at_risk,
        },
      }),
    ])

    if (resSuggestions.data) {
      summary.value = {
        ...(resSuggestions.data.summary || {}),
        ...(resQueue.data?.summary || {}),
      }
      suggestions.value = Array.isArray(resSuggestions.data.suggestions) ? resSuggestions.data.suggestions : []
    }

    if (resQueue.data) {
      const q = Array.isArray(resQueue.data.supplier_queue) ? resQueue.data.supplier_queue : []
      supplierQueue.value = q
      // Expand all suppliers by default
      q.forEach(g => {
        if (expandedSuppliers[g.supplier_id] === undefined) {
          expandedSuppliers[g.supplier_id] = true
        }
      })
    }
  } catch (err) {
    console.error('Failed to load restock data:', err)
    error.value = err.response?.data?.detail || err.message || 'Failed to load restock recommendations'
  } finally {
    loading.value = false
  }
}

async function runForecast() {
  runningForecast.value = true
  error.value = ''
  try {
    const res = await api.post('/purchasing/restock/run-forecast', {
      days: filters.days,
      safety_margin_days: filters.safety_margin_days,
      target_coverage_days: filters.target_coverage_days,
      send_notification: false,
    })
    successMsg.value = `AI demand forecast completed! Evaluated ${res.data.total_skus_evaluated} SKUs; found ${res.data.at_risk_count} restock recommendations.`
    await loadData()
  } catch (err) {
    console.error('Failed to run forecast:', err)
    error.value = err.response?.data?.detail || err.message || 'Failed to execute demand forecast'
  } finally {
    runningForecast.value = false
  }
}

function toggleSupplierExpand(supplierId) {
  expandedSuppliers[supplierId] = !expandedSuppliers[supplierId]
}

async function approveSupplierQueue(group) {
  const supId = group.supplier_id
  actionLoading['sup_' + supId] = true
  try {
    const res = await api.post(`/purchasing/restock/supplier-queue/${supId}/approve`, {
      supplier_id: supId,
    })
    const poNumber = res.data.purchase_order?.order_number || 'PO'
    successMsg.value = `Draft Purchase Order ${poNumber} generated for ${group.supplier_name || 'Supplier'} (${res.data.total_items} items, $${formatMoney(res.data.total_amount)})`
    await loadData()
  } catch (err) {
    console.error('Failed to approve supplier queue:', err)
    alert(err.response?.data?.detail || 'Failed to generate draft purchase order')
  } finally {
    actionLoading['sup_' + supId] = false
  }
}

async function approveAllSuppliers() {
  if (!confirm(`Are you sure you want to generate consolidated draft Purchase Orders for all ${supplierQueue.value.length} suppliers?`)) {
    return
  }

  approvingAll.value = true
  try {
    const res = await api.post('/purchasing/restock/supplier-queue/approve-all', null, {
      params: {
        days: filters.days,
        safety_margin_days: filters.safety_margin_days,
        target_coverage_days: filters.target_coverage_days,
      },
    })
    successMsg.value = res.data.message || `Successfully generated ${res.data.total_pos} consolidated draft purchase orders!`
    await loadData()
  } catch (err) {
    console.error('Failed to approve all suppliers:', err)
    alert(err.response?.data?.detail || 'Failed to batch generate purchase orders')
  } finally {
    approvingAll.value = false
  }
}

function openSupplierEditModal(group) {
  currentSupplierEdit.value = group
  supplierEditForm.expected_date = group.expected_date || ''
  supplierEditForm.notes = group.po_notes || ''
  supplierEditForm.items = group.items.map(it => ({
    product_id: it.product_id,
    product_name: it.product_name,
    sku: it.sku,
    qty: it.suggested_order_qty || it.min_order_qty || 1,
    unit_price: it.unit_cost || 0,
  }))
  showSupplierEditModal.value = true
}

function closeSupplierEditModal() {
  showSupplierEditModal.value = false
  currentSupplierEdit.value = null
}

async function submitSupplierEdit() {
  if (!currentSupplierEdit.value) return
  submittingSupplierEdit.value = true
  const supId = currentSupplierEdit.value.supplier_id

  try {
    const payload = {
      supplier_id: supId,
      expected_date: supplierEditForm.expected_date || undefined,
      notes: supplierEditForm.notes,
      items: supplierEditForm.items.map(it => ({
        product_id: it.product_id,
        product_name: it.product_name,
        qty: it.qty,
        unit_price: it.unit_price,
      })),
    }

    const res = await api.post(`/purchasing/restock/supplier-queue/${supId}/approve`, payload)
    const poNumber = res.data.purchase_order?.order_number || 'PO'
    successMsg.value = `Customized Draft Purchase Order ${poNumber} generated successfully with ${res.data.total_items} items ($${formatMoney(res.data.total_amount)})`
    closeSupplierEditModal()
    await loadData()
  } catch (err) {
    console.error('Failed to create customized supplier PO:', err)
    alert(err.response?.data?.detail || 'Failed to create customized draft purchase order')
  } finally {
    submittingSupplierEdit.value = false
  }
}

async function approveSuggestion(item) {
  const pId = item.product_id
  actionLoading[pId] = true
  try {
    const res = await api.post(`/purchasing/restock/suggestions/${pId}/approve`)
    const poNumber = res.data.purchase_order?.order_number || 'PO'
    successMsg.value = `${t('restock-approved-success', 'Draft Purchase Order')} ${poNumber} created successfully.`
    suggestions.value = suggestions.value.filter(s => s.product_id !== pId)
    if (summary.value.at_risk_count) summary.value.at_risk_count -= 1
    await loadData()
  } catch (err) {
    console.error('Failed to approve suggestion:', err)
    alert(err.response?.data?.detail || 'Failed to approve restock suggestion')
  } finally {
    actionLoading[pId] = false
  }
}

async function rejectSuggestion(item) {
  const pId = item.product_id
  try {
    await api.post(`/purchasing/restock/suggestions/${pId}/reject`, {
      reason: 'Dismissed by purchasing manager',
    })
    suggestions.value = suggestions.value.filter(s => s.product_id !== pId)
    if (summary.value.at_risk_count) summary.value.at_risk_count -= 1
    successMsg.value = `${t('restock-rejected-success', 'Restock suggestion dismissed for')} ${item.sku}.`
  } catch (err) {
    console.error('Failed to dismiss suggestion:', err)
  }
}

function toggleRationale(id) {
  expandedRationale[id] = !expandedRationale[id]
}

function openEditModal(item) {
  currentEditItem.value = item
  editForm.qty = item.suggested_order_qty || item.min_order_qty || 1
  editForm.unit_price = item.unit_cost || 0
  editForm.supplier_id = item.supplier_id || (suppliers.value[0]?.id || 1)
  editForm.expected_date = item.projected_stockout_date || ''
  editForm.notes = item.rationale || ''
  showEditModal.value = true
}

function closeEditModal() {
  showEditModal.value = false
  currentEditItem.value = null
}

async function submitEdit() {
  if (!currentEditItem.value) return
  submittingEdit.value = true
  const pId = currentEditItem.value.product_id

  try {
    const res = await api.post(`/purchasing/restock/suggestions/${pId}/edit`, {
      qty: editForm.qty,
      unit_price: editForm.unit_price,
      supplier_id: editForm.supplier_id,
      expected_date: editForm.expected_date || undefined,
      notes: editForm.notes,
    })

    const poNumber = res.data.purchase_order?.order_number || 'PO'
    successMsg.value = `${t('restock-approved-success', 'Draft Purchase Order')} ${poNumber} created successfully.`
    suggestions.value = suggestions.value.filter(s => s.product_id !== pId)
    if (summary.value.at_risk_count) summary.value.at_risk_count -= 1
    closeEditModal()
    await loadData()
  } catch (err) {
    console.error('Failed to create customized PO:', err)
    alert(err.response?.data?.detail || 'Failed to create purchase order')
  } finally {
    submittingEdit.value = false
  }
}

function urgencyBadge(urgency) {
  switch (urgency) {
    case 'CRITICAL':
      return 'badge-danger font-bold animate-pulse'
    case 'HIGH':
      return 'badge-warning font-semibold'
    case 'MEDIUM':
      return 'badge-info'
    case 'HEALTHY':
      return 'badge-success'
    default:
      return 'badge-secondary'
  }
}

function formatMoney(v) {
  return Number(v || 0).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

function formatUnits(v) {
  return Number(v || 0).toLocaleString('en-US')
}

onMounted(() => {
  loadSuppliers()
  loadData()
})
</script>

<style scoped>
.restock-view {
  width: 100%;
}

.kpi-card {
  background: white;
  padding: 1.25rem;
  border-radius: 0.75rem;
  border: 1px solid #e5e7eb;
  box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.05);
}

.kpi-label {
  font-size: 0.8125rem;
  font-weight: 500;
  color: #6b7280;
}

.kpi-value {
  font-size: 1.625rem;
  font-weight: 700;
  margin-top: 0.25rem;
  line-height: 1.2;
}

.kpi-subtext {
  font-size: 0.75rem;
}
</style>
