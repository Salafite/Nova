import axios from 'axios'

const CONFIG = { apiBase: import.meta.env.VITE_API_BASE || 'http://localhost:8070' }

const api = axios.create({ baseURL: CONFIG.apiBase + '/api' })

api.interceptors.request.use(config => {
  const token = localStorage.getItem('nova_token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

api.interceptors.response.use(
  res => res,
  err => {
    if (err.response?.status === 401) {
      localStorage.removeItem('nova_token')
      localStorage.removeItem('nova_user')
      window.location.hash = '#/login'
    }
    return Promise.reject(err)
  }
)

export { api, CONFIG }
