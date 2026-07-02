<template>
  <div class="settings-layout" :dir="dir">
    <div class="settings-sidebar">
      <h3 class="sidebar-title">{{ t('settings', 'Settings') }}</h3>
      <div class="search-box">
        <span class="material-symbols-outlined search-icon">search</span>
        <input type="text" v-model="store.searchQuery" :placeholder="t('search-settings', 'Search settings...')" class="search-input" />
      </div>
      <nav class="settings-nav">
        <a v-for="grp in store.filteredGroups" :key="grp.group"
           :class="['nav-link', { active: activeGroup === grp.group }]"
           href="#"
           @click.prevent="scrollToGroup(grp.group)">
          <span class="nav-icon">
            <span class="material-symbols-outlined">{{ groupIcon(grp.group) }}</span>
          </span>
          <span class="nav-label">{{ grp.group }}</span>
          <span v-if="store.groupHasChanges(grp.group)" class="nav-dirty" title="Unsaved changes">*</span>
        </a>
      </nav>
      <div class="sidebar-footer">
        <div v-if="store.dirtyCount" class="dirty-summary">
          {{ store.dirtyCount }} {{ t('unsaved-changes', 'unsaved change') }}{{ store.dirtyCount !== 1 ? 's' : '' }}
        </div>
      </div>
    </div>

    <div class="settings-content" ref="contentRef" @scroll="onScroll">
      <div class="page-header">
        <div>
          <h2 class="page-title">System Settings</h2>
          <p class="page-subtitle">Manage global system preferences and configurations</p>
        </div>
        <button class="btn-primary" :disabled="!store.hasChanges || store.saving" @click="saveAll">
          <span class="material-symbols-outlined">{{ store.saving ? 'hourglass_top' : 'save' }}</span>
          {{ store.saving ? t('saving') : t('save-all', 'Save All Changes') }}
        </button>
      </div>

      <SkeletonCard v-if="store.loading" variant="form" />
      <ErrorState v-else-if="store.error" :message="store.error" @retry="store.load" />
      <div v-else-if="store.filteredGroups.length === 0" class="empty-state">
        <span class="material-symbols-outlined empty-icon">search_off</span>
        <p>No settings match "{{ store.searchQuery }}"</p>
      </div>

      <div v-else class="groups-container">
        <section v-for="grp in store.filteredGroups" :key="grp.group"
                 :ref="el => setSectionRef(grp.group, el)"
                 class="settings-section"
                 :class="{ 'section-dirty': store.groupHasChanges(grp.group) }">
          <div class="section-header">
            <span class="section-icon">
              <span class="material-symbols-outlined">{{ groupIcon(grp.group) }}</span>
            </span>
            <h3 class="section-title">{{ grp.group }}</h3>
            <span v-if="store.groupHasChanges(grp.group)" class="section-dirty-badge">{{ store.groupDirtyCount(grp.group) }} unsaved</span>
            <span class="section-count">{{ grp.settings.length }}</span>
            <button v-if="store.groupHasChanges(grp.group)" class="btn-sm btn-save-group" @click="saveGroup(grp.group)">
              <span class="material-symbols-outlined">save</span> {{ t('save-group', 'Save Group') }}
            </button>
          </div>

          <div class="section-body">
            <div v-for="setting in grp.settings" :key="setting.id"
                 class="setting-row"
                 :class="{ 'row-dirty': store.dirtyKeys[setting.setting_key] }">
              <div v-if="isToggle(setting)" class="setting-toggle">
                <div class="setting-info">
                  <div class="setting-label">{{ setting.description || setting.setting_key }}</div>
                  <div class="setting-key-wrapper">
                    <span class="setting-key">{{ setting.setting_key }}</span>
                    <span v-if="store.dirtyKeys[setting.setting_key]" class="dirty-dot" :title="t('unsaved', 'Unsaved')"></span>
                  </div>
                </div>
                <label class="toggle-switch">
                  <input type="checkbox"
                         :checked="store.getValue(setting.setting_key) === 'true'"
                         @change="toggleSetting(setting, $event.target.checked)" />
                  <span class="toggle-slider"></span>
                </label>
              </div>

              <div v-else-if="isOption(setting)" class="setting-option">
                <div class="setting-info">
                  <div class="setting-label">{{ setting.description || setting.setting_key }}</div>
                  <div class="setting-key-wrapper">
                    <span class="setting-key">{{ setting.setting_key }}</span>
                    <span v-if="store.dirtyKeys[setting.setting_key]" class="dirty-dot" :title="t('unsaved', 'Unsaved')"></span>
                  </div>
                </div>
                <div class="option-group">
                  <button v-for="opt in getOptions(setting)" :key="opt"
                          :class="['option-btn', { active: store.getValue(setting.setting_key) === opt }]"
                          @click="setOption(setting, opt)">
                    {{ opt === 'en-US' ? 'English' : opt === 'ar-EG' ? 'العربية' : opt }}
                  </button>
                </div>
              </div>

              <div v-else class="setting-input-row">
                <div class="setting-info">
                  <div class="setting-label">{{ setting.description || setting.setting_key }}</div>
                  <div class="setting-key-wrapper">
                    <span class="setting-key">{{ setting.setting_key }}</span>
                    <span v-if="store.dirtyKeys[setting.setting_key]" class="dirty-dot" :title="t('unsaved', 'Unsaved')"></span>
                  </div>
                </div>
                <div class="input-with-reset">
                  <input type="text" class="setting-input"
                         :value="store.getValue(setting.setting_key)"
                         @input="setTextValue(setting, $event.target.value)" />
                  <button v-if="store.dirtyKeys[setting.setting_key]"
                          class="btn-reset"
                          @click="resetSetting(setting)"
                          :title="t('reset-value', 'Reset to saved value')">
                    <span class="material-symbols-outlined">undo</span>
                  </button>
                </div>
              </div>
            </div>
          </div>
        </section>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { useSettingsStore } from '../../stores/settings.js'
import { useNavStore } from '../../stores/nav.js'
import { useToast } from '../../composables/useToast.js'
import { useSettingsUI } from '../../composables/useSettingsUI.js'
import { useI18n } from '../../composables/useI18n.js'
import SkeletonCard from '../../components/SkeletonCard.vue'
import ErrorState from '../../components/ErrorState.vue'

const store = useSettingsStore()
const navStore = useNavStore()
const { show: toast } = useToast()
const { t, dir } = useI18n()
const { isToggle, isOption, getOptions, groupIcon } = useSettingsUI()

const contentRef = ref(null)
const activeGroup = ref('')
const sectionRefs = {}

function setSectionRef(groupName, el) {
  if (el) sectionRefs[groupName] = el
}

function scrollToGroup(groupName) {
  activeGroup.value = groupName
  const el = sectionRefs[groupName]
  if (el && contentRef.value) {
    el.scrollIntoView({ behavior: 'smooth', block: 'start' })
    contentRef.value.scrollTop -= 24
  }
}

let scrollRaf = null

function onScroll() {
  if (scrollRaf) return
  scrollRaf = requestAnimationFrame(() => {
    scrollRaf = null
    if (!contentRef.value) return
    const container = contentRef.value
    let current = ''
    for (const grp of store.filteredGroups) {
      const el = sectionRefs[grp.group]
      if (el && el.offsetTop - container.offsetTop - 120 <= container.scrollTop) {
        current = grp.group
      }
    }
    if (current) activeGroup.value = current
  })
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
  toast(ok ? 'Settings saved' : 'Failed to save settings', ok ? 'success' : 'error')
  if (ok) { syncNavStyle(); syncLanguage() }
}

async function saveGroup(groupName) {
  const ok = await store.saveGroup(groupName)
  toast(ok ? `${groupName} settings saved` : `Failed to save ${groupName} settings`, ok ? 'success' : 'error')
  if (ok && groupName === 'App Preferences') { syncNavStyle(); syncLanguage() }
}

onMounted(async () => {
  await store.load()
  if (store.groups.length) activeGroup.value = store.groups[0].group
})

onUnmounted(() => {
  if (autoSaveTimer) clearTimeout(autoSaveTimer)
  if (scrollRaf) cancelAnimationFrame(scrollRaf)
})
</script>

<style scoped>
.settings-layout {
  display: flex;
  gap: 24px;
  height: 100%;
  max-width: 1200px;
  margin: 0 auto;
}

.settings-sidebar {
  width: 220px;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.sidebar-title {
  font-size: 14px;
  font-weight: 700;
  color: #1a1a2e;
  padding: 0 12px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.search-box {
  position: relative;
  margin: 0 12px;
}

.search-icon {
  position: absolute;
  left: 10px;
  top: 50%;
  transform: translateY(-50%);
  font-size: 16px;
  color: #999;
  pointer-events: none;
}

.search-input {
  width: 100%;
  padding: 8px 8px 8px 32px;
  border: 1px solid #ddd;
  border-radius: 8px;
  font-size: 12px;
  outline: none;
  box-sizing: border-box;
  transition: border-color 0.15s;
}

.search-input:focus {
  border-color: #5d3fd3;
}

.settings-nav {
  display: flex;
  flex-direction: column;
  gap: 2px;
  flex: 1;
  overflow-y: auto;
}

.nav-link {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 500;
  color: #555;
  text-decoration: none;
  transition: all 0.15s;
  cursor: pointer;
}

.nav-link:hover {
  background: #f0f0f4;
  color: #1a1a2e;
}

.nav-link.active {
  background: #e6deff;
  color: #5d3fd3;
  font-weight: 600;
}

.nav-label {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.nav-dirty {
  color: #e65100;
  font-weight: 700;
  font-size: 14px;
}

.nav-icon .material-symbols-outlined {
  font-size: 18px;
}

.sidebar-footer {
  padding: 8px 12px;
  border-top: 1px solid #eee;
}

.dirty-summary {
  font-size: 11px;
  color: #e65100;
  font-weight: 600;
  text-align: center;
}

.settings-content {
  flex: 1;
  overflow-y: auto;
  padding-right: 8px;
}

.page-header {
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

.btn-primary {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 10px 20px;
  background: #5d3fd3;
  color: #fff;
  border: none;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.15s;
}

.btn-primary:hover:not(:disabled) {
  background: #4a32b0;
}

.btn-primary:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-primary .material-symbols-outlined {
  font-size: 18px;
}

.loading-state,
.error-state,
.empty-state {
  text-align: center;
  padding: 48px;
  color: #999;
  font-size: 14px;
}

.error-state {
  color: #ba1a1a;
}

.empty-icon {
  font-size: 48px;
  color: #ccc;
  margin-bottom: 16px;
}

.groups-container {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.settings-section {
  background: #fff;
  border: 1px solid #e0e0e0;
  border-radius: 12px;
  overflow: hidden;
  transition: border-color 0.2s;
}

.settings-section.section-dirty {
  border-color: #ff9800;
}

.section-header {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 16px 20px;
  background: #fafafe;
  border-bottom: 1px solid #eee;
  flex-wrap: wrap;
}

.section-icon .material-symbols-outlined {
  font-size: 20px;
  color: #5d3fd3;
}

.section-title {
  font-size: 15px;
  font-weight: 700;
  color: #1a1a2e;
  flex: 1;
  margin: 0;
}

.section-dirty-badge {
  font-size: 11px;
  color: #e65100;
  background: #fff3e0;
  padding: 2px 8px;
  border-radius: 10px;
  font-weight: 600;
}

.section-count {
  font-size: 11px;
  color: #999;
  background: #f0f0f4;
  padding: 2px 8px;
  border-radius: 10px;
  font-weight: 600;
}

.btn-sm {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 6px 12px;
  border: none;
  border-radius: 6px;
  font-size: 11px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.15s;
}

.btn-save-group {
  background: #5d3fd3;
  color: #fff;
}

.btn-save-group:hover {
  background: #4a32b0;
}

.btn-save-group .material-symbols-outlined {
  font-size: 14px;
}

.section-body {
  padding: 4px 0;
}

.setting-row {
  padding: 12px 20px;
  border-bottom: 1px solid #f5f5f5;
  transition: background 0.15s;
}

.setting-row:last-child {
  border-bottom: none;
}

.setting-row.row-dirty {
  background: #fffde7;
}

.setting-info {
  flex: 1;
  min-width: 0;
}

.setting-label {
  font-size: 14px;
  font-weight: 600;
  color: #1a1a2e;
}

.setting-key-wrapper {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-top: 2px;
}

.setting-key {
  font-size: 11px;
  color: #999;
  font-family: 'JetBrains Mono', monospace;
}

.dirty-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #e65100;
  flex-shrink: 0;
}

.setting-toggle {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

.toggle-switch {
  position: relative;
  width: 44px;
  height: 24px;
  flex-shrink: 0;
}

.toggle-switch input {
  opacity: 0;
  width: 0;
  height: 0;
}

.toggle-slider {
  position: absolute;
  inset: 0;
  background: #ccc;
  border-radius: 12px;
  cursor: pointer;
  transition: background 0.2s;
}

.toggle-slider::before {
  content: '';
  position: absolute;
  width: 20px;
  height: 20px;
  left: 2px;
  top: 2px;
  background: #fff;
  border-radius: 50%;
  transition: transform 0.2s;
}

.toggle-switch input:checked + .toggle-slider {
  background: #5d3fd3;
}

.toggle-switch input:checked + .toggle-slider::before {
  transform: translateX(20px);
}

.setting-option {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

.option-group {
  display: flex;
  gap: 4px;
  background: #f5f5f9;
  padding: 3px;
  border-radius: 8px;
  flex-shrink: 0;
}

.option-btn {
  padding: 6px 14px;
  border: none;
  border-radius: 6px;
  font-size: 12px;
  font-weight: 600;
  color: #666;
  background: transparent;
  cursor: pointer;
  transition: all 0.15s;
  text-transform: capitalize;
}

.option-btn:hover {
  color: #333;
}

.option-btn.active {
  background: #fff;
  color: #5d3fd3;
  box-shadow: 0 1px 4px rgba(0,0,0,0.1);
}

.setting-input-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

.input-with-reset {
  display: flex;
  align-items: center;
  gap: 4px;
  flex-shrink: 0;
}

.setting-input {
  width: 260px;
  padding: 8px 12px;
  border: 1px solid #ddd;
  border-radius: 6px;
  font-size: 13px;
  color: #333;
  outline: none;
  transition: border-color 0.15s;
}

.setting-input:focus {
  border-color: #5d3fd3;
}

.btn-reset {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border: 1px solid #ddd;
  border-radius: 6px;
  background: #fff;
  cursor: pointer;
  color: #999;
  transition: all 0.15s;
}

.btn-reset:hover {
  border-color: #e65100;
  color: #e65100;
  background: #fff3e0;
}

.btn-reset .material-symbols-outlined {
  font-size: 16px;
}
</style>
