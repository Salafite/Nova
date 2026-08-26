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

  it('supports v-model:modelValue and emits update:modelValue on page selection', async () => {
    const wrapper = mount(PaginationBar, {
      props: {
        modelValue: 3,
        pageSize: 10,
        totalCount: 50,
      },
    })

    const pageButtons = wrapper.findAll('.page-btn-num')
    expect(pageButtons[2].classes()).toContain('is-active')

    await pageButtons[4].trigger('click')
    expect(wrapper.emitted('update:modelValue')?.[0]).toEqual([5])
    expect(wrapper.emitted('page-change')?.[0]).toEqual([5])
  })

  it('calculates visible page numbers with ellipses for large page counts', () => {
    // 1. Middle page (page 10 of 20) -> should show first, ellipsis, neighbors, ellipsis, last
    const midWrapper = mount(PaginationBar, {
      props: {
        page: 10,
        pageSize: 10,
        totalCount: 200,
        maxVisibleButtons: 5,
      },
    })
    const midItems = midWrapper.findAll('.pagination-pages > *')
    const midTexts = midItems.map((item) => item.text())
    expect(midTexts).toContain('…')
    expect(midTexts[0]).toBe('1')
    expect(midTexts[midTexts.length - 1]).toBe('20')

    // 2. Start page (page 2 of 20) -> should show start numbers and ellipsis before last
    const startWrapper = mount(PaginationBar, {
      props: {
        page: 2,
        pageSize: 10,
        totalCount: 200,
        maxVisibleButtons: 5,
      },
    })
    const startItems = startWrapper.findAll('.pagination-pages > *')
    const startTexts = startItems.map((item) => item.text())
    expect(startTexts[0]).toBe('1')
    expect(startTexts).toContain('…')
    expect(startTexts[startTexts.length - 1]).toBe('20')

    // 3. End page (page 19 of 20) -> should show first, ellipsis, end numbers
    const endWrapper = mount(PaginationBar, {
      props: {
        page: 19,
        pageSize: 10,
        totalCount: 200,
        maxVisibleButtons: 5,
      },
    })
    const endItems = endWrapper.findAll('.pagination-pages > *')
    const endTexts = endItems.map((item) => item.text())
    expect(endTexts[0]).toBe('1')
    expect(endTexts[1]).toBe('…')
    expect(endTexts[endTexts.length - 1]).toBe('20')
  })

  it('navigates to first and last pages when first/last buttons are clicked', async () => {
    const wrapper = mount(PaginationBar, {
      props: {
        page: 3,
        pageSize: 10,
        totalCount: 100,
        showFirstLast: true,
      },
    })

    const iconButtons = wrapper.findAll('.page-btn-icon')
    // iconButtons: [first_page, prev_page, next_page, last_page]
    // Click first page (index 0)
    await iconButtons[0].trigger('click')
    expect(wrapper.emitted('page-change')?.[0]).toEqual([1])

    // Click last page (index 3)
    await iconButtons[3].trigger('click')
    expect(wrapper.emitted('page-change')?.[1]).toEqual([10])
  })

  it('automatically adds current limit into pageSizeOptions if not present', () => {
    const wrapper = mount(PaginationBar, {
      props: {
        page: 1,
        pageSize: 75,
        totalCount: 200,
        pageSizeOptions: [10, 25, 50, 100],
      },
    })

    const options = wrapper.findAll('select.size-select option')
    const optionValues = options.map((opt) => Number(opt.element.value))
    expect(optionValues).toContain(75)
    // Should be sorted
    expect(optionValues).toEqual([10, 25, 50, 75, 100])
  })

  it('hides elements when visibility props are set to false', () => {
    const wrapper = mount(PaginationBar, {
      props: {
        page: 1,
        pageSize: 50,
        totalCount: 100,
        showTotal: false,
        showPageSize: false,
        showFirstLast: false,
      },
    })

    expect(wrapper.find('.pagination-info').exists()).toBe(false)
    expect(wrapper.find('.pagination-size').exists()).toBe(false)
    // Only prev and next buttons in pagination-nav
    const iconButtons = wrapper.findAll('.page-btn-icon')
    expect(iconButtons.length).toBe(2)
  })
})
