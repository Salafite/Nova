import { ref } from 'vue'

const STORAGE_KEY = 'nova_theme'

const dark = ref(localStorage.getItem(STORAGE_KEY) === 'dark')

function apply(d) {
  dark.value = d
  document.documentElement.classList.toggle('dark', d)
  localStorage.setItem(STORAGE_KEY, d ? 'dark' : 'light')
}

// Init on load
apply(dark.value)

export function useTheme() {
  function toggle() { apply(!dark.value) }
  function setTheme(mode) { apply(mode === 'dark') }
  return { dark, toggle, setTheme }
}
