<template>
  <div class="portal-layout" :dir="dir">
    <!-- Portal Top Navigation Header -->
    <header class="portal-topbar">
      <div class="portal-topbar-inner">
        <!-- Brand & Title -->
        <div class="portal-brand-area">
          <router-link to="/portal/dashboard" class="portal-brand-link">
            <div class="portal-logo-badge">
              <span class="material-symbols-outlined">storefront</span>
            </div>
            <div class="portal-brand-text">
              <span class="portal-brand-name">Nova</span>
              <span class="portal-brand-tag">B2B Customer Portal</span>
            </div>
          </router-link>
        </div>

        <!-- Navigation Links -->
        <nav class="portal-nav">
          <router-link to="/portal/dashboard" class="portal-nav-link" active-class="active">
            <span class="material-symbols-outlined">dashboard</span>
            <span>{{ t('portal-nav-dashboard', 'Dashboard') }}</span>
          </router-link>
          <router-link to="/portal/catalog" class="portal-nav-link" active-class="active">
            <span class="material-symbols-outlined">inventory_2</span>
            <span>{{ t('portal-nav-supplies', 'Order Supplies') }}</span>
          </router-link>
          <router-link to="/portal/orders" class="portal-nav-link" active-class="active">
            <span class="material-symbols-outlined">receipt_long</span>
            <span>{{ t('portal-nav-orders', 'Orders') }}</span>
          </router-link>
          <router-link to="/portal/invoices" class="portal-nav-link" active-class="active">
            <span class="material-symbols-outlined">payments</span>
            <span>{{ t('portal-nav-invoices', 'Invoices') }}</span>
          </router-link>
        </nav>

        <!-- Right Side Account & Cart Quick Actions -->
        <div class="portal-actions">
          <!-- Cutoff Status Mini Badge -->
          <div
            v-if="portal.cutoffStatus"
            class="portal-cutoff-pill"
            :class="{ 'cutoff-passed': portal.isPastCutoff }"
            :title="portal.cutoffStatus.message"
          >
            <span class="material-symbols-outlined pill-icon">
              {{ portal.isPastCutoff ? 'schedule' : 'bolt' }}
            </span>
            <span class="pill-text">
              {{ portal.isPastCutoff ? 'Cutoff Passed (D+2 Delivery)' : `Next-Day Cutoff: ${portal.cutoffStatus.cutoff_time || '22:00'}` }}
            </span>
          </div>

          <!-- Cart Action Button -->
          <router-link to="/portal/cart" class="portal-cart-btn" :class="{ 'has-items': portal.cartItemCount > 0 }">
            <div class="cart-icon-wrapper">
              <span class="material-symbols-outlined">shopping_cart</span>
              <span v-if="portal.cartItemCount > 0" class="cart-badge-count">
                {{ portal.cartItemCount }}
              </span>
            </div>
            <div class="cart-btn-info" v-if="portal.cartSubtotal > 0">
              <span class="cart-subtotal-val">${{ portal.cartSubtotal.toFixed(2) }}</span>
            </div>
          </router-link>

          <!-- Customer Profile & Logout -->
          <div class="portal-user-profile">
            <div class="user-avatar">
              <span class="material-symbols-outlined">person</span>
            </div>
            <div class="user-info-text">
              <span class="customer-name-display">{{ customerDisplayName }}</span>
              <span class="customer-balance-preview" v-if="portal.accountSummary">
                Bal: ${{ (portal.accountSummary.current_balance || 0).toFixed(2) }}
              </span>
            </div>
            <button class="portal-logout-btn" @click="handleLogout" :title="t('logout', 'Sign Out')">
              <span class="material-symbols-outlined">logout</span>
            </button>
          </div>
        </div>
      </div>
    </header>

    <!-- Main Portal Content -->
    <main class="portal-main">
      <router-view />
    </main>

    <!-- Toast Notifications Container -->
    <div class="toast-container">
      <div v-for="t in toasts" :key="t.id" :class="['toast', `toast-${t.type}`]">
        {{ t.message }}
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { usePortalStore } from '../stores/portal.js'
import { useAuthStore } from '../stores/auth.js'
import { useToast } from '../composables/useToast.js'
import { useI18n } from '../composables/useI18n.js'

const router = useRouter()
const portal = usePortalStore()
const auth = useAuthStore()
const { toasts } = useToast()
const { t, dir } = useI18n()

const customerDisplayName = computed(() => {
  if (portal.accountSummary?.company_name) return portal.accountSummary.company_name
  if (portal.accountSummary?.customer_name) return portal.accountSummary.customer_name
  if (auth.user?.full_name) return auth.user.full_name
  if (auth.user?.username) return auth.user.username
  return 'Customer Account'
})

function handleLogout() {
  auth.logout()
  router.push('/login')
}

onMounted(() => {
  portal.fetchAccountSummary()
  portal.fetchCutoffStatus()
})
</script>

<style scoped>
.portal-layout {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  background: var(--bg-body, #0f0f1a);
  color: var(--text-primary, #e8e8f0);
}

.portal-topbar {
  background: var(--bg-surface, #1a1a2e);
  border-bottom: 1px solid var(--border-default, #2a2a4a);
  position: sticky;
  top: 0;
  z-index: 100;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.15);
}

.portal-topbar-inner {
  max-width: 1440px;
  margin: 0 auto;
  padding: 0 24px;
  height: 68px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 20px;
}

.portal-brand-area {
  display: flex;
  align-items: center;
}

.portal-brand-link {
  display: flex;
  align-items: center;
  gap: 12px;
  text-decoration: none;
  color: inherit;
}

.portal-logo-badge {
  width: 40px;
  height: 40px;
  border-radius: 10px;
  background: linear-gradient(135deg, #6366f1, #8b5cf6);
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
}

.portal-logo-badge .material-symbols-outlined {
  font-size: 22px;
}

.portal-brand-text {
  display: flex;
  flex-direction: column;
}

.portal-brand-name {
  font-size: 17px;
  font-weight: 700;
  letter-spacing: -0.3px;
  color: var(--text-primary, #fff);
  line-height: 1.2;
}

.portal-brand-tag {
  font-size: 11px;
  font-weight: 500;
  color: #a5b4fc;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.portal-nav {
  display: flex;
  align-items: center;
  gap: 6px;
}

.portal-nav-link {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 8px 14px;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 600;
  color: var(--text-secondary, #94a3b8);
  text-decoration: none;
  transition: all 0.15s ease;
}

.portal-nav-link .material-symbols-outlined {
  font-size: 19px;
}

.portal-nav-link:hover {
  background: var(--bg-surface-hover, rgba(255, 255, 255, 0.05));
  color: var(--text-primary, #fff);
}

.portal-nav-link.active {
  background: rgba(99, 102, 241, 0.15);
  color: #a5b4fc;
  font-weight: 700;
}

.portal-actions {
  display: flex;
  align-items: center;
  gap: 14px;
}

.portal-cutoff-pill {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  border-radius: 20px;
  font-size: 11px;
  font-weight: 600;
  background: rgba(34, 197, 94, 0.12);
  color: #4ade80;
  border: 1px solid rgba(34, 197, 94, 0.25);
}

.portal-cutoff-pill.cutoff-passed {
  background: rgba(245, 158, 11, 0.12);
  color: #fbbf24;
  border-color: rgba(245, 158, 11, 0.25);
}

.portal-cutoff-pill .pill-icon {
  font-size: 15px;
}

.portal-cart-btn {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  padding: 8px 16px;
  background: rgba(99, 102, 241, 0.12);
  border: 1px solid rgba(99, 102, 241, 0.3);
  border-radius: 10px;
  color: #a5b4fc;
  text-decoration: none;
  font-weight: 600;
  transition: all 0.2s ease;
}

.portal-cart-btn:hover {
  background: rgba(99, 102, 241, 0.2);
  border-color: rgba(99, 102, 241, 0.5);
  color: #fff;
  transform: translateY(-1px);
}

.cart-icon-wrapper {
  position: relative;
  display: flex;
  align-items: center;
}

.cart-icon-wrapper .material-symbols-outlined {
  font-size: 20px;
}

.cart-badge-count {
  position: absolute;
  top: -8px;
  right: -10px;
  background: #ef4444;
  color: #fff;
  font-size: 10px;
  font-weight: 700;
  min-width: 17px;
  height: 17px;
  border-radius: 9px;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0 4px;
  border: 2px solid var(--bg-surface, #1a1a2e);
}

.cart-btn-info {
  display: flex;
  align-items: center;
  font-size: 13px;
  font-weight: 700;
  color: var(--text-primary, #fff);
}

.portal-user-profile {
  display: flex;
  align-items: center;
  gap: 10px;
  padding-left: 12px;
  border-left: 1px solid var(--border-default, #2a2a4a);
}

.user-avatar {
  width: 34px;
  height: 34px;
  border-radius: 50%;
  background: var(--bg-surface-low, #222240);
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--text-secondary, #94a3b8);
}

.user-avatar .material-symbols-outlined {
  font-size: 18px;
}

.user-info-text {
  display: flex;
  flex-direction: column;
  line-height: 1.2;
}

.customer-name-display {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-primary, #fff);
  max-width: 140px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.customer-balance-preview {
  font-size: 10px;
  color: var(--text-muted, #94a3b8);
}

.portal-logout-btn {
  background: none;
  border: none;
  color: var(--text-muted, #94a3b8);
  cursor: pointer;
  padding: 6px;
  border-radius: 6px;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.15s ease;
}

.portal-logout-btn:hover {
  background: var(--bg-surface-hover, rgba(255, 255, 255, 0.05));
  color: #f87171;
}

.portal-logout-btn .material-symbols-outlined {
  font-size: 18px;
}

.portal-main {
  flex: 1;
  padding: 24px 0 48px;
}

@media (max-width: 900px) {
  .portal-topbar-inner {
    padding: 0 16px;
    height: auto;
    flex-wrap: wrap;
    padding-top: 10px;
    padding-bottom: 10px;
  }
  .portal-nav {
    order: 3;
    width: 100%;
    overflow-x: auto;
    padding-top: 6px;
  }
  .portal-cutoff-pill {
    display: none;
  }
}
</style>
