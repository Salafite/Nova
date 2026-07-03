from modules.core.controllers import all_routers
from modules.inventory.controllers.adjustments import router as adjustments_router

all_routers.append(adjustments_router)