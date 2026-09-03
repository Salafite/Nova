"""
Unit & Integration Tests for Delivery Route Planning & Driver Dispatch Service & Repository.
"""
import pytest
from unittest.mock import MagicMock
from datetime import date
from modules.sales.services.delivery_route_service import DeliveryRouteService
from modules.sales.models.delivery_route import (
    VehicleAssignmentRequest,
    DriverManifestResponse,
    LIFOPickListResponse,
)


def test_delivery_route_service_create_run():
    mock_repo = MagicMock()
    mock_repo.schema = 'Nova'
    mock_repo.generate_run_number.return_value = 'RUN-20260903-001'
    mock_repo.create_delivery_run.return_value = {
        'id': 1,
        'run_number': 'RUN-20260903-001',
        'run_date': date(2026, 9, 3),
        'zone': 'North Zone',
        'status': 'Draft',
        'total_stops': 0,
        'total_weight_kg': 0.0,
        'total_volume_m3': 0.0,
        'is_active': True,
    }
    mock_repo.get_unassigned_orders.return_value = [
        {
            'sales_order_id': 10,
            'sales_order_number': 'SO-1001',
            'customer_id': 5,
            'customer_name': 'Acme Corp',
            'delivery_address': '123 Main St',
            'customer_phone': '555-0100',
            'total_weight': 100.0,
            'total_volume': 8.0,
        },
        {
            'sales_order_id': 11,
            'sales_order_number': 'SO-1002',
            'customer_id': 6,
            'customer_name': 'Beta Retail',
            'delivery_address': '456 Oak St',
            'customer_phone': '555-0200',
            'total_weight': 50.0,
            'total_volume': 4.0,
        },
    ]
    mock_repo.get_delivery_run.return_value = {
        'id': 1,
        'run_number': 'RUN-20260903-001',
        'run_date': date(2026, 9, 3),
        'zone_name': 'North Zone',
        'status': 'Draft',
        'total_orders': 2,
        'total_weight': 150.0,
        'total_volume': 12.0,
        'vehicle_code': None,
        'driver_name': None,
        'is_active': True,
    }
    mock_repo.get_run_stops.return_value = [
        {'id': 101, 'sales_order_id': 10, 'stop_number': 1, 'lifo_staging_sequence': 2},
        {'id': 102, 'sales_order_id': 11, 'stop_number': 2, 'lifo_staging_sequence': 1},
    ]

    service = DeliveryRouteService(repo=mock_repo)

    payload = {
        "run_date": date(2026, 9, 3),
        "zone_name": "North Zone",
        "sales_order_ids": [10, 11],
    }
    result = service.create_delivery_run(payload)

    assert result['id'] == 1
    assert result['run_number'] == 'RUN-20260903-001'
    assert result['total_orders'] == 2
    assert result['total_weight'] == 150.0
    mock_repo.create_delivery_run.assert_called_once()
    assert mock_repo.create_run_stop.call_count == 2


def test_delivery_route_service_vehicle_assignment():
    mock_repo = MagicMock()
    mock_repo.get_delivery_run.return_value = {
        'id': 1,
        'run_number': 'RUN-001',
        'status': 'Draft',
        'total_weight': 1200.0,
        'total_volume': 15.0,
        'driver_id': 10,
        'driver_name': 'John Driver',
    }
    mock_repo.get_vehicle_by_id_or_code.return_value = {
        'id': 50,
        'vehicle_code': 'TRK-01',
        'name': 'Delivery Van #1',
        'max_weight_capacity_kg': 1000.0,  # lower than payload (1200) -> trigger warning
        'max_volume_capacity_m3': 20.0,
    }

    service = DeliveryRouteService(repo=mock_repo)

    req = {
        "vehicle_id": 50,
        "vehicle_code": "TRK-01",
        "driver_id": 10,
        "driver_name": "John Driver",
    }
    resp = service.assign_vehicle(run_id=1, request_data=req)

    assert resp.run_id == 1
    assert resp.vehicle_code == 'TRK-01'
    assert resp.driver_name == 'John Driver'
    assert resp.capacity_warning is not None
    assert 'Payload weight (1200.0 kg) exceeds vehicle max capacity (1000.0 kg)' in resp.capacity_warning
    mock_repo.update_delivery_run.assert_called_once()


def test_delivery_route_service_resequence_stops_and_lifo():
    mock_repo = MagicMock()
    mock_repo.get_delivery_run.return_value = {
        'id': 1,
        'run_number': 'RUN-001',
        'run_date': date(2026, 9, 3),
        'zone_name': 'South Zone',
        'status': 'Planned',
        'total_orders': 3,
    }
    mock_repo.get_run_stops.return_value = []

    service = DeliveryRouteService(repo=mock_repo)

    # Resequence stops order to [3, 1, 2]
    res = service.resequence_stops(run_id=1, stop_ids_in_order=[3, 1, 2])

    assert res['id'] == 1
    # Check that update_run_stop was called with updated stop numbers and LIFO sequences
    # Total stops = 3
    # First in list (id=3): stop_sequence = 1, lifo_staging_sequence = 3 (loaded last into vehicle / 1st drop off)
    # Second in list (id=1): stop_sequence = 2, lifo_staging_sequence = 2
    # Third in list (id=2): stop_sequence = 3, lifo_staging_sequence = 1 (loaded first into vehicle / 3rd drop off)
    calls = mock_repo.update_run_stop.call_args_list
    assert len(calls) == 3
    assert calls[0][0] == (3, {'stop_sequence': 1, 'lifo_staging_sequence': 3})
    assert calls[1][0] == (1, {'stop_sequence': 2, 'lifo_staging_sequence': 2})
    assert calls[2][0] == (2, {'stop_sequence': 3, 'lifo_staging_sequence': 1})


def test_delivery_route_service_unassigned_orders():
    mock_repo = MagicMock()
    mock_repo.get_unassigned_orders.return_value = [
        {
            'sales_order_id': 100,
            'sales_order_number': 'SO-5000',
            'order_date': date(2026, 9, 3),
            'customer_id': 20,
            'customer_name': 'Apex Supplies',
            'delivery_address': '789 Commercial Way',
            'customer_phone': '555-9988',
            'zone_name': 'East Zone',
            'total_weight': 75.5,
            'total_volume': 5.0,
            'total_amount': 1500.0,
        }
    ]

    service = DeliveryRouteService(repo=mock_repo)
    unassigned = service.get_unassigned_orders(zone_name='East Zone')

    assert len(unassigned) == 1
    assert unassigned[0].sales_order_number == 'SO-5000'
    assert unassigned[0].zone_name == 'East Zone'
    assert unassigned[0].total_weight == 75.5


def test_delivery_route_service_driver_manifest_and_lifo_pick_list():
    mock_repo = MagicMock()
    mock_repo.get_driver_manifest_details.return_value = {
        'run_id': 1,
        'run_number': 'RUN-001',
        'run_date': date(2026, 9, 3),
        'zone_name': 'North Zone',
        'vehicle_code': 'TRK-01',
        'driver_name': 'Driver Bob',
        'status': 'Dispatched',
        'total_stops': 1,
        'stops': [
            {
                'stop_number': 1,
                'sales_order_id': 10,
                'sales_order_number': 'SO-1001',
                'customer_id': 5,
                'customer_name': 'Acme Corp',
                'delivery_address': '123 Main St',
                'customer_phone': '555-0100',
                'contact_person': 'John Doe',
                'status': 'Pending',
                'special_instructions': 'Call ahead',
                'items_count': 3,
                'total_weight': 50.0,
            }
        ],
    }

    mock_repo.get_lifo_staging_pick_list_details.return_value = {
        'run_id': 1,
        'run_number': 'RUN-001',
        'run_date': date(2026, 9, 3),
        'zone_name': 'North Zone',
        'warehouse_id': 1,
        'vehicle_code': 'TRK-01',
        'driver_name': 'Driver Bob',
        'total_stops': 1,
        'staging_sequence': [
            {
                'staging_sequence': 1,  # Loaded first into vehicle
                'stop_number': 1,
                'sales_order_id': 10,
                'sales_order_number': 'SO-1001',
                'customer_name': 'Acme Corp',
                'delivery_address': '123 Main St',
                'items': [
                    {
                        'product_id': 50,
                        'product_name': 'Widgets',
                        'sku': 'WDG-01',
                        'qty': 10.0,
                        'uom_name': 'Box',
                        'location_code': 'A-01-01',
                    }
                ],
            }
        ],
    }

    service = DeliveryRouteService(repo=mock_repo)

    manifest = service.get_driver_manifest(run_id=1)
    assert isinstance(manifest, DriverManifestResponse)
    assert manifest.run_number == 'RUN-001'
    assert manifest.stops[0].customer_name == 'Acme Corp'

    lifo_list = service.get_lifo_staging_pick_list(run_id=1)
    assert isinstance(lifo_list, LIFOPickListResponse)
    assert lifo_list.staging_sequence[0].staging_sequence == 1
    assert lifo_list.staging_sequence[0].items[0].product_name == 'Widgets'
