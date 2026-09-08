<template>
  <div class="modal-overlay" v-if="modelValue" @click.self="close">
    <div class="modal-content">
      <div class="modal-header">
        <h3>{{ t('pos-split-payment', 'Split Payment') }}</h3>
        <button class="close-btn" @click="close">&times;</button>
      </div>
      <div class="modal-body">
        <div class="summary-row">
          <span class="label">{{ t('pos-total-due', 'Total Due') }}:</span>
          <span class="value">{{ formatMoney(total) }}</span>
        </div>
        <div class="summary-row">
          <span class="label">{{ t('pos-remaining', 'Remaining') }}:</span>
          <span class="value" :class="{ 'text-error': remaining > 0, 'text-success': remaining <= 0 }">{{ formatMoney(Math.max(0, remaining)) }}</span>
        </div>
        <div class="summary-row" v-if="remaining < 0">
          <span class="label">{{ t('pos-change', 'Change Due') }}:</span>
          <span class="value pop">{{ formatMoney(Math.abs(remaining)) }}</span>
        </div>

        <div class="tender-rows">
          <div v-for="(split, idx) in splits" :key="idx" class="tender-row">
            <select v-model="split.payment_method" class="tender-select">
              <option value="Cash">{{ t('pos-cash', 'Cash') }}</option>
              <option value="Card">{{ t('pos-card', 'Card') }}</option>
              <option value="Store Credit">{{ t('pos-store-credit', 'Store Credit') }}</option>
            </select>
            <input type="number" v-model.number="split.amount" class="tender-input" min="0" step="0.01" />
            <button class="remove-btn" @click="removeSplit(idx)" v-if="splits.length > 1">&times;</button>
          </div>
        </div>

        <button class="add-split-btn" @click="addSplit" v-if="remaining > 0">+ {{ t('pos-add-split', 'Add Split') }}</button>

        <div class="quick-bills" v-if="hasCashSplit">
          <button v-for="bill in quickBills" :key="bill" class="bill-btn" @click="addQuickBill(bill)">
            +{{ formatMoney(bill) }}
          </button>
          <button class="bill-btn exact" @click="setExactCash">{{ t('pos-exact', 'Exact') }}</button>
        </div>
      </div>
      <div class="modal-footer">
        <button class="cancel-btn" @click="close">{{ t('pos-cancel', 'Cancel') }}</button>
        <button class="confirm-btn" :disabled="remaining > 0" @click="confirm">
          {{ t('pos-confirm-payment', 'Confirm Payment') }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { useI18n } from '../../composables/useI18n.js'

const props = defineProps({
  modelValue: Boolean,
  total: { type: Number, required: true }
})

const emit = defineEmits(['update:modelValue', 'confirm'])

const { t } = useI18n()

const splits = ref([{ payment_method: 'Cash', amount: 0 }])

watch(() => props.modelValue, (val) => {
  if (val) {
    splits.value = [{ payment_method: 'Cash', amount: props.total }]
  }
})

const totalTendered = computed(() => {
  return splits.value.reduce((sum, s) => sum + (Number(s.amount) || 0), 0)
})

const remaining = computed(() => {
  return props.total - totalTendered.value
})

const hasCashSplit = computed(() => {
  return splits.value.some(s => s.payment_method === 'Cash')
})

const quickBills = [5, 10, 20, 50, 100]

function addQuickBill(amount) {
  let cashSplit = splits.value.find(s => s.payment_method === 'Cash')
  if (!cashSplit) {
    cashSplit = { payment_method: 'Cash', amount: 0 }
    splits.value.push(cashSplit)
  }
  cashSplit.amount = (Number(cashSplit.amount) || 0) + amount
}

function setExactCash() {
  let cashSplit = splits.value.find(s => s.payment_method === 'Cash')
  if (!cashSplit) {
    cashSplit = { payment_method: 'Cash', amount: 0 }
    splits.value.push(cashSplit)
  }
  const otherTendered = totalTendered.value - (Number(cashSplit.amount) || 0)
  cashSplit.amount = Math.max(0, props.total - otherTendered)
}

function addSplit() {
  splits.value.push({ payment_method: 'Card', amount: Math.max(0, remaining.value) })
}

function removeSplit(idx) {
  splits.value.splice(idx, 1)
}

function close() {
  emit('update:modelValue', false)
}

function confirm() {
  if (remaining.value > 0) return
  emit('confirm', {
    splits: splits.value.map(s => ({ ...s, amount: Number(s.amount) })),
    amount_tendered: totalTendered.value
  })
  close()
}

function formatMoney(n) {
  return '$' + (n || 0).toFixed(2).replace(/\B(?=(\d{3})+(?!\d))/g, ',')
}
</script>

<style scoped>
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}
.modal-content {
  background: var(--bg-surface);
  border-radius: 12px;
  width: 400px;
  max-width: 90vw;
  box-shadow: 0 10px 25px rgba(0,0,0,0.2);
  display: flex;
  flex-direction: column;
}
.modal-header {
  padding: 16px 20px;
  border-bottom: 1px solid var(--border-default);
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.modal-header h3 {
  margin: 0;
  font-size: 18px;
  color: var(--text-primary);
}
.close-btn {
  background: none;
  border: none;
  font-size: 24px;
  cursor: pointer;
  color: var(--text-muted);
}
.modal-body {
  padding: 20px;
}
.summary-row {
  display: flex;
  justify-content: space-between;
  font-size: 16px;
  margin-bottom: 10px;
}
.summary-row .label {
  font-weight: 500;
  color: var(--text-muted);
}
.summary-row .value {
  font-family: 'JetBrains Mono', monospace;
  font-weight: 700;
}
.text-error { color: var(--color-error); }
.text-success { color: var(--color-success); }
.pop { color: var(--color-primary); font-size: 20px; }
.tender-rows {
  margin-top: 20px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.tender-row {
  display: flex;
  gap: 10px;
  align-items: center;
}
.tender-select {
  flex: 1;
  padding: 8px;
  border: 1px solid var(--border-default);
  border-radius: 6px;
  background: var(--bg-surface-low);
  color: var(--text-primary);
}
.tender-input {
  width: 120px;
  padding: 8px;
  border: 1px solid var(--border-default);
  border-radius: 6px;
  background: var(--bg-surface-low);
  color: var(--text-primary);
  font-family: 'JetBrains Mono', monospace;
  text-align: right;
}
.remove-btn {
  background: none;
  border: none;
  color: var(--color-error);
  font-size: 20px;
  cursor: pointer;
}
.add-split-btn {
  margin-top: 10px;
  background: none;
  border: 1px dashed var(--color-primary);
  color: var(--color-primary);
  padding: 8px;
  border-radius: 6px;
  cursor: pointer;
  width: 100%;
}
.quick-bills {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 20px;
}
.bill-btn {
  flex: 1;
  padding: 8px 0;
  background: var(--bg-surface-hover);
  border: 1px solid var(--border-default);
  border-radius: 6px;
  cursor: pointer;
  font-weight: 600;
  font-family: 'JetBrains Mono', monospace;
}
.bill-btn:hover {
  background: var(--color-primary);
  color: #fff;
}
.modal-footer {
  padding: 16px 20px;
  border-top: 1px solid var(--border-default);
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}
.cancel-btn {
  padding: 10px 20px;
  background: var(--bg-surface-hover);
  border: 1px solid var(--border-default);
  border-radius: 6px;
  cursor: pointer;
}
.confirm-btn {
  padding: 10px 20px;
  background: var(--color-primary);
  color: #fff;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-weight: 600;
}
.confirm-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
</style>
