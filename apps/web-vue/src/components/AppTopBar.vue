<template>
  <header class="topbar">
    <button class="menu-btn" @click="$emit('toggle')" aria-label="Toggle sidebar">
      <span class="material-symbols-outlined">menu</span>
    </button>
    <h2 class="page-title">{{ title }}</h2>
    <div class="spacer"></div>
    <span class="user-role">{{ auth.role }}</span>
    <button class="logout-btn" @click="logout" aria-label="Log out">{{ t('logout') }}</button>
  </header>
</template>

<script setup>
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth.js'
import { useI18n } from '../composables/useI18n.js'

defineProps({ title: { type: String, default: '' } })
defineEmits(['toggle'])

const { t } = useI18n()
const router = useRouter()
const auth = useAuthStore()

function logout() {
  auth.logout()
  router.push('/login')
}
</script>

<style scoped>
.topbar { height: 56px; display: flex; align-items: center; padding: 0 24px; gap: 16px; background: #fff; border-bottom: 1px solid #e0e0e0; flex-shrink: 0; }
.menu-btn { background: none; border: none; font-size: 24px; cursor: pointer; padding: 4px; color: #333; border-radius: 8px; }
.menu-btn:hover { background: #f0f0f0; }
.page-title { font-size: 18px; font-weight: 600; color: #1a1a2e; }
.spacer { flex: 1; }
.user-role { font-size: 13px; color: #666; padding: 4px 12px; background: #f5f5f5; border-radius: 4px; }
.logout-btn { font-size: 13px; color: #ba1a1a; background: none; border: 1px solid #ba1a1a; padding: 4px 12px; border-radius: 4px; cursor: pointer; }
.logout-btn:hover { background: #ba1a1a; color: #fff; }
</style>
