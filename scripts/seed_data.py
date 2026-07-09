"""Seed initial data into Nova ERP via the REST API.

Usage:
    python scripts/seed_data.py                      # uses env vars for auth
    python scripts/seed_data.py --base-url https://yourdomain.com

Requires env vars:
    API_USERNAME, API_PASSWORD  (or use --username / --password)
    Optionally: API_BASE_URL (default: http://localhost:8070)
"""

import os
import sys
import json
import time
import argparse
from urllib.request import Request, urlopen
from urllib.parse import urljoin
from urllib.error import HTTPError

BASE_URL = os.getenv('API_BASE_URL', 'http://localhost:8070').rstrip('/')


def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)


# ── HTTP helpers ──────────────────────────────────────────────────────────

def _request(method, url, data=None, token=None):
    headers = {'Content-Type': 'application/json'}
    if token:
        headers['Authorization'] = f'Bearer {token}'
    body = json.dumps(data).encode() if data is not None else None
    req = Request(url, data=body, method=method, headers=headers)
    try:
        with urlopen(req) as resp:
            text = resp.read().decode()
            return json.loads(text) if text else None
    except HTTPError as e:
        body = e.read().decode()
        try:
            detail = json.loads(body).get('detail', body)
        except json.JSONDecodeError:
            detail = body
        eprint(f'  HTTP {e.code} {detail}')
        return None
    except Exception as e:
        eprint(f'  Request failed: {e}')
        return None


def post(url, data, token):
    return _request('POST', url, data, token)


def get(url, token):
    return _request('GET', url, token=token)


# ── Auth ───────────────────────────────────────────────────────────────────

def login(username, password):
    data = post(urljoin(BASE_URL, '/api/auth/login'), {'username': username, 'password': password}, None)
    if data and 'access_token' in data:
        return data['access_token']
    return None


def signup(business_name, username, password, full_name, email):
    data = post(urljoin(BASE_URL, '/api/auth/signup'), {
        'business_name': business_name,
        'username': username,
        'password': password,
        'full_name': full_name,
        'email': email,
    }, None)
    if data and 'access_token' in data:
        return data['access_token']
    return None


# ── Idempotent creators ───────────────────────────────────────────────────

def create_if_missing(api_prefix, items, token, name_field='name', code_field=None):
    """Post each item if it doesn't already exist (matched by name or code)."""
    existing = get(urljoin(BASE_URL, api_prefix), token) or []
    existing_names = {e.get(name_field, '').strip().lower() for e in existing}
    if code_field:
        existing_codes = {e.get(code_field, '').strip().lower() for e in existing}
    else:
        existing_codes = set()

    created = 0
    for item in items:
        match_key = item.get(name_field, '').strip().lower()
        match_code = item.get(code_field, '').strip().lower() if code_field else ''
        if match_key in existing_names or (code_field and match_code in existing_codes):
            continue
        result = post(urljoin(BASE_URL, api_prefix), item, token)
        if result:
            created += 1
            print(f'  + {item.get(name_field, item.get(code_field, "?"))}')
        else:
            eprint(f'  ! Failed: {item.get(name_field, item.get(code_field, "?"))}')
    print(f'  -> {created} created, {len(items) - created} already existed')
    return created


# ── Seed data ─────────────────────────────────────────────────────────────

SEED_UOMS = [
    {'uom_code': 'EA', 'uom_name': 'Each', 'category': 'Quantity', 'is_base_unit': True},
    {'uom_code': 'KG', 'uom_name': 'Kilogram', 'category': 'Weight', 'is_base_unit': True},
    {'uom_code': 'G', 'uom_name': 'Gram', 'category': 'Weight', 'is_base_unit': False},
    {'uom_code': 'HR', 'uom_name': 'Hour', 'category': 'Time', 'is_base_unit': True},
    {'uom_code': 'M', 'uom_name': 'Meter', 'category': 'Length', 'is_base_unit': True},
    {'uom_code': 'L', 'uom_name': 'Liter', 'category': 'Volume', 'is_base_unit': True},
    {'uom_code': 'BOX', 'uom_name': 'Box', 'category': 'Quantity', 'is_base_unit': False},
    {'uom_code': 'PR', 'uom_name': 'Pair', 'category': 'Quantity', 'is_base_unit': False},
    {'uom_code': 'CM', 'uom_name': 'Centimeter', 'category': 'Length', 'is_base_unit': False},
    {'uom_code': 'PKT', 'uom_name': 'Packet', 'category': 'Quantity', 'is_base_unit': False},
]

SEED_WAREHOUSES = [
    {'name': 'Main Warehouse', 'location': 'Primary storage location'},
    {'name': 'Returns Warehouse', 'location': 'Customer returns and defective goods'},
]

SEED_ACCOUNTS = [
    {'account_code': '1000', 'account_name': 'Cash', 'account_type': 'Asset'},
    {'account_code': '1100', 'account_name': 'Accounts Receivable', 'account_type': 'Asset'},
    {'account_code': '1200', 'account_name': 'Inventory', 'account_type': 'Asset'},
    {'account_code': '1300', 'account_name': 'Fixed Assets', 'account_type': 'Asset'},
    {'account_code': '2000', 'account_name': 'Accounts Payable', 'account_type': 'Liability'},
    {'account_code': '2100', 'account_name': 'Accrued Expenses', 'account_type': 'Liability'},
    {'account_code': '2200', 'account_name': 'Tax Payable', 'account_type': 'Liability'},
    {'account_code': '3000', 'account_name': 'Owner Equity', 'account_type': 'Equity'},
    {'account_code': '4000', 'account_name': 'Sales Revenue', 'account_type': 'Revenue'},
    {'account_code': '4100', 'account_name': 'Service Revenue', 'account_type': 'Revenue'},
    {'account_code': '5000', 'account_name': 'Cost of Goods Sold', 'account_type': 'Expense'},
    {'account_code': '5100', 'account_name': 'Salaries & Wages', 'account_type': 'Expense'},
    {'account_code': '5200', 'account_name': 'Rent & Utilities', 'account_type': 'Expense'},
    {'account_code': '5300', 'account_name': 'Office Supplies', 'account_type': 'Expense'},
    {'account_code': '5400', 'account_name': 'Marketing & Advertising', 'account_type': 'Expense'},
    {'account_code': '5500', 'account_name': 'Depreciation', 'account_type': 'Expense'},
    {'account_code': '5600', 'account_name': 'Other Operating Expenses', 'account_type': 'Expense'},
]

SEED_PAYMENT_TERMS = [
    {'name': 'Due on Receipt', 'code': 'DUE_ON_RECEIPT', 'description': 'Payment due immediately upon receipt', 'due_days': 0, 'is_default': True},
    {'name': 'Net 15', 'code': 'NET_15', 'description': 'Payment due within 15 days', 'due_days': 15},
    {'name': 'Net 30', 'code': 'NET_30', 'description': 'Payment due within 30 days', 'due_days': 30},
    {'name': 'Net 60', 'code': 'NET_60', 'description': 'Payment due within 60 days', 'due_days': 60},
]

SEED_PAYMENT_METHODS = [
    {'name': 'Cash', 'code': 'CASH', 'description': 'Cash payment', 'is_default': True},
    {'name': 'Bank Transfer', 'code': 'BANK_TRANSFER', 'description': 'Direct bank transfer'},
    {'name': 'Credit Card', 'code': 'CREDIT_CARD', 'description': 'Credit card payment'},
    {'name': 'Check', 'code': 'CHECK', 'description': 'Payment by check'},
    {'name': 'Mobile Wallet', 'code': 'MOBILE_WALLET', 'description': 'Mobile payment wallet'},
]

SEED_DEPARTMENTS = [
    {'department_code': 'ADMIN', 'department_name': 'Administration'},
    {'department_code': 'FIN', 'department_name': 'Finance & Accounting'},
    {'department_code': 'HR', 'department_name': 'Human Resources'},
    {'department_code': 'IT', 'department_name': 'Information Technology'},
    {'department_code': 'SALES', 'department_name': 'Sales & Marketing'},
    {'department_code': 'OPS', 'department_name': 'Operations'},
    {'department_code': 'WAREHOUSE', 'department_name': 'Warehouse & Logistics'},
]

SEED_DESIGNATIONS = [
    {'designation_code': 'CEO', 'designation_name': 'Chief Executive Officer'},
    {'designation_code': 'CFO', 'designation_name': 'Chief Financial Officer'},
    {'designation_code': 'CTO', 'designation_name': 'Chief Technology Officer'},
    {'designation_code': 'MGR', 'designation_name': 'Manager'},
    {'designation_code': 'SUPV', 'designation_name': 'Supervisor'},
    {'designation_code': 'CLERK', 'designation_name': 'Clerk'},
    {'designation_code': 'ACCT', 'designation_name': 'Accountant'},
    {'designation_code': 'SALES_REP', 'designation_name': 'Sales Representative'},
    {'designation_code': 'ENG', 'designation_name': 'Engineer'},
    {'designation_code': 'ASST', 'designation_name': 'Assistant'},
]


# ── Main ──────────────────────────────────────────────────────────────────

def run(username, password, base_url, no_signup):
    global BASE_URL
    BASE_URL = base_url.rstrip('/')
    print(f'Connecting to {BASE_URL}')
    print()

    # 1. Obtain token
    token = None
    if not no_signup:
        print('Attempting signup (ignore if user already exists)...')
        token = signup('Default Business', username, password, username, f'{username}@novaerp.local')

    if not token:
        print('Logging in...')
        token = login(username, password)

    if not token:
        eprint('ERROR: Could not authenticate. Check credentials or signup manually first.')
        sys.exit(1)

    print('Authenticated successfully')
    print()

    # 2. Seed each entity type
    sections = [
        ('UOM', '/api/T0001I/', SEED_UOMS, 'uom_name', 'uom_code'),
        ('Warehouses', '/api/T0008I/', SEED_WAREHOUSES, 'name', None),
        ('Chart of Accounts', '/api/T0026I/', SEED_ACCOUNTS, 'account_name', 'account_code'),
        ('Payment Terms', '/api/T0096I/', SEED_PAYMENT_TERMS, 'name', 'code'),
        ('Payment Methods', '/api/T0097I/', SEED_PAYMENT_METHODS, 'name', 'code'),
        ('Departments', '/api/T0028I/', SEED_DEPARTMENTS, 'department_name', 'department_code'),
        ('Designations', '/api/T0029I/', SEED_DESIGNATIONS, 'designation_name', 'designation_code'),
    ]

    total = 0
    for label, prefix, items, name_f, code_f in sections:
        print(f'Seeding {label}...')
        total += create_if_missing(prefix, items, token, name_f, code_f)
        print()

    print(f'Done. Created {total} records total.')
    return 0


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Seed initial data into Nova ERP')
    parser.add_argument('--base-url', default=BASE_URL, help='API base URL')
    parser.add_argument('--username', default=os.getenv('API_USERNAME', 'admin'), help='Login username')
    parser.add_argument('--password', default=os.getenv('API_PASSWORD', 'password123'), help='Login password')
    parser.add_argument('--no-signup', action='store_true', help='Skip signup attempt, only login')
    args = parser.parse_args()
    sys.exit(run(args.username, args.password, args.base_url, args.no_signup))
