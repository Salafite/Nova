<template>
  <div class="legal-page">
    <div class="legal-card">
      <router-link to="/landing" class="back-link">&larr; Back to Home</router-link>
      <h1>Privacy Policy</h1>
      <p class="effective-date"><em>Last updated: July 3, 2026</em></p>

      <section>
        <h2>1. Information We Collect</h2>
        <p>We collect information you provide when creating an account (name, email, company name), data you enter into the system (products, customers, orders, financial records), and technical data automatically collected (IP address, browser type, pages visited).</p>
      </section>

      <section>
        <h2>2. How We Use Your Information</h2>
        <p>We use your information to operate and maintain the ERP service, provide customer support, send service-related communications, improve the product, and comply with legal obligations.</p>
      </section>

      <section>
        <h2>3. Data Storage and Security</h2>
        <p>Your data is stored in encrypted PostgreSQL databases hosted on secure cloud infrastructure (Railway / Neon). We implement industry-standard security measures including encryption at rest and in transit, regular security audits, and access controls.</p>
      </section>

      <section>
        <h2>4. Data Sharing</h2>
        <p>We do not sell your personal data. We may share data with trusted third-party service providers (hosting, email delivery, payment processing) who are bound by data processing agreements. We may disclose data if required by law.</p>
      </section>

      <section>
        <h2>5. Your Rights</h2>
        <p>Depending on your jurisdiction (e.g., GDPR for EU users, CCPA for California users), you may have the right to access, correct, delete, or export your data. Contact us at privacy@novaerp.com to exercise these rights.</p>
      </section>

      <section>
        <h2>6. Data Retention</h2>
        <p>We retain your data for as long as your account is active or as needed to provide the service. Upon account deletion, data is permanently removed within 90 days unless retention is required by law.</p>
      </section>

      <section>
        <h2>7. Cookies</h2>
        <p>We use essential cookies for authentication and session management. We do not use tracking cookies or third-party analytics cookies without your consent.</p>
      </section>

      <section>
        <h2>8. Changes to This Policy</h2>
        <p>We may update this policy from time to time. Material changes will be communicated via email or an in-app notification.</p>
      </section>

      <section>
        <h2>9. Contact</h2>
        <p>For questions about this privacy policy, contact us at <a href="mailto:privacy@novaerp.com">privacy@novaerp.com</a>.</p>
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
