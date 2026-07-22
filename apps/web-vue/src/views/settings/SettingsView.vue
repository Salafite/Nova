<template>
  <div class="sv-page" :dir="dir">
    <header class="sv-header">
      <div class="sv-header-left">
        <h1 class="sv-title">{{ t('settings') }}</h1>
        <p class="sv-subtitle">{{ t('settings-subtitle') }}</p>
      </div>
      <div class="sv-header-right">
        <div class="sv-search">
          <span class="material-symbols-outlined sv-search-icon">search</span>
          <input
            v-model="store.searchQuery"
            class="sv-search-input"
            :placeholder="t('search-settings')"
          />
          <kbd v-if="!store.searchQuery" class="sv-search-hint">/</kbd>
        </div>
        <button
          class="btn-primary"
          :disabled="!store.hasChanges || store.saving"
          @click="saveAll"
        >
          <span class="material-symbols-outlined">{{ store.saving ? 'hourglass_top' : 'save' }}</span>
          {{ store.saving ? t('saving') : t('save-all') }}
        </button>
      </div>
    </header>

    <SkeletonCard v-if="store.loading && !prefs.loaded.value" variant="form" />
    <ErrorState v-else-if="store.error" :message="store.error" @retry="store.load" />

    <!-- Layout Preferences (per-user, persisted to backend) -->
    <section v-if="prefs.loaded.value" class="pref-group">
      <div class="pref-group-header">
        <span class="material-symbols-outlined sv-group-icon">grid_view</span>
        <h2 class="sv-group-title">Layout</h2>
        <span class="sv-group-count">4</span>
      </div>
      <div class="sv-group-body pref-group-body">
        <div v-for="ctrl in layoutControls" :key="ctrl.key" class="pref-row">
          <div class="sv-info">
            <span class="sv-label">{{ ctrl.label }}</span>
            <span class="sv-key">{{ ctrl.key }}</span>
          </div>
          <div class="sv-control">
            <div class="sv-options">
              <button
                v-for="opt in ctrl.options"
                :key="opt"
                :class="['sv-opt-btn', { active: prefs.preferences[ctrl.key] === opt }]"
                @click="setLayoutPref(ctrl.key, opt)"
              >
                {{ optionLabel(opt) }}
              </button>
            </div>
          </div>
        </div>
      </div>
    </section>

    <div v-else-if="!store.filteredGroups.length" class="sv-empty">
      <span class="material-symbols-outlined sv-empty-icon">search_off</span>
      <p v-if="store.searchQuery">{{ t('settings-no-results') }} "{{ store.searchQuery }}"</p>
      <p v-else>{{ t('settings-empty') }}</p>
    </div>

    <div v-else-if="viewReady" class="sv-body">
      <nav class="sv-nav">
        <div class="sv-nav-inner">
          <a
            v-for="grp in store.filteredGroups"
            :key="grp.group"
            :class="['sv-nav-item', { active: activeGroup === grp.group }]"
            href="#"
            @click.prevent="selectGroup(grp.group)"
          >
            <span class="material-symbols-outlined sv-nav-icon">{{ groupIcon(grp.group) }}</span>
            <span class="sv-nav-label">{{ grp.group }}</span>
            <span v-if="store.groupHasChanges(grp.group)" class="sv-nav-dirty" />
          </a>
        </div>
        <div v-if="store.dirtyCount" class="sv-nav-footer">
          <span class="sv-dirty-summary">{{ store.dirtyCount }} {{ t('unsaved-changes') }}{{ store.dirtyCount !== 1 ? 's' : '' }}</span>
        </div>
      </nav>

      <div class="sv-content">
        <template v-if="activeGroupData">
          <section class="sv-group">
            <div class="sv-group-header">
              <span class="material-symbols-outlined sv-group-icon">{{ groupIcon(activeGroupData.group) }}</span>
              <h2 class="sv-group-title">{{ activeGroupData.group }}</h2>
              <span class="sv-group-count">{{ activeGroupData.settings.length }}</span>
              <span v-if="store.groupHasChanges(activeGroupData.group)" class="sv-group-dirty">
                {{ store.groupDirtyCount(activeGroupData.group) }} {{ t('unsaved') }}
              </span>
              <button
                v-if="store.groupHasChanges(activeGroupData.group)"
                class="sv-save-group-btn"
                @click="saveGroup(activeGroupData.group)"
              >
                <span class="material-symbols-outlined">save</span>
                {{ t('save-group') }}
              </button>
            </div>
            <div v-if="activeGroupData.settings.length" class="sv-group-body">
              <div
                v-for="setting in activeGroupData.settings"
                :key="setting.id"
                :class="['sv-row', { 'sv-row-dirty': store.dirtyKeys[setting.setting_key] }]"
              >
                <div class="sv-info">
                  <span class="sv-label">{{ setting.description || setting.setting_key }}</span>
                  <span class="sv-key">{{ setting.setting_key }}</span>
                </div>

                <div v-if="isToggle(setting)" class="sv-control">
                  <label class="sv-toggle">
                    <input
                      type="checkbox"
                      :checked="store.getValue(setting.setting_key) === 'true'"
                      @change="toggleSetting(setting, $event.target.checked)"
                    />
                    <span class="sv-toggle-track"><span class="sv-toggle-thumb"></span></span>
                  </label>
                </div>

                <div v-else-if="isOption(setting)" class="sv-control">
                  <div class="sv-options">
                    <button
                      v-for="opt in getOptions(setting)"
                      :key="opt"
                      :class="['sv-opt-btn', { active: store.getValue(setting.setting_key) === opt }]"
                      @click="setOption(setting, opt)"
                    >
                      {{ optionLabel(opt) }}
                    </button>
                  </div>
                </div>

                <div v-else class="sv-control">
                  <div class="sv-input-wrap">
                    <input
                      type="text"
                      class="sv-input"
                      :value="store.getValue(setting.setting_key)"
                      @input="setTextValue(setting, $event.target.value)"
                    />
                    <button
                      v-if="store.dirtyKeys[setting.setting_key]"
                      class="sv-reset-btn"
                      @click="resetSetting(setting)"
                      :aria-label="t('reset-value')"
                    >
                      <span class="material-symbols-outlined">undo</span>
                    </button>
                  </div>
                </div>

                <span v-if="store.dirtyKeys[setting.setting_key]" class="sv-dirty-dot" />
              </div>
            </div>
            <div v-else-if="store.searchQuery" class="sv-section-empty">
              <span class="material-symbols-outlined sv-empty-icon">search_off</span>
              <p>{{ t('settings-no-results') }} "{{ store.searchQuery }}"</p>
            </div>
          </section>
        </template>
        <div v-else class="sv-empty">
          <span class="material-symbols-outlined sv-empty-icon">search_off</span>
          <p>{{ t('settings-no-results') }} "{{ store.searchQuery }}"</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import { useSettingsStore } from '../../stores/settings.js'
import { useNavStore } from '../../stores/nav.js'
import { useToast } from '../../composables/useToast.js'
import { useSettingsUI } from '../../composables/useSettingsUI.js'
import { useI18n } from '../../composables/useI18n.js'
import { usePreferences } from '../../composables/usePreferences.js'
import SkeletonCard from '../../components/SkeletonCard.vue'
import ErrorState from '../../components/ErrorState.vue'

const store = useSettingsStore()
const navStore = useNavStore()
const { show: toast } = useToast()
const { t, dir } = useI18n()
const { isToggle, isOption, getOptions, groupIcon } = useSettingsUI()
const prefs = usePreferences()

const activeGroup = ref('')
const viewReady = ref(false)

const layoutControls = computed(() => [
  { key: 'THEME', label: 'Theme', options: ['light', 'dark'] },
  { key: 'ACCENT_COLOR', label: 'Accent Color', options: ['blue', 'purple', 'green', 'amber', 'red'] },
  { key: 'FONT_FAMILY', label: 'Font', options: ['inter', 'roboto', 'open-sans', 'system'] },
  { key: 'SIDEBAR_MODE', label: 'Sidebar Mode', options: ['expanded', 'overlay', 'auto-hide'] },
])

function setLayoutPref(key, value) {
  prefs.set(key, value)
  scheduleAutoSaveLayout()
}

let layoutAutoSaveTimer = null

function scheduleAutoSaveLayout() {
  if (layoutAutoSaveTimer) clearTimeout(layoutAutoSaveTimer)
  layoutAutoSaveTimer = setTimeout(() => {
    layoutAutoSaveTimer = null
    prefs.save()
    toast(t('settings-saved'), 'success')
  }, 1500)
}

const activeGroupData = computed(() => {
  return store.filteredGroups.find(g => g.group === activeGroup.value) || null
})

watch(() => store.searchQuery, () => {
  if (activeGroup.value && !store.filteredGroups.find(g => g.group === activeGroup.value)) {
    if (store.filteredGroups.length) {
      activeGroup.value = store.filteredGroups[0].group
    }
  }
})

function optionLabel(opt) {
  const key = `settings.option.${opt}`
  const label = t(key)
  if (label !== key) return label
  return opt
}

function selectGroup(groupName) {
  activeGroup.value = groupName
}

function toggleSetting(setting, checked) {
  store.updateValue(setting.setting_key, checked ? 'true' : 'false')
  scheduleAutoSave()
}

function setOption(setting, value) {
  store.updateValue(setting.setting_key, value)
  scheduleAutoSave()
}

function setTextValue(setting, value) {
  store.updateValue(setting.setting_key, value)
  scheduleAutoSave()
}

function resetSetting(setting) {
  store.resetValue(setting.setting_key)
}

let autoSaveTimer = null

function scheduleAutoSave() {
  if (autoSaveTimer) clearTimeout(autoSaveTimer)
  autoSaveTimer = setTimeout(() => {
    autoSaveTimer = null
    saveAll()
  }, 3000)
}

function syncNavStyle() {
  const v = store.getValue('NAV_STYLE')
  if (v && navStore.navStyle !== v) navStore.setNavStyle(v)
}

function syncLanguage() {
  useI18n().apply()
}

async function saveAll() {
  if (!store.hasChanges) return
  const ok = await store.saveAll()
  toast(ok ? t('settings-saved') : t('settings-save-failed'), ok ? 'success' : 'error')
  if (ok) { syncNavStyle(); syncLanguage() }
}

async function saveGroup(groupName) {
  const ok = await store.saveGroup(groupName)
  toast(ok ? `${groupName} ${t('saved-ok')}` : `${t('failed-save')} ${groupName}`, ok ? 'success' : 'error')
  if (ok && groupName === 'App Preferences') { syncNavStyle(); syncLanguage() }
}

function onKeydown(e) {
  if (e.key === '/' && document.activeElement?.tagName !== 'INPUT') {
    e.preventDefault()
    const input = document.querySelector('.sv-search-input')
    input?.focus()
  }
}

onMounted(async () => {
  document.addEventListener('keydown', onKeydown)
  await store.load()
  if (store.groups.length) activeGroup.value = store.groups[0].group
  viewReady.value = true
})

onUnmounted(() => {
  document.removeEventListener('keydown', onKeydown)
  if (autoSaveTimer) clearTimeout(autoSaveTimer)
  if (layoutAutoSaveTimer) clearTimeout(layoutAutoSaveTimer)
})
</script>

<style scoped>
.sv-page {
  max-width: 1200px;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  height: 100%;
}

/* ── Header ── */
.sv-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 24px;
  flex-shrink: 0;
}
.sv-header-left {
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.sv-title {
  font-size: 22px;
  font-weight: 700;
  color: var(--text-primary);
  margin: 0;
}
.sv-subtitle {
  font-size: 13px;
  color: var(--text-muted);
}
.sv-header-right {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-shrink: 0;
}
.sv-search {
  display: flex;
  align-items: center;
  gap: 8px;
  background: var(--bg-surface);
  border: 1px solid var(--border-input);
  border-radius: 8px;
  padding: 0 12px;
  transition: border-color 0.2s, box-shadow 0.2s;
}
.sv-search:focus-within {
  border-color: var(--color-primary);
  box-shadow: 0 0 0 3px var(--bg-primary-faded);
}
.sv-search-icon {
  font-size: 18px;
  color: var(--text-faint);
  flex-shrink: 0;
}
.sv-search-input {
  height: 40px;
  border: none;
  background: none;
  font-size: 13px;
  color: var(--text-primary);
  outline: none;
  font-family: inherit;
  width: 200px;
}
.sv-search-input::placeholder { color: var(--text-faint); }
.sv-search-hint {
  font-size: 11px;
  color: var(--text-faint);
  background: var(--bg-body);
  border: 1px solid var(--border-light);
  border-radius: 4px;
  padding: 1px 6px;
  font-family: 'JetBrains Mono', monospace;
  flex-shrink: 0;
}

/* ── Body ── */
.sv-body {
  display: flex;
  gap: 24px;
  flex: 1;
  min-height: 0;
  overflow: hidden;
}

/* ── Nav ── */
.sv-nav {
  width: 180px;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  gap: 4px;
  overflow: hidden;
}
.sv-nav-inner {
  flex: 1;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.sv-nav-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 9px 12px;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 500;
  color: var(--text-muted);
  text-decoration: none;
  cursor: pointer;
  transition: all 0.12s;
  position: relative;
}
.sv-nav-item:hover {
  background: var(--bg-surface-hover);
  color: var(--text-primary);
}
.sv-nav-item.active {
  background: var(--bg-primary-faded);
  color: var(--color-primary);
  font-weight: 600;
}
.sv-nav-icon { font-size: 18px; }
.sv-nav-label { flex: 1; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.sv-nav-dirty {
  width: 6px; height: 6px;
  border-radius: 50%;
  background: #F59E0B;
  flex-shrink: 0;
}
.sv-nav-footer {
  padding: 6px 0 0;
  border-top: 1px solid var(--border-light);
}
.sv-dirty-summary {
  font-size: 11px;
  color: #F59E0B;
  font-weight: 600;
  text-align: center;
  display: block;
}

/* ── Content ── */
.sv-content {
  flex: 1;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding-inline-end: 4px;
}

/* ── Group Card ── */
.sv-group {
  background: var(--bg-surface);
  border: 1px solid var(--border-default);
  border-radius: 10px;
  overflow: hidden;
  transition: border-color 0.2s;
}
.sv-group:has(.sv-row-dirty) {
  border-color: #F59E0B;
}
.sv-group-header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 14px 18px;
  background: var(--bg-surface-low);
  border-bottom: 1px solid var(--border-light);
}
.sv-group-icon {
  font-size: 18px;
  color: var(--color-primary);
  flex-shrink: 0;
}
.sv-group-title {
  font-size: 14px;
  font-weight: 700;
  color: var(--text-primary);
  margin: 0;
  flex: 1;
}
.sv-group-count {
  font-size: 11px;
  color: var(--text-faint);
  background: var(--bg-body);
  padding: 2px 8px;
  border-radius: 10px;
  font-weight: 600;
}
.sv-group-dirty {
  font-size: 11px;
  color: #B45309;
  background: #FEF3C7;
  padding: 2px 8px;
  border-radius: 10px;
  font-weight: 600;
}
.sv-save-group-btn {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 5px 10px;
  border: none;
  border-radius: 6px;
  font-size: 11px;
  font-weight: 600;
  cursor: pointer;
  background: var(--color-primary);
  color: #fff;
  transition: background 0.15s;
  font-family: inherit;
}
.sv-save-group-btn:hover { background: var(--color-primary-hover); }
.sv-save-group-btn .material-symbols-outlined { font-size: 14px; }

/* ── Setting Row ── */
.sv-group-body {
  padding: 2px 0;
}
.sv-row {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 18px;
  border-bottom: 1px solid var(--border-light);
  transition: background 0.15s;
  position: relative;
}
.sv-row:last-child { border-bottom: none; }
.sv-row-dirty { background: rgba(245, 158, 11, 0.05); }
.sv-info {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.sv-label {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
}
.sv-key {
  font-size: 11px;
  color: var(--text-faint);
  font-family: 'JetBrains Mono', monospace;
}
.sv-control { flex-shrink: 0; }
.sv-dirty-dot {
  width: 6px; height: 6px;
  border-radius: 50%;
  background: #F59E0B;
  flex-shrink: 0;
  position: absolute;
  inset-inline-end: 10px;
  top: 50%;
  transform: translateY(-50%);
}
.sv-row-dirty .sv-dirty-dot { display: none; }

/* ── Toggle ── */
.sv-toggle {
  position: relative;
  display: inline-block;
  width: 40px;
  height: 22px;
  flex-shrink: 0;
  cursor: pointer;
}
.sv-toggle input {
  opacity: 0;
  width: 0;
  height: 0;
  position: absolute;
}
.sv-toggle-track {
  position: absolute;
  inset: 0;
  background: var(--border-input);
  border-radius: 11px;
  transition: background 0.2s;
}
.sv-toggle-thumb {
  position: absolute;
  width: 18px;
  height: 18px;
  left: 2px;
  top: 2px;
  background: #fff;
  border-radius: 50%;
  transition: transform 0.2s;
  box-shadow: 0 1px 2px rgba(0,0,0,0.15);
}
.sv-toggle input:checked + .sv-toggle-track {
  background: var(--color-primary);
}
.sv-toggle input:checked + .sv-toggle-track .sv-toggle-thumb {
  transform: translateX(18px);
}
.sv-toggle input:focus-visible + .sv-toggle-track {
  outline: 2px solid var(--color-primary);
  outline-offset: 2px;
}

/* ── Options ── */
.sv-options {
  display: flex;
  gap: 3px;
  background: var(--bg-body);
  padding: 3px;
  border-radius: 8px;
}
.sv-opt-btn {
  padding: 5px 12px;
  border: none;
  border-radius: 5px;
  font-size: 12px;
  font-weight: 600;
  color: var(--text-muted);
  background: transparent;
  cursor: pointer;
  transition: all 0.15s;
  font-family: inherit;
}
.sv-opt-btn:hover { color: var(--text-primary); }
.sv-opt-btn.active {
  background: var(--bg-surface);
  color: var(--color-primary);
  box-shadow: 0 1px 3px rgba(0,0,0,0.08);
}

/* ── Input ── */
.sv-input-wrap {
  display: flex;
  align-items: center;
  gap: 4px;
}
.sv-input {
  width: 240px;
  padding: 7px 10px;
  border: 1px solid var(--border-input);
  border-radius: 6px;
  font-size: 13px;
  color: var(--text-primary);
  background: var(--bg-surface);
  outline: none;
  font-family: inherit;
  transition: border-color 0.15s;
}
.sv-input:focus {
  border-color: var(--color-primary);
}
.sv-reset-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 30px;
  height: 30px;
  border: 1px solid var(--border-input);
  border-radius: 6px;
  background: var(--bg-surface);
  cursor: pointer;
  color: var(--text-faint);
  transition: all 0.15s;
}
.sv-reset-btn:hover {
  border-color: #F59E0B;
  color: #F59E0B;
  background: #FEF3C7;
}
.sv-reset-btn .material-symbols-outlined { font-size: 15px; }

/* ── Section Empty ── */
.sv-section-empty {
  text-align: center;
  padding: 32px 18px;
  color: var(--text-faint);
  font-size: 13px;
}
.sv-section-empty .sv-empty-icon {
  font-size: 32px;
  margin-bottom: 8px;
  display: block;
}

/* ── Empty ── */
.sv-empty {
  text-align: center;
  padding: 60px 24px;
  color: var(--text-faint);
}
.sv-empty-icon {
  font-size: 48px;
  color: var(--border-default);
  margin-bottom: 12px;
  display: block;
}
.sv-empty p { font-size: 14px; }

/* ── Layout Preferences ── */
.pref-group {
  background: var(--bg-surface);
  border: 1px solid var(--color-primary);
  border-radius: 10px;
  overflow: hidden;
  margin-bottom: 16px;
}
.pref-group-header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 14px 18px;
  background: var(--bg-primary-faded);
  border-bottom: 1px solid var(--border-light);
}
.pref-group-body {
  padding: 2px 0;
}
.pref-row {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 18px;
  border-bottom: 1px solid var(--border-light);
}
.pref-row:last-child { border-bottom: none; }

/* ── RTL ── */
[dir="rtl"] .sv-nav { order: 1; }
[dir="rtl"] .sv-content { order: 0; }
[dir="rtl"] .sv-group-header { flex-direction: row-reverse; }
[dir="rtl"] .sv-row { flex-direction: row-reverse; }
[dir="rtl"] .sv-options { flex-direction: row-reverse; }
[dir="rtl"] .sv-header { flex-direction: row-reverse; }
[dir="rtl"] .sv-search-hint { font-family: 'JetBrains Mono', monospace; }

/* ── Responsive ── */
@media (max-width: 1023px) {
  .sv-title { font-size: 18px; }
  .sv-subtitle { font-size: 12px; }
}

@media (max-width: 767px) {
  .sv-page { height: auto; min-height: 100%; }
  .sv-header { flex-direction: column; gap: 12px; }
  .sv-header-left { width: 100%; }
  .sv-header-right { width: 100%; flex-wrap: wrap; }
  .sv-search { flex: 1; min-width: 0; }
  .sv-search-input { width: 100%; }
  .sv-body { flex-direction: column; overflow: visible; }
  .sv-nav {
    width: 100%;
    flex-direction: row;
    overflow-x: auto;
    padding-bottom: 4px;
    gap: 0;
    scrollbar-width: none;
  }
  .sv-nav::-webkit-scrollbar { display: none; }
  .sv-nav-inner {
    flex-direction: row;
    gap: 4px;
    overflow-y: visible;
    flex: none;
    width: auto;
  }
  .sv-nav-item {
    white-space: nowrap;
    flex-shrink: 0;
    padding: 7px 10px;
    font-size: 12px;
  }
  .sv-nav-footer { display: none; }
  .sv-content {
    overflow: visible;
    padding: 0;
    gap: 0;
  }
  .sv-group { border-radius: 8px; }
  .sv-group-header { padding: 12px 14px; flex-wrap: wrap; }
  .sv-group-title { font-size: 13px; }
  .sv-input { width: 100%; min-width: 0; }
  .sv-row { flex-wrap: wrap; gap: 8px; padding: 10px 14px; }
  .sv-info { flex-basis: 100%; }
  .sv-control { width: 100%; }
  .sv-options { flex-wrap: wrap; }
  .btn-primary { width: 100%; justify-content: center; }
}
</style>
