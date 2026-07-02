<template>
  <div class="locale-switcher" :class="{ open: isOpen }" ref="containerRef">
    <button class="locale-trigger" @click="isOpen = !isOpen" :aria-label="t('language')">
      <span class="locale-icon material-symbols-outlined">translate</span>
      <span class="locale-current">{{ current?.nameNative || current?.name || t('language') }}</span>
      <span class="material-symbols-outlined arrow">arrow_drop_down</span>
    </button>
    <div v-if="isOpen" class="locale-dropdown">
      <button
        v-for="loc in availableLocales"
        :key="loc.code"
        :class="['locale-option', { active: loc.code === locale }]"
        @click="select(loc.code)"
      >
        <span class="option-name">{{ loc.nameNative }}</span>
        <span class="option-name-secondary">{{ loc.name }}</span>
        <span v-if="loc.code === locale" class="material-symbols-outlined check">check</span>
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useSettingsStore } from '../stores/settings.js'
import { useI18n } from '../composables/useI18n.js'

const { t, locale, setLocale, availableLocales } = useI18n()
const settings = useSettingsStore()

const containerRef = ref(null)
const isOpen = ref(false)

const current = computed(() => availableLocales.find(l => l.code === locale.value))

function select(code) {
  setLocale(code)
  isOpen.value = false
  if (settings.groups.length) {
    setTimeout(() => settings.saveGroup('general'), 300)
  }
}

function onClickOutside(e) {
  if (containerRef.value && !containerRef.value.contains(e.target)) {
    isOpen.value = false
  }
}

onMounted(() => document.addEventListener('click', onClickOutside))
onUnmounted(() => document.removeEventListener('click', onClickOutside))
</script>

<style scoped>
.locale-switcher { position: relative; }
.locale-trigger {
  display: flex; align-items: center; gap: 4px;
  padding: 4px 8px; border: 1px solid transparent;
  border-radius: 6px; background: none;
  cursor: pointer; font-size: 13px; color: inherit;
  transition: all 0.15s;
}
.locale-trigger:hover { border-color: rgba(255,255,255,0.2); background: rgba(255,255,255,0.06); }
.locale-icon { font-size: 16px; }
.locale-current { max-width: 100px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.arrow { font-size: 16px; transition: transform 0.2s; }
.open .arrow { transform: rotate(180deg); }

.locale-dropdown {
  position: absolute; top: 100%; right: 0; margin-top: 4px;
  background: var(--bg-surface); border: 1px solid var(--border-default);
  border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.12);
  min-width: 180px; z-index: 1100; overflow: hidden;
}
.locale-option {
  display: flex; align-items: center; gap: 8px;
  width: 100%; padding: 10px 14px;
  border: none; background: none;
  cursor: pointer; font-size: 13px; color: var(--text-secondary);
  text-align: left; transition: background 0.1s;
}
.locale-option:hover { background: var(--bg-surface-hover); }
.locale-option.active { background: var(--bg-primary-faded); color: var(--color-primary); font-weight: 600; }
.option-name { flex: 1; }
.option-name-secondary { font-size: 11px; color: var(--text-faint); }
.check { font-size: 16px; color: var(--color-primary); }

[dir="rtl"] .locale-dropdown { right: auto; left: 0; }
[dir="rtl"] .locale-option { text-align: right; }
</style>
