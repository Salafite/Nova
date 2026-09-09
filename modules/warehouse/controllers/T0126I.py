"""
Nova ERP — Vehicle Temperature Compartments Controller (T0126I)
Manages multi-temperature partition compartments on delivery fleet vehicles.
"""
import logging
from modules.warehouse.models.temperature_zone import (
    VehicleCompartmentCreate,
    VehicleCompartmentUpdate,
    VehicleCompartmentResponse,
)
from modules.warehouse.services.cold_chain_service import ColdChainService, COMPARTMENT_REPO
from modules.core.services.base import CrudService
from modules.core.controllers.base import create_crud_router

logger = logging.getLogger(__name__)

compartment_service = CrudService(COMPARTMENT_REPO)

router = create_crud_router(
    '/api/T0126I',
    'T0126 - Vehicle Temperature Compartments',
    compartment_service,
    VehicleCompartmentCreate,
    VehicleCompartmentUpdate,
    VehicleCompartmentResponse,
)
