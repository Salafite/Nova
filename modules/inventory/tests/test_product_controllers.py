import pytest
from modules.inventory.tests.conftest import client
from modules.inventory.controllers.T0003I import repo as product_repo
from modules.inventory.controllers.T0007I import repo as uom_repo
from modules.inventory.models.product import (
    ProductCreate, ProductResponse,
    ProductUOMCreate, ProductUOMResponse,
)


def test_t0003_repo_business_columns():
    expected_dual_uom_cols = [
        'is_catch_weight',
        'pricing_uom_id',
        'nominal_weight',
        'tolerance_pct',
        'pricing_basis',
    ]
    for col in expected_dual_uom_cols:
        assert col in product_repo.business_columns, f"{col} missing from T0003 repo business_columns"


def test_t0007_repo_business_columns():
    expected_dual_uom_cols = [
        'is_catch_weight',
        'pricing_uom_id',
        'nominal_weight',
        'tolerance_pct',
        'pricing_basis',
    ]
    for col in expected_dual_uom_cols:
        assert col in uom_repo.business_columns, f"{col} missing from T0007 repo business_columns"


def test_t0003_create_product_dual_uom(cursor):
    cursor.fetchone.return_value = {
        'id': 101,
        'name': 'Artisan Gouda Wheel',
        'sku': 'GOUDA-WHEEL',
        'barcode': '1234567890123',
        'description': 'Aged Gouda Wheel',
        'type': 'stockable',
        'price': 150.0,
        'cost_price': 90.0,
        'category': 'Dairy',
        'brand': 'Dutch Farm',
        'tax_rate': 0.05,
        'weight': 10.0,
        'volume': 0.0,
        'image_url': None,
        'is_purchasable': True,
        'is_saleable': True,
        'is_phantom': False,
        'last_transaction_date': None,
        'is_active': True,
        'is_catch_weight': True,
        'pricing_uom_id': 2,
        'nominal_weight': 10.5,
        'tolerance_pct': 8.0,
        'pricing_basis': 'weight',
        'created_at': '2026-08-23T00:00:00Z',
        'created_by': 1,
        'updated_at': '2026-08-23T00:00:00Z',
        'updated_by': None,
        'update_number': 0,
    }

    payload = {
        'name': 'Artisan Gouda Wheel',
        'sku': 'GOUDA-WHEEL',
        'price': 150.0,
        'cost_price': 90.0,
        'is_catch_weight': True,
        'pricing_uom_id': 2,
        'nominal_weight': 10.5,
        'tolerance_pct': 8.0,
        'pricing_basis': 'weight',
    }

    resp = client.post('/api/T0003I/', json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data['id'] == 101
    assert data['name'] == 'Artisan Gouda Wheel'
    assert data['is_catch_weight'] is True
    assert data['pricing_uom_id'] == 2
    assert data['nominal_weight'] == 10.5
    assert data['tolerance_pct'] == 8.0
    assert data['pricing_basis'] == 'weight'


def test_t0003_get_product_dual_uom(cursor):
    cursor.fetchone.return_value = {
        'id': 101,
        'name': 'Artisan Gouda Wheel',
        'sku': 'GOUDA-WHEEL',
        'barcode': None,
        'description': None,
        'type': 'stockable',
        'price': 150.0,
        'cost_price': 90.0,
        'category': None,
        'brand': None,
        'tax_rate': 0.05,
        'weight': 10.0,
        'volume': 0.0,
        'image_url': None,
        'is_purchasable': True,
        'is_saleable': True,
        'is_active': True,
        'is_catch_weight': True,
        'pricing_uom_id': 2,
        'nominal_weight': 10.5,
        'tolerance_pct': 8.0,
        'pricing_basis': 'weight',
        'created_at': '2026-08-23T00:00:00Z',
        'created_by': 1,
        'updated_at': '2026-08-23T00:00:00Z',
        'updated_by': None,
        'update_number': 0,
    }

    resp = client.get('/api/T0003I/101')
    assert resp.status_code == 200
    data = resp.json()
    assert data['id'] == 101
    assert data['is_catch_weight'] is True
    assert data['nominal_weight'] == 10.5
    assert data['tolerance_pct'] == 8.0


def test_t0003_update_product_dual_uom(cursor):
    cursor.fetchone.return_value = {
        'id': 101,
        'name': 'Artisan Gouda Wheel',
        'sku': 'GOUDA-WHEEL',
        'barcode': None,
        'description': None,
        'type': 'stockable',
        'price': 150.0,
        'cost_price': 90.0,
        'category': None,
        'brand': None,
        'tax_rate': 0.05,
        'weight': 10.0,
        'volume': 0.0,
        'image_url': None,
        'is_purchasable': True,
        'is_saleable': True,
        'is_active': True,
        'is_catch_weight': True,
        'pricing_uom_id': 2,
        'nominal_weight': 12.0,
        'tolerance_pct': 5.0,
        'pricing_basis': 'weight',
        'created_at': '2026-08-23T00:00:00Z',
        'created_by': 1,
        'updated_at': '2026-08-23T00:00:00Z',
        'updated_by': 1,
        'update_number': 1,
    }

    payload = {
        'nominal_weight': 12.0,
        'tolerance_pct': 5.0,
    }

    resp = client.put('/api/T0003I/101', json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data['id'] == 101
    assert data['nominal_weight'] == 12.0
    assert data['tolerance_pct'] == 5.0


def test_t0003_list_products_dual_uom(cursor):
    cursor.fetchall.return_value = [
        {
            'id': 101,
            'name': 'Artisan Gouda Wheel',
            'sku': 'GOUDA-WHEEL',
            'barcode': None,
            'description': None,
            'type': 'stockable',
            'price': 150.0,
            'cost_price': 90.0,
            'category': None,
            'brand': None,
            'tax_rate': 0.05,
            'weight': 10.0,
            'volume': 0.0,
            'image_url': None,
            'is_purchasable': True,
            'is_saleable': True,
            'is_active': True,
            'is_catch_weight': True,
            'pricing_uom_id': 2,
            'nominal_weight': 10.5,
            'tolerance_pct': 8.0,
            'pricing_basis': 'weight',
            'created_at': '2026-08-23T00:00:00Z',
            'created_by': 1,
            'updated_at': '2026-08-23T00:00:00Z',
            'updated_by': None,
            'update_number': 0,
        }
    ]

    resp = client.get('/api/T0003I/')
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]['is_catch_weight'] is True
    assert data[0]['pricing_uom_id'] == 2


def test_t0007_create_product_uom_dual_uom(cursor):
    cursor.fetchone.return_value = {
        'id': 50,
        'product_id': 101,
        'base_uom_id': 1,
        'purchase_uom_id': 1,
        'sales_uom_id': 1,
        'purchase_factor': 1.0,
        'sales_factor': 1.0,
        'is_catch_weight': True,
        'pricing_uom_id': 2,
        'nominal_weight': 10.5,
        'tolerance_pct': 8.0,
        'pricing_basis': 'weight',
        'created_at': '2026-08-23T00:00:00Z',
        'created_by': 1,
        'updated_at': '2026-08-23T00:00:00Z',
        'updated_by': None,
        'update_number': 0,
    }

    payload = {
        'product_id': 101,
        'base_uom_id': 1,
        'is_catch_weight': True,
        'pricing_uom_id': 2,
        'nominal_weight': 10.5,
        'tolerance_pct': 8.0,
        'pricing_basis': 'weight',
    }

    resp = client.post('/api/T0007I/', json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data['id'] == 50
    assert data['product_id'] == 101
    assert data['is_catch_weight'] is True
    assert data['pricing_uom_id'] == 2
    assert data['nominal_weight'] == 10.5
    assert data['tolerance_pct'] == 8.0
    assert data['pricing_basis'] == 'weight'


def test_t0007_get_product_uom_dual_uom(cursor):
    cursor.fetchone.return_value = {
        'id': 50,
        'product_id': 101,
        'base_uom_id': 1,
        'purchase_uom_id': 1,
        'sales_uom_id': 1,
        'purchase_factor': 1.0,
        'sales_factor': 1.0,
        'is_catch_weight': True,
        'pricing_uom_id': 2,
        'nominal_weight': 10.5,
        'tolerance_pct': 8.0,
        'pricing_basis': 'weight',
        'created_at': '2026-08-23T00:00:00Z',
        'created_by': 1,
        'updated_at': '2026-08-23T00:00:00Z',
        'updated_by': None,
        'update_number': 0,
    }

    resp = client.get('/api/T0007I/50')
    assert resp.status_code == 200
    data = resp.json()
    assert data['id'] == 50
    assert data['is_catch_weight'] is True
    assert data['pricing_uom_id'] == 2


def test_t0007_update_product_uom_dual_uom(cursor):
    cursor.fetchone.return_value = {
        'id': 50,
        'product_id': 101,
        'base_uom_id': 1,
        'purchase_uom_id': 1,
        'sales_uom_id': 1,
        'purchase_factor': 1.0,
        'sales_factor': 1.0,
        'is_catch_weight': True,
        'pricing_uom_id': 2,
        'nominal_weight': 11.2,
        'tolerance_pct': 6.0,
        'pricing_basis': 'weight',
        'created_at': '2026-08-23T00:00:00Z',
        'created_by': 1,
        'updated_at': '2026-08-23T00:00:00Z',
        'updated_by': 1,
        'update_number': 1,
    }

    payload = {
        'nominal_weight': 11.2,
        'tolerance_pct': 6.0,
    }

    resp = client.put('/api/T0007I/50', json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data['id'] == 50
    assert data['nominal_weight'] == 11.2
    assert data['tolerance_pct'] == 6.0


