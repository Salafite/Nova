import { mount } from '@vue/test-utils'
import StatsCard from '../components/StatsCard.vue'
import { describe, it, expect } from 'vitest'

describe('StatsCard', () => {
  it('renders label and value', () => {
    const wrapper = mount(StatsCard, {
      props: { label: 'Revenue', value: '$10,000' },
    })
    expect(wrapper.text()).toContain('Revenue')
    expect(wrapper.text()).toContain('$10,000')
  })

  it('renders with default color', () => {
    const wrapper = mount(StatsCard, {
      props: { label: 'Users', value: 42 },
    })
    const valueEl = wrapper.find('.stat-value')
    expect(valueEl.attributes('style')).toContain('color: rgb(93, 63, 211)')
  })

  it('renders with custom color', () => {
    const wrapper = mount(StatsCard, {
      props: { label: 'Sales', value: '500', color: '#22c55e' },
    })
    const valueEl = wrapper.find('.stat-value')
    expect(valueEl.attributes('style')).toContain('color: rgb(34, 197, 94)')
  })

  it('has clickable class when `to` prop is provided', () => {
    const wrapper = mount(StatsCard, {
      props: { label: 'Orders', value: 99, to: 'orders' },
    })
    expect(wrapper.classes()).toContain('clickable')
  })

  it('does not have clickable class when `to` is empty', () => {
    const wrapper = mount(StatsCard, {
      props: { label: 'Orders', value: 99 },
    })
    expect(wrapper.classes()).not.toContain('clickable')
  })
})
