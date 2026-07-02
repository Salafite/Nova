<template>
  <div class="app-shell" :class="layoutClass">
    <div v-if="!isGrid && mobileSidebarOpen" class="sidebar-overlay" @click="mobileSidebarOpen = false"></div>
    <AppSidebar v-if="!isGrid" :collapsed="sidebarCollapsed" :mobile-open="mobileSidebarOpen" @toggle="toggleSidebar" />

    <main class="main-area">
      <div v-if="isGrid" class="grid-topbar">
        <div class="grid-logo">
          <span class="material-symbols-outlined">diamond</span>
          <span class="grid-brand">Nova ERP</span>
        </div>
        <nav class="grid-nav">
          <a v-for="item in navItems" :key="item.id"
             :class="['grid-nav-item', { active: activeId === item.id }]"
             href="#" @click.prevent="go(item)">
            <span class="material-symbols-outlined">{{ item.icon }}</span>
            <span class="grid-nav-label">{{ isRTL && item.label_ar ? item.label_ar : item.label }}</span>
          </a>
        </nav>
        <div class="grid-actions">
          <LocaleSwitcher />
          <span class="grid-user">{{ userLabel }}</span>
          <button class="grid-logout" @click="logout">
            <span class="material-symbols-outlined">logout</span>
          </button>
        </div>
      </div>

      <AppTopBar v-else :title="pageTitle" @toggle="sidebarCollapsed = !sidebarCollapsed" />

      <div class="content" :class="{ 'content-wide': isGrid }">
        <router-view />
      </div>
    </main>

    <div class="toast-container">
      <div v-for="t in toasts" :key="t.id" :class="['toast', `toast-${t.type}`]">
        {{ t.message }}
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useToast } from '../composables/useToast.js'
import { useI18n } from '../composables/useI18n.js'
import AppSidebar from '../components/AppSidebar.vue'
import AppTopBar from '../components/AppTopBar.vue'
import LocaleSwitcher from '../components/LocaleSwitcher.vue'
import { useNavStore } from '../stores/nav.js'
import { useAuthStore } from '../stores/auth.js'

const route = useRoute()
const router = useRouter()
const navStore = useNavStore()
const auth = useAuthStore()
const { toasts } = useToast()
const { isRTL } = useI18n()
const sidebarCollapsed = ref(false)
const mobileSidebarOpen = ref(false)

function toggleSidebar() {
  if (window.innerWidth < 768) {
    mobileSidebarOpen.value = !mobileSidebarOpen.value
  } else {
    sidebarCollapsed.value = !sidebarCollapsed.value
  }
}

const isGrid = computed(() => navStore.navStyle === 'grid')
const activeId = computed(() => route.name)
const layoutClass = computed(() => isGrid.value ? 'layout-grid' : 'layout-sidebar')

const pageTitle = computed(() => {
  const name = route.name
  const item = navStore.items.find(i => (i.module || i.id) === name)
  if (item) return isRTL.value && item.label_ar ? item.label_ar : item.label
  return name ? name.charAt(0).toUpperCase() + name.slice(1) : 'Nova ERP'
})

const navItems = computed(() => navStore.items.filter(item => !item.section))

const userLabel = computed(() => {
  const user = auth.user
  return user?.full_name || user?.username || 'User'
})

function go(item) {
  router.push({ name: item.module || item.id })
}

function logout() {
  auth.logout()
  router.push('/login')
}

onMounted(() => { navStore.load() })
</script>

<style scoped>
.app-shell { display: flex; height: 100vh; }
.main-area { flex: 1; display: flex; flex-direction: column; overflow: hidden; background: var(--bg-body); }
.content { flex: 1; overflow-y: auto; padding: 24px; }
.content-wide { padding: 0; }

.grid-topbar {
  display: flex;
  align-items: center;
  height: 56px;
  background: var(--color-sidebar-bg);
  color: var(--color-sidebar-text);
  padding: 0 16px;
  gap: 24px;
  flex-shrink: 0;
}
.grid-logo {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 700;
  color: #fff;
  font-size: 14px;
}
.grid-nav {
  display: flex;
  align-items: center;
  gap: 4px;
  flex: 1;
  overflow-x: auto;
}
.grid-nav-item {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 14px;
  border-radius: 8px;
  color: #aaa;
  text-decoration: none;
  font-size: 13px;
  transition: all 0.15s;
  white-space: nowrap;
}
.grid-nav-item:hover { background: rgba(255,255,255,0.06); color: #fff; }
.grid-nav-item.active { background: rgba(93,63,211,0.2); color: #cabeff; }
.grid-nav-item .material-symbols-outlined { font-size: 18px; }
.grid-actions { display: flex; align-items: center; gap: 12px; flex-shrink: 0; }
.grid-user { font-size: 13px; color: #aaa; }
.grid-logout {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border: none;
  border-radius: 8px;
  background: none;
  color: #aaa;
  cursor: pointer;
  transition: all 0.15s;
}
.grid-logout:hover { background: rgba(255,255,255,0.06); color: #fff; }
.grid-logout .material-symbols-outlined { font-size: 18px; }

.toast-container { position: fixed; top: 16px; right: 16px; z-index: 9999; display: flex; flex-direction: column; gap: 8px; }
.toast { padding: 12px 20px; border-radius: 8px; font-size: 14px; font-weight: 500; color: #fff; box-shadow: 0 4px 12px rgba(0,0,0,0.15); animation: slideIn 0.25s ease; }
.toast-success { background: #00897b; }
.toast-error { background: #c62828; }
.toast-info { background: #1565c0; }
@keyframes slideIn { from { transform: translateX(100%); opacity: 0; } to { transform: translateX(0); opacity: 1; } }

.sidebar-overlay { display: none; }
@media (max-width: 767px) {
  .sidebar-overlay { display: block; position: fixed; inset: 0; background: rgba(0,0,0,0.4); z-index: 900; }
  .content { padding: 16px; }
  .toast-container { right: 8px; left: 8px; top: 8px; }
}
</style>
