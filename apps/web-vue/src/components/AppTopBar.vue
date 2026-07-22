<template>
  <header class="topbar">
    <button v-if="sidebarMode !== 'auto-hide'" class="menu-btn" @click="handleMenuClick" aria-label="Toggle sidebar">
      <span class="material-symbols-outlined">{{ sidebarOverlay ? 'menu' : 'menu_open' }}</span>
    </button>
    <button v-if="sidebarMode === 'auto-hide'" class="brand-btn" @click="openAppSwitcher" aria-label="Open apps">
      <span class="material-symbols-outlined">diamond</span>
      <span class="brand-text">Nova ERP</span>
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

  <Transition name="switcher">
    <div v-if="switcherOpen" class="switcher-overlay" @click.self="switcherOpen = false">
      <div class="switcher-header">
        <span class="material-symbols-outlined switcher-logo">diamond</span>
        <span class="switcher-title">Nova ERP</span>
        <button class="switcher-close" @click="switcherOpen = false">
          <span class="material-symbols-outlined">close</span>
        </button>
      </div>
      <div class="switcher-grid">
        <template v-for="item in navStore.items" :key="item.id || item.section">
          <div v-if="item.section" class="switcher-section">{{ isRTL && item.section_ar ? item.section_ar : item.section }}</div>
          <a
            v-else-if="auth.hasPermission(item.permission)"
            :class="['switcher-card', { active: activeId === (item.module || item.id) }]"
            href="#"
            @click.prevent="go(item)"
          >
            <span class="switcher-card-icon material-symbols-outlined">{{ item.icon }}</span>
            <span class="switcher-card-label">{{ isRTL && item.label_ar ? item.label_ar : item.label }}</span>
          </a>
        </template>
      </div>
    </div>
  </Transition>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '../stores/auth.js'
import { useNavStore } from '../stores/nav.js'
import { useI18n } from '../composables/useI18n.js'
import { useTheme } from '../composables/useTheme.js'
import { usePreferences } from '../composables/usePreferences.js'
import LocaleSwitcher from './LocaleSwitcher.vue'

const props = defineProps({
  title: { type: String, default: '' },
  sidebarOverlay: { type: Boolean, default: false },
  sidebarMode: { type: String, default: 'expanded' }
})
const emit = defineEmits(['toggle'])

const { t, isRTL } = useI18n()
const theme = useTheme()
const router = useRouter()
const route = useRoute()
const auth = useAuthStore()
const navStore = useNavStore()
const prefs = usePreferences()

const switcherOpen = ref(false)
const activeId = computed(() => route.name)

function handleMenuClick() {
  if (props.sidebarMode === 'auto-hide') {
    switcherOpen.value = !switcherOpen.value
  } else {
    emit('toggle')
  }
}

function openAppSwitcher() {
  switcherOpen.value = true
}

function toggleTheme() {
  theme.toggle()
  const newVal = theme.dark.value ? 'dark' : 'light'
  prefs.set('THEME', newVal)
  prefs.save()
}

function go(item) {
  switcherOpen.value = false
  router.push({ name: item.module || item.id })
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
  position: relative;
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

.brand-btn {
  display: flex;
  align-items: center;
  gap: 8px;
  background: none;
  border: none;
  cursor: pointer;
  padding: 6px 10px;
  color: var(--text-primary);
  border-radius: 8px;
  font-family: inherit;
  font-size: 14px;
  font-weight: 700;
  flex-shrink: 0;
}
.brand-btn:hover { background: var(--bg-surface-hover); }
.brand-btn .material-symbols-outlined { font-size: 22px; color: var(--color-primary); }
.brand-text { white-space: nowrap; }

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

.switcher-overlay {
  position: fixed;
  inset: 0;
  z-index: 5000;
  background: rgba(0,0,0,0.7);
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 40px 24px;
  overflow-y: auto;
  backdrop-filter: blur(4px);
}
.switcher-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 32px;
  color: #fff;
}
.switcher-logo { font-size: 32px; color: var(--color-primary); }
.switcher-title { font-size: 22px; font-weight: 700; }
.switcher-close {
  margin-inline-start: 24px;
  background: none;
  border: none;
  color: #aaa;
  cursor: pointer;
  font-size: 24px;
  border-radius: 8px;
  padding: 4px;
}
.switcher-close:hover { color: #fff; background: rgba(255,255,255,0.1); }
.switcher-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
  gap: 12px;
  max-width: 720px;
  width: 100%;
}
.switcher-section {
  grid-column: 1 / -1;
  font-size: 11px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 1px;
  color: rgba(255,255,255,0.35);
  padding: 16px 0 4px;
}
.switcher-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  padding: 20px 12px;
  border-radius: 12px;
  background: rgba(255,255,255,0.08);
  color: #ddd;
  text-decoration: none;
  cursor: pointer;
  transition: all 0.15s;
}
.switcher-card:hover { background: rgba(255,255,255,0.14); color: #fff; }
.switcher-card.active { background: rgba(93,63,211,0.3); color: #cabeff; }
.switcher-card-icon { font-size: 32px; }
.switcher-card-label { font-size: 12px; font-weight: 500; text-align: center; }

.switcher-enter-active, .switcher-leave-active { transition: opacity 0.2s; }
.switcher-enter-from, .switcher-leave-to { opacity: 0; }

@media (max-width: 767px) {
  .topbar { padding: 0 12px; gap: 10px; }
  .brand-text { display: none; }
  .switcher-grid { grid-template-columns: repeat(auto-fill, minmax(100px, 1fr)); gap: 8px; }
  .switcher-card { padding: 16px 8px; }
  .switcher-card-icon { font-size: 28px; }
}
</style>
