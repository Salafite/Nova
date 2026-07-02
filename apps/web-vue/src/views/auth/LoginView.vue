<template>
  <div class="login-page" :dir="dir">
    <div class="login-card">
      <div class="logo">Nova ERP</div>
      <p class="subtitle">{{ t('login-title') }}</p>
      <div v-if="error" class="alert error">{{ error }}</div>
      <form @submit.prevent="handleLogin">
        <input v-model="username" class="input" :placeholder="t('login-username')" required />
        <input v-model="password" type="password" class="input" :placeholder="t('login-password')" required />
        <button type="submit" class="btn" :disabled="loading">{{ loading ? t('login-signing-in') : t('login-signin') }}</button>
      </form>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../../stores/auth.js'
import { useI18n } from '../../composables/useI18n.js'

const { t, dir } = useI18n()
const router = useRouter()
const auth = useAuthStore()
const username = ref('')
const password = ref('')
const error = ref('')
const loading = ref(false)

async function handleLogin() {
  loading.value = true; error.value = ''
  const ok = await auth.login(username.value, password.value)
  loading.value = false
  if (ok) router.push('/')
  else error.value = t('login-invalid')
}
</script>

<style scoped>
.login-page { display: flex; align-items: center; justify-content: center; height: 100vh; background: #f5f5f9; }
.login-card { background: #fff; padding: 40px; border-radius: 12px; box-shadow: 0 4px 24px rgba(0,0,0,0.08); width: 100%; max-width: 400px; }
.logo { font-size: 24px; font-weight: 700; color: #5d3fd3; text-align: center; margin-bottom: 4px; }
.subtitle { text-align: center; color: #666; margin-bottom: 24px; font-size: 14px; }
.input { width: 100%; padding: 12px 16px; border: 1px solid #ddd; border-radius: 6px; margin-bottom: 12px; font-size: 14px; box-sizing: border-box; }
.input:focus { outline: none; border-color: #5d3fd3; }
.btn { width: 100%; padding: 12px; background: #5d3fd3; color: #fff; border: none; border-radius: 6px; font-size: 15px; font-weight: 600; cursor: pointer; }
.btn:hover { background: #4a32b0; }
.btn:disabled { opacity: 0.6; }
.alert { padding: 8px 12px; border-radius: 6px; margin-bottom: 12px; font-size: 13px; text-align: center; }
.alert.error { background: #fef2f2; color: #ba1a1a; border: 1px solid #fecaca; }
</style>
