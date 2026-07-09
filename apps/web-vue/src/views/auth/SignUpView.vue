<template>
  <div class="signup-page" :dir="dir">
    <div class="signup-card">
      <div class="logo">Nova ERP</div>
      <p class="subtitle">{{ t('signup-title') }}</p>
      <div v-if="error" class="alert error">{{ error }}</div>
      <form @submit.prevent="handleSignup">
        <label class="sr-only" for="signup-business-name">{{ t('signup-business-name') }}</label>
        <input id="signup-business-name" v-model="business_name" class="input" :placeholder="t('signup-business-name')" required />
        <label class="sr-only" for="signup-full-name">{{ t('signup-full-name') }}</label>
        <input id="signup-full-name" v-model="full_name" class="input" :placeholder="t('signup-full-name')" required />
        <label class="sr-only" for="signup-email">{{ t('signup-email') }}</label>
        <input id="signup-email" v-model="email" type="email" class="input" :placeholder="t('signup-email')" required />
        <label class="sr-only" for="signup-username">{{ t('signup-username') }}</label>
        <input id="signup-username" v-model="username" class="input" :placeholder="t('signup-username')" required />
        <label class="sr-only" for="signup-password">{{ t('signup-password') }}</label>
        <input id="signup-password" v-model="password" type="password" class="input" :placeholder="t('signup-password')" required />
        <label class="sr-only" for="signup-confirm-password">{{ t('signup-confirm-password') }}</label>
        <input id="signup-confirm-password" v-model="confirm_password" type="password" class="input" :placeholder="t('signup-confirm-password')" required />
        <button type="submit" class="btn" :disabled="loading">
          {{ loading ? t('signup-creating') : t('signup-submit') }}
        </button>
      </form>
      <p class="login-link">
        <router-link to="/login">{{ t('signup-login-link') }}</router-link>
      </p>
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

const business_name = ref('')
const full_name = ref('')
const email = ref('')
const username = ref('')
const password = ref('')
const confirm_password = ref('')
const error = ref('')
const loading = ref(false)

async function handleSignup() {
  error.value = ''
  if (password.value !== confirm_password.value) {
    error.value = t('signup-password-mismatch')
    return
  }
  loading.value = true
  try {
    const { api } = await import('../../api/client.js')
    const res = await api.post('/auth/signup', {
      business_name: business_name.value,
      username: username.value,
      password: password.value,
      full_name: full_name.value,
      email: email.value,
    })
    auth.token = res.data.access_token
    auth.user = res.data.user
    localStorage.setItem('nova_token', auth.token)
    localStorage.setItem('nova_user', JSON.stringify(auth.user))
    router.push('/')
  } catch {
    error.value = t('signup-error')
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.signup-page { display: flex; align-items: center; justify-content: center; min-height: 100vh; background: #f5f5f9; padding: 20px; }
.signup-card { background: #fff; padding: 40px; border-radius: 12px; box-shadow: 0 4px 24px rgba(0,0,0,0.08); width: 100%; max-width: 440px; }
.logo { font-size: 24px; font-weight: 700; color: #5d3fd3; text-align: center; margin-bottom: 4px; }
.subtitle { text-align: center; color: #666; margin-bottom: 24px; font-size: 14px; }
.input { width: 100%; padding: 12px 16px; border: 1px solid #ddd; border-radius: 6px; margin-bottom: 12px; font-size: 14px; box-sizing: border-box; }
.input:focus { outline: 2px solid #5d3fd3; outline-offset: 1px; border-color: #5d3fd3; }
.sr-only { position: absolute; width: 1px; height: 1px; padding: 0; margin: -1px; overflow: hidden; clip: rect(0,0,0,0); border: 0; }
.btn { width: 100%; padding: 12px; background: #5d3fd3; color: #fff; border: none; border-radius: 6px; font-size: 15px; font-weight: 600; cursor: pointer; }
.btn:hover { background: #4a32b0; }
.btn:disabled { opacity: 0.6; }
.alert { padding: 8px 12px; border-radius: 6px; margin-bottom: 12px; font-size: 13px; text-align: center; }
.alert.error { background: #fef2f2; color: #ba1a1a; border: 1px solid #fecaca; }
.login-link { text-align: center; margin-top: 16px; font-size: 13px; }
.login-link a { color: #5d3fd3; text-decoration: none; font-weight: 600; }
.login-link a:hover { text-decoration: underline; }
</style>
