"""
Nova ERP — Integrations Controllers Package
"""

from modules.integrations.controllers.T0056I import router as t0056_router
from modules.integrations.controllers.T0057I import router as t0057_router
from modules.integrations.controllers.T0058I import router as t0058_router
from modules.integrations.controllers.T0124I import router as t0124_router
from modules.integrations.controllers.T0125I import router as t0125_router
from modules.integrations.controllers.T0126I import router as t0126_router
from modules.integrations.controllers.T0127I import router as t0127_router
from modules.integrations.controllers.T0128I import router as t0128_router
from modules.integrations.controllers.edi_controller import router as edi_router

__all__ = [
    "t0056_router",
    "t0057_router",
    "t0058_router",
    "t0124_router",
    "t0125_router",
    "t0126_router",
    "t0127_router",
    "t0128_router",
    "edi_router",
]
