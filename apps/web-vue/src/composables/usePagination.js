import { ref, computed, shallowRef } from 'vue'

/**
 * Parses RFC 5988 Link header format:
 * <http://localhost:8000/api/T0003I/?limit=50&offset=0>; rel="first", <http://...>; rel="next"
 *
 * @param {string} linkHeader
 * @returns {{ first: string|null, prev: string|null, next: string|null, last: string|null }}
 */
export function parseLinkHeader(linkHeader) {
  const result = { first: null, prev: null, next: null, last: null }
  if (!linkHeader || typeof linkHeader !== 'string') {
    return result
  }

  const linkRegex = /<([^>]+)>;\s*rel="?([a-zA-Z0-9_-]+)"?/g
  let match
  while ((match = linkRegex.exec(linkHeader)) !== null) {
    const [, url, rel] = match
    if (rel && Object.prototype.hasOwnProperty.call(result, rel)) {
      result[rel] = url
    }
  }
  return result
}

/**
 * Extracts pagination metadata (X-Total-Count, X-Page-Limit, X-Page-Offset, Link)
 * from response headers (AxiosHeaders, plain object, or Map-like headers).
 *
 * @param {object} headers
 * @returns {{ totalCount: number|null, limit: number|null, offset: number|null, links: object }}
 */
export function extractPaginationHeaders(headers) {
  if (!headers) {
    return { totalCount: null, limit: null, offset: null, links: { first: null, prev: null, next: null, last: null } }
  }

  const getHeader = (name) => {
    if (typeof headers.get === 'function') {
      const val = headers.get(name) || headers.get(name.toLowerCase())
      if (val !== undefined && val !== null) return val
    }
    const lowerName = name.toLowerCase()
    for (const key of Object.keys(headers)) {
      if (key.toLowerCase() === lowerName) {
        return headers[key]
      }
    }
    return undefined
  }

  const totalRaw = getHeader('x-total-count')
  const limitRaw = getHeader('x-page-limit')
  const offsetRaw = getHeader('x-page-offset')
  const linkRaw = getHeader('link')

  const parseNum = (val) => {
    if (val === undefined || val === null || val === '') return null
    const n = Number(val)
    return isNaN(n) ? null : n
  }

  const totalCount = parseNum(totalRaw)
  const limit = parseNum(limitRaw)
  const offset = parseNum(offsetRaw)
  const links = parseLinkHeader(linkRaw)

  return { totalCount, limit, offset, links }
}

/**
 * Formats order_by column and direction according to Nova ERP backend standards.
 *
 * @param {string|null} column
 * @param {'asc'|'desc'} direction
 * @returns {string|null}
 */
export function formatOrderBy(column, direction = 'asc') {
  if (!column || typeof column !== 'string' || !column.trim()) {
    return null
  }
  const cleanCol = column.trim()
  return direction === 'desc' ? `-${cleanCol}` : cleanCol
}

/**
 * Vue 3 composable for managing server-side pagination, sorting, headers,
 * query parameters, and infinite scrolling.
 *
 * @param {Function|object} [fetchFnOrOptions] - Async fetch function or options object
 * @param {object} [maybeOptions] - Options if fetch function was provided as first argument
 */
export function usePagination(fetchFnOrOptions = {}, maybeOptions = {}) {
  let fetchFn = null
  let options = {}

  if (typeof fetchFnOrOptions === 'function') {
    fetchFn = fetchFnOrOptions
    options = maybeOptions || {}
  } else if (typeof fetchFnOrOptions === 'object' && fetchFnOrOptions !== null) {
    options = fetchFnOrOptions
    fetchFn = options.fetchFn || options.fetch || null
  }

  const rawLimit = options.defaultLimit !== undefined ? options.defaultLimit : (options.pageSize !== undefined ? options.pageSize : 50)
  const parsedLimit = Number(rawLimit)
  const defaultLimit = Math.min(Math.max(1, isNaN(parsedLimit) ? 50 : parsedLimit), 500)

  const rawPage = options.defaultPage !== undefined ? options.defaultPage : 1
  const parsedPage = Number(rawPage)
  const defaultPage = Math.max(1, isNaN(parsedPage) ? 1 : parsedPage)

  const defaultOrderBy = options.defaultOrderBy || null
  const defaultOrderDir = options.defaultOrderDir === 'desc' ? 'desc' : 'asc'
  const isInfinite = ref(Boolean(options.infinite))
  const idKey = options.idKey || 'id'

  // Reactive State
  const items = ref([])
  const totalCount = ref(0)
  const page = ref(defaultPage)
  const limit = ref(defaultLimit)
  const orderBy = ref(defaultOrderBy)
  const orderDir = ref(defaultOrderDir)
  const loading = ref(false)
  const loadingMore = ref(false)
  const error = ref(null)
  const links = shallowRef({ first: null, prev: null, next: null, last: null })

  // Computed state
  const offset = computed(() => Math.max(0, (page.value - 1) * limit.value))
  const totalPages = computed(() => {
    if (!totalCount.value || totalCount.value <= 0) return 1
    return Math.max(1, Math.ceil(totalCount.value / (limit.value || 50)))
  })
  const hasNextPage = computed(() => page.value < totalPages.value)
  const hasPrevPage = computed(() => page.value > 1)
  const from = computed(() => (totalCount.value === 0 ? 0 : offset.value + 1))
  const to = computed(() => Math.min(offset.value + limit.value, totalCount.value))
  const isFirstPage = computed(() => page.value === 1)
  const isLastPage = computed(() => page.value >= totalPages.value)
  const isEmpty = computed(() => !loading.value && items.value.length === 0)

  const formattedOrderBy = computed(() => formatOrderBy(orderBy.value, orderDir.value))

  const queryParams = computed(() => {
    const params = {
      limit: limit.value,
      offset: offset.value,
    }
    if (formattedOrderBy.value) {
      params.order_by = formattedOrderBy.value
    }
    return params
  })

  /**
   * Updates state from an API response (Axios response or custom object).
   *
   * @param {object|Array} response
   */
  function setFromResponse(response) {
    if (!response) return

    let dataList = []
    let respHeaders = null

    if (Array.isArray(response)) {
      dataList = response
    } else if (response.data !== undefined) {
      dataList = Array.isArray(response.data) ? response.data : []
      respHeaders = response.headers
    } else if (Array.isArray(response.items)) {
      dataList = response.items
      respHeaders = response.headers
    }

    if (respHeaders) {
      const extracted = extractPaginationHeaders(respHeaders)
      if (extracted.totalCount !== null) {
        totalCount.value = extracted.totalCount
      } else if (response.total !== undefined) {
        totalCount.value = Number(response.total) || 0
      } else if (response.totalCount !== undefined) {
        totalCount.value = Number(response.totalCount) || 0
      } else {
        totalCount.value = dataList.length
      }

      if (extracted.limit !== null) {
        limit.value = Math.min(Math.max(1, extracted.limit), 500)
      }
      if (extracted.links) {
        links.value = extracted.links
      }
    } else if (response.total !== undefined) {
      totalCount.value = Number(response.total) || 0
    } else if (response.totalCount !== undefined) {
      totalCount.value = Number(response.totalCount) || 0
    } else {
      totalCount.value = dataList.length
    }

    if (isInfinite.value && page.value > 1) {
      // Append for infinite scroll, deduplicating by idKey if items are objects
      const existingIds = new Set(items.value.map((it) => (it && typeof it === 'object' ? it[idKey] : it)))
      const newItems = dataList.filter((it) => {
        const id = it && typeof it === 'object' ? it[idKey] : it
        return id === undefined || !existingIds.has(id)
      })
      items.value = [...items.value, ...newItems]
    } else {
      items.value = dataList
    }
  }

  /**
   * Main fetch method.
   *
   * @param {number|null} [targetPage=null]
   * @param {object} [extraParams={}]
   * @returns {Promise<any>}
   */
  async function load(targetPage = null, extraParams = {}) {
    if (targetPage !== null) {
      const pNum = Number(targetPage)
      if (!isNaN(pNum)) {
        page.value = Math.max(1, pNum)
      }
    }

    if (!fetchFn || typeof fetchFn !== 'function') {
      return items.value
    }

    loading.value = true
    error.value = null

    try {
      const params = {
        ...queryParams.value,
        ...extraParams,
      }
      const response = await fetchFn(params)
      setFromResponse(response)
      if (typeof options.onPageChange === 'function') {
        options.onPageChange(page.value)
      }
      return response
    } catch (err) {
      error.value = err?.message || 'Failed to load records'
      if (typeof options.onError === 'function') {
        options.onError(err)
      }
      throw err
    } finally {
      loading.value = false
      loadingMore.value = false
    }
  }

  /**
   * Loads next page and appends results (for infinite scroll).
   *
   * @param {object} [extraParams={}]
   * @returns {Promise<any>}
   */
  async function loadMore(extraParams = {}) {
    if (loading.value || loadingMore.value || !hasNextPage.value) {
      return
    }
    loadingMore.value = true
    page.value += 1
    return load(page.value, extraParams)
  }

  /**
   * Changes the current page number and triggers a fetch.
   *
   * @param {number} newPage
   * @param {object} [extraParams={}]
   */
  async function setPage(newPage, extraParams = {}) {
    const num = Number(newPage)
    const target = Math.max(1, Math.min(isNaN(num) ? 1 : num, totalPages.value))
    if (target === page.value && items.value.length > 0) return
    page.value = target
    return load(target, extraParams)
  }

  /**
   * Navigates to the next page.
   */
  async function nextPage(extraParams = {}) {
    if (hasNextPage.value) {
      return setPage(page.value + 1, extraParams)
    }
  }

  /**
   * Navigates to the previous page.
   */
  async function prevPage(extraParams = {}) {
    if (hasPrevPage.value) {
      return setPage(page.value - 1, extraParams)
    }
  }

  /**
   * Navigates to the first page.
   */
  async function firstPage(extraParams = {}) {
    return setPage(1, extraParams)
  }

  /**
   * Navigates to the last page.
   */
  async function lastPage(extraParams = {}) {
    return setPage(totalPages.value, extraParams)
  }

  /**
   * Updates the page size (limit) and reloads from page 1.
   *
   * @param {number} newLimit
   * @param {object} [extraParams={}]
   */
  async function setLimit(newLimit, extraParams = {}) {
    const num = Number(newLimit)
    const clamped = Math.min(Math.max(1, isNaN(num) ? 50 : num), 500)
    if (clamped === limit.value) return
    limit.value = clamped
    page.value = 1
    if (typeof options.onLimitChange === 'function') {
      options.onLimitChange(clamped)
    }
    return load(1, extraParams)
  }

  /**
   * Alias for setLimit.
   */
  const setPageSize = setLimit

  /**
   * Sets sorting column and direction, resets page to 1, and reloads.
   *
   * @param {string|null} column
   * @param {'asc'|'desc'} [direction='asc']
   * @param {object} [extraParams={}]
   */
  async function setSorting(column, direction = 'asc', extraParams = {}) {
    orderBy.value = column || null
    orderDir.value = direction === 'desc' ? 'desc' : 'asc'
    page.value = 1
    return load(1, extraParams)
  }

  /**
   * Toggles sort direction for a given column (asc -> desc -> asc), resets page to 1, and reloads.
   *
   * @param {string} column
   * @param {object} [extraParams={}]
   */
  async function toggleSort(column, extraParams = {}) {
    if (orderBy.value === column) {
      orderDir.value = orderDir.value === 'asc' ? 'desc' : 'asc'
    } else {
      orderBy.value = column
      orderDir.value = 'asc'
    }
    page.value = 1
    return load(1, extraParams)
  }

  /**
   * Resets pagination state to initial values.
   */
  function reset() {
    items.value = []
    totalCount.value = 0
    page.value = defaultPage
    limit.value = defaultLimit
    orderBy.value = defaultOrderBy
    orderDir.value = defaultOrderDir
    loading.value = false
    loadingMore.value = false
    error.value = null
    links.value = { first: null, prev: null, next: null, last: null }
  }

  if (options.immediate && fetchFn) {
    load()
  }

  return {
    // Reactive State
    items,
    totalCount,
    page,
    limit,
    pageSize: limit,
    offset,
    orderBy,
    orderDir,
    loading,
    loadingMore,
    error,
    links,
    isInfinite,

    // Computed Properties
    totalPages,
    hasNextPage,
    hasNext: hasNextPage,
    hasPrevPage,
    hasPrev: hasPrevPage,
    from,
    to,
    isFirstPage,
    isLastPage,
    isEmpty,
    queryParams,
    formattedOrderBy,

    // Methods
    load,
    loadMore,
    setPage,
    nextPage,
    prevPage,
    firstPage,
    lastPage,
    setLimit,
    setPageSize,
    setSorting,
    toggleSort,
    setFromResponse,
    reset,

    // Utilities
    extractPaginationHeaders,
    parseLinkHeader,
  }
}
