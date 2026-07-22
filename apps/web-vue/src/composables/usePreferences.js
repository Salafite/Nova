import { reactive, shallowRef } from 'vue'
import { api } from '../api/client.js'
import { useTheme } from './useTheme.js'

const STORAGE_PREFIX = 'nova_pref_'
const PREFS_KEYS = ['THEME', 'ACCENT_COLOR', 'FONT_FAMILY', 'SIDEBAR_MODE']

const ACCENT_PALETTES = {
  purple: { light: '#5d3fd3', dark: '#cabeff', hover: '#4a32b0' },
  blue: { light: '#2563EB', dark: '#93C5FD', hover: '#1D4ED8' },
  green: { light: '#059669', dark: '#6EE7B7', hover: '#047857' },
  amber: { light: '#D97706', dark: '#FCD34D', hover: '#B45309' },
  red: { light: '#DC2626', dark: '#FCA5A5', hover: '#B91C1C' },
}

const FONTS = {
  inter: "'Inter', -apple-system, sans-serif",
  roboto: "'Roboto', sans-serif",
  'open-sans': "'Open Sans', sans-serif",
  system: "-apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
}

const defaults = { THEME: 'light', ACCENT_COLOR: 'purple', FONT_FAMILY: 'inter', SIDEBAR_MODE: 'expanded' }

const preferences = reactive({ ...defaults })
const loaded = shallowRef(false)

const LEGACY_KEYS = { THEME: ['nova_theme', 'THEME'], ACCENT_COLOR: ['ACCENT_COLOR'], FONT_FAMILY: ['FONT_FAMILY'], SIDEBAR_MODE: ['SIDEBAR_MODE'] }

function loadFromStorage() {
  for (const key of PREFS_KEYS) {
    let stored = localStorage.getItem(STORAGE_PREFIX + key)
    if (!stored) {
      const legacy = LEGACY_KEYS[key] || []
      for (const lk of legacy) {
        stored = localStorage.getItem(lk)
        if (stored) break
      }
    }
    if (stored) preferences[key] = stored
  }
}

function saveToStorage() {
  for (const key of PREFS_KEYS) {
    localStorage.setItem(STORAGE_PREFIX + key, preferences[key])
  }
  const legacyToRemove = ['nova_theme', 'THEME', 'ACCENT_COLOR', 'FONT_FAMILY', 'SIDEBAR_MODE']
  for (const lk of legacyToRemove) localStorage.removeItem(lk)
}

function applyTheme() {
  const { setTheme } = useTheme()
  setTheme(preferences.THEME)
}

function applyAccent() {
  const palette = ACCENT_PALETTES[preferences.ACCENT_COLOR] || ACCENT_PALETTES.purple
  const isDark = document.documentElement.classList.contains('dark')
  const root = document.documentElement
  root.style.setProperty('--color-primary', isDark ? palette.dark : palette.light)
  root.style.setProperty('--color-primary-hover', palette.hover)
}

function applyFont() {
  const font = FONTS[preferences.FONT_FAMILY] || FONTS.inter
  document.body.style.fontFamily = font
}

function applyAll() {
  applyTheme()
  applyAccent()
  applyFont()
}

export function usePreferences() {
  async function initialize() {
    if (loaded.value) return
    loadFromStorage()
    try {
      const res = await api.get('/user/preferences/')
      const serverPrefs = res.data?.preferences || {}
      for (const key of PREFS_KEYS) {
        if (serverPrefs[key] != null) preferences[key] = serverPrefs[key]
      }
      saveToStorage()
    } catch {
      // localStorage fallback already applied
    }
    applyAll()
    loaded.value = true
  }

  async function save() {
    saveToStorage()
    applyAll()
    try {
      await api.put('/user/preferences/', {
        preferences: Object.fromEntries(PREFS_KEYS.map(k => [k, preferences[k]])),
      })
    } catch {
      // silently fail — localStorage persists the values
    }
  }

  function set(key, value) {
    preferences[key] = String(value).toLowerCase()
    if (key === 'THEME') applyTheme()
    if (key === 'ACCENT_COLOR') applyAccent()
    if (key === 'FONT_FAMILY') applyFont()
  }

  function get(key) {
    return preferences[key]
  }

  return { preferences, loaded, initialize, save, set, get, applyAll }
}
