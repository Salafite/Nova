import { describe, it, expect } from 'vitest'
import {
  parseBarcode,
  isValidEAN13,
  isValidUPCA,
  formatGS1Date
} from '../utils/barcodeParser'

describe('barcodeParser Utility', () => {
  describe('isValidEAN13', () => {
    it('returns true for valid EAN-13 barcode', () => {
      expect(isValidEAN13('4006381333931')).toBe(true)
      expect(isValidEAN13('1234567890128')).toBe(true)
    })

    it('returns false for invalid check digit', () => {
      expect(isValidEAN13('4006381333932')).toBe(false)
    })

    it('returns false for invalid lengths or non-numeric strings', () => {
      expect(isValidEAN13('123456')).toBe(false)
      expect(isValidEAN13('40063813339310')).toBe(false)
      expect(isValidEAN13('abc4006381333')).toBe(false)
      expect(isValidEAN13(null)).toBe(false)
    })
  })

  describe('isValidUPCA', () => {
    it('returns true for valid UPC-A barcode', () => {
      expect(isValidUPCA('012345678905')).toBe(true)
      expect(isValidUPCA('639382000393')).toBe(true)
    })

    it('returns false for invalid check digit', () => {
      expect(isValidUPCA('012345678904')).toBe(false)
    })

    it('returns false for invalid lengths or non-numeric strings', () => {
      expect(isValidUPCA('012345')).toBe(false)
      expect(isValidUPCA('0123456789055')).toBe(false)
      expect(isValidUPCA(null)).toBe(false)
    })
  })

  describe('formatGS1Date', () => {
    it('formats YYMMDD to YYYY-MM-DD ISO string', () => {
      expect(formatGS1Date('251231')).toBe('2025-12-31')
      expect(formatGS1Date('260515')).toBe('2026-05-15')
    })

    it('handles DD = 00 as the last day of month', () => {
      expect(formatGS1Date('250200')).toBe('2025-02-28')
      expect(formatGS1Date('251200')).toBe('2025-12-31')
    })

    it('formats YY > 50 as 19YY', () => {
      expect(formatGS1Date('991231')).toBe('1999-12-31')
      expect(formatGS1Date('750615')).toBe('1975-06-15')
    })

    it('returns null for invalid day range in month', () => {
      expect(formatGS1Date('250231')).toBeNull() // Feb 31 invalid
      expect(formatGS1Date('250431')).toBeNull() // April 31 invalid
    })

    it('returns null for invalid month or format', () => {
      expect(formatGS1Date('251301')).toBeNull() // month 13 invalid
      expect(formatGS1Date('123')).toBeNull()
      expect(formatGS1Date(null)).toBeNull()
    })
  })

  describe('parseBarcode', () => {
    it('handles null, undefined or empty input', () => {
      const res = parseBarcode(null)
      expect(res.isValid).toBe(false)
      expect(res.type).toBe('UNKNOWN')

      const resEmpty = parseBarcode('')
      expect(resEmpty.isValid).toBe(false)
      expect(resEmpty.type).toBe('UNKNOWN')

      const resUndef = parseBarcode(undefined)
      expect(resUndef.isValid).toBe(false)
      expect(resUndef.type).toBe('UNKNOWN')
    })

    it('parses valid EAN-13 barcode', () => {
      const res = parseBarcode('4006381333931')
      expect(res.type).toBe('EAN-13')
      expect(res.code).toBe('4006381333931')
      expect(res.gtin).toBe('4006381333931')
      expect(res.isValid).toBe(true)
    })

    it('marks invalid EAN-13 checksum as isValid false', () => {
      const res = parseBarcode('4006381333932')
      expect(res.type).toBe('EAN-13')
      expect(res.code).toBe('4006381333932')
      expect(res.isValid).toBe(false)
    })

    it('parses valid UPC-A barcode', () => {
      const res = parseBarcode('012345678905')
      expect(res.type).toBe('UPC-A')
      expect(res.code).toBe('012345678905')
      expect(res.gtin).toBe('00012345678905')
      expect(res.isValid).toBe(true)
    })

    it('marks invalid UPC-A checksum as isValid false', () => {
      const res = parseBarcode('012345678904')
      expect(res.type).toBe('UPC-A')
      expect(res.code).toBe('012345678904')
      expect(res.isValid).toBe(false)
    })

    it('parses parenthesized GS1-128 barcode with GTIN, batch, expiry, serial, production date, best before date, and quantity', () => {
      const input = '(01)00036000291452(10)LOT998877(17)261231(21)SN123456(11)250101(15)260630(30)50'
      const res = parseBarcode(input)

      expect(res.type).toBe('GS1-128')
      expect(res.gtin).toBe('00036000291452')
      expect(res.batchNumber).toBe('LOT998877')
      expect(res.expiryDate).toBe('2026-12-31')
      expect(res.serialNumber).toBe('SN123456')
      expect(res.productionDate).toBe('2025-01-01')
      expect(res.bestBeforeDate).toBe('2026-06-30')
      expect(res.quantity).toBe(50)
      expect(res.isValid).toBe(true)
      expect(res.attributes['01']).toBe('00036000291452')
    })

    it('parses stream GS1-128 barcode with symbology prefix and FNC1 delimiter', () => {
      const input = ']C1010003600029145210LOT998877\x1d1726123121SN123456'
      const res = parseBarcode(input)

      expect(res.type).toBe('GS1-128')
      expect(res.gtin).toBe('00036000291452')
      expect(res.batchNumber).toBe('LOT998877')
      expect(res.expiryDate).toBe('2026-12-31')
      expect(res.serialNumber).toBe('SN123456')
      expect(res.isValid).toBe(true)
    })

    it('parses stream GS1-128 starting with 01 prefix without symbology header', () => {
      const input = '010003600029145210LOT998877'
      const res = parseBarcode(input)

      expect(res.type).toBe('GS1-128')
      expect(res.gtin).toBe('00036000291452')
      expect(res.batchNumber).toBe('LOT998877')
      expect(res.isValid).toBe(true)
    })

    it('parses standard Code 128 alphanumeric barcode', () => {
      const res = parseBarcode('SKU-WIDGET-001')
      expect(res.type).toBe('CODE-128')
      expect(res.code).toBe('SKU-WIDGET-001')
      expect(res.gtin).toBeNull()
      expect(res.batchNumber).toBeNull()
      expect(res.isValid).toBe(true)
    })
  })
})
