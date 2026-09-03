import pytest
from modules.inventory.tests.conftest import client
from modules.inventory.services.barcode_service import (
    parse_barcode_string,
    find_product_by_barcode,
    find_barcode_record,
    find_product_uom_by_barcode,
)


def test_parse_barcode_string_ean13():
    res = parse_barcode_string("5901234123457")
    assert res['type'] == "EAN-13"
    assert res['gtin'] == "5901234123457"
    assert "5901234123457" in res['candidates']
    assert "05901234123457" in res['candidates']


def test_parse_barcode_string_upca():
    res = parse_barcode_string("012345678905")
    assert res['type'] == "UPC-A"
    assert res['gtin'] == "00012345678905"
    assert "012345678905" in res['candidates']
    assert "00012345678905" in res['candidates']
    assert "0012345678905" in res['candidates']


def test_parse_barcode_string_code128():
    res = parse_barcode_string("SKU-TEST-99")
    assert res['type'] == "CODE-128"
    assert res['code'] == "SKU-TEST-99"
    assert res['candidates'] == ["SKU-TEST-99"]


def test_parse_barcode_string_gs1_128():
    res = parse_barcode_string("(01)00614141000039(10)LOT12345(17)261231")
    assert res['type'] == "GS1-128"
    assert res['gtin'] == "00614141000039"
    assert res['batch_number'] == "LOT12345"
    assert res['expiry_date'] == "261231"
    assert "00614141000039" in res['candidates']
    assert "614141000039" in res['candidates']


def test_t0003_lookup_barcode_endpoint(cursor):
    cursor.fetchone.return_value = {
        'id': 101,
        'name': 'Test Cheese',
        'sku': 'CHEESE-01',
        'barcode': '5901234123457',
        'price': 100.0,
        'cost_price': 50.0,
        'business_id': 1
    }

    resp = client.get('/api/T0003I/lookup-barcode?code=5901234123457')
    assert resp.status_code == 200
    data = resp.json()
    assert data['id'] == 101
    assert data['sku'] == 'CHEESE-01'

    resp_path = client.get('/api/T0003I/by-barcode/5901234123457')
    assert resp_path.status_code == 200
    assert resp_path.json()['id'] == 101


def test_t0004_lookup_barcode_endpoint(cursor):
    cursor.fetchone.return_value = {
        'id': 10,
        'product_id': 101,
        'barcode': '012345678905',
        'barcode_type': 'UPCA',
        'is_primary': True,
        'product_sku': 'CHEESE-01',
        'product_name': 'Test Cheese'
    }

    resp = client.get('/api/T0004I/lookup-barcode?code=012345678905')
    assert resp.status_code == 200
    data = resp.json()
    assert data['product_id'] == 101
    assert data['barcode'] == '012345678905'

    resp_path = client.get('/api/T0004I/by-barcode/012345678905')
    assert resp_path.status_code == 200
    assert resp_path.json()['product_id'] == 101


def test_t0007_lookup_barcode_endpoint(cursor):
    cursor.fetchone.side_effect = [
        {
            'id': 101,
            'name': 'Test Cheese',
            'sku': 'CHEESE-01',
            'barcode': '5901234123457',
            'is_catch_weight': True,
            'pricing_uom_id': 2,
            'nominal_weight': 10.0,
            'tolerance_pct': 5.0,
            'pricing_basis': 'weight'
        },
        {
            'id': 50,
            'product_id': 101,
            'base_uom_id': 1,
            'purchase_uom_id': 1,
            'sales_uom_id': 1,
            'purchase_factor': 1.0,
            'sales_factor': 1.0,
            'is_catch_weight': True,
            'pricing_uom_id': 2,
            'nominal_weight': 10.0,
            'tolerance_pct': 5.0,
            'pricing_basis': 'weight'
        }
    ]
    try:
        resp = client.get('/api/T0007I/lookup-barcode?code=5901234123457')
        assert resp.status_code == 200
        data = resp.json()
        assert data['product_id'] == 101
        assert data['is_catch_weight'] is True
    finally:
        cursor.fetchone.side_effect = None
