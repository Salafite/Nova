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
    },

    clearDirty(key) {
      delete this.dirtyKeys[key]
    },

    async saveAll() {
      if (!this.hasChanges) return
      this.saving = true
      const bulk = []
      for (const grp of this.groups) {
        for (const s of grp.settings) {
          if (this.dirtyKeys[s.setting_key]) {
            bulk.push({ id: s.id, setting_value: this.values[s.setting_key] })
          }
        }
      }
      try {
        await api.put('/T0025I/bulk', { settings: bulk })
        this.dirtyKeys = {}
        return true
      } catch {
        return false
      } finally {
        this.saving = false
      }
    },

    async saveGroup(groupName) {
      const grp = this.groups.find(g => g.group === groupName)
      if (!grp) return false
      const bulk = []
      for (const s of grp.settings) {
        if (this.dirtyKeys[s.setting_key]) {
          bulk.push({ id: s.id, setting_value: this.values[s.setting_key] })
        }
      }
      if (bulk.length === 0) return true
      try {
        await api.put('/T0025I/bulk', { settings: bulk })
        for (const s of grp.settings) {
          delete this.dirtyKeys[s.setting_key]
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
            this.values[key] = s.setting_value ?? ''
            delete this.dirtyKeys[key]
            return
          }
        }
      }
    },
  },
})
