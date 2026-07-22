<template>
  <div class="ai-wrapper">
    <button class="ai-fab" @click="open = !open" :title="open ? 'Close AI' : 'AI Assistant'">
      <span class="material-symbols-outlined">{{ open ? 'close' : 'smart_toy' }}</span>
    </button>

    <Transition name="panel">
      <div v-if="open" class="ai-panel">
        <div class="ai-header">
          <span class="material-symbols-outlined">smart_toy</span>
          <span class="ai-title">AI Assistant</span>
          <button class="ai-clear-btn" @click="store.clearChat()" title="Clear chat">
            <span class="material-symbols-outlined">delete</span>
          </button>
        </div>

        <div class="ai-messages" ref="msgContainer">
          <div v-if="store.messages.length === 0" class="ai-welcome">
            <span class="material-symbols-outlined">smart_toy</span>
            <p>Ask me anything about your ERP data.</p>
            <div class="ai-prompts">
              <button class="ai-prompt-chip" @click="usePrompt('Show me recent products')">Recent products</button>
              <button class="ai-prompt-chip" @click="usePrompt('How many orders do we have?')">Order count</button>
              <button class="ai-prompt-chip" @click="usePrompt('List all customers')">Customers</button>
              <button class="ai-prompt-chip" @click="usePrompt('Check stock levels')">Stock check</button>
            </div>
          </div>

          <div v-for="(msg, i) in store.messages" :key="i" :class="['ai-msg', `ai-msg-${msg.role}`]">
            <div class="ai-msg-bubble">{{ msg.content }}</div>
          </div>

          <div v-if="store.pendingConfirmation" class="ai-confirmation">
            <p>This action requires your confirmation:</p>
            <p class="ai-confirmation-preview">{{ store.pendingConfirmation.preview }}</p>
            <div class="ai-confirmation-actions">
              <button class="ai-confirm-btn" @click="confirmAction">Confirm</button>
              <button class="ai-cancel-btn" @click="cancelAction">Cancel</button>
            </div>
          </div>

          <div v-if="store.loading" class="ai-msg ai-msg-assistant">
            <div class="ai-msg-bubble ai-thinking">
              <span class="ai-dot"></span>
              <span class="ai-dot"></span>
              <span class="ai-dot"></span>
            </div>
          </div>
        </div>

        <div class="ai-input-row">
          <input
            v-model="input"
            class="ai-input"
            placeholder="Ask anything..."
            @keydown.enter="send"
            :disabled="store.isBusy"
          />
          <button class="ai-send-btn" @click="send" :disabled="store.isBusy || !input.trim()">
            <span class="material-symbols-outlined">send</span>
          </button>
        </div>
      </div>
    </Transition>
  </div>
</template>

<script setup>
import { ref, nextTick, watch } from 'vue'
import { useAiStore } from '../stores/ai.js'

const store = useAiStore()
const open = ref(false)
const input = ref('')
const msgContainer = ref(null)

function send() {
  const msg = input.value
  input.value = ''
  store.sendMessage(msg)
}

function usePrompt(text) {
  input.value = text
  store.sendMessage(text)
}

function confirmAction() {
  if (store.pendingConfirmation) {
    store.sendMessage(`yes, please confirm action ${store.pendingConfirmation.actionId}`)
    store.clearConfirmation()
  }
}

function cancelAction() {
  store.clearConfirmation()
}

watch(() => store.messages.length, async () => {
  await nextTick()
  if (msgContainer.value) {
    msgContainer.value.scrollTop = msgContainer.value.scrollHeight
  }
})

watch(() => store.streamContent, async () => {
  await nextTick()
  if (msgContainer.value) {
    msgContainer.value.scrollTop = msgContainer.value.scrollHeight
  }
})
</script>

<style scoped>
.ai-wrapper { position: fixed; bottom: 24px; right: 24px; z-index: 9998; }
.ai-fab {
  width: 56px; height: 56px; border-radius: 50%; border: none;
  background: var(--color-primary, #5d3fd3); color: #fff;
  display: flex; align-items: center; justify-content: center;
  cursor: pointer; box-shadow: 0 4px 16px rgba(0,0,0,0.25);
  transition: all 0.2s; position: relative; z-index: 2;
}
.ai-fab:hover { transform: scale(1.08); }
.ai-fab .material-symbols-outlined { font-size: 28px; }

.ai-panel {
  position: absolute; bottom: 68px; right: 0;
  width: 380px; height: 520px;
  background: var(--bg-surface, #fff);
  border: 1px solid var(--border-default, #e0e0e0);
  border-radius: 16px; box-shadow: 0 8px 32px rgba(0,0,0,0.15);
  display: flex; flex-direction: column; overflow: hidden;
}

.ai-header {
  display: flex; align-items: center; gap: 8px;
  padding: 14px 16px; border-bottom: 1px solid var(--border-default, #e0e0e0);
  background: var(--color-primary, #5d3fd3); color: #fff;
}
.ai-header .material-symbols-outlined { font-size: 20px; }
.ai-title { flex: 1; font-size: 15px; font-weight: 600; }
.ai-clear-btn {
  background: none; border: none; color: rgba(255,255,255,0.8);
  cursor: pointer; padding: 4px; border-radius: 6px; display: flex;
}
.ai-clear-btn:hover { background: rgba(255,255,255,0.15); color: #fff; }

.ai-messages {
  flex: 1; overflow-y: auto; padding: 16px; display: flex;
  flex-direction: column; gap: 10px;
}
.ai-welcome {
  text-align: center; color: var(--text-muted, #999);
  padding: 40px 16px; display: flex; flex-direction: column;
  align-items: center; gap: 8px;
}
.ai-welcome .material-symbols-outlined { font-size: 48px; opacity: 0.4; }
.ai-welcome p { margin: 0; font-size: 14px; }
.ai-prompts { display: flex; flex-wrap: wrap; gap: 6px; justify-content: center; margin-top: 12px; }
.ai-prompt-chip {
  padding: 6px 14px; border: 1px solid var(--border-default, #e0e0e0);
  border-radius: 16px; background: var(--bg-body, #fafafa);
  color: var(--text-primary, #222); font-size: 12px; cursor: pointer;
  transition: all 0.15s; white-space: nowrap;
}
.ai-prompt-chip:hover { background: var(--color-primary, #5d3fd3); color: #fff; border-color: var(--color-primary, #5d3fd3); }

.ai-confirmation {
  padding: 12px; margin: 8px 0; background: #fff8e1; border: 1px solid #ffd54f;
  border-radius: 12px; font-size: 13px;
}
.ai-confirmation-preview { font-family: monospace; font-size: 12px; background: rgba(0,0,0,0.04); padding: 8px; border-radius: 6px; margin: 8px 0; white-space: pre-wrap; word-break: break-word; }
.ai-confirmation-actions { display: flex; gap: 8px; }
.ai-confirm-btn, .ai-cancel-btn {
  flex: 1; padding: 8px; border: none; border-radius: 8px; cursor: pointer; font-size: 13px; font-weight: 600;
}
.ai-confirm-btn { background: var(--color-primary, #5d3fd3); color: #fff; }
.ai-cancel-btn { background: #e0e0e0; color: #333; }

.ai-msg { display: flex; }
.ai-msg-user { justify-content: flex-end; }
.ai-msg-assistant { justify-content: flex-start; }

.ai-msg-bubble {
  max-width: 85%; padding: 10px 14px; border-radius: 12px;
  font-size: 14px; line-height: 1.5; word-break: break-word;
  white-space: pre-wrap;
}
.ai-msg-user .ai-msg-bubble {
  background: var(--color-primary, #5d3fd3); color: #fff;
  border-bottom-right-radius: 4px;
}
.ai-msg-assistant .ai-msg-bubble {
  background: var(--bg-surface-hover, #f5f5f5);
  color: var(--text-primary, #222);
  border-bottom-left-radius: 4px;
}

.ai-thinking { display: flex; gap: 4px; padding: 12px 16px !important; }
.ai-dot {
  width: 8px; height: 8px; border-radius: 50%;
  background: var(--text-muted, #999); animation: bounce 1.4s infinite ease-in-out both;
}
.ai-dot:nth-child(1) { animation-delay: -0.32s; }
.ai-dot:nth-child(2) { animation-delay: -0.16s; }
@keyframes bounce { 0%,80%,100% { transform: scale(0); } 40% { transform: scale(1); } }

.ai-input-row {
  display: flex; gap: 8px; padding: 12px 16px;
  border-top: 1px solid var(--border-default, #e0e0e0);
}
.ai-input {
  flex: 1; padding: 10px 14px; border: 1px solid var(--border-default, #e0e0e0);
  border-radius: 24px; font-size: 14px; outline: none;
  background: var(--bg-body, #fafafa); color: var(--text-primary, #222);
}
.ai-input:focus { border-color: var(--color-primary, #5d3fd3); }
.ai-send-btn {
  width: 40px; height: 40px; border-radius: 50%; border: none;
  background: var(--color-primary, #5d3fd3); color: #fff;
  display: flex; align-items: center; justify-content: center;
  cursor: pointer; flex-shrink: 0;
}
.ai-send-btn:disabled { opacity: 0.4; cursor: default; }
[dir="rtl"] .ai-wrapper { right: auto; left: 24px; }
[dir="rtl"] .ai-panel { right: auto; left: 0; }

.panel-enter-active, .panel-leave-active { transition: all 0.25s ease; }
.panel-enter-from, .panel-leave-to { opacity: 0; transform: translateY(12px) scale(0.96); }
</style>
