<template>
  <div class="landing">
    <header class="landing-header">
      <div class="logo"><span class="material-symbols-outlined">diamond</span> Nova ERP</div>
      <nav>
        <a href="#features">{{ t('Features') }}</a>
        <a href="#pricing">{{ t('Pricing') }}</a>
        <router-link to="/login" class="btn-outline btn-sm">{{ t('Sign In') }}</router-link>
      </nav>
    </header>

    <section class="hero">
      <h1>{{ t('hero-title') }}</h1>
      <p class="hero-sub">{{ t('hero-sub') }}</p>
      <div class="hero-cta">
        <router-link to="/login" class="btn-primary btn-lg">{{ t('Get Started') }}</router-link>
        <a href="https://github.com" class="btn-outline btn-lg">{{ t('View on GitHub') }}</a>
      </div>
    </section>

    <section id="features" class="features">
      <h2>{{ t('features-title') }}</h2>
      <div class="feature-grid">
        <div class="feature-card" v-for="f in features" :key="f.title">
          <span class="material-symbols-outlined feature-icon">{{ f.icon }}</span>
          <h3>{{ f.title }}</h3>
          <p>{{ f.desc }}</p>
        </div>
      </div>
    </section>

    <section id="pricing" class="pricing">
      <h2>{{ t('pricing-title') }}</h2>
      <div class="pricing-card">
        <div class="price-amount">$5 <span>/ {{ t('user-month') }}</span></div>
        <ul>
          <li>{{ t('p-1') }}</li>
          <li>{{ t('p-2') }}</li>
          <li>{{ t('p-3') }}</li>
          <li>{{ t('p-4') }}</li>
        </ul>
        <router-link to="/login" class="btn-primary btn-lg" style="width:100%;justify-content:center;">{{ t('Start Free Trial') }}</router-link>
      </div>
    </section>

    <footer class="landing-footer">
      <p>Nova ERP — {{ t('open-source') }}</p>
      <div class="legal-links">
        <router-link to="/privacy">Privacy Policy</router-link>
        <span class="sep">&middot;</span>
        <router-link to="/terms">Terms of Service</router-link>
      </div>
    </footer>
  </div>
</template>

<script setup>
import { computed } from 'vue'
const locale = computed(() => localStorage.getItem('nova_locale') || 'en')
const isAr = computed(() => locale.value === 'ar-EG')
const t = (key) => ({
  'Features': isAr.value ? 'المميزات' : 'Features',
  'Pricing': isAr.value ? 'التسعير' : 'Pricing',
  'Sign In': isAr.value ? 'تسجيل الدخول' : 'Sign In',
  'hero-title': isAr.value ? 'نظام ERP حديث لإدارة التوزيع الغذائي' : 'Modern ERP for Food & Beverage Distribution',
  'hero-sub': isAr.value ? 'إدارة المخزون، المبيعات، المشتريات، والمحاسبة في نظام واحد مفتوح المصدر' : 'Inventory, sales, purchasing, and accounting — all in one open-source platform.',
  'Get Started': isAr.value ? 'ابدأ الآن' : 'Get Started',
  'View on GitHub': isAr.value ? 'عرض على GitHub' : 'View on GitHub',
  'features-title': isAr.value ? 'مميزات قوية' : 'Powerful Features',
  'pricing-title': isAr.value ? 'تسعير بسيط' : 'Simple Pricing',
  'user-month': isAr.value ? 'مستخدم/شهر' : 'user/month',
  'p-1': isAr.value ? 'مخزون وفواتير غير محدودة' : 'Unlimited inventory & invoices',
  'p-2': isAr.value ? 'تقارير متقدمة' : 'Advanced reporting',
  'p-3': isAr.value ? 'دعم متعدد اللغات' : 'Multi-language support',
  'p-4': isAr.value ? 'تكامل API كامل' : 'Full API access',
  'Start Free Trial': isAr.value ? 'ابدأ النسخة التجريبية' : 'Start Free Trial',
  'open-source': isAr.value ? 'برنامج مفتوح المصدر — مرخص تحت AGPLv3' : 'Open-source software — AGPLv3 licensed',
})[key] || key

const features = [
  { icon: 'inventory_2', title: isAr.value ? 'إدارة المخزون' : 'Inventory Management', desc: isAr.value ? 'تتبع المخزون في مستودعات متعددة مع تنبيهات إعادة الطلب' : 'Track stock across warehouses with reorder alerts.' },
  { icon: 'point_of_sale', title: isAr.value ? 'المبيعات ونقطة البيع' : 'Sales & POS', desc: isAr.value ? 'إدارة الطلبات، عروض الأسعار، ونقطة بيع متكاملة' : 'Manage orders, quotations, and an integrated POS.' },
  { icon: 'receipt_long', title: isAr.value ? 'المشتريات' : 'Purchasing', desc: isAr.value ? 'طلبات شراء، عروض أسعار، واستلام بضائع' : 'Purchase orders, RFQs, and goods receipt.' },
  { icon: 'account_balance', title: isAr.value ? 'المحاسبة' : 'Accounting', desc: isAr.value ? 'فواتير، مدفوعات، وشجرة حسابات كاملة' : 'Invoices, payments, and full chart of accounts.' },
  { icon: 'group', title: isAr.value ? 'CRM' : 'CRM', desc: isAr.value ? 'إدارة العملاء والموردين مع تاريخ كامل' : 'Manage customers and suppliers with full history.' },
  { icon: 'analytics', title: isAr.value ? 'التقارير' : 'Reports', desc: isAr.value ? 'تقارير تحليلية مع رسوم بيانية وإحصائيات' : 'Analytics dashboards with charts and stats.' },
]
</script>

<style scoped>
.landing { min-height: 100vh; background: #fff; color: #1a1a2e; font-family: 'Inter', sans-serif; }
.landing-header { display: flex; align-items: center; justify-content: space-between; padding: 16px 40px; border-bottom: 1px solid #eee; }
.logo { display: flex; align-items: center; gap: 8px; font-size: 18px; font-weight: 700; color: #5d3fd3; }
.landing-header nav { display: flex; align-items: center; gap: 24px; }
.landing-header nav a { color: #555; text-decoration: none; font-size: 14px; }
.hero { text-align: center; padding: 100px 24px 80px; max-width: 700px; margin: 0 auto; }
.hero h1 { font-size: 40px; font-weight: 800; line-height: 1.2; margin-bottom: 16px; }
.hero-sub { font-size: 18px; color: #666; line-height: 1.6; margin-bottom: 32px; }
.hero-cta { display: flex; gap: 12px; justify-content: center; }
.btn-lg { padding: 14px 32px !important; font-size: 15px !important; }
.btn-sm { padding: 6px 16px !important; font-size: 13px !important; }
.features { padding: 80px 40px; background: #f8f7ff; }
.features h2, .pricing h2 { text-align: center; font-size: 28px; margin-bottom: 48px; }
.feature-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 24px; max-width: 1000px; margin: 0 auto; }
.feature-card { background: #fff; border: 1px solid #e5e7eb; border-radius: 12px; padding: 28px; text-align: center; }
.feature-icon { font-size: 40px; color: #5d3fd3; margin-bottom: 12px; }
.feature-card h3 { font-size: 16px; margin-bottom: 8px; }
.feature-card p { font-size: 14px; color: #666; line-height: 1.5; }
.pricing { padding: 80px 24px; text-align: center; }
.pricing-card { max-width: 380px; margin: 0 auto; border: 2px solid #5d3fd3; border-radius: 16px; padding: 40px; }
.price-amount { font-size: 48px; font-weight: 800; color: #1a1a2e; margin-bottom: 24px; }
.price-amount span { font-size: 16px; font-weight: 400; color: #888; }
.pricing-card ul { list-style: none; padding: 0; margin-bottom: 32px; text-align: left; }
.pricing-card li { padding: 8px 0; font-size: 14px; color: #555; }
.pricing-card li::before { content: '✓'; color: #16a34a; margin-right: 8px; font-weight: 700; }
.landing-footer { text-align: center; padding: 32px; color: #999; font-size: 13px; border-top: 1px solid #eee; }
.legal-links { margin-top: 8px; }
.legal-links a { color: #999; text-decoration: none; }
.legal-links a:hover { color: #5d3fd3; text-decoration: underline; }
.sep { margin: 0 8px; color: #ccc; }

@media (max-width: 767px) {
  .hero { padding: 60px 16px 40px; }
  .hero h1 { font-size: 28px; }
  .hero-cta { flex-direction: column; align-items: stretch; }
  .landing-header { padding: 12px 16px; flex-wrap: wrap; gap: 8px; }
}
</style>
