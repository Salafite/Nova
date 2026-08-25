<template>
  <div class="migration-container" :dir="dir">
    <!-- Page Header -->
    <div class="page-header">
      <div>
        <h1 class="page-title">{{ t('migrate-title', 'Automated Legacy ERP Database Migration Bridge') }}</h1>
        <p class="page-subtitle">{{ t('migrate-sub', 'Extract, cleanse, reconcile, commit, and roll back legacy ERP datasets with zero data loss') }}</p>
      </div>
      <div class="header-actions">
        <button v-if="step !== 'history'" class="btn-outline" @click="toggleHistory(true)">
          <span class="material-symbols-outlined">history</span>
          {{ t('migrate-view-history', 'Batch History') }}
        </button>
        <button v-else class="btn-primary" @click="toggleHistory(false)">
          <span class="material-symbols-outlined">add</span>
          {{ t('migrate-new-migration', 'New Migration') }}
        </button>
      </div>
    </div>

    <!-- Multi-Step Wizard Stepper (when not in history view) -->
    <div v-if="step !== 'history'" class="wizard-stepper mb-6">
      <div
        class="step-item"
        :class="{ active: step === 'connect', completed: isStepCompleted('connect') }"
        @click="goToStep('connect')"
      >
        <div class="step-circle">1</div>
        <div class="step-info">
          <span class="step-label">{{ t('step-1-title', 'Connect Source') }}</span>
          <span class="step-desc">{{ t('step-1-sub', 'SQL Server / Dump') }}</span>
        </div>
      </div>
      <div class="step-connector"></div>
      <div
        class="step-item"
        :class="{ active: step === 'mapping', completed: isStepCompleted('mapping'), disabled: !canGoToStep('mapping') }"
        @click="goToStep('mapping')"
      >
        <div class="step-circle">2</div>
        <div class="step-info">
          <span class="step-label">{{ t('step-2-title', 'Schema & Cleansing') }}</span>
          <span class="step-desc">{{ t('step-2-sub', 'Map & Sanitize') }}</span>
        </div>
      </div>
      <div class="step-connector"></div>
      <div
        class="step-item"
        :class="{ active: step === 'reconciliation', completed: isStepCompleted('reconciliation'), disabled: !canGoToStep('reconciliation') }"
        @click="goToStep('reconciliation')"
      >
        <div class="step-circle">3</div>
        <div class="step-info">
          <span class="step-label">{{ t('step-3-title', 'Dry-Run & Reconcile') }}</span>
          <span class="step-desc">{{ t('step-3-sub', 'Balances & Inventory') }}</span>
        </div>
      </div>
      <div class="step-connector"></div>
      <div
        class="step-item"
        :class="{ active: step === 'committed' || step === 'rolled_back', completed: isStepCompleted('committed'), disabled: !canGoToStep('committed') }"
      >
        <div class="step-circle">4</div>
        <div class="step-info">
          <span class="step-label">{{ t('step-4-title', 'Commit & Rollback') }}</span>
          <span class="step-desc">{{ t('step-4-sub', 'Zero Downtime') }}</span>
        </div>
      </div>
    </div>

    <!-- Alert / Global Error State -->
    <div v-if="globalError" class="alert-banner alert-error mb-6">
      <span class="material-symbols-outlined">error</span>
      <div class="alert-content">
        <strong>{{ t('error', 'Error') }}:</strong> {{ globalError }}
      </div>
      <button class="btn-icon" @click="globalError = ''"><span class="material-symbols-outlined">close</span></button>
    </div>

    <!-- STEP 1: Connect Source -->
    <div v-if="step === 'connect'" class="step-content">
      <div class="data-card mb-6">
        <div class="card-header">
          <h3>{{ t('select-source-type', '1. Select Legacy Data Source') }}</h3>
        </div>
        <div class="card-body">
          <div class="source-type-grid">
            <div
              class="source-card"
              :class="{ selected: sourceType === 'sqlserver' }"
              @click="sourceType = 'sqlserver'"
            >
              <span class="material-symbols-outlined source-icon">database</span>
              <h4>{{ t('source-sqlserver-title', 'Direct SQL Server') }}</h4>
              <p>{{ t('source-sqlserver-desc', 'Connect directly to legacy Microsoft SQL Server instance (C# F&B, Retail, Accounting DBs)') }}</p>
              <span v-if="sourceType === 'sqlserver'" class="badge badge-active">{{ t('selected', 'Selected') }}</span>
            </div>

            <div
              class="source-card"
              :class="{ selected: sourceType === 'csv_dump' }"
              @click="sourceType = 'csv_dump'"
            >
              <span class="material-symbols-outlined source-icon">folder_zip</span>
              <h4>{{ t('source-csvdump-title', 'Multi-Table CSV / SQL Dump') }}</h4>
              <p>{{ t('source-csvdump-desc', 'Import multi-table CSV folder, ZIP archive, or legacy SQL backup dump script') }}</p>
              <span v-if="sourceType === 'csv_dump'" class="badge badge-active">{{ t('selected', 'Selected') }}</span>
            </div>

            <div
              class="source-card"
              :class="{ selected: sourceType === 'upload_csv' }"
              @click="sourceType = 'upload_csv'"
            >
              <span class="material-symbols-outlined source-icon">upload_file</span>
              <h4>{{ t('source-singlecsv-title', 'Single CSV Upload') }}</h4>
              <p>{{ t('source-singlecsv-desc', 'Quick upload of a single legacy entity CSV file (Products, Customers, Suppliers)') }}</p>
              <span v-if="sourceType === 'upload_csv'" class="badge badge-active">{{ t('selected', 'Selected') }}</span>
            </div>
          </div>
        </div>
      </div>

      <!-- SQL Server Connection Parameters -->
      <div v-if="sourceType === 'sqlserver'" class="data-card mb-6">
        <div class="card-header">
          <h3>{{ t('sqlserver-config-title', 'SQL Server Database Credentials') }}</h3>
        </div>
        <div class="card-body">
          <div class="form-grid">
            <div class="form-group">
              <label>{{ t('host', 'Server Host / IP') }} <span class="required">*</span></label>
              <input type="text" v-model="sqlConfig.host" class="form-input" placeholder="localhost or 192.168.1.100" />
            </div>

            <div class="form-group">
              <label>{{ t('port', 'Port') }} <span class="required">*</span></label>
              <input type="number" v-model.number="sqlConfig.port" class="form-input" placeholder="1433" />
            </div>

            <div class="form-group">
              <label>{{ t('database-name', 'Database Name') }} <span class="required">*</span></label>
              <input type="text" v-model="sqlConfig.database" class="form-input" placeholder="LegacyERP_DB" />
            </div>

            <div class="form-group">
              <label>{{ t('schema-name', 'Schema') }}</label>
              <input type="text" v-model="sqlConfig.schema_name" class="form-input" placeholder="dbo" />
            </div>

            <div class="form-group">
              <label>{{ t('username', 'Database User') }} <span class="required">*</span></label>
              <input type="text" v-model="sqlConfig.user" class="form-input" placeholder="sa" />
            </div>

            <div class="form-group">
              <label>{{ t('password', 'Password') }}</label>
              <input type="password" v-model="sqlConfig.password" class="form-input" placeholder="••••••••" />
            </div>
          </div>

          <div class="checkbox-row mt-4">
            <label class="checkbox-label">
              <input type="checkbox" v-model="sqlConfig.trust_server_certificate" />
              <span>{{ t('trust-server-cert', 'Trust Server Certificate (SSL Encrypted)') }}</span>
            </label>
          </div>
        </div>
      </div>

      <!-- CSV / SQL Dump Parameters -->
      <div v-if="sourceType === 'csv_dump'" class="data-card mb-6">
        <div class="card-header">
          <h3>{{ t('csvdump-config-title', 'Dump Directory / Archive Settings') }}</h3>
        </div>
        <div class="card-body">
          <div class="form-group mb-4">
            <label>{{ t('dump-path', 'Directory or Archive Path') }}</label>
            <input type="text" v-model="csvDumpConfig.dump_path" class="form-input" placeholder="C:/LegacyData/ or data/legacy_dumps/" />
            <small class="form-hint">{{ t('dump-path-hint', 'Path to directory containing multi-table CSV files or .sql dump file on server') }}</small>
          </div>

          <div class="form-grid">
            <div class="form-group">
              <label>{{ t('delimiter', 'CSV Delimiter') }}</label>
              <select v-model="csvDumpConfig.delimiter" class="form-input">
                <option :value="null">{{ t('auto-detect', 'Auto-detect (, ; \\t |)') }}</option>
                <option value=",">{{ t('comma', 'Comma (,)') }}</option>
                <option value=";">{{ t('semicolon', 'Semicolon (;)') }}</option>
                <option value="&#9;">{{ t('tab', 'Tab (\\t)') }}</option>
                <option value="|">{{ t('pipe', 'Pipe (|)') }}</option>
              </select>
            </div>

            <div class="form-group">
              <label>{{ t('encoding', 'Character Encoding') }}</label>
              <select v-model="csvDumpConfig.encoding" class="form-input">
                <option :value="null">{{ t('auto-detect', 'Auto-detect (UTF-8, CP1252, Windows-1256)') }}</option>
                <option value="utf-8">UTF-8</option>
                <option value="utf-8-sig">UTF-8 with BOM</option>
                <option value="windows-1256">Windows-1256 (Arabic Legacy)</option>
                <option value="cp1252">Windows-1252 (Western European)</option>
              </select>
            </div>
          </div>

          <div class="checkbox-row mt-4">
            <label class="checkbox-label">
              <input type="checkbox" v-model="csvDumpConfig.has_header" />
              <span>{{ t('has-header', 'First row contains column headers') }}</span>
            </label>
          </div>
        </div>
      </div>

      <!-- Single File CSV Upload (Backward Compatible) -->
      <div v-if="sourceType === 'upload_csv'" class="data-card mb-6">
        <div class="card-header">
          <h3>{{ t('upload-single-csv', 'Upload Legacy CSV File') }}</h3>
        </div>
        <div class="card-body">
          <div class="form-group mb-4">
            <label>{{ t('target-entity', 'Target Entity') }}</label>
            <select v-model="singleUploadEntity" class="form-input">
              <option value="products">{{ t('products', 'Products & Pricing') }}</option>
              <option value="customers">{{ t('customers', 'Customers & Balances') }}</option>
              <option value="suppliers">{{ t('suppliers', 'Suppliers') }}</option>
            </select>
          </div>

          <div class="upload-zone" @drop.prevent="handleSingleDrop" @dragover.prevent>
            <input type="file" ref="singleFileInput" accept=".csv" @change="handleSingleFile" hidden />
            <span class="material-symbols-outlined upload-icon">cloud_upload</span>
            <p>{{ t('migrate-drop-hint', 'Drag & drop a CSV file here, or click to browse') }}</p>
            <button class="btn-outline btn-sm" @click="$refs.singleFileInput.click()">{{ t('migrate-browse', 'Browse Files') }}</button>
            <p v-if="singleFile" class="file-name">{{ singleFile.name }} ({{ formatFileSize(singleFile.size) }})</p>
          </div>
        </div>
      </div>

      <!-- Connection Test Results Banner -->
      <div v-if="testResult" class="data-card mb-6">
        <div class="card-body">
          <div class="test-result-box" :class="testResult.success ? 'test-success' : 'test-failure'">
            <div class="flex items-center gap-3">
              <span class="material-symbols-outlined test-icon">
                {{ testResult.success ? 'check_circle' : 'cancel' }}
              </span>
              <div>
                <h4 class="test-title">
                  {{ testResult.success ? t('connection-success', 'Connection Successful') : t('connection-failed', 'Connection Failed') }}
                </h4>
                <p class="test-msg">{{ testResult.message }}</p>
                <div v-if="testResult.success" class="test-meta">
                  <span v-if="testResult.latency_ms" class="meta-item">
                    <strong>{{ t('latency', 'Latency') }}:</strong> {{ testResult.latency_ms.toFixed(1) }} ms
                  </span>
                  <span v-if="testResult.server_version" class="meta-item">
                    <strong>{{ t('version', 'Server Version') }}:</strong> {{ testResult.server_version }}
                  </span>
                  <span v-if="testResult.tables_count" class="meta-item">
                    <strong>{{ t('tables-found', 'Discovered Tables') }}:</strong> {{ testResult.tables_count }}
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Action Buttons for Step 1 -->
      <div class="step-actions">
        <button
          v-if="sourceType !== 'upload_csv'"
          class="btn-outline btn-test-conn"
          :disabled="testingConnection"
          @click="runTestConnection"
        >
          <span v-if="testingConnection" class="spinner-sm"></span>
          <span v-else class="material-symbols-outlined">network_check</span>
          {{ testingConnection ? t('testing', 'Testing Connection...') : t('test-connection', 'Test Connection') }}
        </button>

        <button
          v-if="sourceType !== 'upload_csv'"
          class="btn-primary"
          :disabled="discoveringSchema"
          @click="runDiscoverSchema"
        >
          <span v-if="discoveringSchema" class="spinner-sm"></span>
          <span v-else class="material-symbols-outlined">schema</span>
          {{ discoveringSchema ? t('discovering', 'Discovering Schema...') : t('next-discover', 'Discover Schema & Next') }}
        </button>

        <button
          v-if="sourceType === 'upload_csv'"
          class="btn-primary"
          :disabled="!singleFile || singleUploading"
          @click="uploadSingleCsvFile"
        >
          <span v-if="singleUploading" class="spinner-sm"></span>
          <span v-else class="material-symbols-outlined">upload</span>
          {{ singleUploading ? t('uploading', 'Uploading...') : t('upload-and-preview', 'Upload & Preview') }}
        </button>
      </div>
    </div>

    <!-- STEP 2: Schema Discovery & Visual Mapping Step -->
    <div v-if="step === 'mapping'" class="step-content">
      <!-- Discovered Tables Bar -->
      <div class="data-card mb-6">
        <div class="card-header flex justify-between items-center">
          <div>
            <h3>{{ t('discovered-tables', '2. Discovered Legacy Tables') }} ({{ discoveredTables.length }})</h3>
            <p class="card-subtitle">{{ t('discovered-tables-sub', 'Select and preview source tables to map to Nova ERP entities') }}</p>
          </div>
          <span class="badge badge-active">{{ connectionInfoSummary }}</span>
        </div>
        <div class="card-body">
          <div class="table-chips-grid">
            <div
              v-for="tbl in discoveredTables"
              :key="tbl.name"
              class="table-chip"
              :class="{ active: selectedTableForPreview === tbl.name }"
              @click="selectTableForPreview(tbl.name)"
            >
              <span class="material-symbols-outlined chip-icon">table_chart</span>
              <span class="chip-name">{{ tbl.name }}</span>
              <span class="chip-count" v-if="tbl.row_count != null">{{ tbl.row_count }} {{ t('rows', 'rows') }}</span>
              <button class="btn-chip-preview" title="Preview Sample" @click.stop="openPreviewModal(tbl.name)">
                <span class="material-symbols-outlined">visibility</span>
              </button>
            </div>
          </div>
        </div>
      </div>

      <!-- Entity & T-code Mapping Config -->
      <div class="data-card mb-6">
        <div class="card-header flex justify-between items-center">
          <div>
            <h3>{{ t('entity-mappings-title', 'Entity & T-Code Mapping Rules') }}</h3>
            <p class="card-subtitle">{{ t('entity-mappings-sub', 'Automatic heuristic schema translation from legacy tables to Nova T-codes') }}</p>
          </div>
          <button class="btn-outline btn-sm" @click="autoMapAllEntities">
            <span class="material-symbols-outlined">auto_fix_high</span>
            {{ t('auto-suggest-mappings', 'Auto-Suggest All') }}
          </button>
        </div>
        <div class="card-body">
          <div class="entity-mapping-list">
            <div v-for="entity in entityMappings" :key="entity.key" class="entity-mapping-card">
              <div class="entity-card-header">
                <div class="entity-title-row">
                  <input type="checkbox" v-model="entity.enabled" class="entity-checkbox" />
                  <div>
                    <h4 class="entity-name">{{ entity.label }}</h4>
                    <span class="mono tcode-badge">{{ entity.target_tcode }} ({{ entity.target_table }})</span>
                  </div>
                </div>

                <div class="entity-source-select" v-if="entity.enabled">
                  <label>{{ t('source-table', 'Source Table') }}:</label>
                  <select v-model="entity.source_table" class="form-input form-input-sm" @change="onEntitySourceChanged(entity)">
                    <option value="">-- {{ t('none-selected', 'Not Mapped') }} --</option>
                    <option v-for="tbl in discoveredTables" :key="tbl.name" :value="tbl.name">
                      {{ tbl.name }} {{ tbl.row_count ? `(${tbl.row_count} rows)` : '' }}
                    </option>
                  </select>
                </div>
              </div>

              <!-- Field Mapping Sub-table -->
              <div v-if="entity.enabled && entity.source_table" class="field-mapping-panel">
                <div class="field-mapping-header">
                  <span>{{ t('target-field', 'Nova Attribute') }}</span>
                  <span>{{ t('source-column', 'Legacy Column') }}</span>
                  <span>{{ t('transform-rule', 'Transform') }}</span>
                  <span>{{ t('default-val', 'Default') }}</span>
                </div>

                <div v-for="field in entity.fields" :key="field.target" class="field-mapping-row">
                  <div class="field-target-cell">
                    <span class="field-target-name">{{ field.label }}</span>
                    <span v-if="field.required" class="required">*</span>
                    <span class="field-target-key mono">{{ field.target }}</span>
                  </div>

                  <div class="field-source-cell">
                    <select v-model="field.source" class="form-input form-input-sm">
                      <option value="">-- {{ t('unmapped', 'Unmapped') }} --</option>
                      <option v-for="col in getTableColumns(entity.source_table)" :key="col" :value="col">{{ col }}</option>
                    </select>
                  </div>

                  <div class="field-transform-cell">
                    <select v-model="field.transform" class="form-input form-input-sm">
                      <option value="">{{ t('none', 'None') }}</option>
                      <option value="trim">Trim</option>
                      <option value="uppercase">Uppercase</option>
                      <option value="lowercase">Lowercase</option>
                      <option value="strip_non_numeric">Digits Only</option>
                      <option value="round_2">Round 2 Decimals</option>
                    </select>
                  </div>

                  <div class="field-default-cell">
                    <input type="text" v-model="field.default_value" class="form-input form-input-sm" :placeholder="field.default_placeholder || '-'" />
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Data Cleansing & Phantom Product Options -->
      <div class="data-card mb-6">
        <div class="card-header">
          <h3>{{ t('cleansing-options-title', '3. Data Cleansing & Phantom Product Detection') }}</h3>
          <p class="card-subtitle">{{ t('cleansing-options-sub', 'Automated deduplication, contact sanitization, and dormant product filtering') }}</p>
        </div>
        <div class="card-body">
          <div class="cleansing-grid">
            <div class="cleansing-section">
              <h4 class="cleansing-subhead">
                <span class="material-symbols-outlined">visibility_off</span>
                {{ t('phantom-detection', 'Phantom Product Detection') }}
              </h4>
              <div class="cleansing-options">
                <label class="checkbox-label">
                  <input type="checkbox" v-model="cleansingConfig.enable_phantom_detection" />
                  <span>{{ t('enable-phantom-check', 'Identify phantom products (no sales activity)') }}</span>
                </label>

                <div class="inline-input-group mt-2" v-if="cleansingConfig.enable_phantom_detection">
                  <label>{{ t('inactivity-months', 'Inactivity Threshold (Months)') }}:</label>
                  <input type="number" v-model.number="cleansingConfig.phantom_inactivity_months" min="1" max="60" class="form-input form-input-sm w-24" />
                </div>

                <label class="checkbox-label mt-2" v-if="cleansingConfig.enable_phantom_detection">
                  <input type="checkbox" v-model="cleansingConfig.phantom_zero_stock_check" />
                  <span>{{ t('zero-stock-check', 'Cross-reference zero or negative stock') }}</span>
                </label>

                <div class="inline-input-group mt-2" v-if="cleansingConfig.enable_phantom_detection">
                  <label>{{ t('phantom-action', 'Action for Phantoms') }}:</label>
                  <select v-model="cleansingConfig.phantom_action" class="form-input form-input-sm">
                    <option value="flag">{{ t('phantom-flag', 'Flag in Reconciliation (Keep in Staging)') }}</option>
                    <option value="skip">{{ t('phantom-skip', 'Skip from Import') }}</option>
                    <option value="isolate">{{ t('phantom-isolate', 'Isolate to Inactive/Draft') }}</option>
                  </select>
                </div>
              </div>
            </div>

            <div class="cleansing-section">
              <h4 class="cleansing-subhead">
                <span class="material-symbols-outlined">cleaning_services</span>
                {{ t('normalization-rules', 'Sanitization & Defaults') }}
              </h4>
              <div class="cleansing-options">
                <label class="checkbox-label">
                  <input type="checkbox" v-model="cleansingConfig.deduplicate_skus" />
                  <span>{{ t('dedup-skus', 'Deduplicate SKUs & Barcodes') }}</span>
                </label>

                <label class="checkbox-label mt-2">
                  <input type="checkbox" v-model="cleansingConfig.sanitize_phone_numbers" />
                  <span>{{ t('sanitize-contacts', 'Sanitize phone numbers & email addresses') }}</span>
                </label>

                <label class="checkbox-label mt-2">
                  <input type="checkbox" v-model="cleansingConfig.auto_create_missing_lookups" />
                  <span>{{ t('auto-create-lookups', 'Auto-create missing categories, UOMs & warehouses') }}</span>
                </label>

                <label class="checkbox-label mt-2">
                  <input type="checkbox" v-model="cleansingConfig.clamp_negative_stock" />
                  <span>{{ t('clamp-negative-stock', 'Clamp negative stock levels to 0.0') }}</span>
                </label>

                <div class="defaults-grid mt-3">
                  <div class="form-group">
                    <label class="text-xs">{{ t('default-uom', 'Default UOM') }}</label>
                    <input type="text" v-model="cleansingConfig.default_uom" class="form-input form-input-sm" placeholder="PCS" />
                  </div>
                  <div class="form-group">
                    <label class="text-xs">{{ t('default-category', 'Default Category') }}</label>
                    <input type="text" v-model="cleansingConfig.default_category" class="form-input form-input-sm" placeholder="General" />
                  </div>
                  <div class="form-group">
                    <label class="text-xs">{{ t('default-warehouse', 'Default Warehouse') }}</label>
                    <input type="text" v-model="cleansingConfig.default_warehouse" class="form-input form-input-sm" placeholder="Main Warehouse" />
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Action Buttons for Step 2 -->
      <div class="step-actions">
        <button class="btn-outline" @click="step = 'connect'">
          <span class="material-symbols-outlined">arrow_back</span>
          {{ t('back', 'Back to Connection') }}
        </button>
        <button class="btn-primary" :disabled="runningDryRun" @click="startDryRun">
          <span v-if="runningDryRun" class="spinner-sm"></span>
          <span v-else class="material-symbols-outlined">play_circle</span>
          {{ runningDryRun ? t('simulating', 'Running Dry-Run Simulation...') : t('run-dry-run', 'Run Dry-Run Simulation') }}
        </button>
      </div>
    </div>

    <!-- STEP 3: Dry-Run Reconciliation Dashboard -->
    <div v-if="step === 'reconciliation'" class="step-content">
      <!-- Status Banner -->
      <div class="reconciliation-status-card mb-6" :class="reconciliationStatusClass">
        <div class="flex items-center gap-3">
          <span class="material-symbols-outlined status-icon">{{ reconciliationStatusIcon }}</span>
          <div>
            <h3 class="status-title">{{ reconciliationStatusTitle }}</h3>
            <p class="status-subtitle">
              {{ t('batch-key', 'Batch') }}: <span class="mono">{{ dryRunResult?.batch_key || currentBatchId }}</span> |
              {{ t('duration', 'Duration') }}: {{ (dryRunResult?.execution_duration_ms || 0).toFixed(0) }} ms
            </p>
          </div>
        </div>
        <div class="status-actions">
          <button class="btn-outline btn-sm" @click="step = 'mapping'">
            <span class="material-symbols-outlined">edit</span>
            {{ t('adjust-mappings', 'Adjust Mappings') }}
          </button>
          <button class="btn-primary" @click="openCommitModal">
            <span class="material-symbols-outlined">task_alt</span>
            {{ t('commit-migration', 'One-Click Commit') }}
          </button>
        </div>
      </div>

      <!-- High-Level Metric Cards -->
      <div class="stats-row mb-6">
        <div class="stat-card">
          <span class="stat-label">{{ t('total-source-records', 'Source Records') }}</span>
          <span class="stat-value">{{ dryRunResult?.total_source_rows ?? 0 }}</span>
          <span class="stat-sub text-green">{{ dryRunResult?.valid_rows_count ?? 0 }} {{ t('valid-staged', 'valid staged') }}</span>
        </div>

        <div class="stat-card">
          <span class="stat-label">{{ t('customer-balance-variance', 'Receivables Variance') }}</span>
          <span class="stat-value" :class="receivablesVarianceClass">
            {{ formatCurrency(customerBalanceReconciliation?.total_receivables_delta ?? 0) }}
          </span>
          <span class="stat-sub">
            {{ customerBalanceReconciliation?.matched_count ?? 0 }} / {{ customerBalanceReconciliation?.customers_count ?? 0 }} {{ t('customers-matched', 'matched') }}
          </span>
        </div>

        <div class="stat-card">
          <span class="stat-label">{{ t('inventory-valuation-variance', 'Inventory Valuation Delta') }}</span>
          <span class="stat-value" :class="inventoryValuationVarianceClass">
            {{ formatCurrency(inventoryReconciliation?.total_valuation_delta ?? 0) }}
          </span>
          <span class="stat-sub">
            {{ formatNumber(inventoryReconciliation?.total_quantity_delta ?? 0) }} {{ t('units-diff', 'units variance') }}
          </span>
        </div>

        <div class="stat-card">
          <span class="stat-label">{{ t('cleansing-metrics', 'Phantoms & Cleansed') }}</span>
          <span class="stat-value text-amber">
            {{ dryRunResult?.phantom_products_count ?? 0 }}
          </span>
          <span class="stat-sub">
            {{ dryRunResult?.validation_errors?.length ?? 0 }} {{ t('validation-issues', 'issues found') }}
          </span>
        </div>
      </div>

      <!-- Reconciliation Drill-Down Tabs -->
      <div class="data-card mb-6">
        <div class="tab-bar">
          <button
            class="tab-btn"
            :class="{ active: activeReconTab === 'customer_balances' }"
            @click="activeReconTab = 'customer_balances'"
          >
            <span class="material-symbols-outlined">account_balance_wallet</span>
            {{ t('tab-customer-balances', 'Customer Opening Balances') }}
            <span v-if="customerDiscrepanciesCount" class="tab-badge badge-danger">{{ customerDiscrepanciesCount }}</span>
          </button>

          <button
            class="tab-btn"
            :class="{ active: activeReconTab === 'inventory' }"
            @click="activeReconTab = 'inventory'"
          >
            <span class="material-symbols-outlined">inventory_2</span>
            {{ t('tab-inventory', 'Inventory Quantities & Valuation') }}
            <span v-if="inventoryDiscrepanciesCount" class="tab-badge badge-danger">{{ inventoryDiscrepanciesCount }}</span>
          </button>

          <button
            class="tab-btn"
            :class="{ active: activeReconTab === 'entities' }"
            @click="activeReconTab = 'entities'"
          >
            <span class="material-symbols-outlined">dataset</span>
            {{ t('tab-entities', 'Entity Breakdown & Lookups') }}
          </button>

          <button
            class="tab-btn"
            :class="{ active: activeReconTab === 'errors' }"
            @click="activeReconTab = 'errors'"
          >
            <span class="material-symbols-outlined">warning</span>
            {{ t('tab-errors', 'Validation Errors') }}
            <span v-if="validationErrorsList.length" class="tab-badge badge-danger">{{ validationErrorsList.length }}</span>
          </button>

          <button
            class="tab-btn"
            :class="{ active: activeReconTab === 'recommendations' }"
            @click="activeReconTab = 'recommendations'"
          >
            <span class="material-symbols-outlined">tips_and_updates</span>
            {{ t('tab-recommendations', 'Recommendations') }}
          </button>
        </div>

        <div class="card-body">
          <!-- 1. Customer Balances Tab -->
          <div v-if="activeReconTab === 'customer_balances'">
            <div class="recon-summary-panel mb-4">
              <div class="recon-metric">
                <span class="metric-label">{{ t('legacy-receivables', 'Legacy Total Receivables') }}:</span>
                <span class="metric-value">{{ formatCurrency(customerBalanceReconciliation?.total_legacy_receivables ?? 0) }}</span>
              </div>
              <div class="recon-metric">
                <span class="metric-label">{{ t('nova-receivables', 'Nova Staged Receivables') }}:</span>
                <span class="metric-value">{{ formatCurrency(customerBalanceReconciliation?.total_nova_receivables ?? 0) }}</span>
              </div>
              <div class="recon-metric">
                <span class="metric-label">{{ t('receivables-delta', 'Net Receivables Delta') }}:</span>
                <span class="metric-value" :class="receivablesVarianceClass">
                  {{ formatCurrency(customerBalanceReconciliation?.total_receivables_delta ?? 0) }}
                </span>
              </div>
            </div>

            <div v-if="customerDiscrepancies.length" class="table-wrap">
              <table class="data-table">
                <thead>
                  <tr>
                    <th>{{ t('customer-key', 'Customer Key / Code') }}</th>
                    <th>{{ t('customer-name', 'Customer Name') }}</th>
                    <th class="text-right">{{ t('legacy-balance', 'Legacy Balance') }}</th>
                    <th class="text-right">{{ t('nova-balance', 'Nova Balance') }}</th>
                    <th class="text-right">{{ t('delta', 'Delta') }}</th>
                    <th class="text-center">{{ t('status', 'Status') }}</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="c in customerDiscrepancies" :key="c.customer_key">
                    <td class="mono">{{ c.customer_key }}</td>
                    <td><strong>{{ c.customer_name }}</strong></td>
                    <td class="text-right">{{ formatCurrency(c.legacy_balance) }}</td>
                    <td class="text-right">{{ formatCurrency(c.nova_balance) }}</td>
                    <td class="text-right font-bold" :class="c.delta === 0 ? 'text-green' : 'text-red'">
                      {{ formatCurrency(c.delta) }}
                    </td>
                    <td class="text-center">
                      <span class="badge" :class="c.is_matched ? 'badge-active' : 'badge-danger'">
                        {{ c.is_matched ? 'Matched' : 'Variance' }}
                      </span>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
            <div v-else class="empty-state-sm">
              <span class="material-symbols-outlined text-green">check_circle</span>
              <p>{{ t('all-customers-reconciled', 'All customer opening balances are perfectly reconciled!') }}</p>
            </div>
          </div>

          <!-- 2. Inventory Quantities & Valuation Tab -->
          <div v-if="activeReconTab === 'inventory'">
            <div class="recon-summary-panel mb-4">
              <div class="recon-metric">
                <span class="metric-label">{{ t('legacy-qty', 'Legacy Total Quantity') }}:</span>
                <span class="metric-value">{{ formatNumber(inventoryReconciliation?.total_legacy_quantity ?? 0) }}</span>
              </div>
              <div class="recon-metric">
                <span class="metric-label">{{ t('nova-qty', 'Nova Staged Quantity') }}:</span>
                <span class="metric-value">{{ formatNumber(inventoryReconciliation?.total_nova_quantity ?? 0) }}</span>
              </div>
              <div class="recon-metric">
                <span class="metric-label">{{ t('valuation-delta', 'Valuation Delta') }}:</span>
                <span class="metric-value" :class="inventoryValuationVarianceClass">
                  {{ formatCurrency(inventoryReconciliation?.total_valuation_delta ?? 0) }}
                </span>
              </div>
            </div>

            <!-- Warehouse Breakdown -->
            <div v-if="warehouseSummariesList.length" class="mb-6">
              <h4 class="subhead mb-2">{{ t('warehouse-breakdown', 'Warehouse Breakdown') }}</h4>
              <div class="table-wrap">
                <table class="data-table">
                  <thead>
                    <tr>
                      <th>{{ t('warehouse', 'Warehouse') }}</th>
                      <th class="text-right">{{ t('legacy-qty', 'Legacy Qty') }}</th>
                      <th class="text-right">{{ t('nova-qty', 'Nova Qty') }}</th>
                      <th class="text-right">{{ t('qty-delta', 'Qty Delta') }}</th>
                      <th class="text-right">{{ t('legacy-val', 'Legacy Valuation') }}</th>
                      <th class="text-right">{{ t('nova-val', 'Nova Valuation') }}</th>
                      <th class="text-right">{{ t('val-delta', 'Valuation Delta') }}</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr v-for="wh in warehouseSummariesList" :key="wh.warehouse_name">
                      <td><strong>{{ wh.warehouse_name }}</strong></td>
                      <td class="text-right">{{ formatNumber(wh.legacy_total_quantity) }}</td>
                      <td class="text-right">{{ formatNumber(wh.nova_total_quantity) }}</td>
                      <td class="text-right" :class="wh.quantity_delta === 0 ? 'text-green' : 'text-red'">
                        {{ formatNumber(wh.quantity_delta) }}
                      </td>
                      <td class="text-right">{{ formatCurrency(wh.legacy_total_valuation) }}</td>
                      <td class="text-right">{{ formatCurrency(wh.nova_total_valuation) }}</td>
                      <td class="text-right" :class="wh.valuation_delta === 0 ? 'text-green' : 'text-red'">
                        {{ formatCurrency(wh.valuation_delta) }}
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>

            <!-- Stock Discrepancies -->
            <div v-if="inventoryDiscrepancies.length">
              <h4 class="subhead mb-2">{{ t('stock-discrepancies', 'Stock Discrepancies & Negative Stock Items') }}</h4>
              <div class="table-wrap">
                <table class="data-table">
                  <thead>
                    <tr>
                      <th>{{ t('sku', 'SKU') }}</th>
                      <th>{{ t('product-name', 'Product Name') }}</th>
                      <th>{{ t('warehouse', 'Warehouse') }}</th>
                      <th class="text-right">{{ t('legacy-qty', 'Legacy Qty') }}</th>
                      <th class="text-right">{{ t('nova-qty', 'Nova Qty') }}</th>
                      <th class="text-right">{{ t('valuation-delta', 'Valuation Delta') }}</th>
                      <th class="text-center">{{ t('status', 'Status') }}</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr v-for="item in inventoryDiscrepancies" :key="item.product_key + item.warehouse_name">
                      <td class="mono">{{ item.sku }}</td>
                      <td><strong>{{ item.product_name }}</strong></td>
                      <td>{{ item.warehouse_name }}</td>
                      <td class="text-right">{{ formatNumber(item.legacy_quantity) }}</td>
                      <td class="text-right">{{ formatNumber(item.nova_quantity) }}</td>
                      <td class="text-right">{{ formatCurrency(item.valuation_delta) }}</td>
                      <td class="text-center">
                        <span class="badge" :class="item.status === 'OK' ? 'badge-active' : 'badge-danger'">
                          {{ item.status }}
                        </span>
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>
            <div v-else class="empty-state-sm">
              <span class="material-symbols-outlined text-green">check_circle</span>
              <p>{{ t('inventory-perfectly-reconciled', 'All inventory stock quantities and valuations are reconciled!') }}</p>
            </div>
          </div>

          <!-- 3. Entity Breakdown & Cleansing Tab -->
          <div v-if="activeReconTab === 'entities'">
            <div class="table-wrap mb-6">
              <table class="data-table">
                <thead>
                  <tr>
                    <th>{{ t('entity-type', 'Entity Type') }}</th>
                    <th class="text-right">{{ t('source-count', 'Source Rows') }}</th>
                    <th class="text-right">{{ t('staged-count', 'Staged Rows') }}</th>
                    <th class="text-right">{{ t('phantom-count', 'Phantoms') }}</th>
                    <th class="text-right">{{ t('cleansed-count', 'Cleansed') }}</th>
                    <th class="text-right">{{ t('error-count', 'Errors') }}</th>
                    <th class="text-center">{{ t('match-status', 'Status') }}</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="(entity, k) in entityCountsList" :key="k">
                    <td><strong>{{ entity.entity_type || k }}</strong></td>
                    <td class="text-right">{{ entity.source_count ?? 0 }}</td>
                    <td class="text-right font-bold">{{ entity.staged_count ?? 0 }}</td>
                    <td class="text-right text-amber">{{ entity.phantom_count ?? 0 }}</td>
                    <td class="text-right text-green">{{ entity.cleansed_count ?? 0 }}</td>
                    <td class="text-right" :class="entity.error_count ? 'text-red font-bold' : ''">{{ entity.error_count ?? 0 }}</td>
                    <td class="text-center">
                      <span class="badge" :class="entity.error_count ? 'badge-danger' : 'badge-active'">
                        {{ entity.match_status || (entity.error_count ? 'Errors' : 'Matched') }}
                      </span>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>

            <!-- Auto-Created Lookups -->
            <div v-if="discoveredLookupsList.length" class="lookup-discovery-box">
              <h4 class="subhead mb-2">{{ t('auto-created-lookups', 'Auto-Discovered Lookup Master Records') }}</h4>
              <div class="lookup-badges">
                <div v-for="lk in discoveredLookupsList" :key="lk.type" class="lookup-group">
                  <span class="lookup-group-label">{{ lk.type }}:</span>
                  <span v-for="val in lk.values" :key="val" class="badge badge-outline">{{ val }}</span>
                </div>
              </div>
            </div>
          </div>

          <!-- 4. Validation Errors Tab -->
          <div v-if="activeReconTab === 'errors'">
            <div v-if="validationErrorsList.length" class="table-wrap">
              <table class="data-table">
                <thead>
                  <tr>
                    <th>{{ t('row', 'Row') }}</th>
                    <th>{{ t('entity', 'Entity') }}</th>
                    <th>{{ t('field', 'Field') }}</th>
                    <th>{{ t('error-type', 'Error Type') }}</th>
                    <th>{{ t('message', 'Message') }}</th>
                    <th class="text-center">{{ t('severity', 'Severity') }}</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="(err, idx) in validationErrorsList" :key="idx">
                    <td class="mono">#{{ err.row_index ?? err.row }}</td>
                    <td><strong>{{ err.entity_type }}</strong></td>
                    <td class="mono text-xs">{{ err.field_name || '-' }}</td>
                    <td><span class="badge badge-disabled">{{ err.error_type || 'Validation' }}</span></td>
                    <td class="text-red">{{ err.message || err.error }}</td>
                    <td class="text-center">
                      <span class="badge" :class="err.severity === 'warning' ? 'badge-warning' : 'badge-danger'">
                        {{ err.severity || 'Error' }}
                      </span>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
            <div v-else class="empty-state-sm">
              <span class="material-symbols-outlined text-green">task_alt</span>
              <p>{{ t('no-validation-errors', 'No validation errors encountered!') }}</p>
            </div>
          </div>

          <!-- 5. Recommendations Tab -->
          <div v-if="activeReconTab === 'recommendations'">
            <div v-if="recommendationsList.length" class="recommendations-list">
              <div v-for="(rec, idx) in recommendationsList" :key="idx" class="rec-item">
                <span class="material-symbols-outlined rec-icon">lightbulb</span>
                <p class="rec-text">{{ rec }}</p>
              </div>
            </div>
            <div v-else class="empty-state-sm">
              <span class="material-symbols-outlined text-green">verified</span>
              <p>{{ t('no-action-needed', 'No corrective actions required. The dataset is ready for commit.') }}</p>
            </div>
          </div>
        </div>
      </div>

      <!-- Action Buttons for Step 3 -->
      <div class="step-actions">
        <button class="btn-outline" @click="step = 'mapping'">
          <span class="material-symbols-outlined">arrow_back</span>
          {{ t('back', 'Back to Mapping') }}
        </button>
        <button class="btn-secondary" :disabled="runningDryRun" @click="startDryRun">
          <span class="material-symbols-outlined">refresh</span>
          {{ t('rerun-dry-run', 'Re-Run Simulation') }}
        </button>
        <button class="btn-primary" :disabled="committing" @click="openCommitModal">
          <span v-if="committing" class="spinner-sm"></span>
          <span v-else class="material-symbols-outlined">rocket_launch</span>
          {{ committing ? t('committing', 'Committing Records...') : t('commit-migration', 'One-Click Commit to Production') }}
        </button>
      </div>
    </div>

    <!-- STEP 4: Post-Commit Success Screen -->
    <div v-if="step === 'committed'" class="step-content">
      <div class="data-card mb-6 text-center py-8">
        <span class="material-symbols-outlined committed-icon">check_circle</span>
        <h2 class="committed-title">{{ t('commit-success-title', 'Migration Committed Successfully!') }}</h2>
        <p class="committed-sub">
          {{ t('batch', 'Batch') }} <strong class="mono">#{{ commitResult?.batch_id || currentBatchId }}</strong> {{ t('committed-to-nova', 'has been written to Nova ERP business tables with zero data loss.') }}
        </p>

        <!-- Insertion Breakdown Card -->
        <div class="commit-stats-grid max-w-xl mx-auto my-6">
          <div class="stat-card">
            <span class="stat-label">{{ t('total-inserted-records', 'Total Inserted') }}</span>
            <span class="stat-value text-green">{{ commitResult?.total_inserted ?? commitResult?.inserted_rows ?? 0 }}</span>
          </div>
          <div class="stat-card">
            <span class="stat-label">{{ t('execution-duration', 'Execution Time') }}</span>
            <span class="stat-value">{{ (commitResult?.execution_time_ms ?? 0).toFixed(0) }} ms</span>
          </div>
        </div>

        <!-- Entity Breakdown List -->
        <div v-if="commitResult?.inserted_by_entity" class="inserted-entities-box max-w-xl mx-auto mb-8">
          <h4 class="subhead mb-3">{{ t('inserted-by-entity', 'Records Inserted by Entity') }}</h4>
          <div class="inserted-entity-chips">
            <span v-for="(cnt, ent) in commitResult.inserted_by_entity" :key="ent" class="badge badge-active py-2 px-3 text-sm">
              <strong>{{ ent }}:</strong> {{ cnt }}
            </span>
          </div>
        </div>

        <!-- Actions -->
        <div class="flex justify-center gap-4">
          <button class="btn-outline" @click="resetWizard">
            <span class="material-symbols-outlined">add</span>
            {{ t('new-migration', 'Start New Migration') }}
          </button>
          <button class="btn-secondary" @click="toggleHistory(true)">
            <span class="material-symbols-outlined">history</span>
            {{ t('view-batches', 'View Batch History') }}
          </button>
          <button class="btn-danger" @click="openRollbackModal(commitResult?.batch_id || currentBatchId)">
            <span class="material-symbols-outlined">undo</span>
            {{ t('instant-rollback', 'Instant Rollback') }}
          </button>
        </div>
      </div>
    </div>

    <!-- STEP 5: Post-Rollback Screen -->
    <div v-if="step === 'rolled_back'" class="step-content">
      <div class="data-card mb-6 text-center py-8">
        <span class="material-symbols-outlined rollback-icon">settings_backup_restore</span>
        <h2 class="committed-title">{{ t('rollback-success-title', 'Migration Batch Rolled Back Successfully') }}</h2>
        <p class="committed-sub">
          {{ rollbackResult?.total_deleted ?? rollbackResult?.deleted_rows ?? 0 }} {{ t('records-safely-deleted', 'records safely deleted in reverse foreign-key order. Pre-existing tenant data is completely intact.') }}
        </p>

        <div class="flex justify-center gap-4 mt-6">
          <button class="btn-primary" @click="resetWizard">
            <span class="material-symbols-outlined">refresh</span>
            {{ t('start-fresh', 'Start Fresh Migration') }}
          </button>
          <button class="btn-outline" @click="toggleHistory(true)">
            <span class="material-symbols-outlined">history</span>
            {{ t('view-batches', 'Batch History') }}
          </button>
        </div>
      </div>
    </div>

    <!-- BATCH HISTORY VIEW -->
    <div v-if="step === 'history'" class="step-content">
      <div class="data-card">
        <div class="card-header flex justify-between items-center">
          <div>
            <h3>{{ t('migration-batches', 'Migration Batches & Audit Trail') }}</h3>
            <p class="card-subtitle">{{ t('migration-batches-sub', 'Track, reconcile, and roll back all legacy migration batches') }}</p>
          </div>
          <button class="btn-outline btn-sm" @click="loadBatchesList">
            <span class="material-symbols-outlined">refresh</span>
            {{ t('refresh', 'Refresh') }}
          </button>
        </div>

        <div class="card-body">
          <div v-if="loadingBatches" class="p-8 text-center">
            <span class="spinner-lg"></span>
            <p class="mt-2">{{ t('loading-batches', 'Loading migration batches...') }}</p>
          </div>

          <div v-else-if="!batchesList.length" class="empty-state">
            <span class="material-symbols-outlined empty-icon">database</span>
            <p>{{ t('no-batches-found', 'No migration batches found') }}</p>
            <button class="btn-primary" @click="toggleHistory(false)">{{ t('create-first-migration', 'Start First Migration') }}</button>
          </div>

          <div v-else class="table-wrap">
            <table class="data-table">
              <thead>
                <tr>
                  <th>{{ t('batch-id', 'Batch ID') }}</th>
                  <th>{{ t('source-type', 'Source') }}</th>
                  <th>{{ t('entity-type', 'Entity / Description') }}</th>
                  <th class="text-right">{{ t('total-rows', 'Total Rows') }}</th>
                  <th class="text-right">{{ t('inserted-rows', 'Inserted') }}</th>
                  <th>{{ t('status', 'Status') }}</th>
                  <th>{{ t('created-at', 'Created At') }}</th>
                  <th class="text-center">{{ t('actions', 'Actions') }}</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="b in batchesList" :key="b.id">
                  <td><strong class="mono">#{{ b.id }}</strong></td>
                  <td>
                    <span class="badge" :class="b.source_type === 'sqlserver' ? 'badge-primary' : 'badge-disabled'">
                      {{ b.source_type || 'csv_dump' }}
                    </span>
                  </td>
                  <td>{{ b.entity_type || b.batch_key || '-' }}</td>
                  <td class="text-right">{{ b.total_rows ?? 0 }}</td>
                  <td class="text-right font-bold" :class="b.inserted_rows ? 'text-green' : ''">{{ b.inserted_rows ?? 0 }}</td>
                  <td>
                    <span class="badge" :class="getBatchStatusBadgeClass(b.status)">
                      {{ b.status || 'Draft' }}
                    </span>
                  </td>
                  <td class="text-xs">{{ formatDate(b.created_at) }}</td>
                  <td class="text-center">
                    <div class="action-btn-group">
                      <button
                        class="btn-icon"
                        :title="t('view-reconciliation', 'View Reconciliation Report')"
                        @click="viewBatchReconciliationReport(b.id)"
                      >
                        <span class="material-symbols-outlined">analytics</span>
                      </button>
                      <button
                        class="btn-icon"
                        :title="t('view-tracked-items', 'View Tracked Records')"
                        @click="openBatchItemsModal(b.id)"
                      >
                        <span class="material-symbols-outlined">receipt_long</span>
                      </button>
                      <button
                        v-if="b.status === 'Committed'"
                        class="btn-icon btn-icon-danger"
                        :title="t('rollback-batch', 'Rollback Batch')"
                        @click="openRollbackModal(b.id)"
                      >
                        <span class="material-symbols-outlined">undo</span>
                      </button>
                    </div>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>

    <!-- MODAL: Table Sample Preview -->
    <div v-if="showTablePreviewModal" class="modal-overlay" @click.self="showTablePreviewModal = false">
      <div class="modal-content modal-lg">
        <div class="modal-header">
          <h3>
            <span class="material-symbols-outlined">table_chart</span>
            {{ t('sample-preview-for', 'Sample Preview') }}: <span class="mono">{{ previewModalTableName }}</span>
          </h3>
          <button class="btn-icon" @click="showTablePreviewModal = false"><span class="material-symbols-outlined">close</span></button>
        </div>
        <div class="modal-body">
          <div v-if="loadingTablePreview" class="p-6 text-center">
            <span class="spinner-sm"></span>
            <p class="mt-2">{{ t('loading-preview', 'Sampling legacy table...') }}</p>
          </div>
          <div v-else-if="!tablePreviewData?.sample_rows?.length" class="empty-state-sm">
            <p>{{ t('no-rows-in-sample', 'No records found in preview sample') }}</p>
          </div>
          <div v-else class="table-wrap max-h-96">
            <table class="data-table table-sm">
              <thead>
                <tr>
                  <th v-for="col in tablePreviewData.columns" :key="col">{{ col }}</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="(r, i) in tablePreviewData.sample_rows" :key="i">
                  <td v-for="col in tablePreviewData.columns" :key="col" class="text-xs">
                    {{ r[col] !== null ? r[col] : 'NULL' }}
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
          <div class="modal-actions">
            <button class="btn-primary" @click="showTablePreviewModal = false">{{ t('close', 'Close') }}</button>
          </div>
        </div>
      </div>
    </div>

    <!-- MODAL: Commit Confirmation -->
    <div v-if="showCommitConfirmModal" class="modal-overlay" @click.self="showCommitConfirmModal = false">
      <div class="modal-content modal-md">
        <div class="modal-header">
          <h3>
            <span class="material-symbols-outlined text-green">task_alt</span>
            {{ t('confirm-commit-title', 'Confirm Migration Commit') }}
          </h3>
          <button class="btn-icon" @click="showCommitConfirmModal = false"><span class="material-symbols-outlined">close</span></button>
        </div>
        <div class="modal-body">
          <p class="mb-4">
            {{ t('commit-warning-msg', 'You are about to commit validated records from staged storage into active Nova ERP business tables.') }}
          </p>

          <div class="alert-banner alert-info mb-4">
            <span class="material-symbols-outlined">shield</span>
            <div class="alert-content text-xs">
              <strong>{{ t('multi-tenant-isolated', 'Multi-Tenant Isolated') }}:</strong>
              {{ t('commit-tenant-note', 'All records will be stamped with your active business context. Every insert is tracked for instant zero-loss rollback.') }}
            </div>
          </div>

          <div v-if="reconciliationHasWarnings" class="checkbox-row mb-4">
            <label class="checkbox-label text-amber">
              <input type="checkbox" v-model="commitForceFlag" />
              <span>{{ t('force-commit-warnings', 'Acknowledge reconciliation warnings and proceed with commit') }}</span>
            </label>
          </div>

          <div class="modal-actions">
            <button class="btn-outline" @click="showCommitConfirmModal = false">{{ t('cancel', 'Cancel') }}</button>
            <button
              class="btn-primary"
              :disabled="committing || (reconciliationHasWarnings && !commitForceFlag)"
              @click="executeCommit"
            >
              <span v-if="committing" class="spinner-sm"></span>
              <span v-else class="material-symbols-outlined">rocket_launch</span>
              {{ committing ? t('committing', 'Committing...') : t('confirm-commit-btn', 'Commit Now') }}
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- MODAL: Rollback Confirmation -->
    <div v-if="showRollbackModal" class="modal-overlay" @click.self="showRollbackModal = false">
      <div class="modal-content modal-md">
        <div class="modal-header">
          <h3 class="text-red">
            <span class="material-symbols-outlined">undo</span>
            {{ t('confirm-rollback-title', 'Confirm Instant Rollback') }}
          </h3>
          <button class="btn-icon" @click="showRollbackModal = false"><span class="material-symbols-outlined">close</span></button>
        </div>
        <div class="modal-body">
          <p class="mb-4">
            {{ t('rollback-warning-msg', 'Are you sure you want to roll back batch') }}
            <strong class="mono">#{{ rollbackTargetBatchId }}</strong>?
          </p>

          <div class="alert-banner alert-warning mb-4">
            <span class="material-symbols-outlined">warning</span>
            <div class="alert-content text-xs">
              {{ t('rollback-details-msg', 'This will safely delete only the records inserted during this migration batch in strict reverse foreign-key dependency order. Pre-existing records are completely unaffected.') }}
            </div>
          </div>

          <div class="form-group mb-4">
            <label>{{ t('rollback-reason', 'Reason for Rollback (Optional)') }}</label>
            <input type="text" v-model="rollbackReason" class="form-input" placeholder="e.g., Reconciliation variance review" />
          </div>

          <div class="modal-actions">
            <button class="btn-outline" @click="showRollbackModal = false">{{ t('cancel', 'Cancel') }}</button>
            <button class="btn-danger" :disabled="rollingBack" @click="executeRollback">
              <span v-if="rollingBack" class="spinner-sm"></span>
              <span v-else class="material-symbols-outlined">delete_forever</span>
              {{ rollingBack ? t('rolling-back', 'Rolling back...') : t('confirm-rollback-btn', 'Roll Back Now') }}
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- MODAL: Batch Items Tracking Drawer -->
    <div v-if="showBatchItemsModal" class="modal-overlay" @click.self="showBatchItemsModal = false">
      <div class="modal-content modal-lg">
        <div class="modal-header">
          <h3>
            <span class="material-symbols-outlined">receipt_long</span>
            {{ t('tracked-items-for-batch', 'Tracked Items for Batch') }} #{{ activeBatchIdForItems }}
          </h3>
          <button class="btn-icon" @click="showBatchItemsModal = false"><span class="material-symbols-outlined">close</span></button>
        </div>
        <div class="modal-body">
          <div v-if="loadingBatchItems" class="p-6 text-center">
            <span class="spinner-sm"></span>
            <p class="mt-2">{{ t('loading-items', 'Loading tracked audit records...') }}</p>
          </div>
          <div v-else-if="!batchItemsList.length" class="empty-state-sm">
            <p>{{ t('no-items-tracked', 'No individual record items found for this batch') }}</p>
          </div>
          <div v-else class="table-wrap max-h-96">
            <table class="data-table table-sm">
              <thead>
                <tr>
                  <th>{{ t('id', 'ID') }}</th>
                  <th>{{ t('entity-type', 'Entity') }}</th>
                  <th>{{ t('target-table', 'Table') }}</th>
                  <th>{{ t('target-id', 'Target ID') }}</th>
                  <th>{{ t('source-key', 'Source Key') }}</th>
                  <th>{{ t('status', 'Status') }}</th>
                  <th>{{ t('created-at', 'Timestamp') }}</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="item in batchItemsList" :key="item.id">
                  <td class="mono">{{ item.id }}</td>
                  <td><strong>{{ item.entity_type }}</strong></td>
                  <td class="mono">{{ item.target_table }}</td>
                  <td class="mono font-bold">{{ item.target_id }}</td>
                  <td class="mono">{{ item.source_key || '-' }}</td>
                  <td>
                    <span class="badge" :class="item.status === 'Inserted' ? 'badge-active' : 'badge-disabled'">
                      {{ item.status }}
                    </span>
                  </td>
                  <td class="text-xs">{{ formatDate(item.created_at) }}</td>
                </tr>
              </tbody>
            </table>
          </div>
          <div class="modal-actions">
            <button class="btn-primary" @click="showBatchItemsModal = false">{{ t('close', 'Close') }}</button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useI18n } from '../../composables/useI18n.js'
import { migrationApi } from '../../api/migration.js'

const { t, dir } = useI18n()

// ==============================================================================
// State Variables
// ==============================================================================

// Stepper / Navigation State: 'connect' | 'mapping' | 'reconciliation' | 'committed' | 'rolled_back' | 'history'
const step = ref('connect')
const globalError = ref('')

// Step 1: Source Configuration
const sourceType = ref('sqlserver') // 'sqlserver' | 'csv_dump' | 'upload_csv'
const sqlConfig = ref({
  host: 'localhost',
  port: 1433,
  database: '',
  user: 'sa',
  password: '',
  trust_server_certificate: true,
  schema_name: 'dbo',
})

const csvDumpConfig = ref({
  dump_path: '',
  delimiter: null,
  encoding: null,
  has_header: true,
})

// Single File CSV Upload
const singleUploadEntity = ref('products')
const singleFile = ref(null)
const singleFileInput = ref(null)
const singleUploading = ref(false)

// Connection Testing State
const testingConnection = ref(false)
const testResult = ref(null)

// Step 2: Schema Discovery & Mapping State
const discoveringSchema = ref(false)
const discoveredTables = ref([])
const tableSchemas = ref({})
const selectedTableForPreview = ref('')

// Table Sample Preview Modal State
const showTablePreviewModal = ref(false)
const previewModalTableName = ref('')
const loadingTablePreview = ref(false)
const tablePreviewData = ref({ columns: [], sample_rows: [] })

// Entity Mappings List
const entityMappings = ref([
  {
    key: 'products',
    label: 'Products & SKUs',
    target_tcode: 'T0003',
    target_table: 't0003',
    enabled: true,
    source_table: '',
    fields: [
      { label: 'SKU / Product Code', target: 'sku', source: '', required: true, transform: 'trim' },
      { label: 'Product Name', target: 'name', source: '', required: true, transform: 'trim' },
      { label: 'Category', target: 'category_id', source: '', default_placeholder: 'General' },
      { label: 'Unit of Measure', target: 'uom_id', source: '', default_placeholder: 'PCS' },
      { label: 'Selling Price', target: 'selling_price', source: '', transform: 'round_2' },
      { label: 'Cost Price', target: 'cost_price', source: '', transform: 'round_2' },
      { label: 'Barcode', target: 'barcode', source: '', transform: 'trim' },
    ],
  },
  {
    key: 'customers',
    label: 'Customers & Receivables',
    target_tcode: 'T0010',
    target_table: 't0010',
    enabled: true,
    source_table: '',
    fields: [
      { label: 'Customer Code', target: 'code', source: '', required: true, transform: 'trim' },
      { label: 'Customer Name', target: 'name', source: '', required: true, transform: 'trim' },
      { label: 'Phone Number', target: 'phone', source: '', transform: 'strip_non_numeric' },
      { label: 'Email', target: 'email', source: '', transform: 'trim' },
      { label: 'Opening Balance', target: 'opening_balance', source: '', transform: 'round_2' },
      { label: 'Credit Limit', target: 'credit_limit', source: '', transform: 'round_2' },
    ],
  },
  {
    key: 'suppliers',
    label: 'Suppliers & Vendors',
    target_tcode: 'T0011',
    target_table: 't0011',
    enabled: true,
    source_table: '',
    fields: [
      { label: 'Supplier Code', target: 'code', source: '', required: true, transform: 'trim' },
      { label: 'Supplier Name', target: 'name', source: '', required: true, transform: 'trim' },
      { label: 'Phone', target: 'phone', source: '', transform: 'strip_non_numeric' },
      { label: 'Contact Person', target: 'contact_person', source: '', transform: 'trim' },
    ],
  },
  {
    key: 'inventory_opening',
    label: 'Inventory Opening Balances',
    target_tcode: 'T0009',
    target_table: 't0009',
    enabled: true,
    source_table: '',
    fields: [
      { label: 'Product SKU / Code', target: 'sku', source: '', required: true, transform: 'trim' },
      { label: 'Warehouse Name', target: 'warehouse_name', source: '', default_placeholder: 'Main Warehouse' },
      { label: 'Opening Quantity', target: 'quantity', source: '', required: true, transform: 'round_2' },
      { label: 'Unit Cost', target: 'unit_cost', source: '', transform: 'round_2' },
    ],
  },
])

// Data Cleansing Configuration
const cleansingConfig = ref({
  enable_phantom_detection: true,
  phantom_inactivity_months: 12,
  phantom_zero_stock_check: true,
  phantom_action: 'flag',
  deduplicate_skus: true,
  deduplicate_barcodes: true,
  sanitize_phone_numbers: true,
  sanitize_email_addresses: true,
  auto_create_missing_lookups: true,
  clamp_negative_stock: true,
  default_uom: 'PCS',
  default_category: 'General',
  default_warehouse: 'Main Warehouse',
})

// Step 3: Dry Run & Reconciliation State
const runningDryRun = ref(false)
const dryRunResult = ref(null)
const reconciliationReport = ref(null)
const currentBatchId = ref(null)
const activeReconTab = ref('customer_balances')

// Step 4: Commit & Rollback Modal States
const showCommitConfirmModal = ref(false)
const commitForceFlag = ref(false)
const committing = ref(false)
const commitResult = ref(null)

const showRollbackModal = ref(false)
const rollbackTargetBatchId = ref(null)
const rollbackReason = ref('')
const rollingBack = ref(false)
const rollbackResult = ref(null)

// Step 5: Batches History & Audit Items State
const batchesList = ref([])
const loadingBatches = ref(false)
const showBatchItemsModal = ref(false)
const activeBatchIdForItems = ref(null)
const loadingBatchItems = ref(false)
const batchItemsList = ref([])

// ==============================================================================
// Computed Properties
// ==============================================================================

const connectionInfoSummary = computed(() => {
  if (sourceType.value === 'sqlserver') {
    return `SQL Server (${sqlConfig.value.database || sqlConfig.value.host})`
  }
  if (sourceType.value === 'csv_dump') {
    return `CSV Dump (${csvDumpConfig.value.dump_path || 'Archive'})`
  }
  return 'Single CSV Upload'
})

const customerBalanceReconciliation = computed(() => {
  return reconciliationReport.value?.customer_balance || dryRunResult.value?.reconciliation_summary?.customer_balance || null
})

const inventoryReconciliation = computed(() => {
  return reconciliationReport.value?.inventory || dryRunResult.value?.reconciliation_summary?.inventory || null
})

const customerDiscrepancies = computed(() => {
  const cbr = customerBalanceReconciliation.value
  if (!cbr) return []
  return cbr.discrepancies?.length ? cbr.discrepancies : (cbr.top_variances || [])
})

const customerDiscrepanciesCount = computed(() => {
  return customerDiscrepancies.value.filter(c => !c.is_matched).length
})

const warehouseSummariesList = computed(() => {
  const inv = inventoryReconciliation.value
  if (!inv?.warehouse_summaries) return []
  return Object.values(inv.warehouse_summaries)
})

const inventoryDiscrepancies = computed(() => {
  return inventoryReconciliation.value?.discrepancies || []
})

const inventoryDiscrepanciesCount = computed(() => {
  return inventoryDiscrepancies.value.filter(i => !i.is_matched || i.status !== 'OK').length
})

const entityCountsList = computed(() => {
  const report = reconciliationReport.value
  if (report?.entity_counts && Object.keys(report.entity_counts).length) {
    return report.entity_counts
  }
  return dryRunResult.value?.entity_summaries || {}
})

const discoveredLookupsList = computed(() => {
  const cl = dryRunResult.value?.cleansing_summary
  if (!cl?.discovered_lookups) return []
  return Object.entries(cl.discovered_lookups).map(([type, values]) => ({ type, values }))
})

const validationErrorsList = computed(() => {
  return dryRunResult.value?.validation_errors || []
})

const recommendationsList = computed(() => {
  return reconciliationReport.value?.recommendations || []
})

const reconciliationStatus = computed(() => {
  return reconciliationReport.value?.overall_status || (dryRunResult.value?.success ? 'Passed' : 'Failed')
})

const reconciliationStatusClass = computed(() => {
  if (reconciliationStatus.value === 'Passed') return 'status-card-passed'
  if (reconciliationStatus.value === 'PassedWithWarnings') return 'status-card-warning'
  return 'status-card-failed'
})

const reconciliationStatusIcon = computed(() => {
  if (reconciliationStatus.value === 'Passed') return 'check_circle'
  if (reconciliationStatus.value === 'PassedWithWarnings') return 'warning'
  return 'error'
})

const reconciliationStatusTitle = computed(() => {
  if (reconciliationStatus.value === 'Passed') return t('recon-passed', 'Dry-Run Simulation Passed — Ready to Commit')
  if (reconciliationStatus.value === 'PassedWithWarnings') return t('recon-warning', 'Dry-Run Passed with Reconciliation Warnings')
  return t('recon-failed', 'Dry-Run Simulation Failed')
})

const reconciliationHasWarnings = computed(() => {
  return reconciliationStatus.value === 'PassedWithWarnings' || (validationErrorsList.value.length > 0)
})

const receivablesVarianceClass = computed(() => {
  const delta = customerBalanceReconciliation.value?.total_receivables_delta ?? 0
  return Math.abs(delta) < 0.01 ? 'text-green' : 'text-red'
})

const inventoryValuationVarianceClass = computed(() => {
  const delta = inventoryReconciliation.value?.total_valuation_delta ?? 0
  return Math.abs(delta) < 0.01 ? 'text-green' : 'text-red'
})

// ==============================================================================
// Methods & Actions
// ==============================================================================

function isStepCompleted(s) {
  const order = ['connect', 'mapping', 'reconciliation', 'committed']
  const curIdx = order.indexOf(step.value)
  const targetIdx = order.indexOf(s)
  return targetIdx !== -1 && curIdx > targetIdx
}

function canGoToStep(s) {
  if (s === 'connect') return true
  if (s === 'mapping') return discoveredTables.value.length > 0 || testResult.value?.success
  if (s === 'reconciliation') return dryRunResult.value !== null
  if (s === 'committed') return commitResult.value !== null
  return false
}

function goToStep(s) {
  if (canGoToStep(s)) {
    step.value = s
  }
}

function toggleHistory(show) {
  if (show) {
    step.value = 'history'
    loadBatchesList()
  } else {
    step.value = 'connect'
  }
}

function resetWizard() {
  step.value = 'connect'
  globalError.value = ''
  testResult.value = null
  dryRunResult.value = null
  reconciliationReport.value = null
  commitResult.value = null
  rollbackResult.value = null
  singleFile.value = null
}

function handleSingleFile(e) {
  singleFile.value = e.target.files[0] || null
}

function handleSingleDrop(e) {
  singleFile.value = e.dataTransfer.files[0] || null
}

function buildConnectionPayload() {
  if (sourceType.value === 'sqlserver') {
    return {
      source_type: 'sqlserver',
      config: {
        host: sqlConfig.value.host,
        port: sqlConfig.value.port,
        database: sqlConfig.value.database,
        user: sqlConfig.value.user,
        password: sqlConfig.value.password,
        trust_server_certificate: sqlConfig.value.trust_server_certificate,
        schema_name: sqlConfig.value.schema_name,
      },
    }
  } else {
    return {
      source_type: 'csv_dump',
      config: {
        dump_path: csvDumpConfig.value.dump_path,
        delimiter: csvDumpConfig.value.delimiter,
        encoding: csvDumpConfig.value.encoding,
        has_header: csvDumpConfig.value.has_header,
      },
    }
  }
}

async function runTestConnection() {
  globalError.value = ''
  testingConnection.value = true
  testResult.value = null

  try {
    const payload = buildConnectionPayload()
    const res = await migrationApi.testConnection(payload)
    testResult.value = res
    if (res.tables && res.tables.length) {
      discoveredTables.value = res.tables.map(name => ({ name, row_count: null }))
    }
  } catch (err) {
    globalError.value = err.response?.data?.detail || err.message || 'Connection test failed'
    testResult.value = { success: false, message: globalError.value }
  } finally {
    testingConnection.value = false
  }
}

async function runDiscoverSchema() {
  globalError.value = ''
  discoveringSchema.value = true

  try {
    const payload = buildConnectionPayload()
    const res = await migrationApi.discoverSchema(payload)
    if (res.schemas) {
      tableSchemas.value = res.schemas
      discoveredTables.value = Object.entries(res.schemas).map(([name, meta]) => ({
        name,
        row_count: meta.row_count_estimate,
        columns: meta.columns || [],
      }))
    } else if (res.tables) {
      discoveredTables.value = res.tables.map(name => ({ name, row_count: null }))
    }

    autoMapAllEntities()
    step.value = 'mapping'
  } catch (err) {
    globalError.value = err.response?.data?.detail || err.message || 'Schema discovery failed'
  } finally {
    discoveringSchema.value = false
  }
}

async function uploadSingleCsvFile() {
  if (!singleFile.value) return
  singleUploading.value = true
  globalError.value = ''

  try {
    const res = await migrationApi.uploadCsv(singleFile.value, singleUploadEntity.value, {})
    currentBatchId.value = res.batch_id
    dryRunResult.value = {
      batch_key: res.batch_key || `BATCH-${res.batch_id}`,
      batch_id: res.batch_id,
      success: true,
      total_source_rows: res.total_rows || 0,
      valid_rows_count: res.valid_rows || 0,
      error_rows_count: res.error_rows || 0,
      validation_errors: res.errors || [],
      entity_summaries: {
        [singleUploadEntity.value]: {
          source_count: res.total_rows || 0,
          staged_count: res.valid_rows || 0,
          error_count: res.error_rows || 0,
        },
      },
    }
    step.value = 'reconciliation'
  } catch (err) {
    globalError.value = err.response?.data?.detail || err.message || 'Upload failed'
  } finally {
    singleUploading.value = false
  }
}

function getTableColumns(tableName) {
  if (!tableName) return []
  const schema = tableSchemas.value[tableName]
  if (schema?.column_names?.length) return schema.column_names
  if (schema?.columns?.length) return schema.columns.map(c => c.name || c)
  return []
}

function autoMapAllEntities() {
  entityMappings.value.forEach(entity => {
    // Fuzzy match table name
    const match = discoveredTables.value.find(t => {
      const n = t.name.toLowerCase()
      if (entity.key === 'products') return n.includes('product') || n.includes('item') || n.includes('article')
      if (entity.key === 'customers') return n.includes('customer') || n.includes('client') || n.includes('debtor')
      if (entity.key === 'suppliers') return n.includes('supplier') || n.includes('vendor') || n.includes('creditor')
      if (entity.key === 'inventory_opening') return n.includes('stock') || n.includes('inventory') || n.includes('opening')
      return false
    })

    if (match) {
      entity.source_table = match.name
      onEntitySourceChanged(entity)
    }
  })
}

function onEntitySourceChanged(entity) {
  if (!entity.source_table) return
  const cols = getTableColumns(entity.source_table)
  if (!cols.length) return

  entity.fields.forEach(f => {
    if (!f.source) {
      const match = cols.find(c => {
        const cl = c.toLowerCase()
        const tl = f.target.toLowerCase()
        return cl === tl || cl.includes(tl) || (tl === 'sku' && (cl.includes('code') || cl.includes('itemno')))
      })
      if (match) f.source = match
    }
  })
}

function selectTableForPreview(tableName) {
  selectedTableForPreview.value = tableName
}

async function openPreviewModal(tableName) {
  previewModalTableName.value = tableName
  showTablePreviewModal.value = true
  loadingTablePreview.value = true
  tablePreviewData.value = { columns: [], sample_rows: [] }

  try {
    const payload = {
      source_type: sourceType.value,
      connection: buildConnectionPayload().config,
      table_name: tableName,
      limit: 20,
    }
    const res = await migrationApi.previewTable(payload)
    tablePreviewData.value = {
      columns: res.columns || [],
      sample_rows: res.sample_rows || res.rows || [],
    }
  } catch (err) {
    globalError.value = `Failed to preview ${tableName}: ${err.message}`
  } finally {
    loadingTablePreview.value = false
  }
}

async function startDryRun() {
  globalError.value = ''
  runningDryRun.value = true

  try {
    const mappingsObj = {}
    entityMappings.value.forEach(ent => {
      if (ent.enabled && ent.source_table) {
        const fieldMap = {}
        ent.fields.forEach(f => {
          if (f.source) fieldMap[f.source] = f.target
        })
        mappingsObj[ent.key] = {
          entity_type: ent.key,
          target_tcode: ent.target_tcode,
          target_table: ent.target_table,
          source_table: ent.source_table,
          field_mappings: fieldMap,
          enabled: true,
        }
      }
    })

    const payload = {
      source_type: sourceType.value,
      connection_config: buildConnectionPayload().config,
      mapping_config: { mappings: mappingsObj },
      cleansing_config: cleansingConfig.value,
    }

    const res = await migrationApi.runDryRun(payload)
    dryRunResult.value = res
    currentBatchId.value = res.batch_id

    // Fetch comprehensive reconciliation report if batch_id exists
    if (res.batch_id) {
      try {
        const report = await migrationApi.getBatchReconciliation(res.batch_id)
        reconciliationReport.value = report
      } catch {
        // Fallback to inline summary if reconciliation endpoint fails
        reconciliationReport.value = res.reconciliation_summary
      }
    }

    step.value = 'reconciliation'
  } catch (err) {
    globalError.value = err.response?.data?.detail || err.message || 'Dry-run simulation failed'
  } finally {
    runningDryRun.value = false
  }
}

function openCommitModal() {
  commitForceFlag.value = false
  showCommitConfirmModal.value = true
}

async function executeCommit() {
  const batchId = dryRunResult.value?.batch_id || currentBatchId.value
  if (!batchId) {
    globalError.value = 'No active batch ID found to commit'
    return
  }

  committing.value = true
  globalError.value = ''

  try {
    const res = await migrationApi.commitBatch(batchId, commitForceFlag.value)
    commitResult.value = res
    showCommitConfirmModal.value = false
    step.value = 'committed'
  } catch (err) {
    globalError.value = err.response?.data?.detail || err.message || 'Commit failed'
  } finally {
    committing.value = false
  }
}

function openRollbackModal(batchId) {
  rollbackTargetBatchId.value = batchId
  rollbackReason.value = ''
  showRollbackModal.value = true
}

async function executeRollback() {
  if (!rollbackTargetBatchId.value) return
  rollingBack.value = true
  globalError.value = ''

  try {
    const res = await migrationApi.rollbackBatch(rollbackTargetBatchId.value, rollbackReason.value)
    rollbackResult.value = res
    showRollbackModal.value = false
    step.value = 'rolled_back'
  } catch (err) {
    globalError.value = err.response?.data?.detail || err.message || 'Rollback failed'
  } finally {
    rollingBack.value = false
  }
}

async function loadBatchesList() {
  loadingBatches.value = true
  try {
    const res = await migrationApi.listBatches({ limit: 100 })
    batchesList.value = res.items || res || []
  } catch (err) {
    globalError.value = err.response?.data?.detail || err.message || 'Failed to load batch history'
  } finally {
    loadingBatches.value = false
  }
}

async function viewBatchReconciliationReport(batchId) {
  globalError.value = ''
  try {
    currentBatchId.value = batchId
    const report = await migrationApi.getBatchReconciliation(batchId)
    reconciliationReport.value = report
    dryRunResult.value = {
      batch_id: batchId,
      batch_key: report.batch_key || `BATCH-${batchId}`,
      success: true,
      total_source_rows: report.entity_counts ? Object.values(report.entity_counts).reduce((a, b) => a + (b.source_count || 0), 0) : 0,
      valid_rows_count: report.entity_counts ? Object.values(report.entity_counts).reduce((a, b) => a + (b.staged_count || 0), 0) : 0,
      error_rows_count: report.unresolved_errors_count || 0,
      validation_errors: [],
    }
    step.value = 'reconciliation'
  } catch (err) {
    globalError.value = err.response?.data?.detail || err.message || 'Failed to load reconciliation report'
  }
}

async function openBatchItemsModal(batchId) {
  activeBatchIdForItems.value = batchId
  showBatchItemsModal.value = true
  loadingBatchItems.value = true
  batchItemsList.value = []

  try {
    const items = await migrationApi.getBatchItems(batchId, { limit: 100 })
    batchItemsList.value = items || []
  } catch (err) {
    globalError.value = err.response?.data?.detail || err.message || 'Failed to load tracked items'
  } finally {
    loadingBatchItems.value = false
  }
}

function getBatchStatusBadgeClass(st) {
  if (st === 'Committed') return 'badge-active'
  if (st === 'DryRunCompleted' || st === 'Preview') return 'badge-primary'
  if (st === 'RolledBack') return 'badge-danger'
  return 'badge-disabled'
}

function formatCurrency(val) {
  if (val == null) return '$0.00'
  const num = Number(val)
  const isNegative = num < 0
  const absVal = Math.abs(num).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })
  return isNegative ? `-$${absVal}` : `$${absVal}`
}

function formatNumber(val) {
  if (val == null) return '0'
  return Number(val).toLocaleString(undefined, { maximumFractionDigits: 2 })
}

function formatFileSize(bytes) {
  if (!bytes) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return `${(bytes / Math.pow(k, i)).toFixed(1)} ${sizes[i]}`
}

function formatDate(dt) {
  if (!dt) return '-'
  try {
    return new Date(dt).toLocaleString()
  } catch {
    return String(dt)
  }
}

onMounted(() => {
  // Initial mount hook
})
</script>

<style scoped>
.migration-container { padding: 0 4px; }
.page-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 24px; }
.header-actions { display: flex; gap: 12px; }

/* Wizard Stepper */
.wizard-stepper { display: flex; align-items: center; justify-content: space-between; background: var(--bg-surface); border: 1px solid var(--border-default); border-radius: 12px; padding: 16px 24px; }
.step-item { display: flex; align-items: center; gap: 12px; cursor: pointer; opacity: 0.6; transition: all 0.2s; }
.step-item.active { opacity: 1; font-weight: 700; }
.step-item.completed { opacity: 0.9; }
.step-item.disabled { cursor: not-allowed; opacity: 0.35; }
.step-circle { width: 36px; height: 36px; border-radius: 50%; background: var(--bg-surface-hover); color: var(--text-secondary); display: flex; align-items: center; justify-content: center; font-weight: 700; font-size: 14px; border: 2px solid var(--border-input); }
.step-item.active .step-circle { background: var(--color-primary); color: #fff; border-color: var(--color-primary); }
.step-item.completed .step-circle { background: var(--color-success); color: #fff; border-color: var(--color-success); }
.step-info { display: flex; flex-direction: column; }
.step-label { font-size: 13px; font-weight: 600; color: var(--text-primary); }
.step-desc { font-size: 11px; color: var(--text-muted); }
.step-connector { flex: 1; height: 2px; background: var(--border-default); margin: 0 16px; }

/* Cards & Layout */
.card-header { padding: 18px 24px; border-bottom: 1px solid var(--border-light); }
.card-header h3 { font-size: 16px; font-weight: 700; color: var(--text-primary); margin: 0; }
.card-subtitle { font-size: 12px; color: var(--text-muted); margin-top: 4px; }
.card-body { padding: 24px; }

/* Source Type Grid */
.source-type-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 16px; }
.source-card { border: 2px solid var(--border-default); border-radius: 10px; padding: 20px; cursor: pointer; transition: all 0.2s; background: var(--bg-surface); text-align: left; position: relative; }
.source-card:hover { border-color: var(--color-primary); transform: translateY(-2px); box-shadow: 0 4px 12px rgba(0,0,0,0.05); }
.source-card.selected { border-color: var(--color-primary); background: var(--bg-primary-faded); }
.source-icon { font-size: 36px; color: var(--color-primary); margin-bottom: 12px; display: block; }
.source-card h4 { font-size: 15px; font-weight: 700; color: var(--text-primary); margin: 0 0 6px; }
.source-card p { font-size: 12px; color: var(--text-muted); margin: 0; line-height: 1.4; }

/* Forms */
.form-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 16px; }
.form-group { margin-bottom: 14px; }
.form-group label { display: block; font-size: 12px; font-weight: 600; color: var(--text-secondary); margin-bottom: 4px; }
.form-input { width: 100%; padding: 8px 12px; border: 1px solid var(--border-input); border-radius: 6px; font-size: 13px; outline: none; transition: border 0.15s; background: var(--bg-surface); color: var(--text-primary); }
.form-input:focus { border-color: var(--color-primary); }
.form-input-sm { padding: 4px 8px; font-size: 12px; }
.form-hint { font-size: 11px; color: var(--text-muted); margin-top: 4px; display: block; }

/* Upload Zone */
.upload-zone { border: 2px dashed var(--border-input); border-radius: 8px; padding: 36px; text-align: center; margin-bottom: 16px; cursor: pointer; transition: border-color 0.2s; background: var(--bg-surface-low); }
.upload-zone:hover { border-color: var(--color-primary); }
.upload-icon { font-size: 44px; color: var(--text-muted); margin-bottom: 8px; }
.file-name { margin-top: 8px; font-size: 13px; color: var(--color-primary); font-weight: 600; }

/* Test Result Banner */
.test-result-box { padding: 16px 20px; border-radius: 8px; border: 1px solid; }
.test-success { background: #f0fdf4; border-color: #86efac; color: #166534; }
.test-failure { background: #fef2f2; border-color: #fca5a5; color: #991b1b; }
.test-icon { font-size: 32px; }
.test-title { font-size: 15px; font-weight: 700; margin: 0 0 2px; }
.test-msg { font-size: 13px; margin: 0 0 6px; }
.test-meta { display: flex; gap: 16px; font-size: 12px; flex-wrap: wrap; }

/* Alert Banners */
.alert-banner { display: flex; align-items: flex-start; gap: 10px; padding: 12px 16px; border-radius: 8px; border: 1px solid; font-size: 13px; }
.alert-error { background: #fef2f2; border-color: #fca5a5; color: var(--color-error); }
.alert-warning { background: #fffbeb; border-color: #fde68a; color: #92400e; }
.alert-info { background: #eff6ff; border-color: #bfdbfe; color: #1e40af; }
.alert-content { flex: 1; }

/* Discovered Tables Chips */
.table-chips-grid { display: flex; flex-wrap: wrap; gap: 10px; }
.table-chip { display: inline-flex; align-items: center; gap: 6px; background: var(--bg-surface-low); border: 1px solid var(--border-default); border-radius: 20px; padding: 6px 14px; font-size: 12px; cursor: pointer; transition: all 0.15s; }
.table-chip:hover, .table-chip.active { border-color: var(--color-primary); background: var(--bg-primary-faded); }
.chip-icon { font-size: 16px; color: var(--color-primary); }
.chip-name { font-weight: 600; color: var(--text-primary); }
.chip-count { font-size: 11px; color: var(--text-muted); }
.btn-chip-preview { background: none; border: none; cursor: pointer; color: var(--text-muted); display: flex; align-items: center; padding: 2px; }
.btn-chip-preview:hover { color: var(--color-primary); }

/* Entity Mapping Cards */
.entity-mapping-list { display: flex; flex-direction: column; gap: 16px; }
.entity-mapping-card { border: 1px solid var(--border-default); border-radius: 8px; background: var(--bg-surface); overflow: hidden; }
.entity-card-header { display: flex; justify-content: space-between; align-items: center; padding: 14px 18px; background: var(--bg-surface-low); border-bottom: 1px solid var(--border-light); }
.entity-title-row { display: flex; align-items: center; gap: 12px; }
.entity-checkbox { width: 18px; height: 18px; cursor: pointer; }
.entity-name { font-size: 14px; font-weight: 700; color: var(--text-primary); margin: 0; }
.tcode-badge { font-size: 11px; padding: 2px 6px; background: var(--bg-surface); border: 1px solid var(--border-default); border-radius: 4px; }
.entity-source-select { display: flex; align-items: center; gap: 8px; font-size: 12px; font-weight: 600; }

.field-mapping-panel { padding: 16px; }
.field-mapping-header { display: grid; grid-template-columns: 2fr 2fr 1.5fr 1.5fr; gap: 12px; font-size: 11px; font-weight: 700; color: var(--text-muted); text-transform: uppercase; margin-bottom: 8px; }
.field-mapping-row { display: grid; grid-template-columns: 2fr 2fr 1.5fr 1.5fr; gap: 12px; align-items: center; padding: 6px 0; border-bottom: 1px solid var(--border-light); font-size: 12px; }
.field-target-cell { display: flex; align-items: center; gap: 6px; }
.field-target-name { font-weight: 600; color: var(--text-primary); }
.field-target-key { font-size: 11px; color: var(--text-muted); }

/* Cleansing Grid */
.cleansing-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 24px; }
.cleansing-section { border: 1px solid var(--border-default); border-radius: 8px; padding: 18px; background: var(--bg-surface-low); }
.cleansing-subhead { display: flex; align-items: center; gap: 8px; font-size: 14px; font-weight: 700; color: var(--text-primary); margin: 0 0 14px; }
.defaults-grid { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 10px; }
.inline-input-group { display: flex; align-items: center; gap: 10px; font-size: 12px; }

/* Status Cards & Reconciliation */
.reconciliation-status-card { display: flex; justify-content: space-between; align-items: center; padding: 20px 24px; border-radius: 10px; border: 1px solid; }
.status-card-passed { background: #f0fdf4; border-color: #86efac; color: #166534; }
.status-card-warning { background: #fffbeb; border-color: #fde68a; color: #92400e; }
.status-card-failed { background: #fef2f2; border-color: #fca5a5; color: #991b1b; }
.status-icon { font-size: 36px; }
.status-title { font-size: 18px; font-weight: 700; margin: 0 0 2px; }
.status-subtitle { font-size: 12px; opacity: 0.9; margin: 0; }
.status-actions { display: flex; gap: 12px; }

/* Stats Row */
.stats-row { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 16px; }
.stat-card { background: var(--bg-surface); border: 1px solid var(--border-default); border-radius: 10px; padding: 18px; text-align: left; }
.stat-label { display: block; font-size: 11px; font-weight: 700; text-transform: uppercase; color: var(--text-muted); margin-bottom: 6px; }
.stat-value { font-size: 24px; font-weight: 700; color: var(--text-primary); display: block; }
.stat-sub { font-size: 12px; margin-top: 4px; display: block; color: var(--text-muted); }

/* Tabs */
.tab-bar { display: flex; border-bottom: 1px solid var(--border-default); background: var(--bg-surface-low); padding: 0 16px; gap: 8px; overflow-x: auto; }
.tab-btn { display: inline-flex; align-items: center; gap: 8px; padding: 14px 18px; background: none; border: none; border-bottom: 2px solid transparent; font-size: 13px; font-weight: 600; color: var(--text-muted); cursor: pointer; transition: all 0.15s; white-space: nowrap; }
.tab-btn:hover { color: var(--color-primary); }
.tab-btn.active { color: var(--color-primary); border-bottom-color: var(--color-primary); font-weight: 700; }
.tab-badge { font-size: 10px; padding: 1px 6px; border-radius: 10px; }

/* Reconciliation Drilldown Details */
.recon-summary-panel { display: flex; gap: 24px; background: var(--bg-surface-low); padding: 14px 20px; border-radius: 8px; border: 1px solid var(--border-light); flex-wrap: wrap; }
.recon-metric { display: flex; flex-direction: column; }
.metric-label { font-size: 11px; text-transform: uppercase; color: var(--text-muted); font-weight: 600; }
.metric-value { font-size: 16px; font-weight: 700; color: var(--text-primary); }
.subhead { font-size: 14px; font-weight: 700; color: var(--text-primary); margin: 0; }
.empty-state-sm { text-align: center; padding: 32px; color: var(--text-muted); font-size: 13px; }
.empty-state-sm .material-symbols-outlined { font-size: 36px; margin-bottom: 8px; }

/* Lookups & Recommendations */
.lookup-discovery-box { background: var(--bg-surface-low); border: 1px solid var(--border-default); border-radius: 8px; padding: 16px; }
.lookup-badges { display: flex; flex-direction: column; gap: 8px; margin-top: 8px; }
.lookup-group { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.lookup-group-label { font-size: 12px; font-weight: 600; color: var(--text-secondary); width: 100px; }
.badge-outline { background: var(--bg-surface); border: 1px solid var(--border-default); color: var(--text-primary); }

.recommendations-list { display: flex; flex-direction: column; gap: 10px; }
.rec-item { display: flex; align-items: flex-start; gap: 10px; background: var(--bg-surface-low); padding: 12px 16px; border-radius: 6px; border-left: 4px solid var(--color-primary); }
.rec-icon { color: var(--color-primary); font-size: 20px; }
.rec-text { font-size: 13px; color: var(--text-primary); margin: 0; }

/* Step Actions */
.step-actions { display: flex; justify-content: flex-end; gap: 12px; margin-top: 24px; }

/* Modals */
.modal-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.5); z-index: 1000; display: flex; align-items: center; justify-content: center; }
.modal-content { background: var(--bg-surface); border-radius: 12px; width: 680px; max-width: 92vw; max-height: 88vh; overflow-y: auto; box-shadow: 0 12px 36px rgba(0,0,0,0.2); }
.modal-sm { width: 440px; }
.modal-md { width: 560px; }
.modal-lg { width: 840px; }
.modal-header { display: flex; justify-content: space-between; align-items: center; padding: 18px 24px; border-bottom: 1px solid var(--border-light); }
.modal-header h3 { font-size: 16px; font-weight: 700; color: var(--text-primary); margin: 0; display: flex; align-items: center; gap: 8px; }
.modal-body { padding: 24px; }
.modal-actions { display: flex; justify-content: flex-end; gap: 12px; margin-top: 24px; }

/* Committed & Rollback Screens */
.committed-icon { font-size: 64px; color: var(--color-success); margin-bottom: 12px; }
.rollback-icon { font-size: 64px; color: var(--color-error); margin-bottom: 12px; }
.committed-title { font-size: 24px; font-weight: 800; color: var(--text-primary); margin: 0 0 6px; }
.committed-sub { font-size: 14px; color: var(--text-muted); margin: 0; }
.commit-stats-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; text-align: left; }
.inserted-entity-chips { display: flex; flex-wrap: wrap; gap: 10px; justify-content: center; }

/* Utilities */
.text-amber { color: #d97706; }
.text-right { text-align: right; }
.text-xs { font-size: 11px; }
.font-bold { font-weight: 700; }
.py-8 { padding-top: 32px; padding-bottom: 32px; }
.my-6 { margin-top: 24px; margin-bottom: 24px; }
.mt-4 { margin-top: 16px; }
.mt-3 { margin-top: 12px; }
.mt-2 { margin-top: 8px; }
.mb-2 { margin-bottom: 8px; }
.mb-3 { margin-bottom: 12px; }
.mb-4 { margin-bottom: 16px; }
.mb-8 { margin-bottom: 32px; }
.w-24 { width: 96px; }
.max-w-xl { max-width: 580px; }
.mx-auto { margin-left: auto; margin-right: auto; }
.max-h-96 { max-height: 380px; }
.flex { display: flex; }
.items-center { align-items: center; }
.justify-between { display: flex; justify-content: space-between; }
.justify-center { justify-content: center; }
.gap-3 { gap: 12px; }
.gap-4 { gap: 16px; }
.badge-primary { background: var(--bg-primary-faded); color: var(--color-primary); }
.badge-warning { background: #fef3c7; color: #92400e; }
.btn-danger { background: var(--color-error); color: #fff; border: none; padding: 8px 20px; border-radius: 8px; font-size: 13px; font-weight: 600; cursor: pointer; display: inline-flex; align-items: center; gap: 6px; }
.btn-danger:hover { background: #b91c1c; }
.btn-icon-danger:hover { color: var(--color-error); background: #fee2e2; }
.action-btn-group { display: inline-flex; gap: 4px; }
.spinner-sm { width: 16px; height: 16px; border: 2px solid rgba(255,255,255,0.3); border-top-color: #fff; border-radius: 50%; animation: spin 0.6s linear infinite; display: inline-block; }
.spinner-lg { width: 32px; height: 32px; border: 3px solid rgba(0,0,0,0.1); border-top-color: var(--color-primary); border-radius: 50%; animation: spin 0.6s linear infinite; display: inline-block; }
@keyframes spin { to { transform: rotate(360deg); } }

@media (max-width: 768px) {
  .wizard-stepper { flex-direction: column; gap: 12px; align-items: flex-start; }
  .step-connector { display: none; }
  .cleansing-grid { grid-template-columns: 1fr; }
  .field-mapping-header, .field-mapping-row { grid-template-columns: 1fr; gap: 6px; }
}
</style>
