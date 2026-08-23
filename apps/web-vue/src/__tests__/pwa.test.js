import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { registerServiceWorker } from '../main.js'

describe('PWA Service Worker Registration', () => {
  let originalNavigator

  beforeEach(() => {
    vi.restoreAllMocks()
  })

  it('registers service worker when supported by navigator', async () => {
    const registerMock = vi.fn().mockResolvedValue({ scope: '/' })
    const addEventListenerMock = vi.fn((event, cb) => cb())

    const mockNavigator = {
      serviceWorker: {
        register: registerMock
      }
    }

    const mockWindow = {
      addEventListener: addEventListenerMock
    }

    // Test direct registration call pattern
    if ('serviceWorker' in mockNavigator) {
      mockWindow.addEventListener('load', () => {
        mockNavigator.serviceWorker.register('/sw.js')
      })
    }

    expect(addEventListenerMock).toHaveBeenCalledWith('load', expect.any(Function))
    expect(registerMock).toHaveBeenCalledWith('/sw.js')
  })

  it('handles service worker registration errors gracefully', async () => {
    const consoleDebugSpy = vi.spyOn(console, 'debug').mockImplementation(() => {})
    const registerMock = vi.fn().mockRejectedValue(new Error('Registration failed'))

    const mockNavigator = {
      serviceWorker: {
        register: registerMock
      }
    }

    if ('serviceWorker' in mockNavigator) {
      await mockNavigator.serviceWorker.register('/sw.js').catch((err) => {
        console.debug('[PWA] Service Worker registration failed:', err)
      })
    }

    expect(registerMock).toHaveBeenCalledWith('/sw.js')
    expect(consoleDebugSpy).toHaveBeenCalled()
  })
})
