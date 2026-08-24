import { describe, it, expect, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useI18n } from '../composables/useI18n.js'
import en from '../locales/en.json'
import ar from '../locales/ar.json'

describe('Catch-Weight & Dual UOM Bilingual i18n Localization', () => {
  beforeEach(() => {
    localStorage.clear()
    setActivePinia(createPinia())
  })

  it('validates en.json and ar.json structure and non-empty values', () => {
    expect(typeof en).toBe('object')
    expect(typeof ar).toBe('object')
    expect(Object.keys(en).length).toBeGreaterThan(500)
    expect(Object.keys(ar).length).toBeGreaterThan(500)
  })

  const coreCwKeys = [
    // Product Master & Dual UOM Setup
    'catch-weight',
    'catch-weight-dual-uom',
    'dual-uom-catch-weight',
    'dual-uom-pricing-engine',
    'dual-uom-config',
    'stocking-uom',
    'stocking-uom-label',
    'pricing-uom',
    'pricing-uom-label',
    'nominal-weight',
    'nominal-weight-case',
    'nominal-weight-short',
    'price-per-pricing-uom',
    'price-per-unit',
    'pricing-basis',
    'pricing-basis-rate',
    'pricing-rate',
    'tolerance-pct',
    'tolerance-percentage',
    'default-tolerance',
    'require-supervisor-approval',

    // Warehouse Scale Capture & Tolerance Discrepancy Approvals
    'scale-weight',
    'scale-weighed',
    'record-scale-weight',
    'pending-scale-weight',
    'weight-variance',
    'net-weight-variance',
    'tolerance-discrepancy',
    'tolerance-discrepancy-title',
    'within-tolerance',
    'out-of-tolerance',
    'tolerance-approved',
    'supervisor-approval-title',
    'supervisor-id',
    'supervisor-notes',
    'approve-all',
    'cannot-complete-discrepancy',
    'cannot-deliver-discrepancy',

    // Sales Order & Invoice Recalculation
    'dual-uom-order',
    'recalculate-cw',
    'cw-pricing-applied',
    'weight-adjustment',
    'recalculated-subtotal',
    'recalculated-price',
    'weight-fulfillment',
    'catch-weight-invoice',
    'sync-weights',
    'scale-weight-billing',
  ]

  it('contains all essential catch-weight keys in en.json', () => {
    coreCwKeys.forEach((key) => {
      expect(en[key], `en.json missing key: ${key}`).toBeDefined()
      expect(typeof en[key]).toBe('string')
      expect(en[key].length).toBeGreaterThan(0)
    })
  })

  it('contains all essential catch-weight keys in ar.json', () => {
    coreCwKeys.forEach((key) => {
      expect(ar[key], `ar.json missing key: ${key}`).toBeDefined()
      expect(typeof ar[key]).toBe('string')
      expect(ar[key].length).toBeGreaterThan(0)
    })
  })

  it('correctly translates keys with useI18n in en-US and ar-EG locales', () => {
    const { t, setLocale, isRTL } = useI18n()

    // Test English
    setLocale('en-US')
    expect(isRTL.value).toBe(false)
    expect(t('catch-weight')).toBe('Catch-Weight')
    expect(t('dual-uom-pricing-engine')).toBe('Dual UOM & Catch-Weight Engine')
    expect(t('recalculate-cw')).toBe('Recalculate Pricing')
    expect(t('tolerance-discrepancy')).toBe('Tolerance Discrepancy')
    expect(t('scale-weight')).toBe('Scale Weight (Dual UOM)')

    // Test Arabic
    setLocale('ar-EG')
    expect(isRTL.value).toBe(true)
    expect(t('catch-weight')).toBe('الوزن المتغير')
    expect(t('dual-uom-pricing-engine')).toBe('محرك التسعير بالوزن المتغير والوحدات المزدوجة')
    expect(t('recalculate-cw')).toBe('إعادة احتساب التسعير')
    expect(t('tolerance-discrepancy')).toBe('فارق في نسبة السماحية')
    expect(t('scale-weight')).toBe('وزن الميزان (وحدة مزدوجة)')
  })

  it('interpolates count parameters properly in both languages', () => {
    const { t, setLocale } = useI18n()

    // English count interpolation
    setLocale('en-US')
    expect(t('pick-updated', { count: 3 })).toBe('Line #3 pick recorded')
    expect(t('item-approved-success', { count: 2 })).toBe('Line #2 tolerance discrepancy approved')

    // Arabic count interpolation
    setLocale('ar-EG')
    expect(t('pick-updated', { count: 3 })).toBe('تم تسجيل تجهيز البند رقم 3')
    expect(t('item-approved-success', { count: 2 })).toBe('تم اعتماد فارق نسبة السماحية للبند رقم 2 بنجاح')
  })
})
