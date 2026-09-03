/**
 * Barcode Parser Utility Module
 * Supports EAN-13, UPC-A, Code 128, and GS1-128 AI parsing.
 * Extracts GTIN, batch/lot numbers, expiration dates, serial numbers, etc.
 */

/**
 * Validates EAN-13 checksum using standard modulo 10 algorithm.
 * @param {string} code 
 * @returns {boolean}
 */
export function isValidEAN13(code) {
  if (!code || typeof code !== 'string' || !/^\d{13}$/.test(code)) {
    return false
  }
  let sum = 0
  for (let i = 0; i < 12; i++) {
    const digit = parseInt(code[i], 10)
    sum += (i % 2 === 0) ? digit : digit * 3
  }
  const calcCheckDigit = (10 - (sum % 10)) % 10
  return calcCheckDigit === parseInt(code[12], 10)
}

/**
 * Validates UPC-A checksum using standard modulo 10 algorithm.
 * @param {string} code 
 * @returns {boolean}
 */
export function isValidUPCA(code) {
  if (!code || typeof code !== 'string' || !/^\d{12}$/.test(code)) {
    return false
  }
  let sum = 0
  for (let i = 0; i < 11; i++) {
    const digit = parseInt(code[i], 10)
    sum += (i % 2 === 0) ? digit * 3 : digit
  }
  const calcCheckDigit = (10 - (sum % 10)) % 10
  return calcCheckDigit === parseInt(code[11], 10)
}

/**
 * Formats GS1 YYMMDD date string to ISO YYYY-MM-DD format.
 * If DD is '00', it defaults to the last day of the given month.
 * @param {string} yyMMdd 
 * @returns {string|null}
 */
export function formatGS1Date(yyMMdd) {
  if (!yyMMdd || typeof yyMMdd !== 'string' || !/^\d{6}$/.test(yyMMdd)) {
    return null
  }

  const yy = parseInt(yyMMdd.substring(0, 2), 10)
  const mm = parseInt(yyMMdd.substring(2, 4), 10)
  let dd = parseInt(yyMMdd.substring(4, 6), 10)

  if (mm < 1 || mm > 12) return null

  // GS1 rule: YY 51-99 => 19YY, YY 00-50 => 20YY
  const currentYearPrefix = new Date().getFullYear().toString().substring(0, 2)
  const year = yy > 50 ? 1900 + yy : parseInt(`${currentYearPrefix}${yy < 10 ? '0' + yy : yy}`, 10)

  // Handle DD = 00 (GS1 standard specifies last day of month)
  if (dd === 0) {
    dd = new Date(year, mm, 0).getDate()
  }

  // Validate day range
  const maxDaysInMonth = new Date(year, mm, 0).getDate()
  if (dd < 1 || dd > maxDaysInMonth) return null

  const formattedMonth = String(mm).padStart(2, '0')
  const formattedDay = String(dd).padStart(2, '0')

  return `${year}-${formattedMonth}-${formattedDay}`
}

/**
 * GS1 AI definitions configuration
 */
const GS1_AI_DEFINITIONS = [
  { ai: '01', name: 'gtin', length: 14, fixed: true, type: 'numeric' },
  { ai: '02', name: 'contentGtin', length: 14, fixed: true, type: 'numeric' },
  { ai: '10', name: 'batchNumber', length: 20, fixed: false, type: 'alphanumeric' },
  { ai: '11', name: 'productionDate', length: 6, fixed: true, type: 'date' },
  { ai: '12', name: 'dueDate', length: 6, fixed: true, type: 'date' },
  { ai: '13', name: 'packagingDate', length: 6, fixed: true, type: 'date' },
  { ai: '15', name: 'bestBeforeDate', length: 6, fixed: true, type: 'date' },
  { ai: '17', name: 'expiryDate', length: 6, fixed: true, type: 'date' },
  { ai: '21', name: 'serialNumber', length: 20, fixed: false, type: 'alphanumeric' },
  { ai: '30', name: 'quantity', length: 8, fixed: false, type: 'numeric' },
  { ai: '37', name: 'count', length: 8, fixed: false, type: 'numeric' }
]

/**
 * Helper to parse parenthesized GS1-128 strings like (01)0036000291452(10)LOT123(17)261231
 * @param {string} input 
 * @returns {Record<string, string>|null}
 */
function parseParenthesizedGS1(input) {
  const regex = /\((\d{2,4})\)([^()]+)/g
  let match
  const attributes = {}
  let count = 0

  while ((match = regex.exec(input)) !== null) {
    const ai = match[1]
    const value = match[2].trim()
    attributes[ai] = value
    count++
  }

  return count > 0 ? attributes : null
}

/**
 * Helper to parse raw stream GS1-128 string (with FNC1 ASCII 29 / \x1d delimiters or fixed lengths)
 * @param {string} input 
 * @returns {Record<string, string>|null}
 */
function parseStreamGS1(input) {
  // Strip GS1 symbology prefixes if present: ]C1, ]e0
  let cleanInput = input.replace(/^\][C|e][01]/, '')
  const attributes = {}
  let pos = 0
  let matchedAny = false

  while (pos < cleanInput.length) {
    // Check if remaining string starts with FNC1 character
    if (cleanInput.charCodeAt(pos) === 29 || cleanInput[pos] === '\u001d' || cleanInput[pos] === '\x1d') {
      pos++
      continue
    }

    let aiMatched = false
    for (const def of GS1_AI_DEFINITIONS) {
      if (cleanInput.startsWith(def.ai, pos)) {
        aiMatched = true
        pos += def.ai.length

        let value = ''
        if (def.fixed) {
          if (cleanInput.length - pos < def.length) {
            aiMatched = false
            break
          }
          value = cleanInput.substring(pos, pos + def.length)
          pos += def.length
        } else {
          // Variable length: until FNC1, next AI in parentheses, or max length
          let endPos = pos
          while (
            endPos < cleanInput.length &&
            (endPos - pos) < def.length &&
            cleanInput.charCodeAt(endPos) !== 29 &&
            cleanInput[endPos] !== '\u001d' &&
            cleanInput[endPos] !== '\x1d'
          ) {
            endPos++
          }
          value = cleanInput.substring(pos, endPos)
          pos = endPos
        }

        attributes[def.ai] = value
        matchedAny = true
        break
      }
    }

    if (!aiMatched) {
      // If AI match fails at current position, not a valid AI stream
      break
    }
  }

  return matchedAny ? attributes : null
}

/**
 * Main Barcode Parsing Function
 * Parses EAN-13, UPC-A, GS1-128, and Code 128 barcodes.
 * 
 * @param {string|number} rawInput 
 * @returns {Object} Parsed barcode result object
 */
export function parseBarcode(rawInput) {
  if (rawInput === null || rawInput === undefined) {
    return {
      raw: '',
      type: 'UNKNOWN',
      gtin: null,
      code: '',
      batchNumber: null,
      expiryDate: null,
      serialNumber: null,
      productionDate: null,
      bestBeforeDate: null,
      quantity: null,
      attributes: {},
      isValid: false
    }
  }

  const raw = String(rawInput).trim()
  if (!raw) {
    return {
      raw: '',
      type: 'UNKNOWN',
      gtin: null,
      code: '',
      batchNumber: null,
      expiryDate: null,
      serialNumber: null,
      productionDate: null,
      bestBeforeDate: null,
      quantity: null,
      attributes: {},
      isValid: false
    }
  }

  // 1. Check GS1-128 parenthesized format: e.g. (01)0036000291452(10)LOT123
  if (/^\(\d{2,4}\)/.test(raw)) {
    const attributes = parseParenthesizedGS1(raw)
    if (attributes) {
      const gtin = attributes['01'] || attributes['02'] || null
      const expiryDate = attributes['17'] ? formatGS1Date(attributes['17']) : null
      const productionDate = attributes['11'] ? formatGS1Date(attributes['11']) : null
      const bestBeforeDate = attributes['15'] ? formatGS1Date(attributes['15']) : null
      const batchNumber = attributes['10'] || null
      const serialNumber = attributes['21'] || null
      const quantity = attributes['30'] ? parseInt(attributes['30'], 10) : null

      return {
        raw,
        type: 'GS1-128',
        gtin,
        code: gtin || raw,
        batchNumber,
        expiryDate,
        serialNumber,
        productionDate,
        bestBeforeDate,
        quantity,
        attributes,
        isValid: true
      }
    }
  }

  // 2. Check GS1-128 stream/prefix format: e.g. ]C101003600029145210LOT123 or starting with 01 + 14 digits
  if (raw.startsWith(']C1') || raw.startsWith(']e0') || (raw.length > 16 && /^(01\d{14})/.test(raw))) {
    const attributes = parseStreamGS1(raw)
    if (attributes && (attributes['01'] || attributes['10'] || attributes['17'] || attributes['21'])) {
      const gtin = attributes['01'] || attributes['02'] || null
      const expiryDate = attributes['17'] ? formatGS1Date(attributes['17']) : null
      const productionDate = attributes['11'] ? formatGS1Date(attributes['11']) : null
      const bestBeforeDate = attributes['15'] ? formatGS1Date(attributes['15']) : null
      const batchNumber = attributes['10'] || null
      const serialNumber = attributes['21'] || null
      const quantity = attributes['30'] ? parseInt(attributes['30'], 10) : null

      return {
        raw,
        type: 'GS1-128',
        gtin,
        code: gtin || raw,
        batchNumber,
        expiryDate,
        serialNumber,
        productionDate,
        bestBeforeDate,
        quantity,
        attributes,
        isValid: true
      }
    }
  }

  // 3. Check EAN-13 format (13 numeric digits)
  if (/^\d{13}$/.test(raw)) {
    const validCheck = isValidEAN13(raw)
    return {
      raw,
      type: 'EAN-13',
      gtin: raw,
      code: raw,
      batchNumber: null,
      expiryDate: null,
      serialNumber: null,
      productionDate: null,
      bestBeforeDate: null,
      quantity: null,
      attributes: {},
      isValid: validCheck
    }
  }

  // 4. Check UPC-A format (12 numeric digits)
  if (/^\d{12}$/.test(raw)) {
    const validCheck = isValidUPCA(raw)
    return {
      raw,
      type: 'UPC-A',
      gtin: `00${raw}`, // 14-digit GTIN representation
      code: raw,
      batchNumber: null,
      expiryDate: null,
      serialNumber: null,
      productionDate: null,
      bestBeforeDate: null,
      quantity: null,
      attributes: {},
      isValid: validCheck
    }
  }

  // 5. Fallback: Code 128 / standard barcode
  return {
    raw,
    type: 'CODE-128',
    gtin: null,
    code: raw,
    batchNumber: null,
    expiryDate: null,
    serialNumber: null,
    productionDate: null,
    bestBeforeDate: null,
    quantity: null,
    attributes: {},
    isValid: true
  }
}
