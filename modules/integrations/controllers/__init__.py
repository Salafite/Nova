"""
Nova ERP — Integrations Controllers Package
"""

from modules.integrations.controllers.T0056I import router as t0056_router
from modules.integrations.controllers.T0057I import router as t0057_router
from modules.integrations.controllers.T0058I import router as t0058_router
from modules.integrations.controllers.T0134I import router as t0134_router
from modules.integrations.controllers.T0135I import router as t0135_router
from modules.integrations.controllers.T0136I import router as t0136_router
from modules.integrations.controllers.T0137I import router as t0137_router
from modules.integrations.controllers.T0138I import router as t0138_router
from modules.integrations.controllers.edi_controller import router as edi_router

__all__ = [
    "t0056_router",
    "t0057_router",
    "t0058_router",
    "t0134_router",
    "t0135_router",
    "t0136_router",
    "t0137_router",
    "t0138_router",
    "edi_router",
]
