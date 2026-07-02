import { mount } from '@vue/test-utils'
import ErrorState from '../components/ErrorState.vue'
import { describe, it, expect } from 'vitest'

describe('ErrorState', () => {
  it('renders default error message', () => {
    const wrapper = mount(ErrorState)
    expect(wrapper.text()).toContain('Something went wrong. Please try again.')
  })

  it('renders custom error message', () => {
    const wrapper = mount(ErrorState, {
      props: { message: 'Custom error message' },
    })
    expect(wrapper.text()).toContain('Custom error message')
  })

  it('renders retry button by default', () => {
    const wrapper = mount(ErrorState)
    expect(wrapper.find('button').exists()).toBe(true)
    expect(wrapper.find('button').text()).toBe('Retry')
  })

  it('hides retry button when showRetry is false', () => {
    const wrapper = mount(ErrorState, {
      props: { showRetry: false },
    })
    expect(wrapper.find('button').exists()).toBe(false)
  })

  it('renders custom retry label', () => {
    const wrapper = mount(ErrorState, {
      props: { retryLabel: 'Try Again' },
    })
    expect(wrapper.find('button').text()).toBe('Try Again')
  })

  it('emits retry event when retry button is clicked', () => {
    const wrapper = mount(ErrorState)
    wrapper.find('button').trigger('click')
    expect(wrapper.emitted('retry')).toBeTruthy()
    expect(wrapper.emitted('retry').length).toBe(1)
  })
})
