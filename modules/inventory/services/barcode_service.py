import re
from typing import List, Dict, Any, Optional, Tuple
import psycopg2.extras
from packages.database.connection import get_connection, release_connection
from modules.core.context import get_current_tenant


def parse_gs1_weight_ai(ai: str, val: str) -> Tuple[Optional[float], Optional[str], Optional[str]]:
    """
    Parse GS1 weight Application Identifiers:
      3100-3105: Net weight in kilograms (AI 310d, d=0..5 decimal places)
      3200-3205: Net weight in pounds (lbs) (AI 320d, d=0..5 decimal places)
      3300-3305: Gross weight in kilograms (AI 330d, d=0..5 decimal places)
      3400-3405: Gross weight in pounds (lbs) (AI 340d, d=0..5 decimal places)
    Returns: (weight, uom, weight_type)
    """
    if not ai or len(ai) != 4:
        return None, None, None

    prefix = ai[:3]
    try:
        decimals = int(ai[3])
    except (ValueError, IndexError):
        return None, None, None

    # Clean digits from val (GS1 standard is 6 digits)
    digits_only = re.sub(r'\D', '', val)
    if not digits_only:
        return None, None, None

    # Take first 6 digits or length
    num_str = digits_only[:6]
    try:
        raw_int = int(num_str)
        divisor = 10 ** decimals
        weight = round(raw_int / divisor, decimals if decimals > 0 else 0)
    except Exception:
        return None, None, None

    if prefix == '310':
        return weight, 'kg', 'net'
    elif prefix == '320':
        return weight, 'lbs', 'net'
    elif prefix == '330':
        return weight, 'kg', 'gross'
    elif prefix == '340':
        return weight, 'lbs', 'gross'

    return None, None, None


def parse_scale_barcode(raw: str) -> Optional[Dict[str, Any]]:
    """
    Parse in-store / scale embedded variable-weight barcodes:
    - EAN-13 variable weight (13 digits starting with 20-29 or 02)
    - UPC-A variable weight (12 digits starting with 2)
    """
    if not raw:
        return None
    raw_str = str(raw).strip()

    # EAN-13 Scale Barcode (13 digits)
    if re.match(r'^(2[0-9]|02)\d{11}$', raw_str):
        # Format 1: 20 + 4-5 digit item + 5-4 digit weight + 1 check digit
        prefix = raw_str[:2]
        # Common standard: 2 digits prefix + 4 or 5 digits item code + 5 or 4 digits weight
        # 5-digit weight in grams / 3 decimals (e.g. 01250 -> 1.250 kg)
        item_code_5 = raw_str[2:7]
        weight_digits_5 = raw_str[7:12]
        
        item_code_4 = raw_str[2:6]
        weight_digits_6 = raw_str[6:12]

        try:
            # Default standard for 5-digit weight: 3 decimals (grams to kg)
            weight_val = round(int(weight_digits_5) / 1000.0, 3)
        except Exception:
            weight_val = None

        item_candidates = [
            f"{prefix}{item_code_5}",
            item_code_5,
            f"{prefix}{item_code_4}",
            item_code_4,
            f"{prefix}{item_code_5}000000",
            f"{prefix}{item_code_4}0000000",
            f"0{prefix}{item_code_5}000000",
            f"0{prefix}{item_code_4}0000000",
        ]

        return {
            'type': 'SCALE-EAN13',
            'item_code': item_code_5,
            'weight': weight_val,
            'weight_uom': 'kg',
            'weight_type': 'net',
            'candidates': item_candidates
        }

    # UPC-A Scale Barcode (12 digits starting with 2)
    if re.match(r'^2\d{11}$', raw_str):
        item_code = raw_str[1:6]  # 5 digit item code
        weight_digits = raw_str[6:11]  # 5 digit weight or price (often 2 decimals in US/lbs)

        try:
            # Standard US grocery weight: 2 decimal places (e.g. 00550 -> 5.50 lbs)
            # or 3 decimal places (e.g. 00550 -> 0.550 lbs). 2 decimals is most standard for retail lbs.
            weight_val = round(int(weight_digits) / 100.0, 2)
        except Exception:
            weight_val = None

        item_candidates = [
            f"2{item_code}",
            item_code,
            f"2{item_code}000000",
            f"002{item_code}000000",
            f"02{item_code}000000",
        ]

        return {
            'type': 'SCALE-UPCA',
            'item_code': item_code,
            'weight': weight_val,
            'weight_uom': 'lbs',
            'weight_type': 'net',
            'candidates': item_candidates
        }

    return None


def parse_barcode_string(raw: str) -> Dict[str, Any]:
    """
    Parse a barcode string into structured metadata and search candidates.
    Supports EAN-13, UPC-A, Code 128, GS1-128 (GTIN, batch, expiry, serial, scale weight),
    and in-store variable-weight scale barcodes (EAN-13 prefix 20-29, UPC-A prefix 2).
    """
    if not raw:
        return {
            'raw': '',
            'type': 'UNKNOWN',
            'gtin': None,
            'code': '',
            'batch_number': None,
            'expiry_date': None,
            'serial_number': None,
            'weight': None,
            'catch_weight_actual': None,
            'weight_uom': None,
            'weight_type': None,
            'item_code': None,
            'price': None,
            'candidates': []
        }

    raw_str = str(raw).strip()
    candidates = []
    if raw_str:
        candidates.append(raw_str)

    parsed_gtin = None
    batch_number = None
    expiry_date = None
    serial_number = None
    weight = None
    weight_uom = None
    weight_type = None
    item_code = None
    price = None
    barcode_type = 'CODE-128'

    # 1. GS1-128 parenthesized format: e.g. (01)00614141000039(3102)001250(10)LOT123(17)261231
    if re.match(r'^\(\d{2,4}\)', raw_str):
        barcode_type = 'GS1-128'
        pairs = re.findall(r'\((\d{2,4})\)([^()]+)', raw_str)
        ai_dict = {ai: val.strip() for ai, val in pairs}

        if '01' in ai_dict:
            parsed_gtin = ai_dict['01']
        elif '02' in ai_dict:
            parsed_gtin = ai_dict['02']

        if '10' in ai_dict:
            batch_number = ai_dict['10']
        if '17' in ai_dict:
            expiry_date = ai_dict['17']
        elif '15' in ai_dict:
            expiry_date = ai_dict['15']
        if '21' in ai_dict:
            serial_number = ai_dict['21']

        # Check for weight AIs (310x, 320x, 330x, 340x)
        for ai, val in ai_dict.items():
            if len(ai) == 4 and ai[:3] in ('310', '320', '330', '340'):
                w, uom, wt_type = parse_gs1_weight_ai(ai, val)
                if w is not None:
                    weight = w
                    weight_uom = uom
                    weight_type = wt_type
                    break
            elif len(ai) == 4 and ai[:3] == '392':
                try:
                    dec = int(ai[3])
                    price = round(int(re.sub(r'\D', '', val)) / (10 ** dec), dec)
                except Exception:
                    pass

    # 2. GS1-128 stream/prefix format: e.g. ]C10100614141000039... or 0100614141000039... (length >= 16)
    elif raw_str.startswith(']C1') or raw_str.startswith(']e0') or raw_str.startswith(']d2') or raw_str.startswith(']Q3') or (len(raw_str) >= 16 and raw_str.startswith('01') and raw_str[2:16].isdigit()):
        barcode_type = 'GS1-128'
        clean = re.sub(r'^\][CeQd][0123]', '', raw_str)

        if clean.startswith('01') and len(clean) >= 16 and clean[2:16].isdigit():
            parsed_gtin = clean[2:16]
            rem = clean[16:]

            # Split by FNC1 group separators if present
            if '\x1d' in rem or '\u001d' in rem or '<GS>' in rem:
                parts = [p for p in re.split(r'[\x1d\u001d]|<GS>', rem) if p]
                for part in parts:
                    if part.startswith('10'):
                        batch_number = part[2:]
                    elif part.startswith('17') and len(part) >= 8 and part[2:8].isdigit():
                        expiry_date = part[2:8]
                    elif part.startswith('15') and len(part) >= 8 and part[2:8].isdigit():
                        expiry_date = part[2:8]
                    elif part.startswith('21'):
                        serial_number = part[2:]
                    elif len(part) >= 10 and part[:3] in ('310', '320', '330', '340') and part[:4].isdigit():
                        w, uom, wt_type = parse_gs1_weight_ai(part[:4], part[4:10])
                        if w is not None:
                            weight = w
                            weight_uom = uom
                            weight_type = wt_type
            else:
                # Step-through parsing of continuous GS1 stream
                idx = 0
                while idx < len(rem):
                    # Check 4-digit weight AIs
                    if idx + 4 <= len(rem) and rem[idx:idx+3] in ('310', '320', '330', '340') and rem[idx:idx+4].isdigit():
                        ai = rem[idx:idx+4]
                        val = rem[idx+4:idx+10]
                        w, uom, wt_type = parse_gs1_weight_ai(ai, val)
                        if w is not None:
                            weight = w
                            weight_uom = uom
                            weight_type = wt_type
                        idx += 10
                    # Check 2-digit fixed dates (17, 15, 11)
                    elif idx + 8 <= len(rem) and rem[idx:idx+2] in ('17', '15', '11', '12', '13') and rem[idx+2:idx+8].isdigit():
                        if rem[idx:idx+2] in ('17', '15'):
                            expiry_date = rem[idx+2:idx+8]
                        idx += 8
                    # Check variable AI (10 - batch)
                    elif rem[idx:idx+2] == '10':
                        batch_rem = rem[idx+2:]
                        # Look for next AI pattern like 17yymmdd or 310x
                        m_next = re.search(r'(17\d{6}|15\d{6}|310\d{7}|320\d{7}|21\w+)', batch_rem)
                        if m_next:
                            batch_number = batch_rem[:m_next.start()]
                            idx += 2 + m_next.start()
                        else:
                            batch_number = batch_rem
                            idx = len(rem)
                    # Check variable AI (21 - serial)
                    elif rem[idx:idx+2] == '21':
                        serial_number = rem[idx+2:]
                        idx = len(rem)
                    else:
                        idx += 1

    # 3. Variable-weight scale barcodes (EAN-13 20-29/02 or UPC-A 2)
    elif re.match(r'^(2[0-9]|02)\d{11}$', raw_str) or re.match(r'^2\d{11}$', raw_str):
        scale_info = parse_scale_barcode(raw_str)
        if scale_info:
            barcode_type = scale_info['type']
            weight = scale_info.get('weight')
            weight_uom = scale_info.get('weight_uom')
            weight_type = scale_info.get('weight_type')
            item_code = scale_info.get('item_code')
            if scale_info.get('candidates'):
                candidates.extend(scale_info['candidates'])
            if len(raw_str) == 13:
                parsed_gtin = raw_str
            elif len(raw_str) == 12:
                parsed_gtin = f"00{raw_str}"

    # 4. Standard EAN-13 format (13 digits)
    elif re.match(r'^\d{13}$', raw_str):
        barcode_type = 'EAN-13'
        parsed_gtin = raw_str

    # 5. Standard UPC-A format (12 digits)
    elif re.match(r'^\d{12}$', raw_str):
        barcode_type = 'UPC-A'
        parsed_gtin = f"00{raw_str}"

    if parsed_gtin and parsed_gtin not in candidates:
        candidates.append(parsed_gtin)

    # Generate GTIN / UPC / EAN normalized candidates
    for candidate in list(candidates):
        if re.match(r'^\d{14}$', candidate):
            if candidate.startswith('00'):
                upc_candidate = candidate[2:]
                if upc_candidate not in candidates:
                    candidates.append(upc_candidate)
            if candidate.startswith('0'):
                ean_candidate = candidate[1:]
                if ean_candidate not in candidates:
                    candidates.append(ean_candidate)
        elif re.match(r'^\d{12}$', candidate):
            gtin14 = f"00{candidate}"
            ean13 = f"0{candidate}"
            if gtin14 not in candidates:
                candidates.append(gtin14)
            if ean13 not in candidates:
                candidates.append(ean13)
        elif re.match(r'^\d{13}$', candidate):
            gtin14 = f"0{candidate}"
            if gtin14 not in candidates:
                candidates.append(gtin14)
            if candidate.startswith('0'):
                upc12 = candidate[1:]
                if upc12 not in candidates:
                    candidates.append(upc12)

    deduped_candidates = []
    for c in candidates:
        if c not in deduped_candidates:
            deduped_candidates.append(c)

    return {
        'raw': raw_str,
        'type': barcode_type,
        'gtin': parsed_gtin,
        'code': parsed_gtin or raw_str,
        'batch_number': batch_number,
        'expiry_date': expiry_date,
        'serial_number': serial_number,
        'weight': weight,
        'catch_weight_actual': weight,
        'weight_uom': weight_uom,
        'weight_type': weight_type,
        'item_code': item_code,
        'price': price,
        'candidates': deduped_candidates
    }


def verify_scale_barcode(barcode_str: str, nominal_weight: Optional[float] = None, tolerance_pct: Optional[float] = None) -> Dict[str, Any]:
    """
    Validate and evaluate a scale barcode against expected nominal weight and tolerance.
    """
    parsed = parse_barcode_string(barcode_str)
    actual_weight = parsed.get('weight')
    
    variance_pct = None
    tolerance_status = 'Not Applicable'
    if actual_weight is not None and nominal_weight is not None and float(nominal_weight) > 0:
        nom_val = float(nominal_weight)
        act_val = float(actual_weight)
        variance_pct = round(((act_val - nom_val) / nom_val) * 100.0, 2)
        tol_limit = float(tolerance_pct) if tolerance_pct is not None else 0.0
        if abs(variance_pct) <= (tol_limit + 1e-6):
            tolerance_status = 'Within Tolerance'
        else:
            tolerance_status = 'Out of Tolerance'
    elif actual_weight is not None:
        tolerance_status = 'Within Tolerance'

    return {
        'raw_barcode': barcode_str,
        'parsed_barcode': parsed,
        'actual_weight': actual_weight,
        'weight_uom': parsed.get('weight_uom'),
        'nominal_weight': nominal_weight,
        'tolerance_pct': tolerance_pct,
        'variance_pct': variance_pct,
        'tolerance_status': tolerance_status,
        'has_scale_weight': actual_weight is not None,
    }


def find_product_by_barcode(conn, barcode_str: str, tenant_id: Optional[int] = None) -> Optional[Dict[str, Any]]:
    """
    Looks up a product by barcode string (EAN-13, UPC-A, Code 128, GS1-128 GTIN, or scale barcode).
    Searches both t0003 (Products) and t0004 (Product Barcodes).
    """
    info = parse_barcode_string(barcode_str)
    candidates = info['candidates']
    if not candidates:
        return None

    if tenant_id is None:
        tenant_id = get_current_tenant()

    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        if tenant_id is not None:
            cur.execute("""
                SELECT DISTINCT p.*
                FROM "Nova".t0003 p
                LEFT JOIN "Nova".t0004 b ON b.product_id = p.id AND (b.business_id = %s OR b.business_id IS NULL)
                WHERE (p.business_id = %s OR p.business_id IS NULL)
                  AND (
                    p.barcode = ANY(%s)
                    OR p.sku = ANY(%s)
                    OR b.barcode = ANY(%s)
                  )
                LIMIT 1
            """, (tenant_id, tenant_id, candidates, candidates, candidates))
        else:
            cur.execute("""
                SELECT DISTINCT p.*
                FROM "Nova".t0003 p
                LEFT JOIN "Nova".t0004 b ON b.product_id = p.id
                WHERE p.barcode = ANY(%s)
                   OR p.sku = ANY(%s)
                   OR b.barcode = ANY(%s)
                LIMIT 1
            """, (candidates, candidates, candidates))

        row = cur.fetchone()
        if row:
            res = dict(row)
            res['_parsed_barcode'] = info
            return res
    return None


def find_barcode_record(conn, barcode_str: str, tenant_id: Optional[int] = None) -> Optional[Dict[str, Any]]:
    """
    Looks up a barcode record (from t0004 or t0003) by barcode string.
    """
    info = parse_barcode_string(barcode_str)
    candidates = info['candidates']
    if not candidates:
        return None

    if tenant_id is None:
        tenant_id = get_current_tenant()

    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        if tenant_id is not None:
            cur.execute("""
                SELECT b.*, p.sku as product_sku, p.name as product_name
                FROM "Nova".t0004 b
                JOIN "Nova".t0003 p ON p.id = b.product_id
                WHERE (b.business_id = %s OR b.business_id IS NULL)
                  AND b.barcode = ANY(%s)
                LIMIT 1
            """, (tenant_id, candidates))
        else:
            cur.execute("""
                SELECT b.*, p.sku as product_sku, p.name as product_name
                FROM "Nova".t0004 b
                JOIN "Nova".t0003 p ON p.id = b.product_id
                WHERE b.barcode = ANY(%s)
                LIMIT 1
            """, (candidates,))

        row = cur.fetchone()
        if row:
            res = dict(row)
            res['_parsed_barcode'] = info
            return res

        if tenant_id is not None:
            cur.execute("""
                SELECT p.id as product_id, p.barcode as barcode, 'EAN13' as barcode_type, true as is_primary,
                       p.business_id, p.sku as product_sku, p.name as product_name
                FROM "Nova".t0003 p
                WHERE (p.business_id = %s OR p.business_id IS NULL)
                  AND (p.barcode = ANY(%s) OR p.sku = ANY(%s))
                LIMIT 1
            """, (tenant_id, candidates, candidates))
        else:
            cur.execute("""
                SELECT p.id as product_id, p.barcode as barcode, 'EAN13' as barcode_type, true as is_primary,
                       p.business_id, p.sku as product_sku, p.name as product_name
                FROM "Nova".t0003 p
                WHERE p.barcode = ANY(%s) OR p.sku = ANY(%s)
                LIMIT 1
            """, (candidates, candidates))

        row = cur.fetchone()
        if row:
            res = dict(row)
            res['_parsed_barcode'] = info
            return res

    return None


def find_product_uom_by_barcode(conn, barcode_str: str, tenant_id: Optional[int] = None) -> Optional[Dict[str, Any]]:
    """
    Looks up Product UOM (t0007) record by scanning product barcode.
    """
    product = find_product_by_barcode(conn, barcode_str, tenant_id=tenant_id)
    if not product:
        return None

    product_id = product['id']
    if tenant_id is None:
        tenant_id = get_current_tenant()

    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        if tenant_id is not None:
            cur.execute("""
                SELECT u.*
                FROM "Nova".t0007 u
                WHERE (u.business_id = %s OR u.business_id IS NULL)
                  AND u.product_id = %s
                LIMIT 1
            """, (tenant_id, product_id))
        else:
            cur.execute("""
                SELECT u.*
                FROM "Nova".t0007 u
                WHERE u.product_id = %s
                LIMIT 1
            """, (product_id,))

        row = cur.fetchone()
        if row:
            res = dict(row)
            res['product'] = product
            return res

        return {
            'product_id': product_id,
            'base_uom_id': None,
            'purchase_uom_id': None,
            'sales_uom_id': None,
            'purchase_factor': 1.0,
            'sales_factor': 1.0,
            'is_catch_weight': product.get('is_catch_weight', False),
            'pricing_uom_id': product.get('pricing_uom_id'),
            'nominal_weight': product.get('nominal_weight'),
            'tolerance_pct': product.get('tolerance_pct'),
            'pricing_basis': product.get('pricing_basis'),
            'product': product
        }

