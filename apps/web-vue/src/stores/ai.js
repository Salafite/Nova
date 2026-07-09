import { defineStore } from 'pinia'
import { api } from '../api/client.js'

export const useAiStore = defineStore('ai', {
  state: () => ({
    messages: [],
    loading: false,
    streaming: false,
    streamContent: '',
    error: null,
    pendingConfirmation: null,
  }),

  getters: {
    chatMessages(state) {
      return state.messages
    },
    isBusy(state) {
      return state.loading || state.streaming
    },
  },

  actions: {
    addMessage(role, content) {
      this.messages.push({ role, content })
    },

    async sendMessage(message) {
      if (!message.trim() || this.isBusy) return

      this.addMessage('user', message)
      this.loading = true
      this.error = null
      this.streaming = false
      this.streamContent = ''

      try {
        const history = this.messages.slice(0, -1).map(m => ({
          role: m.role,
          content: m.content || null,
        }))

        const token = localStorage.getItem('nova_token')
        const res = await fetch('/api/ai/chat', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify({ message, history }),
        })

        if (!res.ok) {
          const err = await res.json().catch(() => ({ detail: res.statusText }))
          throw new Error(err.detail || 'Request failed')
        }

        this.loading = false
        this.streaming = true

        const reader = res.body.getReader()
        const decoder = new TextDecoder()
        let buffer = ''

        while (true) {
          const { done, value } = await reader.read()
          if (done) break

          buffer += decoder.decode(value, { stream: true })
          const lines = buffer.split('\n')
          buffer = lines.pop() || ''

          for (const line of lines) {
            if (!line.startsWith('data: ')) continue
            const payload = line.slice(6).trim()
            if (!payload) continue
            try {
              const event = JSON.parse(payload)
              this._handleEvent(event)
            } catch {
              // skip malformed events
            }
          }
        }

        if (buffer.startsWith('data: ')) {
          try {
            const payload = buffer.slice(6).trim()
            if (payload) {
              const event = JSON.parse(payload)
              this._handleEvent(event)
            }
          } catch {
            // skip
          }
        }
      } catch (err) {
        this.error = err.message || 'An error occurred'
        this.addMessage('assistant', `Error: ${this.error}`)
      } finally {
        this.loading = false
        this.streaming = false
        this.streamContent = ''
      }
    },

    _handleEvent(event) {
      if (event.type === 'text' && event.content) {
        this.streamContent += event.content
        const last = this.messages[this.messages.length - 1]
        if (last && last.role === 'assistant') {
          last.content = this.streamContent
        } else {
          this.addMessage('assistant', this.streamContent)
        }
      } else if (event.type === 'tool_start') {
        // tool execution indicator
      } else if (event.type === 'tool_end') {
        // tool execution complete
      } else if (event.type === 'confirmation_required') {
        this.pendingConfirmation = {
          actionId: event.action_id,
          tool: event.tool,
          preview: event.preview,
        }
      } else if (event.type === 'error') {
        this.error = event.content
      }
    },

    clearConfirmation() {
      this.pendingConfirmation = null
    },

    clearChat() {
      this.messages = []
      this.error = null
      this.pendingConfirmation = null
    },
  },
})
