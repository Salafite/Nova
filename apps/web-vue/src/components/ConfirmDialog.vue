<template>
  <Teleport to="body">
    <div class="overlay" @click.self="cancel">
      <div class="dialog" :dir="dir">
        <h3 class="dialog-title">{{ title }}</h3>
        <p class="dialog-msg">{{ message }}</p>
        <div class="dialog-actions">
          <button class="btn-outline" @click="cancel">{{ t('confirm-cancel') }}</button>
          <button class="btn-danger" @click="confirm">{{ t('confirm-delete') }}</button>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup>
import { useI18n } from '../composables/useI18n.js'

const { t, dir } = useI18n()

defineProps({
  title: { type: String, default: '' },
  message: { type: String, default: '' }
})

const emit = defineEmits(['confirm', 'cancel'])

function confirm() { emit('confirm') }
function cancel() { emit('cancel') }
</script>

<style scoped>
.overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.4); display: flex; align-items: center; justify-content: center; z-index: 10000; }
.dialog { background: var(--bg-surface); border-radius: 12px; padding: 24px; max-width: 400px; width: 90%; box-shadow: 0 8px 32px rgba(0,0,0,0.2); }
.dialog-title { font-size: 16px; font-weight: 600; margin-bottom: 8px; color: var(--text-primary); }
.dialog-msg { font-size: 14px; color: var(--text-muted); margin-bottom: 20px; }
.dialog-actions { display: flex; gap: 8px; justify-content: flex-end; }
.btn-outline { padding: 8px 20px; border: 1px solid var(--border-input); border-radius: 8px; background: transparent; font-size: 13px; font-weight: 600; cursor: pointer; color: var(--text-secondary); }
.btn-outline:hover { background: var(--bg-surface-hover); }
.btn-danger { padding: 8px 20px; border: none; border-radius: 8px; background: #c62828; color: #fff; font-size: 13px; font-weight: 600; cursor: pointer; }
.btn-danger:hover { background: #b71c1c; }
</style>
