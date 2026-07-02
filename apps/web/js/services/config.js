const CONFIG = {
  env: 'development',
  apiBase: 'http://localhost:8070',
  frontendUrl: 'http://localhost:8070'
}

async function loadConfig() {
  try {
    const res = await fetch('/config.json')
    if (res.ok) Object.assign(CONFIG, await res.json())
  } catch (e) {
    console.warn('Failed to load config.json, using defaults', e)
  }
  return CONFIG
}
