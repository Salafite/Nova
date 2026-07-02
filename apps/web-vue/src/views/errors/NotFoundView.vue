<template>
  <div :dir="dir" class="not-found-page">
    <div class="not-found-card">
      <span class="material-symbols-outlined not-found-icon">search_off</span>
      <h1>404</h1>
      <p>{{ t('pageNotFound', 'Page not found') }}</p>
      <p class="sub">{{ t('pageNotFoundDesc', 'The page you are looking for does not exist or has been moved.') }}</p>
      <router-link to="/dashboard" class="btn-primary">
        <span class="material-symbols-outlined">home</span> {{ t('goToDashboard', 'Go to Dashboard') }}
      </router-link>
    </div>
  </div>
</template>

<script setup>
import { useI18n } from '../../composables/useI18n.js'
const { t, dir } = useI18n()
</script>

<style scoped>
.not-found-page {
  display: flex; align-items: center; justify-content: center;
  min-height: 100vh; padding: 2rem;
  background: var(--bg-color, #f5f5f5);
}
.not-found-card {
  text-align: center; max-width: 420px;
  background: var(--card-bg, #fff); padding: 3rem 2rem;
  border-radius: 16px; box-shadow: 0 2px 12px rgba(0,0,0,0.08);
}
.not-found-icon { font-size: 64px; color: var(--color-primary, #5d3fd3); }
h1 { font-size: 72px; margin: 0; color: var(--color-primary, #5d3fd3); }
p { font-size: 18px; color: var(--text-color, #333); margin: 0.5rem 0; }
.sub { font-size: 14px; color: var(--text-muted, #888); margin-bottom: 1.5rem; }
.btn-primary { display: inline-flex; align-items: center; gap: 8px; }
</style>
