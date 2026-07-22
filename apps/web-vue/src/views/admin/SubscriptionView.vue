<template>
  <div :dir="dir">
    <div class="page-header">
      <div>
        <h1 class="page-title">{{ t('subscription') }}</h1>
        <p class="page-subtitle">{{ t('subscription-sub') }}</p>
      </div>
    </div>

    <SkeletonCard v-if="loading" variant="card" />
    <ErrorState v-else-if="error" :message="error" @retry="load" />

    <div v-else class="subscription-card">
      <div class="plan-header" :class="`plan-${sub.status}`">
        <span class="plan-name">{{ sub.plan }}</span>
        <span class="plan-status">{{ t(`status-${sub.status}`) }}</span>
      </div>
      <div class="plan-body">
        <div class="plan-price">
          <span class="price-amount">$5</span>
          <span class="price-period">/{{ t('user-month') }}</span>
        </div>
        <ul class="plan-features">
          <li>{{ t('f-unlimited') }}</li>
          <li>{{ t('f-analytics') }}</li>
          <li>{{ t('f-support') }}</li>
          <li>{{ t('f-api') }}</li>
        </ul>
        <div class="plan-actions">
          <button v-if="sub.status === 'none'" class="btn-primary btn-lg" @click="startCheckout" :disabled="loadingAction">
            {{ loadingAction ? t('processing') : t('subscribe') }}
          </button>
          <button v-else class="btn-outline btn-lg" @click="openPortal" :disabled="loadingAction">
            {{ loadingAction ? t('processing') : t('manage') }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { api } from '../../api/client.js'
import { useI18n } from '../../composables/useI18n.js'
import { useToast } from '../../composables/useToast.js'
import SkeletonCard from '../../components/SkeletonCard.vue'
import ErrorState from '../../components/ErrorState.vue'

const { t, dir } = useI18n()
const { show: toast } = useToast()

const loading = ref(true)
const loadingAction = ref(false)
const error = ref('')
const sub = ref({ status: 'none', plan: 'Free' })

async function load() {
  loading.value = true
  error.value = ''
  try {
    const res = await api.get('/billing/subscription')
    sub.value = res.data || { status: 'none', plan: 'Free' }
  } catch {
    error.value = t('failed-load')
  } finally {
    loading.value = false
  }
}

async function startCheckout() {
  loadingAction.value = true
  try {
    const res = await api.post('/billing/create-checkout', {
      success_url: window.location.href,
      cancel_url: window.location.href,
    })
    if (res.data.url) {
      window.location.href = res.data.url
    } else {
      toast(t('stripe-not-configured'), 'error')
    }
  } catch (e) {
    toast(e.response?.data?.detail || t('failed'), 'error')
  } finally {
    loadingAction.value = false
  }
}

async function openPortal() {
  loadingAction.value = true
  try {
    const res = await api.post('/billing/create-portal', {
      return_url: window.location.href,
    })
    if (res.data.url) {
      window.location.href = res.data.url
    } else {
      toast(t('stripe-not-configured'), 'error')
    }
  } catch (e) {
    toast(e.response?.data?.detail || t('failed'), 'error')
  } finally {
    loadingAction.value = false
  }
}

onMounted(load)
</script>

<style scoped>
.page-header { margin-bottom: 24px; }
.page-title { font-size: 22px; font-weight: 700; color: #1a1a2e; margin: 0; }
.page-subtitle { font-size: 13px; color: #666; margin-top: 4px; }
.subscription-card { max-width: 480px; margin: 0 auto; border: 1px solid #e0e0e0; border-radius: 12px; overflow: hidden; }
.plan-header { padding: 20px 24px; display: flex; justify-content: space-between; align-items: center; }
.plan-none { background: #f3f4f6; }
.plan-active { background: #dcfce7; }
.plan-past_due { background: #fef3c7; }
.plan-name { font-size: 16px; font-weight: 700; }
.plan-status { font-size: 12px; padding: 4px 10px; border-radius: 20px; background: rgba(0,0,0,0.08); text-transform: capitalize; }
.plan-body { padding: 24px; }
.plan-price { text-align: center; margin-bottom: 24px; }
.price-amount { font-size: 48px; font-weight: 800; color: #1a1a2e; }
.price-period { font-size: 16px; color: #888; }
.plan-features { list-style: none; padding: 0; margin: 0 0 24px; }
.plan-features li { padding: 8px 0; font-size: 14px; color: #555; border-bottom: 1px solid #f0f0f0; }
.plan-features li::before { content: '✓'; color: #16a34a; margin-right: 8px; font-weight: 700; }
[dir="rtl"] .plan-features li::before { margin-right: 0; margin-left: 8px; }
.plan-features li:last-child { border-bottom: none; }
.plan-actions { text-align: center; }
.btn-lg { padding: 12px 32px !important; font-size: 15px !important; width: 100%; justify-content: center; }
</style>
