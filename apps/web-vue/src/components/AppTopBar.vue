<template>
  <header class="topbar">
    <button class="menu-btn" @click="$emit('toggle')" aria-label="Toggle sidebar">
      <span class="material-symbols-outlined">{{ sidebarOverlay ? 'menu' : 'menu_open' }}</span>
    </button>
    <h2 class="page-title">{{ title }}</h2>
    <div class="spacer"></div>
    <LocaleSwitcher />
    <button
      class="theme-btn"
      @click="toggleTheme"
      :aria-label="theme.dark ? 'Light mode' : 'Dark mode'"
      :title="theme.dark ? 'Light mode' : 'Dark mode'"
    >
      <span class="material-symbols-outlined">{{ theme.dark ? 'light_mode' : 'dark_mode' }}</span>
    </button>
    <span class="user-role">{{ auth.role }}</span>
    <button class="logout-btn" @click="logout" aria-label="Log out">{{ t('logout') }}</button>
  </header>
</template>

<script setup>
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth.js'
import { useI18n } from '../composables/useI18n.js'
import { useTheme } from '../composables/useTheme.js'
import { usePreferences } from '../composables/usePreferences.js'
import LocaleSwitcher from './LocaleSwitcher.vue'

defineProps({
  title: { type: String, default: '' },
  sidebarOverlay: { type: Boolean, default: false }
})
defineEmits(['toggle'])

const { t } = useI18n()
const theme = useTheme()
const router = useRouter()
const auth = useAuthStore()
const prefs = usePreferences()

function toggleTheme() {
  theme.toggle()
  const newVal = theme.dark.value ? 'dark' : 'light'
  prefs.set('THEME', newVal)
  prefs.save()
}

function logout() {
  auth.logout()
  router.push('/login')
}
</script>

<style scoped>
.topbar {
  height: 56px;
  display: flex;
  align-items: center;
  padding: 0 24px;
  gap: 16px;
  background: var(--bg-surface);
  border-bottom: 1px solid var(--border-default);
  flex-shrink: 0;
}
.menu-btn {
  background: none;
  border: none;
  font-size: 24px;
  cursor: pointer;
  padding: 4px;
  color: var(--text-secondary);
  border-radius: 8px;
  display: flex;
  align-items: center;
}
.menu-btn:hover { background: var(--bg-surface-hover); }
.page-title { font-size: 18px; font-weight: 600; color: var(--text-primary); }
.spacer { flex: 1; }
.user-role {
  font-size: 13px;
  color: var(--text-muted);
  padding: 4px 12px;
  background: var(--bg-surface-hover);
  border-radius: 4px;
}
.theme-btn {
  background: none;
  border: none;
  font-size: 20px;
  cursor: pointer;
  padding: 4px;
  color: var(--text-muted);
  border-radius: 8px;
  display: flex;
  align-items: center;
}
.theme-btn:hover { background: var(--bg-surface-hover); color: var(--color-primary); }
.logout-btn {
  font-size: 13px;
  color: #ba1a1a;
  background: none;
  border: 1px solid #ba1a1a;
  padding: 4px 12px;
  border-radius: 4px;
  cursor: pointer;
}
.logout-btn:hover { background: #ba1a1a; color: #fff; }
</style>
