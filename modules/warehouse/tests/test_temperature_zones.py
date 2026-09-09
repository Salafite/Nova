"""
Unit and integration tests for Warehouse Temperature Zones, Bins, Compartments,
and Cold-Chain Thermal Compatibility Validation.
"""
import pytest
from unittest.mock import MagicMock
from modules.warehouse.models.temperature_zone import (
    TemperatureZoneCreate,
    TemperatureZoneUpdate,
    TemperatureZoneResponse,
    WarehouseBinCreate,
    WarehouseBinUpdate,
    WarehouseBinResponse,
    VehicleCompartmentCreate,
    VehicleCompartmentResponse,
    TemperatureCheckResponse,
    ThermalPickSequenceItem,
)
from modules.warehouse.services.cold_chain_service import ColdChainService


class InMemoryRepo:
    def __init__(self, data=None):
        self._data = dict(data or {})
        self._next_id = max(self._data.keys(), default=0) + 1

    def list(self, filters=None, limit=50, offset=0, order_by=None, **kwargs):
        res = list(self._data.values())
        if filters:
            for k, v in filters.items():
                res = [r for r in res if r.get(k) == v]
        return res[offset:offset + limit]

    def get(self, id_val, **kwargs):
        return self._data.get(id_val)

    def create(self, payload, **kwargs):
        obj = dict(payload)
        new_id = obj.get('id') or self._next_id
        self._next_id = max(self._next_id, new_id + 1)
        obj['id'] = new_id
        self._data[new_id] = obj
        return obj

    def update(self, id_val, payload, **kwargs):
        if id_val not in self._data:
            return None
        self._data[id_val].update(payload)
        return self._data[id_val]

    def delete(self, id_val, **kwargs):
        if id_val in self._data:
            del self._data[id_val]
            return True
        return False


def test_temperature_zone_models():
    create_req = TemperatureZoneCreate(
        name="Main Cold Storage Room",
        warehouse_id=1,
        zone_type="Frozen",
        min_temperature=-22.0,
        max_temperature=-18.0,
        target_temperature=-20.0,
        sensor_id="SENS-FROZ-01",
    )
    assert create_req.name == "Main Cold Storage Room"
    assert create_req.zone_type == "Frozen"
    assert create_req.min_temperature == -22.0
    assert create_req.max_temperature == -18.0

    zone_resp = TemperatureZoneResponse(
        id=1,
        zone_code="ZONE-00001",
        name="Main Cold Storage Room",
        warehouse_id=1,
        warehouse_name="Central Distribution Hub",
        zone_type="Frozen",
        min_temperature=-22.0,
        max_temperature=-18.0,
        target_temperature=-20.0,
        status="Normal",
        sensor_id="SENS-FROZ-01",
        is_active=True,
    )
    assert zone_resp.id == 1
    assert zone_resp.zone_code == "ZONE-00001"
    assert zone_resp.status == "Normal"


def test_cold_chain_service_zone_crud():
    zone_repo = InMemoryRepo()
    wh_repo = InMemoryRepo({1: {'id': 1, 'name': 'Central Hub', 'is_active': True}})
    bin_repo = InMemoryRepo()
    service = ColdChainService(zone_repo=zone_repo, wh_repo=wh_repo, bin_repo=bin_repo)

    # 1. Create Zone
    created = service.create_zone({
        'name': 'Dairy Chiller',
        'warehouse_id': 1,
        'zone_type': 'Chilled',
        'min_temperature': 2.0,
        'max_temperature': 4.0,
        'target_temperature': 3.0,
        'sensor_id': 'SENSOR-01',
    })
    assert created['id'] is not None
    assert created['zone_code'].startswith('ZONE-')
    assert created['zone_type'] == 'Chilled'

    # 2. Get Zone
    fetched = service.get_zone(created['id'])
    assert fetched['name'] == 'Dairy Chiller'
    assert fetched['warehouse_name'] == 'Central Hub'

    # 3. Update Zone
    updated = service.update_zone(created['id'], {'target_temperature': 3.5})
    assert updated['target_temperature'] == 3.5

    # 4. Record Zone Sensor Reading (Normal)
    reading_norm = service.record_zone_reading(created['id'], recorded_temperature=3.2)
    assert reading_norm['current_temperature'] == 3.2
    assert reading_norm['status'] == 'Normal'

    # 5. Record Zone Sensor Reading (Excursion breach)
    reading_exc = service.record_zone_reading(created['id'], recorded_temperature=8.5)
    assert reading_exc['current_temperature'] == 8.5
    assert reading_exc['status'] == 'Excursion'


def test_temperature_compatibility_checks():
    product_repo = InMemoryRepo({
        1: {
            'id': 1,
            'name': 'Frozen Beef Halves',
            'is_cold_chain': True,
            'temp_zone_type': 'Frozen',
            'min_temperature': -22.0,
            'max_temperature': -18.0,
            'critical_temp_limit': -18.0,
        },
        2: {
            'id': 2,
            'name': 'Fresh Pasteurized Milk',
            'is_cold_chain': True,
            'temp_zone_type': 'Chilled',
            'min_temperature': 2.0,
            'max_temperature': 4.0,
            'critical_temp_limit': 6.0,
        },
        3: {
            'id': 3,
            'name': 'Dry Rice Bags 25kg',
            'is_cold_chain': False,
            'temp_zone_type': 'Ambient',
            'min_temperature': 15.0,
            'max_temperature': 25.0,
            'critical_temp_limit': None,
        }
    })
    zone_repo = InMemoryRepo({
        10: {'id': 10, 'zone_code': 'ZONE-AMB', 'name': 'Ambient Aisle 1', 'zone_type': 'Ambient', 'min_temperature': 15.0, 'max_temperature': 25.0},
        20: {'id': 20, 'zone_code': 'ZONE-CHILL', 'name': 'Chiller 2-4C', 'zone_type': 'Chilled', 'min_temperature': 2.0, 'max_temperature': 4.0},
        30: {'id': 30, 'zone_code': 'ZONE-FROZ', 'name': 'Deep Freezer -18C', 'zone_type': 'Frozen', 'min_temperature': -25.0, 'max_temperature': -18.0},
    })
    bin_repo = InMemoryRepo({
        101: {'id': 101, 'bin_code': 'BIN-A1', 'warehouse_id': 1, 'zone_id': 10, 'temperature_profile': 'Ambient', 'min_temperature': 15.0, 'max_temperature': 25.0},
        201: {'id': 201, 'bin_code': 'BIN-C1', 'warehouse_id': 1, 'zone_id': 20, 'temperature_profile': 'Chilled', 'min_temperature': 2.0, 'max_temperature': 4.0},
        301: {'id': 301, 'bin_code': 'BIN-F1', 'warehouse_id': 1, 'zone_id': 30, 'temperature_profile': 'Frozen', 'min_temperature': -25.0, 'max_temperature': -18.0},
    })

    service = ColdChainService(product_repo=product_repo, zone_repo=zone_repo, bin_repo=bin_repo)

    # 1. Storing Dry Goods in Ambient -> Compatible
    amb_res = service.check_temperature_compatibility(product_id=3, target_zone_id=10)
    assert amb_res.is_compatible is True
    assert amb_res.severity is None

    # 2. Storing Frozen Meat in Frozen Bin -> Compatible
    froz_ok = service.check_temperature_compatibility(product_id=1, target_bin_id=301)
    assert froz_ok.is_compatible is True
    assert froz_ok.is_haccp_violation is False

    # 3. Storing Frozen Meat in Ambient Area -> Critical HACCP Violation
    froz_in_amb = service.check_temperature_compatibility(product_id=1, target_zone_id=10)
    assert froz_in_amb.is_compatible is False
    assert froz_in_amb.severity == 'Critical'
    assert froz_in_amb.is_haccp_violation is True
    assert froz_in_amb.quarantine_recommended is True

    # 4. Storing Chilled Milk in Ambient Area -> Critical HACCP Violation
    chill_in_amb = service.check_temperature_compatibility(product_id=2, target_zone_id=10)
    assert chill_in_amb.is_compatible is False
    assert chill_in_amb.severity == 'Critical'
    assert chill_in_amb.is_haccp_violation is True


def test_thermal_picking_sequence_sorting():
    service = ColdChainService()
    items = [
        {'id': 101, 'product_id': 1, 'product_name': 'Frozen Chicken Breasts', 'temp_zone_type': 'Frozen', 'thermal_priority_rank': 3},
        {'id': 102, 'product_id': 2, 'product_name': 'Ice Cream Tubs', 'temp_zone_type': 'Deep Freeze', 'thermal_priority_rank': 4},
        {'id': 103, 'product_id': 3, 'product_name': 'Canned Beans', 'temp_zone_type': 'Ambient', 'thermal_priority_rank': 1},
        {'id': 104, 'product_id': 4, 'product_name': 'Cheddar Cheese Block', 'temp_zone_type': 'Chilled', 'thermal_priority_rank': 2},
    ]

    sequence = service.get_thermal_pick_sequence(items)
    assert len(sequence) == 4

    # Order must strictly be: Ambient (1) -> Chilled (2) -> Frozen (3) -> Deep Freeze (4)
    assert sequence[0].product_name == 'Canned Beans'
    assert sequence[0].thermal_priority_rank == 1
    assert sequence[0].suggested_picking_order == 1

    assert sequence[1].product_name == 'Cheddar Cheese Block'
    assert sequence[1].thermal_priority_rank == 2
    assert sequence[1].suggested_picking_order == 2

    assert sequence[2].product_name == 'Frozen Chicken Breasts'
    assert sequence[2].thermal_priority_rank == 3
    assert sequence[2].suggested_picking_order == 3

    assert sequence[3].product_name == 'Ice Cream Tubs'
    assert sequence[3].thermal_priority_rank == 4
    assert sequence[3].suggested_picking_order == 4
