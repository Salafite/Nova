import { ref, onUnmounted } from 'vue'

export function useWebSocket(path) {
  const connected = ref(false)
  const lastEvent = ref(null)
  let ws = null
  let reconnectTimer = null
  let handlers = {}

  function connect() {
    const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:'
    const url = `${protocol}//${location.host}${path}`
    try {
      ws = new WebSocket(url)
    } catch {
      scheduleReconnect()
      return
    }

    ws.onopen = () => { connected.value = true }

    ws.onclose = () => {
      connected.value = false
      scheduleReconnect()
    }

    ws.onmessage = (e) => {
      try {
        const msg = JSON.parse(e.data)
        lastEvent.value = msg
        const handler = handlers[msg.event]
        if (handler) handler(msg.data)
      } catch { /* ignore */ }
    }
  }

  function scheduleReconnect() {
    if (reconnectTimer) return
    reconnectTimer = setTimeout(() => {
      reconnectTimer = null
      connect()
    }, 3000)
  }

  function on(event, callback) {
    handlers[event] = callback
  }

  function disconnect() {
    if (reconnectTimer) clearTimeout(reconnectTimer)
    reconnectTimer = null
    if (ws) ws.close()
    ws = null
    connected.value = false
  }

  connect()

  onUnmounted(disconnect)

  return { connected, lastEvent, on, disconnect }
}
