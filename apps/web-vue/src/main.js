import { createApp } from 'vue'
import { createPinia } from 'pinia'
import router from './router/index.js'
import App from './App.vue'
import './style.css'

export function registerServiceWorker() {
  if (typeof window !== 'undefined' && 'serviceWorker' in navigator) {
    window.addEventListener('load', () => {
      navigator.serviceWorker
        .register('/sw.js')
        .then((registration) => {
          console.debug('[PWA] ServiceWorker registered with scope:', registration.scope)
        })
        .catch((error) => {
          console.debug('[PWA] ServiceWorker registration failed:', error)
        })
    })
  }
}

registerServiceWorker()

const app = createApp(App)
app.use(createPinia())
app.use(router)
app.mount('#app')

