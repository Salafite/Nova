import { computed, watch, shallowRef } from 'vue'
import { useSettingsStore } from '../stores/settings.js'

import en from '../locales/en.json'
import ar from '../locales/ar.json'

const LS_KEY = 'nova_locale'
const FALLBACK_LOCALE = 'en-US'

const catalog = {
  'en-US': { dict: en, dir: 'ltr', name: 'English', nameNative: 'English' },
  'ar-EG': { dict: ar, dir: 'rtl', name: 'Arabic', nameNative: 'العربية' },
}

function loadStoredLocale() {
  const stored = localStorage.getItem(LS_KEY)
  if (stored && catalog[stored]) return stored
  return FALLBACK_LOCALE
}

function saveLocale(v) {
  localStorage.setItem(LS_KEY, v)
}

function pluralCategory(count) {
  if (typeof Intl !== 'undefined' && Intl.PluralRules) {
    try {
      const pr = new Intl.PluralRules('ar-EG')
      return pr.select(count)
    } catch {}
  }
  return count === 1 ? 'one' : 'other'
}

function resolveKey(dict, key, count) {
  if (count == null) return dict[key]
  const cat = pluralCategory(count)
  const pluralKey = key + '.' + cat
  if (dict[pluralKey] !== undefined) return dict[pluralKey]
  const otherKey = key + '.other'
  if (dict[otherKey] !== undefined) return dict[otherKey]
  return dict[key]
}

function interpolate(str, count) {
  if (str == null) return ''
  if (count != null) return str.replace(/\{count\}/g, String(count))
  return str
}

export const availableLocales = Object.entries(catalog).map(([code, meta]) => ({
  code,
  name: meta.name,
  nameNative: meta.nameNative,
  dir: meta.dir,
}))

export function useI18n() {
  const settings = useSettingsStore()
  const localeRef = shallowRef(loadStoredLocale())

  const locale = computed(() => {
    const sv = settings.values['SYSTEM_LANGUAGE']
    if (sv && catalog[sv]) return sv
    return localeRef.value
  })

  const dir = computed(() => catalog[locale.value]?.dir || 'ltr')
  const isRTL = computed(() => dir.value === 'rtl')

  function t(key, ...args) {
    let fallback = ''
    let count = null

    if (args.length === 1) {
      if (typeof args[0] === 'number') {
        count = args[0]
      } else if (args[0] && typeof args[0] === 'object' && 'count' in args[0]) {
        count = args[0].count
      } else {
        fallback = args[0]
      }
    } else if (args.length >= 2) {
      fallback = args[0]
      count = args[1]
    }

    const d = catalog[locale.value]?.dict || {}
    const resolved = resolveKey(d, key, count)
    if (resolved === undefined) return interpolate(fallback || key, count)
    return interpolate(resolved, count)
  }

  function setLocale(code) {
    if (!catalog[code]) return
    localeRef.value = code
    saveLocale(code)
    settings.updateValue('SYSTEM_LANGUAGE', code)
    applyDir()
  }

  function applyDir() {
    const entry = catalog[locale.value]
    const d = entry?.dir || 'ltr'
    document.documentElement.setAttribute('dir', d)
    document.documentElement.setAttribute('lang', locale.value)
  }

  watch(locale, () => { applyDir() }, { immediate: true })

  watch(() => settings.values['SYSTEM_LANGUAGE'], (v) => {
    if (v && catalog[v] && v !== localeRef.value) {
      localeRef.value = v
      saveLocale(v)
      applyDir()
    }
  })

  return { locale, dir, isRTL, t, setLocale, availableLocales, apply: applyDir }
}
