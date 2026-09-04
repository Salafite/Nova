<template>
  <div class="thermal-receipt-container" :class="[paperSize, { 'is-printing': isPrinting }]" ref="receiptRef">
    <div class="receipt-header">
      <h2 class="store-name">{{ storeName }}</h2>
      <div class="store-address">{{ storeAddress }}</div>
      <div class="store-phone">{{ storePhone }}</div>
    </div>
    
    <div class="receipt-meta">
      <div class="meta-row">
        <span>{{ t('receipt-date', 'Date:') }}</span>
        <span>{{ dateFormatted }}</span>
      </div>
      <div class="meta-row">
        <span>{{ t('receipt-order', 'Order #:') }}</span>
        <span>{{ orderNumber }}</span>
      </div>
      <div class="meta-row">
        <span>{{ t('receipt-customer', 'Customer:') }}</span>
        <span>{{ customerName || t('pos-walkin', 'Walk-in') }}</span>
      </div>
    </div>

    <div class="receipt-divider"></div>

    <table class="receipt-items">
      <thead>
        <tr>
          <th class="col-qty">Q</th>
          <th class="col-desc">Item</th>
          <th class="col-price">Price</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="(item, idx) in items" :key="idx">
          <td class="col-qty">{{ item.qty }}</td>
          <td class="col-desc">
            <div>{{ item.name || item.product_name }}</div>
            <div class="item-sku" v-if="item.sku">{{ item.sku }}</div>
          </td>
          <td class="col-price">{{ formatMoney(item.qty * (item.price ?? item.unit_price ?? 0)) }}</td>
        </tr>
      </tbody>
    </table>

    <div class="receipt-divider"></div>

    <div class="receipt-summary">
      <div class="summary-row">
        <span>{{ t('receipt-subtotal', 'Subtotal:') }}</span>
        <span>{{ formatMoney(subtotal) }}</span>
      </div>
      <div class="summary-row">
        <span>{{ t('receipt-tax', 'Tax:') }}</span>
        <span>{{ formatMoney(tax) }}</span>
      </div>
      <div class="summary-row grand-total">
        <span>{{ t('receipt-total', 'Total:') }}</span>
        <span>{{ formatMoney(total) }}</span>
      </div>
    </div>
    
    <div class="receipt-payments" v-if="payments && payments.length">
      <div class="receipt-divider"></div>
      <div class="summary-row" v-for="(payment, idx) in payments" :key="idx">
        <span>{{ payment.payment_method || payment.method }}</span>
        <span>{{ formatMoney(payment.amount) }}</span>
      </div>
      <div class="summary-row" v-if="change > 0">
        <span>{{ t('receipt-change', 'Change:') }}</span>
        <span>{{ formatMoney(change) }}</span>
      </div>
    </div>

    <div class="receipt-footer">
      <div class="footer-msg">{{ t('receipt-thanks', 'Thank you for your business!') }}</div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, nextTick, onMounted, watch } from 'vue'
import { useI18n } from '../../composables/useI18n.js'

const props = defineProps({
  paperSize: {
    type: String,
    default: 'mm80', // 'mm80' or 'mm58'
  },
  storeName: {
    type: String,
    default: 'NOVA ERP',
  },
  storeAddress: {
    type: String,
    default: '123 Business Rd, City',
  },
  storePhone: {
    type: String,
    default: '(555) 123-4567',
  },
  orderNumber: {
    type: String,
    default: '',
  },
  date: {
    type: [String, Date],
    default: () => new Date(),
  },
  customerName: {
    type: String,
    default: '',
  },
  items: {
    type: Array,
    default: () => [],
  },
  subtotal: {
    type: Number,
    default: 0,
  },
  tax: {
    type: Number,
    default: 0,
  },
  total: {
    type: Number,
    default: 0,
  },
  payments: {
    type: Array,
    default: () => [],
  },
  change: {
    type: Number,
    default: 0,
  },
})

const { t } = useI18n()

const receiptRef = ref(null)
const isPrinting = ref(false)

const dateFormatted = computed(() => {
  const d = new Date(props.date)
  return d.toLocaleString()
})

function formatMoney(n) {
  return '$' + (n || 0).toFixed(2).replace(/\B(?=(\d{3})+(?!\d))/g, ',')
}

const print = () => {
  return new Promise((resolve) => {
    isPrinting.value = true
    nextTick(() => {
      window.print()
      setTimeout(() => {
        isPrinting.value = false
        resolve()
      }, 500)
    })
  })
}

defineExpose({
  print
})
</script>

<style scoped>
.thermal-receipt-container {
  display: none;
  background: white;
  color: black;
  font-family: 'Courier New', Courier, monospace;
  font-size: 12px;
  line-height: 1.4;
  padding: 10px;
}

.thermal-receipt-container.is-printing {
  display: block;
}

.thermal-receipt-container.mm80 {
  width: 80mm;
}

.thermal-receipt-container.mm58 {
  width: 58mm;
  font-size: 11px;
}

.receipt-header {
  text-align: center;
  margin-bottom: 10px;
}

.store-name {
  font-size: 16px;
  font-weight: bold;
  margin: 0 0 4px 0;
}

.receipt-meta {
  margin-bottom: 10px;
}

.meta-row {
  display: flex;
  justify-content: space-between;
}

.receipt-divider {
  border-top: 1px dashed black;
  margin: 8px 0;
}

.receipt-items {
  width: 100%;
  border-collapse: collapse;
}

.receipt-items th {
  text-align: left;
  border-bottom: 1px dashed black;
  padding-bottom: 4px;
  font-weight: normal;
}

.receipt-items td {
  padding: 4px 0;
  vertical-align: top;
}

.col-qty {
  width: 15%;
}

.col-desc {
  width: 55%;
}

.item-sku {
  font-size: 10px;
  color: #333;
}

.col-price {
  width: 30%;
  text-align: right;
}

.receipt-items th.col-price {
  text-align: right;
}

.summary-row {
  display: flex;
  justify-content: space-between;
  margin-bottom: 4px;
}

.grand-total {
  font-weight: bold;
  font-size: 14px;
  margin-top: 6px;
}

.receipt-footer {
  text-align: center;
  margin-top: 15px;
}

.footer-msg {
  margin-bottom: 10px;
}

.receipt-barcode {
  max-width: 100%;
}

@media print {
  @page {
    margin: 0;
    size: auto;
  }
  
  body * {
    visibility: hidden;
  }
  
  .thermal-receipt-container.is-printing,
  .thermal-receipt-container.is-printing * {
    visibility: visible;
  }
  
  .thermal-receipt-container.is-printing {
    position: absolute;
    left: 0;
    top: 0;
    margin: 0;
    padding: 0;
    box-shadow: none;
  }
}
</style>
