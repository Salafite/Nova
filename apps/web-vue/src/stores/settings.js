import { defineStore } from 'pinia'
import { api } from '../api/client.js'

export const useSettingsStore = defineStore('settings', {
  state: () => ({
    groups: [],
    values: {},
    dirtyKeys: {},
    loading: false,
    error: '',
    searchQuery: '',
    saving: false,
    localDefaults: {
      THEME: 'light',
      ACCENT_COLOR: 'blue',
      FONT_FAMILY: 'inter',
      SIDEBAR_MODE: 'expanded',
    },
  }),

  getters: {
    hasChanges: state => Object.keys(state.dirtyKeys).length > 0,
    dirtyCount: state => Object.keys(state.dirtyKeys).length,
    filteredGroups(state) {
      if (!state.searchQuery) return state.groups
      const q = state.searchQuery.toLowerCase()
      return state.groups
        .map(grp => {
          const filtered = grp.settings.filter(s =>
            s.setting_key.toLowerCase().includes(q) ||
            (s.description || '').toLowerCase().includes(q)
          )
          return { ...grp, settings: filtered }
        })
        .filter(grp => grp.settings.length > 0)
    },
    groupDirtyCount: state => (groupName) => {
      const grp = state.groups.find(g => g.group === groupName)
      if (!grp) return 0
      return grp.settings.filter(s => state.dirtyKeys[s.setting_key]).length
    },
    groupHasChanges: state => (groupName) => {
      const grp = state.groups.find(g => g.group === groupName)
      if (!grp) return false
      return grp.settings.some(s => state.dirtyKeys[s.setting_key])
    },
  },

  actions: {
    async load() {
      this.loading = true
      this.error = ''
      try {
        const res = await api.get('/T0025I/by-group/summary')
        this.groups = res.data || []
        for (const grp of this.groups) {
          for (const s of grp.settings) {
            this.values[s.setting_key] = s.setting_value ?? ''
          }
        }
      } catch {
        this.error = 'Failed to load settings.'
      } finally {
        this.loading = false
      }
      this.injectLocalGroups()
    },

    injectLocalGroups() {
      const layoutSettings = [
        { setting_key: 'THEME', description: 'Theme', default: this.localDefaults.THEME, setting_value: localStorage.getItem('THEME') || this.localDefaults.THEME, is_local: true },
        { setting_key: 'ACCENT_COLOR', description: 'Accent Color', default: this.localDefaults.ACCENT_COLOR, setting_value: localStorage.getItem('ACCENT_COLOR') || this.localDefaults.ACCENT_COLOR, is_local: true },
        { setting_key: 'FONT_FAMILY', description: 'Font', default: this.localDefaults.FONT_FAMILY, setting_value: localStorage.getItem('FONT_FAMILY') || this.localDefaults.FONT_FAMILY, is_local: true },
        { setting_key: 'SIDEBAR_MODE', description: 'Sidebar Mode', default: this.localDefaults.SIDEBAR_MODE, setting_value: localStorage.getItem('SIDEBAR_MODE') || this.localDefaults.SIDEBAR_MODE, is_local: true },
      ]

      this.groups.push({ group: 'Layout', settings: layoutSettings })

      for (const s of layoutSettings) {
        if (!(s.setting_key in this.values)) {
          this.values[s.setting_key] = s.setting_value
        }
      }
    },

    getValue(key) {
      if (key in this.values) return this.values[key]
      for (const grp of this.groups) {
        for (const s of grp.settings) {
          if (s.setting_key === key) return s.setting_value ?? ''
        }
      }
      return ''
    },

    updateValue(key, value) {
      this.values[key] = value
      this.dirtyKeys[key] = true
      for (const grp of this.groups) {
        for (const s of grp.settings) {
          if (s.setting_key === key && s.is_local) {
            localStorage.setItem(key, value)
            return
          }
        }
      }
    },

    clearDirty(key) {
      delete this.dirtyKeys[key]
    },

    async saveAll() {
      if (!this.hasChanges) return
      this.saving = true
      const bulk = []
      const localKeys = []
      for (const grp of this.groups) {
        for (const s of grp.settings) {
          if (this.dirtyKeys[s.setting_key]) {
            if (s.is_local) {
              localKeys.push(s.setting_key)
            } else {
              bulk.push({ id: s.id, setting_value: this.values[s.setting_key] })
            }
          }
        }
      }
      try {
        if (bulk.length) await api.put('/T0025I/bulk', { settings: bulk })
        this.dirtyKeys = {}
        return true
      } catch {
        for (const key of localKeys) delete this.dirtyKeys[key]
        if (!this.hasChanges) return true
        return false
      } finally {
        this.saving = false
      }
    },

    async saveGroup(groupName) {
      const grp = this.groups.find(g => g.group === groupName)
      if (!grp) return false
      const bulk = []
      let hasLocal = false
      for (const s of grp.settings) {
        if (this.dirtyKeys[s.setting_key]) {
          if (s.is_local) {
            hasLocal = true
          } else {
            bulk.push({ id: s.id, setting_value: this.values[s.setting_key] })
          }
        }
      }
      if (!bulk.length && !hasLocal) return true
      try {
        if (bulk.length) await api.put('/T0025I/bulk', { settings: bulk })
        for (const s of grp.settings) {
          if (this.dirtyKeys[s.setting_key]) {
            delete this.dirtyKeys[s.setting_key]
          }
        }
        return true
      } catch {
        return false
      }
    },

    resetValue(key) {
      for (const grp of this.groups) {
        for (const s of grp.settings) {
          if (s.setting_key === key) {
            if (s.is_local) {
              const def = s.default ?? this.localDefaults[key] ?? ''
              this.values[key] = def
              localStorage.setItem(key, def)
            } else {
              this.values[key] = s.setting_value ?? ''
            }
            delete this.dirtyKeys[key]
            return
          }
        }
      }
    },
  },
})
