import 'fake-indexeddb/auto'
import { describe, it, expect, beforeEach } from 'vitest'
import {
  CatalogSearchEngine,
  PrefixTrie,
  tokenize,
  levenshteinDistance,
  catalogSearch
} from '../services/catalogSearch.js'
import { OfflineDb } from '../services/offlineDb.js'

describe('CatalogSearch Service', () => {
  let searchEngine
  const mockProducts = [
    {
      id: 1,
      sku: 'SKU-APPLES-01',
      barcode: '111222333444',
      name: 'Organic Honeycrisp Apples 1kg',
      description: 'Crisp and sweet fresh organic apples',
      category: 'Produce',
      category_id: 1,
      base_price: 3.99,
      available_qty: 120,
      warehouse_id: 1,
      is_active: true
    },
    {
      id: 2,
      sku: 'SKU-APPLES-02',
      barcode: '111222333555',
      name: 'Granny Smith Green Apples',
      description: 'Tart baking apples',
      category: 'Produce',
      category_id: 1,
      base_price: 2.49,
      available_qty: 0,
      warehouse_id: 1,
      is_active: true
    },
    {
      id: 3,
      sku: 'SKU-BANANAS-01',
      barcode: '999888777666',
      name: 'Cavendish Bananas Bunch',
      description: 'Fresh yellow bananas',
      category: 'Produce',
      category_id: 1,
      base_price: 1.29,
      available_qty: 250,
      warehouse_id: 1,
      is_active: true
    },
    {
      id: 4,
      sku: 'SKU-MILK-WHOLE',
      barcode: '444555666777',
      name: 'Organic Whole Milk 1L',
      description: 'Pasteurized grade A whole milk carton',
      category: 'Dairy',
      category_id: 2,
      base_price: 2.19,
      available_qty: 45,
      warehouse_id: 2,
      is_active: true
    },
    {
      id: 5,
      sku: 'SKU-MILK-OAT',
      barcode: '555666777888',
      name: 'Barista Oat Milk 1L',
      description: 'Plant-based oat beverage for coffee',
      category: 'Dairy Alternatives',
      category_id: 3,
      base_price: 3.49,
      available_qty: 80,
      warehouse_id: 2,
      is_active: true
    },
    {
      id: 6,
      sku: 'SKU-DISCONTINUED',
      barcode: '000000000000',
      name: 'Old Discontinued Item',
      description: 'No longer for sale',
      category: 'Misc',
      category_id: 99,
      base_price: 9.99,
      available_qty: 0,
      warehouse_id: 1,
      is_active: false
    }
  ]

  beforeEach(() => {
    searchEngine = new CatalogSearchEngine()
    searchEngine.buildIndex(mockProducts)
  })

  describe('Tokenization and Levenshtein Utilities', () => {
    it('tokenizes text correctly handling special characters and casing', () => {
      const tokens = tokenize('Organic Honeycrisp-Apples 1kg (Fresh!)')
      expect(tokens).toEqual(['organic', 'honeycrisp', 'apples', '1kg', 'fresh'])
    })

    it('handles empty and null tokens', () => {
      expect(tokenize('')).toEqual([])
      expect(tokenize(null)).toEqual([])
      expect(tokenize(undefined)).toEqual([])
    })

    it('calculates levenshtein edit distances with threshold', () => {
      expect(levenshteinDistance('apple', 'apple', 2)).toBe(0)
      expect(levenshteinDistance('apple', 'aple', 2)).toBe(1)
      expect(levenshteinDistance('apple', 'aplle', 2)).toBe(1)
      expect(levenshteinDistance('banana', 'banan', 2)).toBe(1)
      expect(levenshteinDistance('apple', 'orange', 2)).toBe(3) // > 2 returns 3 (maxDistance + 1)
    })
  })

  describe('Prefix Trie Indexer', () => {
    it('inserts and retrieves product IDs by prefix', () => {
      const trie = new PrefixTrie()
      trie.insert('SKU-APPLES-01', 1)
      trie.insert('SKU-APPLES-02', 2)
      trie.insert('SKU-BANANAS-01', 3)

      const apples = trie.searchPrefix('SKU-APP')
      expect(apples.has(1)).toBe(true)
      expect(apples.has(2)).toBe(true)
      expect(apples.has(3)).toBe(false)

      const bananas = trie.searchPrefix('SKU-BAN')
      expect(bananas.has(3)).toBe(true)
      expect(bananas.has(1)).toBe(false)
    })

    it('removes product IDs from trie', () => {
      const trie = new PrefixTrie()
      trie.insert('SKU-APPLES-01', 1)
      trie.insert('SKU-APPLES-02', 2)

      trie.remove('SKU-APPLES-01', 1)
      const matches = trie.searchPrefix('SKU-APP')
      expect(matches.has(1)).toBe(false)
      expect(matches.has(2)).toBe(true)
    })
  })

  describe('Exact Lookup Methods (O(1))', () => {
    it('looks up product by barcode directly', () => {
      const p = searchEngine.lookupBarcode('111222333444')
      expect(p).not.toBeNull()
      expect(p.id).toBe(1)
      expect(p.sku).toBe('SKU-APPLES-01')
    })

    it('falls back to SKU if barcode query is an exact SKU', () => {
      const p = searchEngine.lookupBarcode('SKU-BANANAS-01')
      expect(p).not.toBeNull()
      expect(p.id).toBe(3)
    })

    it('looks up product by exact SKU', () => {
      const p = searchEngine.lookupSku('sku-milk-whole')
      expect(p).not.toBeNull()
      expect(p.id).toBe(4)
      expect(p.name).toBe('Organic Whole Milk 1L')
    })

    it('returns null for non-existent barcode or SKU', () => {
      expect(searchEngine.lookupBarcode('999999999999')).toBeNull()
      expect(searchEngine.lookupSku('SKU-NON-EXISTENT')).toBeNull()
    })
  })

  describe('SKU Prefix Search', () => {
    it('searches products by SKU prefix', () => {
      const results = searchEngine.searchSkuPrefix('SKU-MILK')
      expect(results.length).toBe(2)
      const ids = results.map(r => r.id)
      expect(ids).toContain(4)
      expect(ids).toContain(5)
    })
  })

  describe('Multi-Token and Fuzzy Search', () => {
    it('matches multi-token queries across name and category', () => {
      const results = searchEngine.search('organic milk')
      expect(results.length).toBeGreaterThanOrEqual(1)
      expect(results[0].id).toBe(4) // Organic Whole Milk 1L
    })

    it('handles fuzzy typos in product name (e.g. "honeycris")', () => {
      const results = searchEngine.search('honeycris')
      expect(results.length).toBeGreaterThanOrEqual(1)
      expect(results[0].id).toBe(1)
    })

    it('ranks exact barcode and exact SKU highest', () => {
      const barcodeResults = searchEngine.search('999888777666')
      expect(barcodeResults[0].id).toBe(3)

      const skuResults = searchEngine.search('SKU-APPLES-02')
      expect(skuResults[0].id).toBe(2)
    })
  })

  describe('Filtering and Options', () => {
    it('filters by category', () => {
      const results = searchEngine.search('', { category: 'Produce' })
      expect(results.length).toBe(3)
      for (const r of results) {
        expect(r.category).toBe('Produce')
      }
    })

    it('filters by inStockOnly', () => {
      const inStock = searchEngine.search('apples', { inStockOnly: true })
      expect(inStock.length).toBe(1)
      expect(inStock[0].id).toBe(1) // Organic Honeycrisp has 120 qty, Granny Smith has 0
    })

    it('filters by warehouse_id', () => {
      const wh2 = searchEngine.search('', { warehouse_id: 2 })
      expect(wh2.length).toBe(2)
      expect(wh2.map(p => p.id).sort()).toEqual([4, 5])
    })

    it('filters by isActive status', () => {
      const activeOnly = searchEngine.search('', { isActive: true })
      expect(activeOnly.map(p => p.id)).not.toContain(6)
    })

    it('supports sorting by price ascending and descending', () => {
      const asc = searchEngine.search('', { sortBy: 'price_asc' })
      expect(asc[0].base_price).toBeLessThanOrEqual(asc[1].base_price)

      const desc = searchEngine.search('', { sortBy: 'price_desc' })
      expect(desc[0].base_price).toBeGreaterThanOrEqual(desc[1].base_price)
    })

    it('supports sorting by stock descending', () => {
      const stockSorted = searchEngine.search('', { sortBy: 'stock_desc' })
      expect(stockSorted[0].id).toBe(3) // Bananas 250 qty
    })

    it('supports pagination limit and offset', () => {
      const page1 = searchEngine.search('', { limit: 2, offset: 0, sortBy: 'name_asc' })
      const page2 = searchEngine.search('', { limit: 2, offset: 2, sortBy: 'name_asc' })

      expect(page1.length).toBe(2)
      expect(page2.length).toBe(2)
      expect(page1[0].id).not.toBe(page2[0].id)
    })
  })

  describe('Search With Meta & Category Aggregation', () => {
    it('returns structured metadata with execution time', () => {
      const meta = searchEngine.searchWithMeta('milk', { limit: 10 })
      expect(meta.query).toBe('milk')
      expect(meta.total).toBe(2)
      expect(meta.items.length).toBe(2)
      expect(typeof meta.executionTimeMs).toBe('number')
      expect(meta.executionTimeMs).toBeGreaterThanOrEqual(0)
    })

    it('aggregates unique categories with product counts', () => {
      const categories = searchEngine.getCategories()
      expect(categories.length).toBeGreaterThan(0)
      const produce = categories.find(c => c.name === 'Produce')
      expect(produce).toBeDefined()
      expect(produce.count).toBe(3)
    })
  })

  describe('Dynamic Index Updates', () => {
    it('adds a new product and makes it instantly searchable', () => {
      const newProduct = {
        id: 7,
        sku: 'SKU-ORANGE-VAL',
        barcode: '777888999000',
        name: 'Valencia Fresh Oranges 1kg',
        category: 'Produce',
        base_price: 2.79,
        available_qty: 90,
        is_active: true
      }

      searchEngine.addProduct(newProduct)
      expect(searchEngine.totalProducts).toBe(7)

      const found = searchEngine.lookupSku('SKU-ORANGE-VAL')
      expect(found).not.toBeNull()
      expect(found.id).toBe(7)

      const searchResults = searchEngine.search('valencia oranges')
      expect(searchResults.length).toBe(1)
      expect(searchResults[0].id).toBe(7)
    })

    it('updates an existing product', () => {
      const updated = {
        ...mockProducts[0],
        name: 'Super Organic Honeycrisp Apples Mega Pack',
        base_price: 5.99
      }

      searchEngine.updateProduct(updated)
      const found = searchEngine.getProductById(1)
      expect(found.name).toBe('Super Organic Honeycrisp Apples Mega Pack')
      expect(found.base_price).toBe(5.99)
    })

    it('removes a product from all index structures', () => {
      searchEngine.removeProduct(1)
      expect(searchEngine.getProductById(1)).toBeNull()
      expect(searchEngine.lookupBarcode('111222333444')).toBeNull()
      expect(searchEngine.lookupSku('SKU-APPLES-01')).toBeNull()

      const results = searchEngine.search('Honeycrisp')
      expect(results.length).toBe(0)
    })
  })

  describe('Loading from OfflineDb', () => {
    it('loads products directly from an OfflineDb instance', async () => {
      const testDb = new OfflineDb(`test_search_db_${Date.now()}`, 1)
      try {
        await testDb.saveProducts(mockProducts)

        const loadedEngine = new CatalogSearchEngine()
        const count = await loadedEngine.loadFromDb(testDb)
        expect(count).toBe(mockProducts.length)
        expect(loadedEngine.totalProducts).toBe(mockProducts.length)

        const searchRes = loadedEngine.search('Bananas')
        expect(searchRes.length).toBe(1)
        expect(searchRes[0].id).toBe(3)
      } finally {
        await testDb.deleteDatabase()
      }
    })
  })

  describe('Default Singleton Export', () => {
    it('exports catalogSearch singleton instance', () => {
      expect(catalogSearch).toBeDefined()
      expect(typeof catalogSearch.search).toBe('function')
      expect(typeof catalogSearch.lookupBarcode).toBe('function')
    })
  })
})
