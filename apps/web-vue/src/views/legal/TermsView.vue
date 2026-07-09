<template>
  <div class="legal-page">
    <div class="legal-card">
      <router-link to="/landing" class="back-link">&larr; Back to Home</router-link>
      <h1>Terms of Service</h1>
      <p class="effective-date"><em>Last updated: July 3, 2026</em></p>

      <section>
        <h2>1. Acceptance of Terms</h2>
        <p>By accessing or using Nova ERP ("the Service"), you agree to be bound by these Terms of Service. If you do not agree, do not use the Service.</p>
      </section>

      <section>
        <h2>2. Description of Service</h2>
        <p>Nova ERP is a cloud-based Enterprise Resource Planning application that provides tools for managing business operations including inventory, sales, purchasing, manufacturing, HR, finance, and reporting.</p>
      </section>

      <section>
        <h2>3. User Accounts</h2>
        <p>You are responsible for maintaining the confidentiality of your account credentials and for all activities under your account. You must provide accurate information and keep it updated. You must be at least 18 years old to use the Service.</p>
      </section>

      <section>
        <h2>4. Acceptable Use</h2>
        <p>You agree not to: use the Service for any unlawful purpose; attempt to gain unauthorized access to the Service or its systems; interfere with the Service's operation; transmit malware or harmful code; use the Service to store illegal content.</p>
      </section>

      <section>
        <h2>5. Data Ownership</h2>
        <p>You retain all ownership of the data you enter into the Service. We do not claim any intellectual property rights over your data.</p>
      </section>

      <section>
        <h2>6. Payment and Billing</h2>
        <p>If you subscribe to a paid plan, fees are charged in advance on a monthly or annual basis as selected. All payments are processed securely through Stripe. Refunds are handled according to our refund policy.</p>
      </section>

      <section>
        <h2>7. Cancellation and Termination</h2>
        <p>You may cancel your account at any time. Upon cancellation, access to the Service will be terminated at the end of the current billing period. We may terminate or suspend access for violation of these terms.</p>
      </section>

      <section>
        <h2>8. Limitation of Liability</h2>
        <p>The Service is provided "as is" without warranty of any kind. We are not liable for any indirect, incidental, or consequential damages arising from your use of the Service.</p>
      </section>

      <section>
        <h2>9. Governing Law</h2>
        <p>These terms are governed by the laws of the jurisdiction where the service provider is established. Any disputes shall be resolved through binding arbitration.</p>
      </section>

      <section>
        <h2>10. Changes to Terms</h2>
        <p>We reserve the right to modify these terms. Material changes will be communicated via email or in-app notification. Continued use after changes constitutes acceptance.</p>
      </section>

      <section>
        <h2>11. Contact</h2>
        <p>For questions about these terms, contact us at <a href="mailto:legal@novaerp.com">legal@novaerp.com</a>.</p>
      </section>
    </div>
  </div>
</template>

<style scoped>
.legal-page { min-height: 100vh; background: var(--bg-body, #f5f5f9); display: flex; justify-content: center; padding: 40px 16px; }
.legal-card { max-width: 720px; width: 100%; background: var(--bg-surface, #fff); border: 1px solid var(--border-default, #e0e0e0); border-radius: 12px; padding: 40px; }
.back-link { display: inline-block; margin-bottom: 24px; color: var(--color-primary, #5d3fd3); text-decoration: none; font-size: 14px; }
.back-link:hover { text-decoration: underline; }
h1 { font-size: 28px; font-weight: 700; color: var(--text-primary, #1a1a2e); margin-bottom: 4px; }
.effective-date { color: var(--text-muted, #666); font-size: 13px; margin-bottom: 32px; }
section { margin-bottom: 24px; }
h2 { font-size: 18px; font-weight: 600; color: var(--text-primary, #1a1a2e); margin-bottom: 8px; }
p { font-size: 14px; line-height: 1.7; color: var(--text-secondary, #333); }
a { color: var(--color-primary, #5d3fd3); }
</style>
