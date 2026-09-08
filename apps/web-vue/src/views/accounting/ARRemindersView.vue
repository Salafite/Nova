<template>
  <div class="page" :dir="dir">
    <!-- Header -->
    <div class="page-head">
      <div>
        <h1 class="page-title">{{ t('ar-reminders-title', 'AR Reminders & Statement Dispatch') }}</h1>
        <p class="page-subtitle">{{ t('ar-reminders-sub', 'Configure automated collection rules, customize message templates, and run batch dispatches via WhatsApp & Email') }}</p>
      </div>
      <div class="flex items-center gap-2">
        <button class="btn-outline" @click="openRunBatchModal">
          <span class="material-symbols-outlined">bolt</span>
          {{ t('run-batch-reminders', 'Run Batch Evaluation') }}
        </button>
        <button v-if="activeTab === 'rules'" class="btn-primary" @click="openAddRuleModal">
          <span class="material-symbols-outlined">add</span>
          {{ t('new-reminder-rule', 'New Rule') }}
        </button>
        <button v-else-if="activeTab === 'templates'" class="btn-primary" @click="openAddTemplateModal">
          <span class="material-symbols-outlined">add</span>
          {{ t('new-template', 'New Template') }}
        </button>
        <button v-else-if="activeTab === 'dispatch'" class="btn-primary" @click="openQuickDispatchModal">
          <span class="material-symbols-outlined">send</span>
          {{ t('quick-dispatch', 'Dispatch Reminder') }}
        </button>
      </div>
    </div>

    <!-- Summary Metrics -->
    <div class="stats-row">
      <div class="stat-card">
        <span class="stat-value text-danger">${{ formatCurrency(summary.total_overdue || 0) }}</span>
        <span class="stat-label">{{ t('total-overdue-ar', 'Total Overdue AR') }}</span>
      </div>
      <div class="stat-card">
        <span class="stat-value">{{ summary.overdue_customers_count || 0 }}</span>
        <span class="stat-label">{{ t('overdue-customers', 'Overdue Accounts') }}</span>
      </div>
      <div class="stat-card">
        <span class="stat-value">{{ activeRulesCount }}</span>
        <span class="stat-label">{{ t('active-rules', 'Active Rules') }}</span>
      </div>
      <div class="stat-card">
        <span class="stat-value">{{ templates.length }}</span>
        <span class="stat-label">{{ t('templates-count', 'Message Templates') }}</span>
      </div>
    </div>

    <!-- Aging Overview Bar -->
    <div v-if="summary.aging_breakdown" class="data-card mb-6 p-4">
      <div class="flex justify-between items-center mb-2">
        <h4 class="font-semibold text-sm text-gray-700">{{ t('portfolio-aging-breakdown', 'Portfolio Aging Breakdown') }}</h4>
        <span class="text-xs text-muted">{{ t('as-of-date', 'As of') }}: {{ summary.as_of_date || today() }}</span>
      </div>
      <div class="aging-summary-grid">
        <div class="aging-pill pill-current">
          <span class="pill-label">{{ t('current', 'Current (0-30d)') }}</span>
          <span class="pill-val">${{ formatCurrency(summary.aging_breakdown.current || 0) }}</span>
        </div>
        <div class="aging-pill pill-1-30">
          <span class="pill-label">{{ t('aging-1-30', '1–30 Days Overdue') }}</span>
          <span class="pill-val">${{ formatCurrency(summary.aging_breakdown['1_30'] || 0) }}</span>
        </div>
        <div class="aging-pill pill-31-60">
          <span class="pill-label">{{ t('aging-31-60', '31–60 Days Overdue') }}</span>
          <span class="pill-val">${{ formatCurrency(summary.aging_breakdown['31_60'] || 0) }}</span>
        </div>
        <div class="aging-pill pill-61-90">
          <span class="pill-label">{{ t('aging-61-90', '61–90 Days Overdue') }}</span>
          <span class="pill-val">${{ formatCurrency(summary.aging_breakdown['61_90'] || 0) }}</span>
        </div>
        <div class="aging-pill pill-90-plus">
          <span class="pill-label">{{ t('aging-90-plus', '90+ Days Overdue') }}</span>
          <span class="pill-val text-danger font-bold">${{ formatCurrency(summary.aging_breakdown['90_plus'] || 0) }}</span>
        </div>
      </div>
    </div>

    <!-- Navigation Tabs -->
    <div class="tabs">
      <button class="tab" :class="{ active: activeTab === 'rules' }" @click="activeTab = 'rules'">
        <span class="material-symbols-outlined tab-icon">tune</span>
        {{ t('reminder-rules-tab', 'Reminder Rules') }} ({{ rules.length }})
      </button>
      <button class="tab" :class="{ active: activeTab === 'templates' }" @click="activeTab = 'templates'">
        <span class="material-symbols-outlined tab-icon">chat</span>
        {{ t('message-templates-tab', 'Message Templates') }} ({{ templates.length }})
      </button>
      <button class="tab" :class="{ active: activeTab === 'batch' }" @click="activeTab = 'batch'">
        <span class="material-symbols-outlined tab-icon">play_circle</span>
        {{ t('batch-engine-tab', 'Batch Evaluation') }}
      </button>
      <button class="tab" :class="{ active: activeTab === 'dispatch' }" @click="activeTab = 'dispatch'">
        <span class="material-symbols-outlined tab-icon">send</span>
        {{ t('manual-dispatch-tab', 'Manual Dispatch') }}
      </button>
    </div>

    <!-- Loading / Error States -->
    <SkeletonTable v-if="loading" />
    <ErrorState v-else-if="error" :message="error" @retry="loadAllData" />

    <!-- TAB 1: Reminder Rules -->
    <div v-else-if="activeTab === 'rules'">
      <div v-if="!rules.length" class="empty-state">
        <span class="material-symbols-outlined empty-icon">rule</span>
        <p>{{ t('no-reminder-rules', 'No AR reminder rules configured yet.') }}</p>
        <button class="btn-primary mt-4" @click="openAddRuleModal">{{ t('create-first-rule', 'Create First Rule') }}</button>
      </div>

      <div v-else class="data-card">
        <div class="table-wrap">
          <table class="data-table">
            <thead>
              <tr>
                <th>{{ t('rule-name', 'Rule Name') }}</th>
                <th>{{ t('trigger-type', 'Trigger Type') }}</th>
                <th>{{ t('threshold', 'Threshold / Schedule') }}</th>
                <th>{{ t('channel', 'Channel') }}</th>
                <th>{{ t('template', 'Template') }}</th>
                <th class="text-center">{{ t('statement-pdf', 'Statement PDF') }}</th>
                <th class="text-center">{{ t('payment-link', 'Payment Link') }}</th>
                <th class="text-center">{{ t('status', 'Status') }}</th>
                <th class="text-center">{{ t('actions', 'Actions') }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="rule in rules" :key="rule.id">
                <td>
                  <strong>{{ rule.rule_name || rule.name }}</strong>
                  <div v-if="rule.description" class="text-xs text-muted">{{ rule.description }}</div>
                </td>
                <td>
                  <span class="badge" :class="triggerBadgeClass(rule.trigger_type)">
                    {{ formatTriggerType(rule.trigger_type) }}
                  </span>
                </td>
                <td class="cell-mono font-medium">
                  <span v-if="rule.trigger_type === 'AGING_THRESHOLD'">{{ rule.threshold_days }} {{ t('days-overdue', 'days overdue') }}</span>
                  <span v-else-if="rule.trigger_type === 'STATEMENT_SCHEDULE'">{{ rule.frequency || 'WEEKLY' }}</span>
                  <span v-else>{{ rule.threshold_days || 0 }} {{ t('days', 'days') }}</span>
                </td>
                <td>
                  <span class="channel-badge" :class="'channel-' + (rule.channel || 'ALL').toLowerCase()">
                    <span class="material-symbols-outlined icon-xs">{{ channelIcon(rule.channel) }}</span>
                    {{ rule.channel || 'ALL' }}
                  </span>
                </td>
                <td>{{ getTemplateName(rule.template_id) }}</td>
                <td class="text-center">
                  <span v-if="rule.attach_statement_pdf" class="material-symbols-outlined text-success">check_circle</span>
                  <span v-else class="text-muted">-</span>
                </td>
                <td class="text-center">
                  <span v-if="rule.include_payment_link" class="material-symbols-outlined text-success">check_circle</span>
                  <span v-else class="text-muted">-</span>
                </td>
                <td class="text-center">
                  <span class="badge" :class="rule.is_active ? 'badge-active' : 'badge-disabled'">
                    {{ rule.is_active ? t('active', 'Active') : t('inactive', 'Inactive') }}
                  </span>
                </td>
                <td class="text-center">
                  <button class="btn-icon" @click="editRule(rule)" :title="t('edit', 'Edit')">
                    <span class="material-symbols-outlined">edit</span>
                  </button>
                  <button class="btn-icon text-primary" @click="testRule(rule)" :title="t('test-rule', 'Test Rule')">
                    <span class="material-symbols-outlined">play_arrow</span>
                  </button>
                  <button class="btn-icon btn-icon-danger" @click="confirmDeleteRule(rule)" :title="t('delete', 'Delete')">
                    <span class="material-symbols-outlined">delete</span>
                  </button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <!-- TAB 2: Message Templates -->
    <div v-else-if="activeTab === 'templates'">
      <div v-if="!templates.length" class="empty-state">
        <span class="material-symbols-outlined empty-icon">chat_bubble</span>
        <p>{{ t('no-templates', 'No reminder message templates configured yet.') }}</p>
        <button class="btn-primary mt-4" @click="openAddTemplateModal">{{ t('create-first-template', 'Create First Template') }}</button>
      </div>

      <div v-else class="data-card">
        <div class="table-wrap">
          <table class="data-table">
            <thead>
              <tr>
                <th>{{ t('template-code', 'Code') }}</th>
                <th>{{ t('template-name', 'Template Name') }}</th>
                <th>{{ t('channel', 'Channel') }}</th>
                <th>{{ t('subject-preview', 'Subject / Header') }}</th>
                <th>{{ t('body-preview', 'Body Preview') }}</th>
                <th class="text-center">{{ t('default', 'Default') }}</th>
                <th class="text-center">{{ t('status', 'Status') }}</th>
                <th class="text-center">{{ t('actions', 'Actions') }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="tmpl in templates" :key="tmpl.id">
                <td class="cell-mono font-bold">{{ tmpl.template_code }}</td>
                <td><strong>{{ tmpl.name }}</strong></td>
                <td>
                  <span class="channel-badge" :class="'channel-' + (tmpl.channel || 'EMAIL').toLowerCase()">
                    <span class="material-symbols-outlined icon-xs">{{ channelIcon(tmpl.channel) }}</span>
                    {{ tmpl.channel }}
                  </span>
                </td>
                <td class="truncate-cell">{{ tmpl.subject || tmpl.whatsapp_template_id || '-' }}</td>
                <td class="truncate-cell text-muted">{{ tmpl.body_text }}</td>
                <td class="text-center">
                  <span v-if="tmpl.is_default" class="badge badge-active">{{ t('default', 'Default') }}</span>
                  <span v-else class="text-muted">-</span>
                </td>
                <td class="text-center">
                  <span class="badge" :class="tmpl.is_active ? 'badge-active' : 'badge-disabled'">
                    {{ tmpl.is_active ? t('active', 'Active') : t('inactive', 'Inactive') }}
                  </span>
                </td>
                <td class="text-center">
                  <button class="btn-icon" @click="editTemplate(tmpl)" :title="t('edit', 'Edit')">
                    <span class="material-symbols-outlined">edit</span>
                  </button>
                  <button class="btn-icon btn-icon-danger" @click="confirmDeleteTemplate(tmpl)" :title="t('delete', 'Delete')">
                    <span class="material-symbols-outlined">delete</span>
                  </button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <!-- TAB 3: Batch Evaluation & Execution -->
    <div v-else-if="activeTab === 'batch'" class="batch-container">
      <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div class="data-card p-6 md:col-span-1">
          <h3 class="font-bold text-lg mb-4 text-gray-800">{{ t('batch-run-config', 'Run Batch Evaluation') }}</h3>
          
          <div class="form-group mb-4">
            <label class="font-medium text-sm">{{ t('select-rule', 'Select AR Rule') }}</label>
            <select v-model="batchForm.rule_id" class="form-input">
              <option :value="null">{{ t('all-active-rules', 'All Active Rules') }}</option>
              <option v-for="r in rules" :key="r.id" :value="r.id">{{ r.rule_name || r.name }}</option>
            </select>
          </div>

          <div class="form-group mb-4">
            <label class="font-medium text-sm">{{ t('as-of-date', 'As of Date') }}</label>
            <input type="date" v-model="batchForm.as_of_date" class="form-input" />
          </div>

          <div class="form-group mb-4">
            <label class="flex items-center gap-2 cursor-pointer">
              <input type="checkbox" v-model="batchForm.dry_run" class="checkbox" />
              <span class="text-sm font-semibold">{{ t('dry-run-preview', 'Dry Run (Preview Only, No Real Dispatch)') }}</span>
            </label>
            <p class="text-xs text-muted ml-6">{{ t('dry-run-desc', 'Calculates eligible candidate accounts and matching templates without sending actual emails or WhatsApp messages.') }}</p>
          </div>

          <div class="form-group mb-6">
            <label class="flex items-center gap-2 cursor-pointer">
              <input type="checkbox" v-model="batchForm.force" class="checkbox" />
              <span class="text-sm">{{ t('force-ignore-cooldown', 'Force (Ignore 3-day Cooldown)') }}</span>
            </label>
          </div>

          <button class="btn-primary w-full justify-center" :disabled="runningBatch" @click="runBatchReminders">
            <span class="material-symbols-outlined">bolt</span>
            {{ runningBatch ? t('evaluating', 'Evaluating Accounts...') : (batchForm.dry_run ? t('preview-batch', 'Preview Candidates') : t('execute-batch', 'Execute Live Dispatch')) }}
          </button>
        </div>

        <!-- Batch Results Display -->
        <div class="data-card p-6 md:col-span-2">
          <h3 class="font-bold text-lg mb-4 text-gray-800">{{ t('batch-results', 'Evaluation Results') }}</h3>
          
          <div v-if="!batchResult" class="empty-state py-12">
            <span class="material-symbols-outlined empty-icon">play_arrow</span>
            <p>{{ t('no-batch-run-yet', 'Configure options and click evaluate to view candidate accounts and dispatch summary.') }}</p>
          </div>

          <div v-else>
            <!-- Summary Counts -->
            <div class="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-6">
              <div class="stat-box bg-slate-50 p-3 rounded-lg border text-center">
                <span class="block text-2xl font-bold text-gray-800">{{ batchResult.total_evaluated || 0 }}</span>
                <span class="text-xs text-muted uppercase tracking-wider">{{ t('evaluated', 'Evaluated') }}</span>
              </div>
              <div class="stat-box bg-blue-50 p-3 rounded-lg border border-blue-200 text-center">
                <span class="block text-2xl font-bold text-blue-700">{{ batchResult.total_eligible || 0 }}</span>
                <span class="text-xs text-blue-600 uppercase tracking-wider">{{ t('eligible', 'Eligible') }}</span>
              </div>
              <div class="stat-box bg-green-50 p-3 rounded-lg border border-green-200 text-center">
                <span class="block text-2xl font-bold text-green-700">{{ batchResult.total_dispatched || 0 }}</span>
                <span class="text-xs text-green-600 uppercase tracking-wider">{{ t('dispatched', 'Dispatched') }}</span>
              </div>
              <div class="stat-box bg-amber-50 p-3 rounded-lg border border-amber-200 text-center">
                <span class="block text-2xl font-bold text-amber-700">{{ (batchResult.total_skipped_vip || 0) + (batchResult.total_skipped_excluded || 0) }}</span>
                <span class="text-xs text-amber-600 uppercase tracking-wider">{{ t('skipped-vip-excl', 'Skipped (VIP/Excl)') }}</span>
              </div>
            </div>

            <!-- Candidate Details Table -->
            <h4 class="font-semibold text-sm mb-2 text-gray-700">{{ t('dispatched-candidates-log', 'Dispatched / Candidate Accounts') }}</h4>
            <div class="table-wrap max-h-80 overflow-y-auto border rounded-lg">
              <table class="data-table">
                <thead>
                  <tr>
                    <th>{{ t('customer', 'Customer') }}</th>
                    <th>{{ t('matched-rule', 'Matched Rule') }}</th>
                    <th>{{ t('channel', 'Channel') }}</th>
                    <th class="text-center">{{ t('status', 'Status') }}</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="(item, idx) in (batchResult.dispatched_communications || [])" :key="idx">
                    <td>
                      <strong>{{ item.customer_name || `#${item.customer_id}` }}</strong>
                    </td>
                    <td>{{ item.rule_name || `Rule #${item.rule_id}` }}</td>
                    <td>
                      <span class="channel-badge" :class="'channel-' + (item.channel || 'EMAIL').toLowerCase()">
                        {{ item.channel }}
                      </span>
                    </td>
                    <td class="text-center">
                      <span class="badge badge-active">{{ item.status || 'READY' }}</span>
                    </td>
                  </tr>
                  <tr v-if="!batchResult.dispatched_communications || !batchResult.dispatched_communications.length">
                    <td colspan="4" class="text-center py-4 text-muted">{{ t('no-candidate-accounts', 'No candidate accounts met dispatch criteria.') }}</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- TAB 4: Manual Quick Dispatch -->
    <div v-else-if="activeTab === 'dispatch'" class="dispatch-container max-w-2xl mx-auto">
      <div class="data-card p-6">
        <h3 class="font-bold text-lg mb-4 text-gray-800">{{ t('manual-dispatch-title', 'Manual Customer Reminder & Statement Dispatch') }}</h3>
        
        <div class="form-row">
          <div class="form-group">
            <label class="font-medium text-sm">{{ t('customer', 'Target Customer') }} <span class="required">*</span></label>
            <select v-model="quickDispatchForm.customer_id" class="form-input">
              <option :value="null">{{ t('select-customer', '-- Select Customer --') }}</option>
              <option v-for="c in customers" :key="c.id" :value="c.id">
                {{ c.name }} (Bal: ${{ formatCurrency(c.balance || 0) }})
              </option>
            </select>
          </div>
          <div class="form-group">
            <label class="font-medium text-sm">{{ t('dispatch-mode', 'Dispatch Action') }} <span class="required">*</span></label>
            <select v-model="quickDispatchForm.mode" class="form-input">
              <option value="REMINDER">{{ t('send-ar-reminder', 'Send AR Collection Reminder') }}</option>
              <option value="STATEMENT">{{ t('send-statement-pdf', 'Send Account Statement PDF') }}</option>
            </select>
          </div>
        </div>

        <div class="form-row">
          <div class="form-group">
            <label class="font-medium text-sm">{{ t('delivery-channel', 'Delivery Channel') }} <span class="required">*</span></label>
            <select v-model="quickDispatchForm.channel" class="form-input">
              <option value="EMAIL">Email</option>
              <option value="WHATSAPP">WhatsApp</option>
              <option value="ALL">Both (Email & WhatsApp)</option>
            </select>
          </div>
          <div class="form-group" v-if="quickDispatchForm.mode === 'REMINDER'">
            <label class="font-medium text-sm">{{ t('message-template', 'Message Template') }}</label>
            <select v-model="quickDispatchForm.template_id" class="form-input">
              <option :value="null">{{ t('use-default-template', 'Use Default Template') }}</option>
              <option v-for="tmpl in templates" :key="tmpl.id" :value="tmpl.id">
                {{ tmpl.name }} ({{ tmpl.channel }})
              </option>
            </select>
          </div>
        </div>

        <div class="form-row" v-if="quickDispatchForm.mode === 'REMINDER'">
          <div class="form-group">
            <label class="flex items-center gap-2 cursor-pointer">
              <input type="checkbox" v-model="quickDispatchForm.attach_statement_pdf" class="checkbox" />
              <span class="text-sm font-medium">{{ t('attach-statement-pdf', 'Attach PDF Account Statement') }}</span>
            </label>
          </div>
          <div class="form-group">
            <label class="flex items-center gap-2 cursor-pointer">
              <input type="checkbox" v-model="quickDispatchForm.include_payment_link" class="checkbox" />
              <span class="text-sm font-medium">{{ t('include-payment-link', 'Include Direct Payment Link') }}</span>
            </label>
          </div>
        </div>

        <div class="form-group mb-4">
          <label class="font-medium text-sm">{{ t('custom-message-optional', 'Custom Note / Message Override (Optional)') }}</label>
          <textarea v-model="quickDispatchForm.custom_message" class="form-input h-24" :placeholder="t('custom-message-placeholder', 'Add optional special payment instructions or greeting...')"></textarea>
        </div>

        <div class="modal-actions pt-4 border-t">
          <button v-if="quickDispatchForm.customer_id" class="btn-outline" @click="downloadCustomerStatementPdf">
            <span class="material-symbols-outlined">download</span>
            {{ t('preview-pdf', 'Download Statement PDF') }}
          </button>
          <button class="btn-primary" :disabled="sendingDispatch || !quickDispatchForm.customer_id" @click="sendQuickDispatch">
            <span class="material-symbols-outlined">send</span>
            {{ sendingDispatch ? t('sending', 'Dispatching...') : t('send-now', 'Send Now') }}
          </button>
        </div>
      </div>
    </div>

    <!-- MODAL: Create / Edit Rule -->
    <div v-if="showRuleModal" class="modal-overlay" @click.self="showRuleModal = false">
      <div class="modal-content modal-lg">
        <div class="modal-header">
          <h3>{{ editingRule ? t('edit-reminder-rule', 'Edit AR Reminder Rule') : t('new-reminder-rule', 'New AR Reminder Rule') }}</h3>
          <button class="btn-icon" @click="showRuleModal = false" aria-label="Close"><span class="material-symbols-outlined">close</span></button>
        </div>
        <div class="modal-body">
          <div class="form-row">
            <div class="form-group">
              <label>{{ t('rule-name', 'Rule Name') }} <span class="required">*</span></label>
              <input type="text" v-model="ruleForm.rule_name" class="form-input" required placeholder="e.g. 30 Days Overdue Reminder" />
            </div>
            <div class="form-group">
              <label>{{ t('trigger-type', 'Trigger Type') }} <span class="required">*</span></label>
              <select v-model="ruleForm.trigger_type" class="form-input">
                <option value="AGING_THRESHOLD">{{ t('aging-threshold', 'Aging Threshold (Days Overdue)') }}</option>
                <option value="STATEMENT_SCHEDULE">{{ t('statement-schedule', 'Statement Schedule (Weekly/Monthly)') }}</option>
                <option value="DUE_DATE_OFFSET">{{ t('due-date-offset', 'Due Date Offset') }}</option>
              </select>
            </div>
          </div>

          <div class="form-group mb-4">
            <label>{{ t('description', 'Description') }}</label>
            <input type="text" v-model="ruleForm.description" class="form-input" placeholder="e.g. Automatic reminder with PDF statement" />
          </div>

          <div class="form-row">
            <div class="form-group">
              <label>{{ t('threshold-days', 'Threshold Days') }}</label>
              <input type="number" v-model.number="ruleForm.threshold_days" class="form-input" min="0" placeholder="30" />
            </div>
            <div class="form-group">
              <label>{{ t('frequency', 'Frequency') }}</label>
              <select v-model="ruleForm.frequency" class="form-input">
                <option value="DAILY">Daily</option>
                <option value="WEEKLY">Weekly</option>
                <option value="BIWEEKLY">Bi-weekly</option>
                <option value="MONTHLY">Monthly</option>
                <option value="ON_EVENT">On Event</option>
              </select>
            </div>
          </div>

          <div class="form-row">
            <div class="form-group">
              <label>{{ t('channel', 'Preferred Channel') }} <span class="required">*</span></label>
              <select v-model="ruleForm.channel" class="form-input">
                <option value="ALL">All (WhatsApp & Email)</option>
                <option value="WHATSAPP">WhatsApp Business</option>
                <option value="EMAIL">Email</option>
              </select>
            </div>
            <div class="form-group">
              <label>{{ t('template', 'Linked Message Template') }}</label>
              <select v-model="ruleForm.template_id" class="form-input">
                <option :value="null">{{ t('system-default', '-- System Default Template --') }}</option>
                <option v-for="t in templates" :key="t.id" :value="t.id">{{ t.name }} ({{ t.channel }})</option>
              </select>
            </div>
          </div>

          <div class="form-row">
            <div class="form-group">
              <label>{{ t('min-balance-threshold', 'Min Overdue Balance ($)') }}</label>
              <input type="number" step="0.01" min="0" v-model.number="ruleForm.min_balance_threshold" class="form-input" />
            </div>
            <div class="form-group">
              <label>{{ t('cooldown-days', 'Cooldown Between Reminders (Days)') }}</label>
              <input type="number" min="0" v-model.number="ruleForm.cooldown_days" class="form-input" />
            </div>
          </div>

          <div class="grid grid-cols-2 gap-4 my-4 p-4 bg-slate-50 rounded-lg border">
            <label class="flex items-center gap-2 cursor-pointer">
              <input type="checkbox" v-model="ruleForm.attach_statement_pdf" class="checkbox" />
              <span class="text-sm font-medium">{{ t('attach-statement-pdf', 'Attach Statement PDF') }}</span>
            </label>
            <label class="flex items-center gap-2 cursor-pointer">
              <input type="checkbox" v-model="ruleForm.include_payment_link" class="checkbox" />
              <span class="text-sm font-medium">{{ t('include-payment-link', 'Include Payment Link') }}</span>
            </label>
            <label class="flex items-center gap-2 cursor-pointer">
              <input type="checkbox" v-model="ruleForm.exclude_vip" class="checkbox" />
              <span class="text-sm font-medium">{{ t('exclude-vip-accounts', 'Exclude VIP Accounts') }}</span>
            </label>
            <label class="flex items-center gap-2 cursor-pointer">
              <input type="checkbox" v-model="ruleForm.is_active" class="checkbox" />
              <span class="text-sm font-semibold text-primary">{{ t('is-active', 'Rule Active') }}</span>
            </label>
          </div>

          <div class="modal-actions">
            <button class="btn-outline" @click="showRuleModal = false">{{ t('cancel', 'Cancel') }}</button>
            <button class="btn-primary" :disabled="savingRule" @click="saveRule">
              {{ savingRule ? t('saving', 'Saving...') : t('save-rule', 'Save Rule') }}
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- MODAL: Create / Edit Template -->
    <div v-if="showTemplateModal" class="modal-overlay" @click.self="showTemplateModal = false">
      <div class="modal-content modal-lg">
        <div class="modal-header">
          <h3>{{ editingTemplate ? t('edit-template', 'Edit Message Template') : t('new-template', 'New Message Template') }}</h3>
          <button class="btn-icon" @click="showTemplateModal = false" aria-label="Close"><span class="material-symbols-outlined">close</span></button>
        </div>
        <div class="modal-body">
          <div class="form-row">
            <div class="form-group">
              <label>{{ t('template-name', 'Template Name') }} <span class="required">*</span></label>
              <input type="text" v-model="templateForm.name" class="form-input" required placeholder="e.g. 30 Days Overdue Reminder" />
            </div>
            <div class="form-group">
              <label>{{ t('channel', 'Channel') }} <span class="required">*</span></label>
              <select v-model="templateForm.channel" class="form-input">
                <option value="EMAIL">Email</option>
                <option value="WHATSAPP">WhatsApp</option>
                <option value="SMS">SMS</option>
              </select>
            </div>
          </div>

          <div class="form-row">
            <div class="form-group">
              <label>{{ t('template-code', 'Template Code') }}</label>
              <input type="text" v-model="templateForm.template_code" class="form-input font-mono" placeholder="TMPL-EM-OVERDUE30" />
            </div>
            <div class="form-group" v-if="templateForm.channel === 'EMAIL'">
              <label>{{ t('email-subject', 'Email Subject Line') }} <span class="required">*</span></label>
              <input type="text" v-model="templateForm.subject" class="form-input" placeholder="e.g. Payment Reminder: Outstanding Balance for {customer_name}" />
            </div>
            <div class="form-group" v-else-if="templateForm.channel === 'WHATSAPP'">
              <label>{{ t('whatsapp-template-id', 'WhatsApp Template Name') }}</label>
              <input type="text" v-model="templateForm.whatsapp_template_id" class="form-input font-mono" placeholder="nova_ar_reminder_v1" />
            </div>
          </div>

          <div class="form-group mb-2">
            <label class="flex justify-between items-center">
              <span>{{ t('message-body', 'Message Body Template') }} <span class="required">*</span></span>
              <span class="text-xs text-muted">{{ t('insert-variables', 'Click placeholder pills below to insert') }}</span>
            </label>
            <textarea v-model="templateForm.body_text" class="form-input h-36 font-mono text-sm" required placeholder="Dear {customer_name}, your balance of {balance} is overdue..."></textarea>
          </div>

          <!-- Variable Placeholders Helper -->
          <div class="variables-bar mb-4">
            <span class="text-xs font-semibold text-gray-500 mr-2">{{ t('placeholders', 'Variables:') }}</span>
            <button v-for="tag in availableVariables" :key="tag" class="var-chip" type="button" @click="insertVariable(tag)">
              {{ tag }}
            </button>
          </div>

          <div class="flex items-center gap-6 my-3 p-3 bg-slate-50 rounded border">
            <label class="flex items-center gap-2 cursor-pointer">
              <input type="checkbox" v-model="templateForm.is_default" class="checkbox" />
              <span class="text-sm font-medium">{{ t('is-channel-default', 'Default Template for this Channel') }}</span>
            </label>
            <label class="flex items-center gap-2 cursor-pointer">
              <input type="checkbox" v-model="templateForm.is_active" class="checkbox" />
              <span class="text-sm font-semibold text-primary">{{ t('is-active', 'Active') }}</span>
            </label>
          </div>

          <div class="modal-actions">
            <button class="btn-outline" @click="showTemplateModal = false">{{ t('cancel', 'Cancel') }}</button>
            <button class="btn-primary" :disabled="savingTemplate" @click="saveTemplate">
              {{ savingTemplate ? t('saving', 'Saving...') : t('save-template', 'Save Template') }}
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- MODAL: Confirm Delete -->
    <div v-if="showDeleteModal" class="modal-overlay" @click.self="showDeleteModal = false">
      <div class="modal-content modal-sm">
        <div class="modal-header">
          <h3>{{ t('confirm-delete', 'Confirm Deletion') }}</h3>
          <button class="btn-icon" @click="showDeleteModal = false" aria-label="Close"><span class="material-symbols-outlined">close</span></button>
        </div>
        <div class="modal-body">
          <p class="delete-text">{{ t('delete-confirm-msg', 'Are you sure you want to delete') }} <strong>{{ deleteTargetName }}</strong>?</p>
          <div class="modal-actions">
            <button class="btn-outline" @click="showDeleteModal = false">{{ t('cancel', 'Cancel') }}</button>
            <button class="btn-danger" :disabled="deletingItem" @click="executeDelete">
              {{ deletingItem ? t('deleting', 'Deleting...') : t('delete', 'Delete') }}
            </button>
          </div>
        </div>
      </div>
    </div>

  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { api } from '../../api/client.js'
import { useToast } from '../../composables/useToast.js'
import { useI18n } from '../../composables/useI18n.js'
import SkeletonTable from '../../components/SkeletonTable.vue'
import ErrorState from '../../components/ErrorState.vue'

const { show: toast } = useToast()
const { t, dir } = useI18n()

const loading = ref(true)
const error = ref('')
const activeTab = ref('rules')

const rules = ref([])
const templates = ref([])
const customers = ref([])
const summary = ref({
  total_overdue: 0,
  overdue_customers_count: 0,
  aging_breakdown: { current: 0, '1_30': 0, '31_60': 0, '61_90': 0, '90_plus': 0 },
})

// Rule modal state
const showRuleModal = ref(false)
const editingRule = ref(false)
const savingRule = ref(false)
const ruleEditId = ref(null)
const ruleForm = ref({
  rule_name: '',
  description: '',
  trigger_type: 'AGING_THRESHOLD',
  threshold_days: 30,
  frequency: 'WEEKLY',
  channel: 'ALL',
  template_id: null,
  min_balance_threshold: 0,
  cooldown_days: 3,
  attach_statement_pdf: true,
  include_payment_link: true,
  exclude_vip: true,
  exclude_disputed: true,
  is_active: true,
})

// Template modal state
const showTemplateModal = ref(false)
const editingTemplate = ref(false)
const savingTemplate = ref(false)
const templateEditId = ref(null)
const templateForm = ref({
  name: '',
  template_code: '',
  channel: 'EMAIL',
  subject: '',
  body_text: '',
  whatsapp_template_id: '',
  whatsapp_language_code: 'en_US',
  is_default: false,
  is_active: true,
})

// Batch run state
const runningBatch = ref(false)
const batchResult = ref(null)
const batchForm = ref({
  rule_id: null,
  as_of_date: today(),
  dry_run: true,
  force: false,
})

// Quick dispatch state
const sendingDispatch = ref(false)
const quickDispatchForm = ref({
  customer_id: null,
  mode: 'REMINDER',
  channel: 'EMAIL',
  template_id: null,
  attach_statement_pdf: true,
  include_payment_link: true,
  custom_message: '',
})

// Delete modal state
const showDeleteModal = ref(false)
const deletingItem = ref(false)
const deleteType = ref('rule') // 'rule' | 'template'
const deleteTargetId = ref(null)
const deleteTargetName = ref('')

const availableVariables = [
  '{customer_name}',
  '{company_name}',
  '{balance}',
  '{overdue_amount}',
  '{invoice_count}',
  '{oldest_due_date}',
  '{payment_link}',
  '{statement_link}',
]

const activeRulesCount = computed(() => rules.value.filter(r => r.is_active).length)

function today() {
  return new Date().toISOString().split('T')[0]
}

function formatCurrency(val) {
  return Number(val || 0).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

function channelIcon(channel) {
  if (channel === 'WHATSAPP') return 'chat'
  if (channel === 'EMAIL') return 'mail'
  if (channel === 'SMS') return 'sms'
  return 'campaign'
}

function formatTriggerType(type) {
  if (type === 'AGING_THRESHOLD') return 'Aging Threshold'
  if (type === 'STATEMENT_SCHEDULE') return 'Statement Schedule'
  if (type === 'DUE_DATE_OFFSET') return 'Due Date Offset'
  return type || 'Threshold'
}

function triggerBadgeClass(type) {
  if (type === 'AGING_THRESHOLD') return 'badge-warning'
  if (type === 'STATEMENT_SCHEDULE') return 'badge-info'
  return 'badge-secondary'
}

function getTemplateName(tmplId) {
  if (!tmplId) return t('system-default', 'System Default')
  const tmpl = templates.value.find(t => t.id === tmplId)
  return tmpl ? tmpl.name : `#${tmplId}`
}

function insertVariable(tag) {
  templateForm.value.body_text = (templateForm.value.body_text || '') + tag
}

// ----------------------------------------------------------------------
// Data Loading
// ----------------------------------------------------------------------
async function loadAllData() {
  loading.value = true
  error.value = ''
  try {
    const [rulesRes, tmplRes, summaryRes, custRes] = await Promise.all([
      api.get('/accounting/reminder-rules'),
      api.get('/accounting/reminder-templates'),
      api.get('/accounting/reminders/summary').catch(() => ({ data: {} })),
      api.get('/T0010I/').catch(() => ({ data: [] })),
    ])
    rules.value = rulesRes.data || []
    templates.value = tmplRes.data || []
    summary.value = summaryRes.data || {}
    customers.value = custRes.data || []
  } catch (err) {
    error.value = t('failed-load-reminders', 'Failed to load AR reminder data.')
    console.error(err)
  } finally {
    loading.value = false
  }
}

// ----------------------------------------------------------------------
// Rules Actions
// ----------------------------------------------------------------------
function openAddRuleModal() {
  editingRule.value = false
  ruleEditId.value = null
  ruleForm.value = {
    rule_name: '',
    description: '',
    trigger_type: 'AGING_THRESHOLD',
    threshold_days: 30,
    frequency: 'WEEKLY',
    channel: 'ALL',
    template_id: null,
    min_balance_threshold: 0,
    cooldown_days: 3,
    attach_statement_pdf: true,
    include_payment_link: true,
    exclude_vip: true,
    exclude_disputed: true,
    is_active: true,
  }
  showRuleModal.value = true
}

function editRule(rule) {
  editingRule.value = true
  ruleEditId.value = rule.id
  ruleForm.value = {
    rule_name: rule.rule_name || rule.name || '',
    description: rule.description || '',
    trigger_type: rule.trigger_type || 'AGING_THRESHOLD',
    threshold_days: rule.threshold_days != null ? rule.threshold_days : 30,
    frequency: rule.frequency || 'WEEKLY',
    channel: rule.channel || 'ALL',
    template_id: rule.template_id || null,
    min_balance_threshold: rule.min_balance_threshold || 0,
    cooldown_days: rule.cooldown_days != null ? rule.cooldown_days : 3,
    attach_statement_pdf: rule.attach_statement_pdf !== false,
    include_payment_link: rule.include_payment_link !== false,
    exclude_vip: rule.exclude_vip !== false,
    exclude_disputed: rule.exclude_disputed !== false,
    is_active: rule.is_active !== false,
  }
  showRuleModal.value = true
}

async function saveRule() {
  if (!ruleForm.value.rule_name) {
    toast(t('rule-name-required', 'Rule name is required'), 'error')
    return
  }
  savingRule.value = true
  try {
    if (editingRule.value) {
      await api.put(`/accounting/reminder-rules/${ruleEditId.value}`, ruleForm.value)
      toast(t('rule-updated', 'Reminder rule updated successfully'), 'success')
    } else {
      await api.post('/accounting/reminder-rules', ruleForm.value)
      toast(t('rule-created', 'Reminder rule created successfully'), 'success')
    }
    showRuleModal.value = false
    await loadAllData()
  } catch (err) {
    toast(t('failed-save-rule', 'Failed to save reminder rule'), 'error')
    console.error(err)
  } finally {
    savingRule.value = false
  }
}

function testRule(rule) {
  batchForm.value.rule_id = rule.id
  batchForm.value.dry_run = true
  activeTab.value = 'batch'
  runBatchReminders()
}

function confirmDeleteRule(rule) {
  deleteType.value = 'rule'
  deleteTargetId.value = rule.id
  deleteTargetName.value = rule.rule_name || rule.name
  showDeleteModal.value = true
}

// ----------------------------------------------------------------------
// Template Actions
// ----------------------------------------------------------------------
function openAddTemplateModal() {
  editingTemplate.value = false
  templateEditId.value = null
  templateForm.value = {
    name: '',
    template_code: `TMPL-EM-${Math.random().toString(36).substring(2, 7).toUpperCase()}`,
    channel: 'EMAIL',
    subject: '',
    body_text: 'Dear {customer_name},\n\nYour account has an overdue balance of {overdue_amount}.\nPlease submit payment at your earliest convenience: {payment_link}\n\nThank you,\n{company_name}',
    whatsapp_template_id: '',
    whatsapp_language_code: 'en_US',
    is_default: false,
    is_active: true,
  }
  showTemplateModal.value = true
}

function editTemplate(tmpl) {
  editingTemplate.value = true
  templateEditId.value = tmpl.id
  templateForm.value = {
    name: tmpl.name || '',
    template_code: tmpl.template_code || '',
    channel: tmpl.channel || 'EMAIL',
    subject: tmpl.subject || '',
    body_text: tmpl.body_text || '',
    whatsapp_template_id: tmpl.whatsapp_template_id || '',
    whatsapp_language_code: tmpl.whatsapp_language_code || 'en_US',
    is_default: tmpl.is_default || false,
    is_active: tmpl.is_active !== false,
  }
  showTemplateModal.value = true
}

async function saveTemplate() {
  if (!templateForm.value.name || !templateForm.value.body_text) {
    toast(t('template-fields-required', 'Name and body text are required'), 'error')
    return
  }
  savingTemplate.value = true
  try {
    if (editingTemplate.value) {
      await api.put(`/accounting/reminder-templates/${templateEditId.value}`, templateForm.value)
      toast(t('template-updated', 'Template updated successfully'), 'success')
    } else {
      await api.post('/accounting/reminder-templates', templateForm.value)
      toast(t('template-created', 'Template created successfully'), 'success')
    }
    showTemplateModal.value = false
    await loadAllData()
  } catch (err) {
    toast(t('failed-save-template', 'Failed to save template'), 'error')
    console.error(err)
  } finally {
    savingTemplate.value = false
  }
}

function confirmDeleteTemplate(tmpl) {
  deleteType.value = 'template'
  deleteTargetId.value = tmpl.id
  deleteTargetName.value = tmpl.name
  showDeleteModal.value = true
}

async function executeDelete() {
  deletingItem.value = true
  try {
    if (deleteType.value === 'rule') {
      await api.delete(`/accounting/reminder-rules/${deleteTargetId.value}`)
      toast(t('rule-deleted', 'Rule deleted successfully'), 'success')
    } else {
      await api.delete(`/accounting/reminder-templates/${deleteTargetId.value}`)
      toast(t('template-deleted', 'Template deleted successfully'), 'success')
    }
    showDeleteModal.value = false
    await loadAllData()
  } catch (err) {
    toast(t('failed-delete', 'Failed to delete item'), 'error')
    console.error(err)
  } finally {
    deletingItem.value = false
  }
}

// ----------------------------------------------------------------------
// Batch Execution
// ----------------------------------------------------------------------
function openRunBatchModal() {
  activeTab.value = 'batch'
}

async function runBatchReminders() {
  runningBatch.value = true
  try {
    const payload = {
      rule_id: batchForm.value.rule_id,
      as_of_date: batchForm.value.as_of_date,
      dry_run: batchForm.value.dry_run,
      force: batchForm.value.force,
    }
    const res = await api.post('/accounting/reminders/run-batch', payload)
    batchResult.value = res.data || {}
    toast(
      batchForm.value.dry_run
        ? t('batch-preview-ready', `Preview complete: ${batchResult.value.total_eligible || 0} candidate accounts`)
        : t('batch-executed', `Dispatched ${batchResult.value.total_dispatched || 0} reminder messages`),
      'success'
    )
  } catch (err) {
    toast(t('batch-failed', 'Failed to execute batch evaluation'), 'error')
    console.error(err)
  } finally {
    runningBatch.value = false
  }
}

// ----------------------------------------------------------------------
// Quick / Manual Dispatch
// ----------------------------------------------------------------------
function openQuickDispatchModal() {
  activeTab.value = 'dispatch'
}

async function sendQuickDispatch() {
  if (!quickDispatchForm.value.customer_id) {
    toast(t('customer-required', 'Please select a customer'), 'error')
    return
  }
  sendingDispatch.value = true
  try {
    if (quickDispatchForm.value.mode === 'REMINDER') {
      await api.post('/accounting/reminders/dispatch', {
        customer_id: quickDispatchForm.value.customer_id,
        template_id: quickDispatchForm.value.template_id,
        channel: quickDispatchForm.value.channel,
        custom_message: quickDispatchForm.value.custom_message,
        attach_statement_pdf: quickDispatchForm.value.attach_statement_pdf,
        include_payment_link: quickDispatchForm.value.include_payment_link,
      })
      toast(t('reminder-dispatched', 'Reminder dispatched successfully'), 'success')
    } else {
      await api.post('/accounting/reminders/dispatch-statement', {
        customer_id: quickDispatchForm.value.customer_id,
        channel: quickDispatchForm.value.channel === 'ALL' ? 'EMAIL' : quickDispatchForm.value.channel,
        custom_message: quickDispatchForm.value.custom_message,
      })
      toast(t('statement-dispatched', 'Account statement dispatched successfully'), 'success')
    }
    quickDispatchForm.value.custom_message = ''
  } catch (err) {
    toast(t('dispatch-failed', 'Failed to dispatch communication'), 'error')
    console.error(err)
  } finally {
    sendingDispatch.value = false
  }
}

async function downloadCustomerStatementPdf() {
  if (!quickDispatchForm.value.customer_id) return
  try {
    const url = `/api/accounting/customers/${quickDispatchForm.value.customer_id}/statement-pdf`
    window.open(url, '_blank')
  } catch (err) {
    toast(t('failed-pdf-download', 'Failed to open statement PDF'), 'error')
  }
}

onMounted(() => {
  loadAllData()
})
</script>

<style scoped>
.page {
  padding: 0;
}

.page-head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 24px;
}

.page-title {
  font-size: 22px;
  font-weight: 700;
  color: #1a1a2e;
  margin: 0;
}

.page-subtitle {
  font-size: 13px;
  color: #666;
  margin-top: 4px;
}

.stats-row {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 16px;
  margin-bottom: 24px;
}

.stat-card {
  background: #fff;
  border: 1px solid #e0e0e0;
  border-radius: 12px;
  padding: 16px 20px;
  display: flex;
  flex-direction: column;
}

.stat-value {
  font-size: 24px;
  font-weight: 700;
  color: #1a1a2e;
}

.stat-label {
  font-size: 12px;
  color: #888;
  margin-top: 4px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.aging-summary-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
  gap: 8px;
}

.aging-pill {
  display: flex;
  flex-direction: column;
  padding: 10px 14px;
  border-radius: 8px;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
}

.pill-label {
  font-size: 11px;
  color: #64748b;
  font-weight: 600;
}

.pill-val {
  font-size: 15px;
  font-weight: 700;
  color: #1e293b;
  margin-top: 2px;
}

.pill-90-plus {
  background: #fef2f2;
  border-color: #fecaca;
}

.tabs {
  display: flex;
  gap: 8px;
  border-bottom: 2px solid #e2e8f0;
  margin-bottom: 20px;
}

.tab {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 10px 18px;
  font-size: 13px;
  font-weight: 600;
  color: #64748b;
  background: none;
  border: none;
  border-bottom: 2px solid transparent;
  margin-bottom: -2px;
  cursor: pointer;
  transition: all 0.15s ease;
}

.tab:hover {
  color: #1e293b;
}

.tab.active {
  color: #4338ca;
  border-bottom-color: #4338ca;
}

.tab-icon {
  font-size: 18px;
}

.data-card {
  background: #fff;
  border: 1px solid #e0e0e0;
  border-radius: 12px;
  overflow: hidden;
}

.table-wrap {
  overflow-x: auto;
}

.data-table {
  width: 100%;
  border-collapse: collapse;
}

.data-table th {
  padding: 10px 18px;
  font-size: 11px;
  font-weight: 700;
  color: #999;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  background: #fafafe;
  border-bottom: 1px solid #eee;
  text-align: left;
  white-space: nowrap;
}

.data-table td {
  padding: 12px 18px;
  border-bottom: 1px solid #f5f5f5;
  font-size: 13px;
  color: #333;
}

.data-table tr:last-child td {
  border-bottom: none;
}

.data-table tr:hover td {
  background: #fafafe;
}

.truncate-cell {
  max-width: 260px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.cell-mono {
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
}

.badge {
  display: inline-block;
  padding: 3px 10px;
  border-radius: 12px;
  font-size: 11px;
  font-weight: 600;
}

.badge-active {
  background: #e8f5e9;
  color: #2e7d32;
}

.badge-disabled {
  background: #f5f5f5;
  color: #999;
}

.badge-warning {
  background: #fff8e1;
  color: #f57f17;
}

.badge-info {
  background: #e0f2fe;
  color: #0369a1;
}

.channel-badge {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 3px 8px;
  border-radius: 6px;
  font-size: 11px;
  font-weight: 600;
}

.channel-whatsapp {
  background: #dcfce7;
  color: #15803d;
}

.channel-email {
  background: #e0e7ff;
  color: #4338ca;
}

.channel-all {
  background: #f1f5f9;
  color: #475569;
}

.icon-xs {
  font-size: 14px;
}

.btn-primary {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 8px 16px;
  background: #4338ca;
  color: #fff;
  border: none;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
}

.btn-primary:hover:not(:disabled) {
  background: #3730a3;
}

.btn-primary:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.btn-outline {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 8px 16px;
  background: #fff;
  color: #333;
  border: 1px solid #d0d0d0;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
}

.btn-outline:hover {
  background: #f8f8fa;
}

.btn-danger {
  padding: 8px 16px;
  background: #dc2626;
  color: #fff;
  border: none;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
}

.btn-danger:hover:not(:disabled) {
  background: #b91c1c;
}

.btn-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border: none;
  border-radius: 6px;
  background: none;
  cursor: pointer;
  color: #666;
}

.btn-icon:hover {
  background: #f0f0f4;
}

.btn-icon-danger:hover {
  background: #fee2e2;
  color: #dc2626;
}

.variables-bar {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  align-items: center;
}

.var-chip {
  padding: 2px 8px;
  border-radius: 12px;
  background: #eef2ff;
  color: #4338ca;
  border: 1px solid #c7d2fe;
  font-size: 11px;
  font-family: monospace;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.1s;
}

.var-chip:hover {
  background: #e0e7ff;
}

.empty-state {
  text-align: center;
  padding: 48px;
  color: #999;
}

.empty-icon {
  font-size: 48px;
  color: #ccc;
  margin-bottom: 12px;
}

/* Modal styles */
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.45);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  padding: 20px;
}

.modal-content {
  background: #fff;
  border-radius: 12px;
  width: 100%;
  max-width: 580px;
  max-height: 90vh;
  overflow-y: auto;
  box-shadow: 0 10px 25px rgba(0, 0, 0, 0.15);
}

.modal-lg {
  max-width: 720px;
}

.modal-sm {
  max-width: 420px;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 24px;
  border-bottom: 1px solid #eee;
}

.modal-header h3 {
  font-size: 16px;
  font-weight: 700;
  margin: 0;
}

.modal-body {
  padding: 20px 24px;
}

.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  margin-top: 20px;
}

.form-row {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 16px;
  margin-bottom: 14px;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.form-group label {
  font-size: 12px;
  font-weight: 600;
  color: #555;
}

.form-input {
  padding: 8px 12px;
  border: 1px solid #d0d0d0;
  border-radius: 6px;
  font-size: 13px;
  outline: none;
  background: #fff;
  transition: border-color 0.15s;
}

.form-input:focus {
  border-color: #4338ca;
}

.required {
  color: #dc2626;
}

.checkbox {
  width: 16px;
  height: 16px;
  accent-color: #4338ca;
}

.delete-text {
  font-size: 14px;
  color: #444;
  margin-bottom: 16px;
}

.text-danger { color: #dc2626; }
.text-success { color: #16a34a; }
.text-muted { color: #888; }
.text-primary { color: #4338ca; }
.text-center { text-align: center; }
.font-mono { font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace; }
</style>
