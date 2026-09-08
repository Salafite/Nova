"""
Nova ERP — Warehouse Cold-Chain & Temperature Zone Management Service
Manages thermal storage zones (Ambient, Chilled, Frozen, Deep Freeze),
storage bins, vehicle temperature compartments, and compatibility validation.
"""
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any, Union
from fastapi import HTTPException, status

from modules.core.services.base import CrudService
from modules.core.repositories.base import CrudRepository
from modules.warehouse.models.temperature_zone import (
    TemperatureZoneCreate,
    TemperatureZoneUpdate,
    TemperatureZoneResponse,
    WarehouseBinCreate,
    WarehouseBinUpdate,
    WarehouseBinResponse,
    VehicleCompartmentCreate,
    VehicleCompartmentUpdate,
    VehicleCompartmentResponse,
    TemperatureCheckRequest,
    TemperatureCheckResponse,
    ThermalPickSequenceItem,
)
from packages.database.sequence import (
    generate_temp_zone_code,
    generate_warehouse_bin_code,
    generate_vehicle_compartment_code,
)
from packages.database.connection import get_connection, release_connection

logger = logging.getLogger(__name__)

ZONE_REPO = CrudRepository(
    'T0124',
    business_columns=[
        'id', 'zone_code', 'name', 'warehouse_id', 'zone_type',
        'min_temperature', 'max_temperature', 'target_temperature',
        'humidity_min', 'humidity_max', 'current_temperature', 'current_humidity',
        'last_monitored_at', 'status', 'sensor_id', 'capacity_m3', 'notes',
        'is_active', 'business_id'
    ]
)

BIN_REPO = CrudRepository(
    'T0125',
    business_columns=[
        'id', 'bin_code', 'warehouse_id', 'zone_id', 'bin_type',
        'temperature_profile', 'min_temperature', 'max_temperature',
        'aisle', 'rack', 'shelf', 'position', 'max_weight_capacity_kg',
        'max_volume_capacity_m3', 'current_weight_kg', 'current_volume_m3',
        'status', 'is_active', 'business_id'
    ]
)

COMPARTMENT_REPO = CrudRepository(
    'T0126',
    business_columns=[
        'id', 'vehicle_id', 'compartment_code', 'name', 'temperature_zone_type',
        'min_temperature', 'max_temperature', 'target_temperature',
        'max_weight_capacity_kg', 'max_volume_capacity_m3', 'current_temperature',
        'sensor_id', 'status', 'is_active', 'business_id'
    ]
)

PRODUCT_REPO = CrudRepository(
    'T0003',
    business_columns=[
        'id', 'name', 'sku', 'barcode', 'is_cold_chain', 'temp_zone_type',
        'min_temperature', 'max_temperature', 'critical_temp_limit',
        'thermal_priority_rank', 'shelf_life_days', 'is_active', 'business_id'
    ]
)

WH_REPO = CrudRepository(
    'T0008',
    business_columns=['id', 'name', 'location', 'is_active', 'business_id']
)

VEHICLE_REPO = CrudRepository(
    'T0114',
    business_columns=[
        'id', 'vehicle_code', 'plate_number', 'is_refrigerated',
        'has_multi_temperature', 'temperature_monitoring_enabled',
        'min_temperature', 'max_temperature', 'is_active', 'business_id'
    ]
)


def _conn_kwargs(conn):
    return {'conn': conn} if conn is not None else {}


class ColdChainService(CrudService):
    """
    Domain service for warehouse temperature zones, storage bins,
    vehicle partitioned compartments, and thermal validation.
    """

    def __init__(
        self,
        zone_repo: Optional[CrudRepository] = None,
        bin_repo: Optional[CrudRepository] = None,
        compartment_repo: Optional[CrudRepository] = None,
        product_repo: Optional[CrudRepository] = None,
        wh_repo: Optional[CrudRepository] = None,
        vehicle_repo: Optional[CrudRepository] = None,
    ):
        super().__init__(zone_repo or ZONE_REPO)
        self.zone_repo = self.repo
        self.bin_repo = bin_repo or BIN_REPO
        self.compartment_repo = compartment_repo or COMPARTMENT_REPO
        self.product_repo = product_repo or PRODUCT_REPO
        self.wh_repo = wh_repo or WH_REPO
        self.vehicle_repo = vehicle_repo or VEHICLE_REPO

    # -------------------------------------------------------------------------
    # Warehouse Temperature Zones (T0124)
    # -------------------------------------------------------------------------

    def list_zones(self, filters: Optional[Dict[str, Any]] = None, conn=None) -> List[Dict[str, Any]]:
        """List temperature zones with warehouse names and bin counts."""
        f = dict(filters or {})
        if 'is_active' not in f:
            f['is_active'] = True
        zones = self.zone_repo.list(filters=f, **_conn_kwargs(conn))
        wh_map = {w['id']: w['name'] for w in self.wh_repo.list(**_conn_kwargs(conn))}

        for z in zones:
            z['warehouse_name'] = wh_map.get(z.get('warehouse_id'))
            bins = self.bin_repo.list(filters={'zone_id': z['id'], 'is_active': True}, **_conn_kwargs(conn))
            z['bins_count'] = len(bins)
        return zones

    def get_zone(self, zone_id: int, conn=None) -> Optional[Dict[str, Any]]:
        """Retrieve zone by ID with enriched details."""
        z = self.zone_repo.get(zone_id, **_conn_kwargs(conn))
        if not z:
            return None
        wh = self.wh_repo.get(z.get('warehouse_id'), **_conn_kwargs(conn))
        z['warehouse_name'] = wh.get('name') if wh else None
        bins = self.bin_repo.list(filters={'zone_id': z['id'], 'is_active': True}, **_conn_kwargs(conn))
        z['bins_count'] = len(bins)
        return z

    def create_zone(self, data: Union[Dict[str, Any], TemperatureZoneCreate], conn=None) -> Dict[str, Any]:
        """Create a new temperature zone with auto-generated zone code."""
        payload = data.model_dump(exclude_unset=True) if isinstance(data, TemperatureZoneCreate) else dict(data)
        if not payload.get('zone_code') or not str(payload.get('zone_code')).strip():
            try:
                payload['zone_code'] = generate_temp_zone_code(**_conn_kwargs(conn))
            except Exception:
                payload['zone_code'] = f"ZONE-{datetime.utcnow().strftime('%M%S')}"

        return self.zone_repo.create(payload, **_conn_kwargs(conn))

    def update_zone(self, zone_id: int, data: Union[Dict[str, Any], TemperatureZoneUpdate], conn=None) -> Dict[str, Any]:
        """Update existing temperature zone."""
        payload = data.model_dump(exclude_unset=True) if isinstance(data, TemperatureZoneUpdate) else dict(data)
        return self.zone_repo.update(zone_id, payload, **_conn_kwargs(conn))

    def delete_zone(self, zone_id: int, conn=None) -> bool:
        """Soft-delete temperature zone."""
        return self.zone_repo.update(zone_id, {'is_active': False}, **_conn_kwargs(conn))

    def record_zone_reading(
        self,
        zone_id: int,
        recorded_temperature: float,
        humidity_pct: Optional[float] = None,
        sensor_id: Optional[str] = None,
        notes: Optional[str] = None,
        conn=None,
    ) -> Dict[str, Any]:
        """Record real-time IoT or manual temperature reading for a zone and update its status."""
        zone = self.zone_repo.get(zone_id, **_conn_kwargs(conn))
        if not zone:
            raise HTTPException(status.HTTP_404_NOT_FOUND, f"Temperature zone #{zone_id} not found")

        min_temp = float(zone.get('min_temperature', 0))
        max_temp = float(zone.get('max_temperature', 0))
        rec_temp = float(recorded_temperature)

        if rec_temp < min_temp or rec_temp > max_temp:
            dev = max(min_temp - rec_temp, rec_temp - max_temp)
            new_status = 'Excursion' if dev > 2.0 else 'Warning'
        else:
            new_status = 'Normal'

        updates = {
            'current_temperature': rec_temp,
            'last_monitored_at': datetime.utcnow(),
            'status': new_status,
        }
        if humidity_pct is not None:
            updates['current_humidity'] = float(humidity_pct)
        if sensor_id:
            updates['sensor_id'] = sensor_id
        if notes:
            updates['notes'] = notes

        return self.zone_repo.update(zone_id, updates, **_conn_kwargs(conn))

    # -------------------------------------------------------------------------
    # Warehouse Bins & Staging Areas (T0125)
    # -------------------------------------------------------------------------

    def list_bins(self, filters: Optional[Dict[str, Any]] = None, conn=None) -> List[Dict[str, Any]]:
        """List warehouse bins with zone and warehouse details."""
        f = dict(filters or {})
        if 'is_active' not in f:
            f['is_active'] = True
        bins = self.bin_repo.list(filters=f, **_conn_kwargs(conn))
        wh_map = {w['id']: w['name'] for w in self.wh_repo.list(**_conn_kwargs(conn))}
        zone_map = {z['id']: z for z in self.zone_repo.list(**_conn_kwargs(conn))}

        for b in bins:
            b['warehouse_name'] = wh_map.get(b.get('warehouse_id'))
            z = zone_map.get(b.get('zone_id'))
            if z:
                b['zone_name'] = z.get('name')
                b['zone_type'] = z.get('zone_type')
        return bins

    def get_bin(self, bin_id: int, conn=None) -> Optional[Dict[str, Any]]:
        """Retrieve bin by ID."""
        b = self.bin_repo.get(bin_id, **_conn_kwargs(conn))
        if not b:
            return None
        wh = self.wh_repo.get(b.get('warehouse_id'), **_conn_kwargs(conn))
        b['warehouse_name'] = wh.get('name') if wh else None
        if b.get('zone_id'):
            z = self.zone_repo.get(b['zone_id'], **_conn_kwargs(conn))
            if z:
                b['zone_name'] = z.get('name')
                b['zone_type'] = z.get('zone_type')
        return b

    def create_bin(self, data: Union[Dict[str, Any], WarehouseBinCreate], conn=None) -> Dict[str, Any]:
        """Create warehouse storage bin or staging area."""
        payload = data.model_dump(exclude_unset=True) if isinstance(data, WarehouseBinCreate) else dict(data)
        if not payload.get('bin_code') or not str(payload.get('bin_code')).strip():
            try:
                payload['bin_code'] = generate_warehouse_bin_code(**_conn_kwargs(conn))
            except Exception:
                payload['bin_code'] = f"BIN-{datetime.utcnow().strftime('%M%S')}"

        # If zone_id provided, inherit profile limits if not explicitly set
        if payload.get('zone_id') and (payload.get('min_temperature') is None or payload.get('max_temperature') is None):
            zone = self.zone_repo.get(payload['zone_id'], **_conn_kwargs(conn))
            if zone:
                if payload.get('min_temperature') is None:
                    payload['min_temperature'] = zone.get('min_temperature')
                if payload.get('max_temperature') is None:
                    payload['max_temperature'] = zone.get('max_temperature')
                if not payload.get('temperature_profile'):
                    payload['temperature_profile'] = zone.get('zone_type', 'Ambient')

        return self.bin_repo.create(payload, **_conn_kwargs(conn))

    def update_bin(self, bin_id: int, data: Union[Dict[str, Any], WarehouseBinUpdate], conn=None) -> Dict[str, Any]:
        """Update warehouse bin."""
        payload = data.model_dump(exclude_unset=True) if isinstance(data, WarehouseBinUpdate) else dict(data)
        return self.bin_repo.update(bin_id, payload, **_conn_kwargs(conn))

    def delete_bin(self, bin_id: int, conn=None) -> bool:
        """Soft-delete warehouse bin."""
        return self.bin_repo.update(bin_id, {'is_active': False}, **_conn_kwargs(conn))

    # -------------------------------------------------------------------------
    # Vehicle Temperature Compartments (T0126)
    # -------------------------------------------------------------------------

    def list_compartments(self, filters: Optional[Dict[str, Any]] = None, conn=None) -> List[Dict[str, Any]]:
        """List vehicle temperature compartments."""
        f = dict(filters or {})
        if 'is_active' not in f:
            f['is_active'] = True
        compartments = self.compartment_repo.list(filters=f, **_conn_kwargs(conn))
        veh_map = {v['id']: v.get('vehicle_code') for v in self.vehicle_repo.list(**_conn_kwargs(conn))}
        for c in compartments:
            c['vehicle_code'] = veh_map.get(c.get('vehicle_id'))
        return compartments

    def get_compartment(self, compartment_id: int, conn=None) -> Optional[Dict[str, Any]]:
        """Retrieve vehicle compartment by ID."""
        c = self.compartment_repo.get(compartment_id, **_conn_kwargs(conn))
        if not c:
            return None
        veh = self.vehicle_repo.get(c.get('vehicle_id'), **_conn_kwargs(conn))
        c['vehicle_code'] = veh.get('vehicle_code') if veh else None
        return c

    def create_compartment(self, data: Union[Dict[str, Any], VehicleCompartmentCreate], conn=None) -> Dict[str, Any]:
        """Create vehicle temperature compartment."""
        payload = data.model_dump(exclude_unset=True) if isinstance(data, VehicleCompartmentCreate) else dict(data)
        if not payload.get('compartment_code') or not str(payload.get('compartment_code')).strip():
            try:
                payload['compartment_code'] = generate_vehicle_compartment_code(**_conn_kwargs(conn))
            except Exception:
                payload['compartment_code'] = f"COMP-{datetime.utcnow().strftime('%M%S')}"

        return self.compartment_repo.create(payload, **_conn_kwargs(conn))

    def update_compartment(self, compartment_id: int, data: Union[Dict[str, Any], VehicleCompartmentUpdate], conn=None) -> Dict[str, Any]:
        """Update vehicle compartment."""
        payload = data.model_dump(exclude_unset=True) if isinstance(data, VehicleCompartmentUpdate) else dict(data)
        return self.compartment_repo.update(compartment_id, payload, **_conn_kwargs(conn))

    def delete_compartment(self, compartment_id: int, conn=None) -> bool:
        """Soft-delete vehicle compartment."""
        return self.compartment_repo.update(compartment_id, {'is_active': False}, **_conn_kwargs(conn))

    # -------------------------------------------------------------------------
    # Temperature Compatibility Validation Engine
    # -------------------------------------------------------------------------

    def check_temperature_compatibility(
        self,
        product_id: int,
        target_zone_id: Optional[int] = None,
        target_bin_id: Optional[int] = None,
        target_compartment_id: Optional[int] = None,
        warehouse_id: Optional[int] = None,
        conn=None,
    ) -> TemperatureCheckResponse:
        """
        Validate whether storing or loading a product into the target zone, bin, or vehicle compartment
        satisfies cold-chain temperature boundary constraints and HACCP critical limits.
        """
        product = self.product_repo.get(product_id, **_conn_kwargs(conn))
        if not product:
            raise HTTPException(status.HTTP_404_NOT_FOUND, f"Product #{product_id} not found")

        prod_name = product.get('name')
        is_cold = bool(product.get('is_cold_chain') or (product.get('temp_zone_type') and product.get('temp_zone_type') != 'Ambient'))
        prod_zone_type = product.get('temp_zone_type') or ('Ambient' if not is_cold else 'Chilled')
        prod_min = float(product['min_temperature']) if product.get('min_temperature') is not None else None
        prod_max = float(product['max_temperature']) if product.get('max_temperature') is not None else None
        prod_crit = float(product['critical_temp_limit']) if product.get('critical_temp_limit') is not None else None

        # Resolve destination
        dest_type = 'zone'
        dest_id = target_zone_id
        dest_label = None
        dest_zone_type = 'Ambient'
        dest_min = None
        dest_max = None
        dest_current_temp = None

        if target_bin_id:
            dest_type = 'bin'
            dest_id = target_bin_id
            bin_obj = self.bin_repo.get(target_bin_id, **_conn_kwargs(conn))
            if not bin_obj:
                raise HTTPException(status.HTTP_404_NOT_FOUND, f"Bin #{target_bin_id} not found")
            dest_label = f"Bin {bin_obj.get('bin_code')}"
            dest_zone_type = bin_obj.get('temperature_profile') or 'Ambient'
            dest_min = float(bin_obj['min_temperature']) if bin_obj.get('min_temperature') is not None else None
            dest_max = float(bin_obj['max_temperature']) if bin_obj.get('max_temperature') is not None else None
            if bin_obj.get('zone_id') and (dest_min is None or dest_max is None):
                z = self.zone_repo.get(bin_obj['zone_id'], **_conn_kwargs(conn))
                if z:
                    dest_min = dest_min or (float(z['min_temperature']) if z.get('min_temperature') is not None else None)
                    dest_max = dest_max or (float(z['max_temperature']) if z.get('max_temperature') is not None else None)
                    dest_current_temp = float(z['current_temperature']) if z.get('current_temperature') is not None else None

        elif target_compartment_id:
            dest_type = 'compartment'
            dest_id = target_compartment_id
            comp_obj = self.compartment_repo.get(target_compartment_id, **_conn_kwargs(conn))
            if not comp_obj:
                raise HTTPException(status.HTTP_404_NOT_FOUND, f"Vehicle compartment #{target_compartment_id} not found")
            dest_label = f"Compartment {comp_obj.get('compartment_code')} ({comp_obj.get('name')})"
            dest_zone_type = comp_obj.get('temperature_zone_type') or 'Chilled'
            dest_min = float(comp_obj['min_temperature']) if comp_obj.get('min_temperature') is not None else None
            dest_max = float(comp_obj['max_temperature']) if comp_obj.get('max_temperature') is not None else None
            dest_current_temp = float(comp_obj['current_temperature']) if comp_obj.get('current_temperature') is not None else None

        elif target_zone_id:
            dest_type = 'zone'
            dest_id = target_zone_id
            zone_obj = self.zone_repo.get(target_zone_id, **_conn_kwargs(conn))
            if not zone_obj:
                raise HTTPException(status.HTTP_404_NOT_FOUND, f"Temperature zone #{target_zone_id} not found")
            dest_label = f"Zone {zone_obj.get('zone_code')} ({zone_obj.get('name')})"
            dest_zone_type = zone_obj.get('zone_type') or 'Ambient'
            dest_min = float(zone_obj['min_temperature']) if zone_obj.get('min_temperature') is not None else None
            dest_max = float(zone_obj['max_temperature']) if zone_obj.get('max_temperature') is not None else None
            dest_current_temp = float(zone_obj['current_temperature']) if zone_obj.get('current_temperature') is not None else None

        else:
            # If no destination specified, assume Ambient
            dest_type = 'ambient'
            dest_label = 'Standard Ambient Storage'
            dest_zone_type = 'Ambient'
            dest_min = 15.0
            dest_max = 25.0

        # Compatibility check logic
        is_compatible = True
        severity = None
        is_haccp_violation = False
        quarantine_recommended = False
        message = f"Product '{prod_name}' is fully compatible with destination {dest_label}."

        # Non-cold items in ambient: compatible
        if not is_cold and dest_zone_type.lower() == 'ambient':
            is_compatible = True
        elif is_cold:
            # Check thermal zone classification mismatch
            p_type = prod_zone_type.lower()
            d_type = dest_zone_type.lower()

            # Incompatible conditions
            if ('froz' in p_type or 'deep' in p_type) and ('ambient' in d_type or 'chill' in d_type):
                is_compatible = False
                severity = 'Critical'
                is_haccp_violation = True
                quarantine_recommended = True
                message = f"CRITICAL HACCP VIOLATION: Cannot place {prod_zone_type} product '{prod_name}' in {dest_zone_type} area ({dest_label}). Spoilage / defrost risk!"
            elif 'chill' in p_type and 'ambient' in d_type:
                is_compatible = False
                severity = 'Critical'
                is_haccp_violation = True
                quarantine_recommended = True
                message = f"CRITICAL HACCP VIOLATION: Chilled product '{prod_name}' requires 2-4°C refrigeration; assigned to Ambient area ({dest_label})."
            elif 'ambient' in p_type and ('froz' in d_type or 'deep' in d_type):
                is_compatible = False
                severity = 'Warning'
                quarantine_recommended = False
                message = f"WARNING: Ambient product '{prod_name}' assigned to Frozen zone ({dest_label}); freezing damage may occur."
            elif prod_crit is not None and dest_max is not None and dest_max > prod_crit:
                is_compatible = False
                severity = 'Critical'
                is_haccp_violation = True
                quarantine_recommended = True
                message = f"CRITICAL HACCP LIMIT BREACH: Destination max temp ({dest_max}°C) exceeds product critical threshold ({prod_crit}°C) for '{prod_name}'."
            elif prod_max is not None and dest_min is not None and dest_min > prod_max:
                is_compatible = False
                severity = 'Warning'
                message = f"Temperature range mismatch: Destination min temp ({dest_min}°C) is above product max limit ({prod_max}°C)."
            elif prod_min is not None and dest_max is not None and dest_max < prod_min:
                is_compatible = False
                severity = 'Warning'
                message = f"Temperature range mismatch: Destination max temp ({dest_max}°C) is below product min limit ({prod_min}°C)."

        return TemperatureCheckResponse(
            is_compatible=is_compatible,
            product_id=product_id,
            product_name=prod_name,
            product_temp_zone_type=prod_zone_type,
            product_min_temp=prod_min,
            product_max_temp=prod_max,
            product_critical_limit=prod_crit,
            destination_type=dest_type,
            destination_id=dest_id,
            destination_label=dest_label,
            destination_min_temp=dest_min,
            destination_max_temp=dest_max,
            current_destination_temp=dest_current_temp,
            severity=severity,
            is_haccp_violation=is_haccp_violation,
            quarantine_recommended=quarantine_recommended,
            message=message,
        )

    # -------------------------------------------------------------------------
    # Thermal Picking Sequence Route Optimization
    # -------------------------------------------------------------------------

    def get_thermal_pick_sequence(self, items: List[Dict[str, Any]]) -> List[ThermalPickSequenceItem]:
        """
        Sort order lines or pick items by thermal priority rank so that Ambient items
        are picked first (Rank 1) and refrigerated/frozen items are picked last immediately
        prior to vehicle dispatch (Chilled = Rank 2, Frozen = Rank 3, Deep Freeze = Rank 4).
        """
        def rank_key(it):
            r = it.get('thermal_priority_rank')
            if r is not None:
                return int(r)
            z = str(it.get('temp_zone_type') or 'Ambient').lower()
            if 'deep' in z:
                return 4
            if 'froz' in z:
                return 3
            if 'chill' in z:
                return 2
            return 1

        sorted_items = sorted(items, key=rank_key)
        results = []
        for idx, item in enumerate(sorted_items, 1):
            r = rank_key(item)
            z_type = item.get('temp_zone_type') or ('Ambient' if r == 1 else ('Chilled' if r == 2 else ('Frozen' if r == 3 else 'Deep Freeze')))
            results.append(ThermalPickSequenceItem(
                item_id=item.get('id') or idx,
                product_id=item.get('product_id') or 0,
                product_name=item.get('product_name') or f"Product #{item.get('product_id')}",
                temp_zone_type=z_type,
                thermal_priority_rank=r,
                min_temperature=item.get('min_temperature'),
                max_temperature=item.get('max_temperature'),
                critical_temp_limit=item.get('critical_temp_limit'),
                suggested_picking_order=idx,
                zone_label=f"Rank #{r} ({z_type})",
            ))
        return results
