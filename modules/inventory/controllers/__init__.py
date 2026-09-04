"""
Inventory Controllers Package
"""
from modules.inventory.controllers.predictive_inventory_controller import router as predictive_inventory_router
from modules.inventory.controllers.replenishment_controller import router as replenishment_router

__all__ = [
    "predictive_inventory_router",
    "replenishment_router",
]
