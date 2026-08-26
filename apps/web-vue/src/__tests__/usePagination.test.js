import { describe, it, expect, vi, beforeEach } from 'vitest'
import {
  usePagination,
  parseLinkHeader,
  extractPaginationHeaders,
  formatOrderBy,
} from '../composables/usePagination.js'

describe('usePagination utilities', () => {
  describe('parseLinkHeader', () => {
    it('returns empty structure for invalid or empty input', () => {
      expect(parseLinkHeader(null)).toEqual({ first: null, prev: null, next: null, last: null })
      expect(parseLinkHeader('')).toEqual({ first: null, prev: null, next: null, last: null })
      expect(parseLinkHeader(123)).toEqual({ first: null, prev: null, next: null, last: null })
    })

    it('parses full RFC 5988 link headers', () => {
      const header = '<http://localhost/api/T0003I/?limit=50&offset=0>; rel="first", <http://localhost/api/T0003I/?limit=50&offset=0>; rel="prev", <http://localhost/api/T0003I/?limit=50&offset=100>; rel="next", <http://localhost/api/T0003I/?limit=50&offset=150>; rel="last"'
      const parsed = parseLinkHeader(header)
      expect(parsed.first).toBe('http://localhost/api/T0003I/?limit=50&offset=0')
      expect(parsed.prev).toBe('http://localhost/api/T0003I/?limit=50&offset=0')
      expect(parsed.next).toBe('http://localhost/api/T0003I/?limit=50&offset=100')
      expect(parsed.last).toBe('http://localhost/api/T0003I/?limit=50&offset=150')
    })

    it('handles unquoted and whitespace-varied rel values', () => {
      const header = '<https://api.novaerp.com/T0001I?offset=50>; rel=next, <https://api.novaerp.com/T0001I?offset=0>; rel=first'
      const parsed = parseLinkHeader(header)
      expect(parsed.next).toBe('https://api.novaerp.com/T0001I?offset=50')
      expect(parsed.first).toBe('https://api.novaerp.com/T0001I?offset=0')
      expect(parsed.prev).toBeNull()
    })
  })

  describe('extractPaginationHeaders', () => {
    it('returns nulls for missing headers', () => {
      expect(extractPaginationHeaders(null)).toEqual({
        totalCount: null,
        limit: null,
        offset: null,
        links: { first: null, prev: null, next: null, last: null },
      })
    })

    it('extracts headers case-insensitively from standard object', () => {
      const headers = {
        'x-total-count': '250',
        'x-page-limit': '50',
        'x-page-offset': '100',
        'link': '<http://api/?offset=0>; rel="first"',
      }
      const res = extractPaginationHeaders(headers)
      expect(res.totalCount).toBe(250)
      expect(res.limit).toBe(50)
      expect(res.offset).toBe(100)
      expect(res.links.first).toBe('http://api/?offset=0')
    })

    it('extracts headers from AxiosHeaders or get() enabled object', () => {
      const headers = {
        get: (key) => {
          if (key.toLowerCase() === 'x-total-count') return '42'
          if (key.toLowerCase() === 'x-page-limit') return '10'
          if (key.toLowerCase() === 'x-page-offset') return '0'
          return null
        },
      }
      const res = extractPaginationHeaders(headers)
      expect(res.totalCount).toBe(42)
      expect(res.limit).toBe(10)
      expect(res.offset).toBe(0)
    })
  })

  describe('formatOrderBy', () => {
    it('returns null for empty/invalid column', () => {
      expect(formatOrderBy(null)).toBeNull()
      expect(formatOrderBy('')).toBeNull()
      expect(formatOrderBy('   ')).toBeNull()
    })

    it('formats ascending and descending sort columns', () => {
      expect(formatOrderBy('sku', 'asc')).toBe('sku')
      expect(formatOrderBy('sku', 'desc')).toBe('-sku')
      expect(formatOrderBy(' created_at ', 'desc')).toBe('-created_at')
    })
  })
})

describe('usePagination composable', () => {
  it('initializes with default values', () => {
    const pagination = usePagination()

    expect(pagination.page.value).toBe(1)
    expect(pagination.limit.value).toBe(50)
    expect(pagination.pageSize.value).toBe(50)
    expect(pagination.offset.value).toBe(0)
    expect(pagination.totalCount.value).toBe(0)
    expect(pagination.totalPages.value).toBe(1)
    expect(pagination.hasNextPage.value).toBe(false)
    expect(pagination.hasPrevPage.value).toBe(false)
    expect(pagination.from.value).toBe(0)
    expect(pagination.to.value).toBe(0)
    expect(pagination.isFirstPage.value).toBe(true)
    expect(pagination.isLastPage.value).toBe(true)
    expect(pagination.isEmpty.value).toBe(true)
    expect(pagination.queryParams.value).toEqual({ limit: 50, offset: 0 })
  })

  it('accepts custom initial options', () => {
    const pagination = usePagination({
      defaultLimit: 25,
      defaultPage: 3,
      defaultOrderBy: 'created_at',
      defaultOrderDir: 'desc',
    })

    expect(pagination.page.value).toBe(3)
    expect(pagination.limit.value).toBe(25)
    expect(pagination.offset.value).toBe(50)
    expect(pagination.orderBy.value).toBe('created_at')
    expect(pagination.orderDir.value).toBe('desc')
    expect(pagination.queryParams.value).toEqual({
      limit: 25,
      offset: 50,
      order_by: '-created_at',
    })
  })

  it('fetches data and updates reactive state from Axios response', async () => {
    const mockData = [{ id: 1, name: 'Product A' }, { id: 2, name: 'Product B' }]
    const mockHeaders = {
      'x-total-count': '100',
      'x-page-limit': '50',
      'x-page-offset': '0',
      'link': '<http://api/?limit=50&offset=50>; rel="next"',
    }

    const fetchFn = vi.fn().mockResolvedValue({
      data: mockData,
      headers: mockHeaders,
    })

    const pagination = usePagination(fetchFn)
    await pagination.load()

    expect(fetchFn).toHaveBeenCalledWith({ limit: 50, offset: 0 })
    expect(pagination.items.value).toEqual(mockData)
    expect(pagination.totalCount.value).toBe(100)
    expect(pagination.totalPages.value).toBe(2)
    expect(pagination.hasNextPage.value).toBe(true)
    expect(pagination.hasPrevPage.value).toBe(false)
    expect(pagination.from.value).toBe(1)
    expect(pagination.to.value).toBe(50)
    expect(pagination.links.value.next).toBe('http://api/?limit=50&offset=50')
  })

  it('handles navigation methods (nextPage, prevPage, setPage, firstPage, lastPage)', async () => {
    const fetchFn = vi.fn().mockResolvedValue({
      data: [{ id: 1 }],
      headers: { 'x-total-count': '150', 'x-page-limit': '50' },
    })

    const pagination = usePagination(fetchFn)
    await pagination.load()

    expect(pagination.page.value).toBe(1)
    expect(pagination.totalPages.value).toBe(3)

    // Next page
    await pagination.nextPage()
    expect(pagination.page.value).toBe(2)
    expect(pagination.offset.value).toBe(50)

    // Next page
    await pagination.nextPage()
    expect(pagination.page.value).toBe(3)
    expect(pagination.hasNextPage.value).toBe(false)
    expect(pagination.hasPrevPage.value).toBe(true)

    // Prev page
    await pagination.prevPage()
    expect(pagination.page.value).toBe(2)

    // First page
    await pagination.firstPage()
    expect(pagination.page.value).toBe(1)

    // Last page
    await pagination.lastPage()
    expect(pagination.page.value).toBe(3)

    // Direct setPage
    await pagination.setPage(2)
    expect(pagination.page.value).toBe(2)
  })

  it('updates limit and resets page to 1 on setLimit / setPageSize', async () => {
    const fetchFn = vi.fn().mockResolvedValue({
      data: [],
      headers: { 'x-total-count': '200' },
    })

    const pagination = usePagination(fetchFn)
    await pagination.load(3)
    expect(pagination.page.value).toBe(3)

    await pagination.setLimit(100)
    expect(pagination.limit.value).toBe(100)
    expect(pagination.page.value).toBe(1)
    expect(fetchFn).toHaveBeenLastCalledWith({ limit: 100, offset: 0 })
  })

  it('clamps limit between 1 and 500', async () => {
    const pagination = usePagination({ defaultLimit: 1000 })
    expect(pagination.limit.value).toBe(500)

    await pagination.setLimit(0)
    expect(pagination.limit.value).toBe(1)

    await pagination.setLimit(800)
    expect(pagination.limit.value).toBe(500)
  })

  it('handles sorting with setSorting and toggleSort', async () => {
    const fetchFn = vi.fn().mockResolvedValue({ data: [], headers: { 'x-total-count': '10' } })
    const pagination = usePagination(fetchFn)

    await pagination.setSorting('name', 'asc')
    expect(pagination.orderBy.value).toBe('name')
    expect(pagination.orderDir.value).toBe('asc')
    expect(pagination.queryParams.value.order_by).toBe('name')

    await pagination.toggleSort('name')
    expect(pagination.orderDir.value).toBe('desc')
    expect(pagination.queryParams.value.order_by).toBe('-name')

    await pagination.toggleSort('price')
    expect(pagination.orderBy.value).toBe('price')
    expect(pagination.orderDir.value).toBe('asc')
    expect(pagination.queryParams.value.order_by).toBe('price')
  })

  it('supports infinite scrolling with loadMore and deduplication', async () => {
    let call = 0
    const fetchFn = vi.fn().mockImplementation(() => {
      call++
      if (call === 1) {
        return Promise.resolve({
          data: [{ id: 1, name: 'Item 1' }, { id: 2, name: 'Item 2' }],
          headers: { 'x-total-count': '4', 'x-page-limit': '2' },
        })
      } else {
        return Promise.resolve({
          data: [{ id: 2, name: 'Item 2' }, { id: 3, name: 'Item 3' }, { id: 4, name: 'Item 4' }],
          headers: { 'x-total-count': '4', 'x-page-limit': '2' },
        })
      }
    })

    const pagination = usePagination({
      fetchFn,
      defaultLimit: 2,
      infinite: true,
    })

    await pagination.load()
    expect(pagination.items.value).toHaveLength(2)

    await pagination.loadMore()
    expect(pagination.page.value).toBe(2)
    // Item 2 should not be duplicated
    expect(pagination.items.value).toEqual([
      { id: 1, name: 'Item 1' },
      { id: 2, name: 'Item 2' },
      { id: 3, name: 'Item 3' },
      { id: 4, name: 'Item 4' },
    ])
  })

  it('handles API errors gracefully and updates error ref', async () => {
    const errorCallback = vi.fn()
    const fetchFn = vi.fn().mockRejectedValue(new Error('Network error'))

    const pagination = usePagination({
      fetchFn,
      onError: errorCallback,
    })

    await expect(pagination.load()).rejects.toThrow('Network error')
    expect(pagination.error.value).toBe('Network error')
    expect(pagination.loading.value).toBe(false)
    expect(errorCallback).toHaveBeenCalled()
  })

  it('resets state correctly with reset()', () => {
    const pagination = usePagination({ defaultLimit: 25, defaultPage: 1 })
    pagination.items.value = [{ id: 1 }]
    pagination.totalCount.value = 50
    pagination.page.value = 2
    pagination.orderBy.value = 'name'

    pagination.reset()
    expect(pagination.items.value).toEqual([])
    expect(pagination.totalCount.value).toBe(0)
    expect(pagination.page.value).toBe(1)
    expect(pagination.limit.value).toBe(25)
    expect(pagination.orderBy.value).toBeNull()
  })

  it('triggers immediate load when immediate: true', () => {
    const fetchFn = vi.fn().mockResolvedValue({ data: [{ id: 1 }], headers: { 'x-total-count': '1' } })
    usePagination({
      fetchFn,
      immediate: true,
    })

    expect(fetchFn).toHaveBeenCalledWith({ limit: 50, offset: 0 })
  })

  it('invokes onPageChange and onLimitChange callbacks', async () => {
    const onPageChange = vi.fn()
    const onLimitChange = vi.fn()
    const fetchFn = vi.fn().mockResolvedValue({ data: [{ id: 1 }], headers: { 'x-total-count': '100' } })

    const pagination = usePagination({
      fetchFn,
      onPageChange,
      onLimitChange,
    })

    await pagination.load()
    await pagination.setPage(2)
    expect(onPageChange).toHaveBeenCalledWith(2)

    await pagination.setLimit(100)
    expect(onLimitChange).toHaveBeenCalledWith(100)
  })

  it('handles various response structures in setFromResponse', () => {
    const pagination = usePagination()

    // 1. Plain array
    pagination.setFromResponse([{ id: 1 }, { id: 2 }])
    expect(pagination.items.value).toEqual([{ id: 1 }, { id: 2 }])
    expect(pagination.totalCount.value).toBe(2)

    // 2. Object with items and totalCount
    pagination.setFromResponse({ items: [{ id: 3 }], totalCount: 40 })
    expect(pagination.items.value).toEqual([{ id: 3 }])
    expect(pagination.totalCount.value).toBe(40)

    // 3. Object with data and total
    pagination.setFromResponse({ data: [{ id: 4 }], total: 50 })
    expect(pagination.items.value).toEqual([{ id: 4 }])
    expect(pagination.totalCount.value).toBe(50)

    // 4. Null / undefined response
    pagination.setFromResponse(null)
    expect(pagination.items.value).toEqual([{ id: 4 }])
  })

  it('passes extra parameters through load, nextPage, and setPage', async () => {
    const fetchFn = vi.fn().mockResolvedValue({ data: [], headers: { 'x-total-count': '100' } })
    const pagination = usePagination(fetchFn)

    await pagination.load(1, { search: 'bolt', category_id: 5 })
    expect(fetchFn).toHaveBeenLastCalledWith({
      limit: 50,
      offset: 0,
      search: 'bolt',
      category_id: 5,
    })

    await pagination.nextPage({ filter: 'active' })
    expect(fetchFn).toHaveBeenLastCalledWith({
      limit: 50,
      offset: 50,
      filter: 'active',
    })
  })

  it('prevents navigation beyond boundaries', async () => {
    const fetchFn = vi.fn().mockResolvedValue({ data: [{ id: 1 }], headers: { 'x-total-count': '50' } })
    const pagination = usePagination(fetchFn)
    await pagination.load()

    expect(pagination.totalPages.value).toBe(1)
    expect(pagination.hasNextPage.value).toBe(false)
    expect(pagination.hasPrevPage.value).toBe(false)

    // Calling nextPage when hasNextPage is false should not fetch
    fetchFn.mockClear()
    await pagination.nextPage()
    expect(fetchFn).not.toHaveBeenCalled()

    // Calling prevPage when hasPrevPage is false should not fetch
    await pagination.prevPage()
    expect(fetchFn).not.toHaveBeenCalled()
  })

  it('supports custom idKey for infinite scrolling deduplication', async () => {
    let call = 0
    const fetchFn = vi.fn().mockImplementation(() => {
      call++
      if (call === 1) {
        return Promise.resolve({
          data: [{ code: 'SKU-1', name: 'Item 1' }, { code: 'SKU-2', name: 'Item 2' }],
          headers: { 'x-total-count': '3', 'x-page-limit': '2' },
        })
      } else {
        return Promise.resolve({
          data: [{ code: 'SKU-2', name: 'Item 2' }, { code: 'SKU-3', name: 'Item 3' }],
          headers: { 'x-total-count': '3', 'x-page-limit': '2' },
        })
      }
    })

    const pagination = usePagination({
      fetchFn,
      defaultLimit: 2,
      infinite: true,
      idKey: 'code',
    })

    await pagination.load()
    expect(pagination.items.value).toHaveLength(2)

    await pagination.loadMore()
    expect(pagination.items.value).toEqual([
      { code: 'SKU-1', name: 'Item 1' },
      { code: 'SKU-2', name: 'Item 2' },
      { code: 'SKU-3', name: 'Item 3' },
    ])
  })

  it('aliases hasNext and hasPrev correctly', async () => {
    const fetchFn = vi.fn().mockResolvedValue({
      data: [{ id: 1 }],
      headers: { 'x-total-count': '100', 'x-page-limit': '50' },
    })

    const pagination = usePagination(fetchFn)
    await pagination.load()

    expect(pagination.hasNext.value).toBe(true)
    expect(pagination.hasPrev.value).toBe(false)

    await pagination.nextPage()
    expect(pagination.hasNext.value).toBe(false)
    expect(pagination.hasPrev.value).toBe(true)
  })
})
