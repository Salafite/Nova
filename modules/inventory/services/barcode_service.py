import re
from typing import List, Dict, Any, Optional
import psycopg2.extras
from packages.database.connection import get_connection, release_connection
from modules.core.context import get_current_tenant


def parse_barcode_string(raw: str) -> Dict[str, Any]:
    """
    Parse a barcode string into structured metadata and search candidates.
    Supports EAN-13, UPC-A, Code 128, and GS1-128 (GTIN, batch, expiry, serial).
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
    barcode_type = 'CODE-128'

    # 1. GS1-128 parenthesized format: e.g. (01)00614141000039(10)LOT123(17)261231
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
        if '21' in ai_dict:
            serial_number = ai_dict['21']

    # 2. GS1-128 stream/prefix format: e.g. ]C10100614141000039... or 0100614141000039... (length >= 16)
    elif raw_str.startswith(']C1') or raw_str.startswith(']e0') or (len(raw_str) >= 16 and raw_str.startswith('01') and raw_str[2:16].isdigit()):
        barcode_type = 'GS1-128'
        clean = re.sub(r'^\][Ce][01]', '', raw_str)
        if clean.startswith('01') and len(clean) >= 16 and clean[2:16].isdigit():
            parsed_gtin = clean[2:16]
            rem = clean[16:]
            if '\x1d' in rem or '\u001d' in rem:
                parts = [p for p in re.split(r'[\x1d\u001d]', rem) if p]
                for part in parts:
                    if part.startswith('10'):
                        batch_number = part[2:]
                    elif part.startswith('17') and len(part) >= 8 and part[2:8].isdigit():
                        expiry_date = part[2:8]
                    elif part.startswith('21'):
                        serial_number = part[2:]
            elif rem.startswith('10'):
                batch_number = rem[2:]
            elif rem.startswith('17') and len(rem) >= 8 and rem[2:8].isdigit():
                expiry_date = rem[2:8]
                if len(rem) > 8 and rem[8:].startswith('10'):
                    batch_number = rem[10:]

    # 3. EAN-13 format (13 digits)
    elif re.match(r'^\d{13}$', raw_str):
        barcode_type = 'EAN-13'
        parsed_gtin = raw_str

    # 4. UPC-A format (12 digits)
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
        'candidates': deduped_candidates
    }


def find_product_by_barcode(conn, barcode_str: str, tenant_id: Optional[int] = None) -> Optional[Dict[str, Any]]:
    """
    Looks up a product by barcode string (EAN-13, UPC-A, Code 128, GS1-128 GTIN).
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
