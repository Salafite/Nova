<template>
  <aside
    :class="[
      'sidebar',
      { collapsed, overlay, 'overlay-open': overlay && open, 'overlay-closed': overlay && !open }
    ]"
    :dir="isRTL ? 'rtl' : 'ltr'"
  >
    <div class="logo">
      <span class="material-symbols-outlined">diamond</span>
      <span v-show="!collapsed || overlay">Nova ERP</span>
    </div>
    <nav>
      <template v-for="item in filteredNav" :key="item.id || item.section">
        <div v-if="item.section" class="nav-section" v-show="!collapsed || overlay">
          {{ isRTL && item.section_ar ? item.section_ar : item.section }}
        </div>
        <a
          v-else
          :data-id="item.id"
          :class="['nav-item', { active: activeId === item.id }]"
          href="#"
          @click.prevent="navigate(item)"
        >
          <span class="material-symbols-outlined">{{ item.icon }}</span>
          <span v-show="!collapsed || overlay" class="label">
            {{ isRTL && item.label_ar ? item.label_ar : item.label }}
          </span>
        </a>
      </template>
    </nav>
    <div class="sidebar-footer">
      <button
        class="mode-btn"
        @click="$emit('switch-mode')"
        :title="overlay ? t('home.sidebar-mode-expanded') : t('home.sidebar-mode-overlay')"
      >
        <span class="material-symbols-outlined">{{ overlay ? 'push_pin' : 'side_navigation' }}</span>
      </button>
      <button
        v-if="!overlay"
        class="collapse-btn"
        @click="$emit('toggle')"
        :aria-label="collapsed ? 'Expand sidebar' : 'Collapse sidebar'"
      >
        <span class="material-symbols-outlined">{{ isRTL ? 'chevron_right' : 'chevron_left' }}</span>
      </button>
      <button
        v-else
        class="collapse-btn"
        @click="$emit('toggle')"
        :aria-label="open ? 'Close sidebar' : 'Open sidebar'"
      >
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

const props = defineProps({
  collapsed: Boolean,
  mobileOpen: { type: Boolean, default: false },
  overlay: { type: Boolean, default: false },
  open: { type: Boolean, default: true }
})
defineEmits(['toggle', 'switch-mode'])

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const navStore = useNavStore()
const { isRTL, t } = useI18n()

const activeId = computed(() => route.name)

const filteredNav = computed(() =>
  navStore.items.filter(item =>
    item.section || auth.hasPermission(item.permission)
  )
)

function navigate(item) {
  const name = item.module || item.id
  router.push({ name })
  if (props.overlay || window.innerWidth < 768) {
    document.querySelector('.sidebar-overlay')?.click()
  }
}
</script>

<style scoped>
.sidebar {
  position: relative;
  z-index: 1000;
  width: 240px;
  background: var(--sidebar-bg, #1a1a2e);
  color: var(--sidebar-text, #ccc);
  display: flex;
  flex-direction: column;
  transition: width 0.3s, transform 0.3s;
  overflow: hidden;
  flex-shrink: 0;
}

.sidebar.collapsed { width: 64px; }

.sidebar.overlay {
  position: fixed;
  top: 0;
  inset-inline-start: 0;
  height: 100vh;
  z-index: 1002;
  width: 240px;
}
.sidebar.overlay-closed {
  transform: translateX(-100%);
}
[dir="rtl"] .sidebar.overlay-closed {
  transform: translateX(100%);
}
.sidebar.overlay-open {
  transform: translateX(0);
}

.logo {
  height: 56px;
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 0 16px;
  font-weight: 700;
  color: var(--sidebar-logo, #fff);
  border-bottom: 1px solid var(--sidebar-border, rgba(255,255,255,0.08));
  flex-shrink: 0;
}

nav { flex: 1; overflow-y: auto; padding: 8px 0; }

.nav-section {
  padding: 8px 16px;
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 1px;
  color: var(--sidebar-muted, rgba(255,255,255,0.3));
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 8px 16px;
  color: var(--sidebar-text, #ccc);
  text-decoration: none;
  cursor: pointer;
  margin: 2px 8px;
  border-radius: 8px;
  transition: all 0.15s;
  border-inline-start: 3px solid transparent;
}
.nav-item:hover { background: var(--sidebar-hover, rgba(255,255,255,0.06)); }
.nav-item.active {
  background: var(--sidebar-active-bg, rgba(93,63,211,0.2));
  color: var(--sidebar-active-text, #cabeff);
  border-inline-start-color: var(--color-primary);
}

.sidebar-footer {
  padding: 8px;
  display: flex;
  gap: 4px;
  border-top: 1px solid var(--sidebar-border, rgba(255,255,255,0.08));
}

.mode-btn,
.collapse-btn {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 8px;
  background: none;
  border: none;
  color: var(--sidebar-text, #ccc);
  cursor: pointer;
  border-radius: 8px;
  font-size: 11px;
  gap: 4px;
}
.mode-btn:hover,
.collapse-btn:hover { background: var(--sidebar-hover, rgba(255,255,255,0.06)); }
.mode-btn .material-symbols-outlined,
.collapse-btn .material-symbols-outlined { font-size: 18px; }

@media (max-width: 767px) {
  .sidebar {
    position: fixed;
    left: -260px;
    height: 100vh;
    transition: left 0.3s;
    z-index: 1001;
    width: 240px;
  }
  .sidebar.mobile-open { left: 0; }
  .sidebar.collapsed { width: 240px; }
  .sidebar.collapsed .label,
  .sidebar.collapsed .nav-section { display: inline; }
  .collapse-btn,
  .mode-btn { display: none; }
  .sidebar.overlay {
    left: auto;
  }
}
</style>
