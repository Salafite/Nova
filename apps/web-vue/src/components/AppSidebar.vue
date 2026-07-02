<template>
  <aside class="sidebar" :class="{ collapsed, 'mobile-open': mobileOpen }">
    <div class="logo">
      <span class="material-symbols-outlined">diamond</span>
      <span v-show="!collapsed">Nova ERP</span>
    </div>
    <nav>
      <template v-for="item in filteredNav" :key="item.id || item.section">
        <div v-if="item.section" class="nav-section" v-show="!collapsed">{{ isRTL && item.section_ar ? item.section_ar : item.section }}</div>
        <a v-else :data-id="item.id" :class="['nav-item', { active: activeId === item.id }]" href="#" @click.prevent="navigate(item)">
          <span class="material-symbols-outlined">{{ item.icon }}</span>
          <span v-show="!collapsed" class="label">{{ isRTL && item.label_ar ? item.label_ar : item.label }}</span>
        </a>
      </template>
    </nav>
    <div class="sidebar-footer">
      <button class="collapse-btn" @click="$emit('toggle')" aria-label="Collapse sidebar">
        <span class="material-symbols-outlined">{{ isRTL ? 'chevron_right' : 'chevron_left' }}</span>
      </button>
    </div>
  </aside>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth.js'
import { useNavStore } from '../stores/nav.js'
import { useI18n } from '../composables/useI18n.js'

defineProps({ collapsed: Boolean, mobileOpen: { type: Boolean, default: false } })
defineEmits(['toggle'])

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const navStore = useNavStore()
const { isRTL } = useI18n()

const activeId = computed(() => route.name)

const filteredNav = computed(() =>
  navStore.items.filter(item =>
    item.section || auth.hasPermission(item.permission)
  )
)

function navigate(item) {
  const name = item.module || item.id
  router.push({ name })
  if (window.innerWidth < 768) {
    document.querySelector('.sidebar-overlay')?.click()
  }
}
</script>

<style scoped>
.sidebar {
  position: relative;
  z-index: 1000;
  width: 240px;
  background: #1a1a2e;
  color: #ccc;
  display: flex;
  flex-direction: column;
  transition: width 0.3s;
  overflow: hidden;
  flex-shrink: 0;
}
.sidebar.collapsed { width: 64px; }
.logo { height: 56px; display: flex; align-items: center; gap: 12px; padding: 0 16px; font-weight: 700; color: #fff; border-bottom: 1px solid rgba(255,255,255,0.08); }
nav { flex: 1; overflow-y: auto; padding: 8px 0; }
.nav-section { padding: 8px 16px; font-size: 11px; text-transform: uppercase; letter-spacing: 1px; color: rgba(255,255,255,0.3); }
.nav-item { display: flex; align-items: center; gap: 12px; padding: 8px 16px; color: #ccc; text-decoration: none; cursor: pointer; border-left: 3px solid transparent; margin: 2px 8px; border-radius: 8px; transition: all 0.15s; }
.nav-item:hover { background: rgba(255,255,255,0.06); }
.nav-item.active { background: rgba(93,63,211,0.2); color: #cabeff; border-left-color: #5d3fd3; }
.sidebar-footer { padding: 8px; border-top: 1px solid rgba(255,255,255,0.08); }
.collapse-btn { width: 100%; padding: 8px; background: none; border: none; color: #ccc; cursor: pointer; border-radius: 8px; }
.collapse-btn:hover { background: rgba(255,255,255,0.06); }
.sidebar.collapsed .collapse-btn span { transform: rotate(180deg); }

@media (max-width: 767px) {
  .sidebar { position: fixed; left: -260px; height: 100vh; transition: left 0.3s; z-index: 1001; }
  .sidebar.mobile-open { left: 0; }
  .sidebar.collapsed { width: 240px; }
  .sidebar.collapsed .label { display: inline; }
  .sidebar.collapsed .nav-section { display: block; }
  .collapse-btn { display: none; }
}
</style>
