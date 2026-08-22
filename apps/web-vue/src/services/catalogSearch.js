/**
 * Nova ERP - Field Sales Mobile Fast Catalog Search Engine
 * Zero-latency in-memory SKU, Barcode, Multi-token Fuzzy Search & Prefix Trie Indexer
 */

import { offlineDb } from './offlineDb.js'

/**
 * Tokenize and normalize text for fast inverted indexing & token matching
 */
export function tokenize(text) {
  if (!text || typeof text !== 'string') return []
  return text
    .toLowerCase()
    .normalize('NFKD')
    .replace(/[^\w\s-]/g, ' ')
    .split(/[\s-]+/)
    .map(t => t.trim())
    .filter(t => t.length > 0)
}

/**
 * Fast Levenshtein distance with early-cutoff max distance threshold
 */
export function levenshteinDistance(str1, str2, maxDistance = 2) {
  if (str1 === str2) return 0
  const len1 = str1.length
  const len2 = str2.length
  if (Math.abs(len1 - len2) > maxDistance) return maxDistance + 1
  if (len1 === 0) return len2 <= maxDistance ? len2 : maxDistance + 1
  if (len2 === 0) return len1 <= maxDistance ? len1 : maxDistance + 1

  let prevRow = new Array(len2 + 1)
  let currRow = new Array(len2 + 1)

  for (let j = 0; j <= len2; j++) {
    prevRow[j] = j
  }

  for (let i = 1; i <= len1; i++) {
    currRow[0] = i
    let minInRow = currRow[0]

    for (let j = 1; j <= len2; j++) {
      const cost = str1[i - 1] === str2[j - 1] ? 0 : 1
      currRow[j] = Math.min(
        prevRow[j] + 1,       // deletion
        currRow[j - 1] + 1,   // insertion
        prevRow[j - 1] + cost // substitution
      )
      if (currRow[j] < minInRow) {
        minInRow = currRow[j]
      }
    }

    if (minInRow > maxDistance) {
      return maxDistance + 1
    }

    const temp = prevRow
    prevRow = currRow
    currRow = temp
  }

  return prevRow[len2]
}

/**
 * Trie node for fast prefix search
 */
class TrieNode {
  constructor() {
    this.children = new Map()
    this.productIds = new Set()
    this.isEndOfWord = false
  }
}

/**
 * Prefix Trie for instantaneous prefix lookups (e.g. SKU and tokens)
 */
export class PrefixTrie {
  constructor() {
    this.root = new TrieNode()
  }

  insert(word, productId) {
    if (!word || typeof word !== 'string') return
    const normalized = word.toLowerCase().trim()
    if (!normalized) return

    let current = this.root
    current.productIds.add(productId)

    for (let i = 0; i < normalized.length; i++) {
      const char = normalized[i]
      if (!current.children.has(char)) {
        current.children.set(char, new TrieNode())
      }
      current = current.children.get(char)
      current.productIds.add(productId)
    }
    current.isEndOfWord = true
  }

  searchPrefix(prefix) {
    if (!prefix || typeof prefix !== 'string') return new Set()
    const normalized = prefix.toLowerCase().trim()
    if (!normalized) return new Set()

    let current = this.root
    for (let i = 0; i < normalized.length; i++) {
      const char = normalized[i]
      if (!current.children.has(char)) {
        return new Set()
      }
      current = current.children.get(char)
    }
    return new Set(current.productIds)
  }

  remove(word, productId) {
    if (!word || typeof word !== 'string') return
    const normalized = word.toLowerCase().trim()
    if (!normalized) return

    const stack = [this.root]
    let current = this.root

    for (let i = 0; i < normalized.length; i++) {
      const char = normalized[i]
      if (!current.children.has(char)) return
      current = current.children.get(char)
      stack.push(current)
    }

    for (const node of stack) {
      node.productIds.delete(productId)
    }
  }

  clear() {
    this.root = new TrieNode()
  }
}

/**
 * In-Memory Zero-Latency Catalog Search Engine
 */
export class CatalogSearchEngine {
  constructor() {
    this.products = []
    this.productMap = new Map()
    this.skuMap = new Map()
    this.barcodeMap = new Map()
    this.skuTrie = new PrefixTrie()
    this.tokenTrie = new PrefixTrie()
    this.categoryMap = new Map()
    this.isInitialized = false
  }

  /**
   * Build in-memory index from a list of products
   */
  buildIndex(products = []) {
    this.clear()
    if (!products || !products.length) {
      this.isInitialized = true
      return
    }

    for (const p of products) {
      this._indexProduct(p)
    }

    this.isInitialized = true
  }

  /**
   * Alias for buildIndex
   */
  init(products = []) {
    return this.buildIndex(products)
  }

  /**
   * Load products directly from IndexedDB offline storage
   */
  async loadFromDb(db = offlineDb) {
    if (!db || typeof db.getAllProducts !== 'function') {
      throw new Error('Valid OfflineDb instance required to load catalog')
    }
    const products = await db.getAllProducts()
    this.buildIndex(products)
    return this.products.length
  }

  /**
   * Index an individual product item
   */
  _indexProduct(product) {
    if (!product || product.id === undefined || product.id === null) return

    const p = { ...product }
    p._searchTokens = tokenize(`${p.name || ''} ${p.sku || ''} ${p.category || ''} ${p.description || ''} ${p.uom_code || ''}`)

    this.products.push(p)
    this.productMap.set(p.id, p)

    // Index SKU
    if (p.sku) {
      const normSku = String(p.sku).toLowerCase().trim()
      this.skuMap.set(normSku, p)
      this.skuTrie.insert(normSku, p.id)
    }

    // Index Barcode (primary + secondary array if present)
    if (p.barcode) {
      const normBarcode = String(p.barcode).toLowerCase().trim()
      this.barcodeMap.set(normBarcode, p)
    }
    if (Array.isArray(p.barcodes)) {
      for (const bc of p.barcodes) {
        if (bc) {
          this.barcodeMap.set(String(bc).toLowerCase().trim(), p)
        }
      }
    }

    // Index Tokens in Prefix Trie
    for (const token of p._searchTokens) {
      this.tokenTrie.insert(token, p.id)
    }

    // Index Category
    if (p.category) {
      const normCat = String(p.category).toLowerCase().trim()
      if (!this.categoryMap.has(normCat)) {
        this.categoryMap.set(normCat, new Set())
      }
      this.categoryMap.get(normCat).add(p.id)
    }
  }

  /**
   * Fast O(1) exact barcode lookup with fallback to SKU
   */
  lookupBarcode(barcode) {
    if (!barcode) return null
    const norm = String(barcode).toLowerCase().trim()
    if (!norm) return null

    if (this.barcodeMap.has(norm)) {
      return this.barcodeMap.get(norm)
    }
    if (this.skuMap.has(norm)) {
      return this.skuMap.get(norm)
    }
    return null
  }

  /**
   * Fast O(1) exact SKU lookup
   */
  lookupSku(sku) {
    if (!sku) return null
    const norm = String(sku).toLowerCase().trim()
    return this.skuMap.get(norm) || null
  }

  /**
   * Fast prefix search on SKU
   */
  searchSkuPrefix(prefix, limit = 20) {
    if (!prefix) return []
    const norm = String(prefix).toLowerCase().trim()
    const productIds = this.skuTrie.searchPrefix(norm)
    const results = []
    for (const id of productIds) {
      const p = this.productMap.get(id)
      if (p) results.push(p)
      if (limit > 0 && results.length >= limit) break
    }
    return results
  }

  /**
   * Get product by ID
   */
  getProductById(id) {
    return this.productMap.get(id) || null
  }

  /**
   * Main Search Method
   * Fast multi-token matching, fuzzy tolerance, category and stock filtering
   * Returns sorted array of products
   */
  search(query = '', options = {}) {
    const {
      category = '',
      category_id = null,
      warehouse_id = null,
      inStockOnly = false,
      minStock = null,
      isActive = undefined,
      limit = 50,
      offset = 0,
      sortBy = 'relevance'
    } = options

    const rawQuery = (query || '').trim()
    const normQuery = rawQuery.toLowerCase()
    const queryTokens = tokenize(rawQuery)

    let candidates = []

    if (!rawQuery) {
      // No query string - filter all indexed products
      candidates = this.products.filter(p => this._matchesFilters(p, options))
    } else {
      // Evaluate products with scoring
      const scoredItems = []

      for (const p of this.products) {
        if (!this._matchesFilters(p, options)) {
          continue
        }

        const score = this._calculateScore(p, normQuery, queryTokens)
        if (score > 0) {
          scoredItems.push({
            product: p,
            score
          })
        }
      }

      // Sort scored items
      this._sortScoredItems(scoredItems, sortBy)

      candidates = scoredItems.map(item => item.product)
    }

    // Sort if not already sorted by relevance (e.g. for empty query or explicit sort)
    if (!rawQuery || sortBy !== 'relevance') {
      this._sortProducts(candidates, sortBy)
    }

    // Apply pagination
    if (limit > 0 || offset > 0) {
      const start = Math.max(0, offset)
      const end = limit > 0 ? start + limit : undefined
      return candidates.slice(start, end)
    }

    return candidates
  }

  /**
   * Search with execution metadata (total count, execution time in ms)
   */
  searchWithMeta(query = '', options = {}) {
    const startTime = typeof performance !== 'undefined' ? performance.now() : Date.now()
    const allMatching = this.search(query, { ...options, limit: 0, offset: 0 })
    const total = allMatching.length
    const limit = options.limit !== undefined ? options.limit : 50
    const offset = options.offset || 0

    const items = limit > 0 ? allMatching.slice(offset, offset + limit) : allMatching.slice(offset)
    const endTime = typeof performance !== 'undefined' ? performance.now() : Date.now()

    return {
      items,
      total,
      query: query || '',
      executionTimeMs: Math.round((endTime - startTime) * 100) / 100
    }
  }

  /**
   * Filter check for category, stock level, warehouse, and active status
   */
  _matchesFilters(p, options) {
    const { category, category_id, warehouse_id, inStockOnly, minStock, isActive } = options

    // Active status check
    if (isActive !== undefined && p.is_active !== undefined && p.is_active !== isActive) {
      return false
    }

    // Category string check
    if (category && category !== 'all') {
      const pCat = (p.category || '').toLowerCase()
      if (pCat !== category.toLowerCase()) return false
    }

    // Category ID check
    if (category_id !== null && category_id !== undefined) {
      if (p.category_id !== category_id) return false
    }

    // Stock available check
    const stockQty = p.available_qty !== undefined ? p.available_qty : (p.stock_quantity || 0)
    if (inStockOnly && stockQty <= 0) {
      return false
    }
    if (minStock !== null && minStock !== undefined && stockQty < minStock) {
      return false
    }

    // Warehouse check
    if (warehouse_id !== null && warehouse_id !== undefined) {
      if (p.warehouse_id !== undefined && p.warehouse_id !== warehouse_id) {
        if (p.warehouse_stock && p.warehouse_stock[String(warehouse_id)] !== undefined) {
          if (inStockOnly && p.warehouse_stock[String(warehouse_id)] <= 0) return false
        } else {
          return false
        }
      }
    }

    return true
  }

  /**
   * Calculate relevance score for a product against query
   */
  _calculateScore(p, normQuery, queryTokens) {
    let score = 0
    let matchedTokensCount = 0

    const normSku = p.sku ? String(p.sku).toLowerCase().trim() : ''
    const normBarcode = p.barcode ? String(p.barcode).toLowerCase().trim() : ''
    const normName = p.name ? String(p.name).toLowerCase() : ''

    // 1. Exact full query matches
    if (normBarcode && normBarcode === normQuery) {
      score += 1500
      matchedTokensCount = queryTokens.length
    } else if (normSku && normSku === normQuery) {
      score += 1200
      matchedTokensCount = queryTokens.length
    } else if (normSku && normSku.startsWith(normQuery)) {
      score += 800
      matchedTokensCount = Math.max(matchedTokensCount, 1)
    } else if (normSku && normSku.includes(normQuery)) {
      score += 600
      matchedTokensCount = Math.max(matchedTokensCount, 1)
    }

    if (normName === normQuery) {
      score += 900
      matchedTokensCount = queryTokens.length
    } else if (normName.startsWith(normQuery)) {
      score += 700
      matchedTokensCount = Math.max(matchedTokensCount, 1)
    } else if (normName.includes(normQuery)) {
      score += 500
      matchedTokensCount = Math.max(matchedTokensCount, 1)
    }

    // 2. Token-level matching
    const productTokens = p._searchTokens || []

    for (const qToken of queryTokens) {
      let bestTokenScore = 0

      // SKU matches
      if (normSku) {
        if (normSku === qToken) {
          bestTokenScore = Math.max(bestTokenScore, 150)
        } else if (normSku.startsWith(qToken)) {
          bestTokenScore = Math.max(bestTokenScore, 100)
        } else if (normSku.includes(qToken)) {
          bestTokenScore = Math.max(bestTokenScore, 60)
        }
      }

      // Barcode matches
      if (normBarcode && normBarcode.includes(qToken)) {
        bestTokenScore = Math.max(bestTokenScore, 120)
      }

      // Name and token matches
      for (const pToken of productTokens) {
        if (pToken === qToken) {
          bestTokenScore = Math.max(bestTokenScore, 100)
          break
        } else if (pToken.startsWith(qToken)) {
          bestTokenScore = Math.max(bestTokenScore, 75)
        } else if (pToken.includes(qToken)) {
          bestTokenScore = Math.max(bestTokenScore, 40)
        } else if (qToken.length >= 3 && pToken.length >= 3) {
          const maxDist = qToken.length <= 4 ? 1 : 2
          const dist = levenshteinDistance(qToken, pToken, maxDist)
          if (dist <= maxDist) {
            const fuzzyScore = dist === 1 ? 35 : 20
            bestTokenScore = Math.max(bestTokenScore, fuzzyScore)
          }
        }
      }

      if (bestTokenScore > 0) {
        score += bestTokenScore
        matchedTokensCount++
      }
    }

    // If no tokens or full-query matches occurred at all, score is 0
    if (score === 0 || matchedTokensCount === 0) {
      return 0
    }

    // Multi-token query requires at least 1 match, with bonus for full coverage
    if (queryTokens.length > 1) {
      if (matchedTokensCount === queryTokens.length) {
        score += 300 // All tokens matched
      }
    }

    // Stock availability bonus (only for matching products)
    const stockQty = p.available_qty !== undefined ? p.available_qty : (p.stock_quantity || 0)
    if (stockQty > 0) {
      score += 10
    }

    return score
  }

  /**
   * Sort scored items by score descending, then name ascending
   */
  _sortScoredItems(items, sortBy) {
    if (sortBy === 'relevance') {
      items.sort((a, b) => {
        if (b.score !== a.score) return b.score - a.score
        return (a.product.name || '').localeCompare(b.product.name || '')
      })
    } else {
      items.sort((a, b) => {
        return this._compareProducts(a.product, b.product, sortBy)
      })
    }
  }

  /**
   * Sort products array
   */
  _sortProducts(products, sortBy) {
    products.sort((a, b) => this._compareProducts(a, b, sortBy))
  }

  /**
   * Product comparator helper
   */
  _compareProducts(a, b, sortBy) {
    switch (sortBy) {
      case 'name_asc':
        return (a.name || '').localeCompare(b.name || '')
      case 'name_desc':
        return (b.name || '').localeCompare(a.name || '')
      case 'price_asc': {
        const priceA = a.base_price !== undefined ? a.base_price : (a.price || 0)
        const priceB = b.base_price !== undefined ? b.base_price : (b.price || 0)
        return priceA - priceB
      }
      case 'price_desc': {
        const priceA = a.base_price !== undefined ? a.base_price : (a.price || 0)
        const priceB = b.base_price !== undefined ? b.base_price : (b.price || 0)
        return priceB - priceA
      }
      case 'stock_desc': {
        const stockA = a.available_qty !== undefined ? a.available_qty : (a.stock_quantity || 0)
        const stockB = b.available_qty !== undefined ? b.available_qty : (b.stock_quantity || 0)
        return stockB - stockA
      }
      case 'sku_asc':
        return (a.sku || '').localeCompare(b.sku || '')
      default:
        return (a.name || '').localeCompare(b.name || '')
    }
  }

  /**
   * Get unique categories with product counts
   */
  getCategories() {
    const categoryCounts = new Map()
    for (const p of this.products) {
      const cat = p.category || 'Uncategorized'
      categoryCounts.set(cat, (categoryCounts.get(cat) || 0) + 1)
    }
    return Array.from(categoryCounts.entries())
      .map(([name, count]) => ({ name, count }))
      .sort((a, b) => a.name.localeCompare(b.name))
  }

  /**
   * Add or replace product in memory
   */
  addProduct(product) {
    if (!product || product.id === undefined) return
    this.removeProduct(product.id)
    this._indexProduct(product)
  }

  /**
   * Update existing product in index
   */
  updateProduct(product) {
    this.addProduct(product)
  }

  /**
   * Remove product from in-memory index
   */
  removeProduct(productId) {
    const existing = this.productMap.get(productId)
    if (!existing) return

    this.productMap.delete(productId)
    this.products = this.products.filter(p => p.id !== productId)

    if (existing.sku) {
      const normSku = String(existing.sku).toLowerCase().trim()
      this.skuMap.delete(normSku)
      this.skuTrie.remove(normSku, productId)
    }

    if (existing.barcode) {
      const normBarcode = String(existing.barcode).toLowerCase().trim()
      this.barcodeMap.delete(normBarcode)
    }

    if (existing._searchTokens) {
      for (const token of existing._searchTokens) {
        this.tokenTrie.remove(token, productId)
      }
    }

    if (existing.category) {
      const normCat = String(existing.category).toLowerCase().trim()
      const catSet = this.categoryMap.get(normCat)
      if (catSet) {
        catSet.delete(productId)
        if (catSet.size === 0) {
          this.categoryMap.delete(normCat)
        }
      }
    }
  }

  /**
   * Clear all indexed data
   */
  clear() {
    this.products = []
    this.productMap.clear()
    this.skuMap.clear()
    this.barcodeMap.clear()
    this.skuTrie.clear()
    this.tokenTrie.clear()
    this.categoryMap.clear()
    this.isInitialized = false
  }

  /**
   * Total number of indexed products
   */
  get size() {
    return this.products.length
  }

  get totalProducts() {
    return this.products.length
  }
}

// Default singleton instance
export const catalogSearch = new CatalogSearchEngine()
export default catalogSearch
