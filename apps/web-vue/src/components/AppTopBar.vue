<template>
  <header class="topbar">
    <button v-if="sidebarMode === 'auto-hide'" class="brand-btn" @click="menuOpen = !menuOpen" aria-label="Open menu">
      <span class="material-symbols-outlined">diamond</span>
      <span class="brand-text">Nova ERP</span>
      <span class="material-symbols-outlined brand-chevron">{{ menuOpen ? 'expand_less' : 'expand_more' }}</span>
    </button>
    <button v-else class="menu-btn" @click="$emit('toggle')" aria-label="Toggle sidebar">
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

    <Transition name="dropdown">
      <div v-if="sidebarMode === 'auto-hide' && menuOpen" class="menu-dropdown" @click.self="menuOpen = false">
        <div class="menu-dropdown-inner">
          <template v-for="item in navStore.items" :key="item.id || item.section">
            <div v-if="item.section" class="menu-section">
              {{ isRTL && item.section_ar ? item.section_ar : item.section }}
            </div>
            <a
              v-else-if="auth.hasPermission(item.permission)"
              :class="['menu-item', { active: activeId === (item.module || item.id) }]"
              href="#"
              @click.prevent="navigate(item)"
            >
              <span class="material-symbols-outlined menu-item-icon">{{ item.icon }}</span>
              <span class="menu-item-label">{{ isRTL && item.label_ar ? item.label_ar : item.label }}</span>
            </a>
          </template>
        </div>
      </div>
    </Transition>
  </header>
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

defineProps({
  title: { type: String, default: '' },
  sidebarOverlay: { type: Boolean, default: false },
  sidebarMode: { type: String, default: 'expanded' }
})
defineEmits(['toggle'])

const { t, isRTL } = useI18n()
const theme = useTheme()
const router = useRouter()
const route = useRoute()
const auth = useAuthStore()
const navStore = useNavStore()
const prefs = usePreferences()

const menuOpen = ref(false)

const activeId = computed(() => route.name)

function toggleTheme() {
  theme.toggle()
  const newVal = theme.dark.value ? 'dark' : 'light'
  prefs.set('THEME', newVal)
  prefs.save()
}

function navigate(item) {
  menuOpen.value = false
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
.brand-chevron { font-size: 16px !important; color: var(--text-faint) !important; }

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

.menu-dropdown {
  position: absolute;
  top: 100%;
  left: 0;
  width: 280px;
  max-height: calc(100vh - 56px);
  overflow-y: auto;
  background: var(--bg-surface);
  border: 1px solid var(--border-default);
  border-radius: 0 0 12px 12px;
  box-shadow: 0 8px 24px rgba(0,0,0,0.12);
  z-index: 2000;
}
.menu-dropdown-inner { padding: 8px; }
.menu-section {
  padding: 10px 12px 4px;
  font-size: 11px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 1px;
  color: var(--text-faint);
}
.menu-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 9px 12px;
  border-radius: 8px;
  color: var(--text-primary);
  text-decoration: none;
  font-size: 13px;
  cursor: pointer;
  transition: background 0.12s;
  border-inline-start: 3px solid transparent;
}
.menu-item:hover { background: var(--bg-surface-hover); }
.menu-item.active {
  background: var(--bg-primary-faded);
  color: var(--color-primary);
  border-inline-start-color: var(--color-primary);
  font-weight: 600;
}
.menu-item-icon { font-size: 18px; flex-shrink: 0; }
.menu-item-label { flex: 1; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

.dropdown-enter-active, .dropdown-leave-active { transition: opacity 0.15s, transform 0.15s; }
.dropdown-enter-from, .dropdown-leave-to { opacity: 0; transform: translateY(-4px); }

@media (max-width: 767px) {
  .topbar { padding: 0 12px; gap: 10px; }
  .brand-text { display: none; }
  .menu-dropdown { width: 100%; }
}
</style>
