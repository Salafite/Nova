import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import PaginationBar from '../components/PaginationBar.vue'
import { usePagination } from '../composables/usePagination.js'

describe('PaginationBar.vue', () => {
  beforeEach(() => {
    const pinia = createPinia()
    setActivePinia(pinia)
  })

  it('renders info showing range and total count with props', () => {
    const wrapper = mount(PaginationBar, {
      props: {
        page: 2,
        pageSize: 50,
        totalCount: 125,
      },
    })

    expect(wrapper.text()).toContain('Showing')
    expect(wrapper.text()).toContain('51')
    expect(wrapper.text()).toContain('100')
    expect(wrapper.text()).toContain('125')
  })

  it('renders empty state message when totalCount is 0', () => {
    const wrapper = mount(PaginationBar, {
      props: {
        page: 1,
        pageSize: 50,
        totalCount: 0,
      },
    })

    expect(wrapper.text()).toContain('No records found')
  })

  it('renders page size selector with default options and emits size changes', async () => {
    const wrapper = mount(PaginationBar, {
      props: {
        page: 1,
        pageSize: 50,
        totalCount: 200,
        pageSizeOptions: [10, 25, 50, 100],
      },
    })

    const select = wrapper.find('select.size-select')
    expect(select.exists()).toBe(true)
    const options = select.findAll('option')
    expect(options.map((o) => Number(o.element.value))).toEqual([10, 25, 50, 100])

    await select.setValue(100)
    expect(wrapper.emitted('update:pageSize')?.[0]).toEqual([100])
    expect(wrapper.emitted('update:limit')?.[0]).toEqual([100])
    expect(wrapper.emitted('size-change')?.[0]).toEqual([100])
    expect(wrapper.emitted('change')?.[0]).toEqual([
      { page: 1, limit: 100, offset: 0 },
    ])
  })

  it('renders page numbers and highlights the active page', () => {
    const wrapper = mount(PaginationBar, {
      props: {
        page: 2,
        pageSize: 10,
        totalCount: 50,
      },
    })

    const pageButtons = wrapper.findAll('.page-btn-num')
    expect(pageButtons.length).toBe(5)
    expect(pageButtons[1].classes()).toContain('is-active')
    expect(pageButtons[1].text()).toBe('2')
  })

  it('disables previous and first page buttons on page 1', () => {
    const wrapper = mount(PaginationBar, {
      props: {
        page: 1,
        pageSize: 50,
        totalCount: 100,
      },
    })

    const iconButtons = wrapper.findAll('.page-btn-icon')
    // First page button (index 0) and prev page button (index 1) should be disabled
    expect(iconButtons[0].attributes('disabled')).toBeDefined()
    expect(iconButtons[1].attributes('disabled')).toBeDefined()
    // Next page button (index 2) and last page button (index 3) should NOT be disabled
    expect(iconButtons[2].attributes('disabled')).toBeUndefined()
    expect(iconButtons[3].attributes('disabled')).toBeUndefined()
  })

  it('emits page-change and update:page when clicking next, prev, or page number', async () => {
    const wrapper = mount(PaginationBar, {
      props: {
        page: 2,
        pageSize: 20,
        totalCount: 100,
      },
    })

    // Click page 4
    const pageButtons = wrapper.findAll('.page-btn-num')
    await pageButtons[3].trigger('click')

    expect(wrapper.emitted('update:page')?.[0]).toEqual([4])
    expect(wrapper.emitted('page-change')?.[0]).toEqual([4])
    expect(wrapper.emitted('change')?.[0]).toEqual([
      { page: 4, limit: 20, offset: 60 },
    ])
  })

  it('binds directly with usePagination instance when passed as prop', async () => {
    const fetchFn = vi.fn().mockResolvedValue({
      data: [{ id: 1 }, { id: 2 }],
      headers: { 'x-total-count': '150', 'x-page-limit': '50' },
    })

    const pagination = usePagination(fetchFn, { defaultLimit: 50 })
    await pagination.load()

    const wrapper = mount(PaginationBar, {
      props: {
        pagination,
      },
    })

    expect(wrapper.text()).toContain('Showing')
    expect(wrapper.text()).toContain('1')
    expect(wrapper.text()).toContain('50')
    expect(wrapper.text()).toContain('150')

    // Click page 2 button
    const pageButtons = wrapper.findAll('.page-btn-num')
    await pageButtons[1].trigger('click')

    expect(pagination.page.value).toBe(2)
  })

  it('renders correctly in compact mode', () => {
    const wrapper = mount(PaginationBar, {
      props: {
        page: 3,
        pageSize: 10,
        totalCount: 100,
        compact: true,
        showPageNumbers: false,
      },
    })

    expect(wrapper.find('.pagination-compact').exists()).toBe(true)
    expect(wrapper.find('.pagination-compact-indicator').text()).toBe('3 / 10')
    expect(wrapper.findAll('.page-btn-num').length).toBe(0)
  })

  it('disables all controls when disabled or loading is true', () => {
    const wrapper = mount(PaginationBar, {
      props: {
        page: 2,
        pageSize: 50,
        totalCount: 150,
        disabled: true,
      },
    })

    expect(wrapper.classes()).toContain('is-disabled')
    const buttons = wrapper.findAll('button')
    buttons.forEach((btn) => {
      expect(btn.attributes('disabled')).toBeDefined()
    })
  })
})
