from modules.inventory.models.product import (
    UOMCreate, UOMUpdate, UOMResponse,
    UOMConvCreate, UOMConvUpdate, UOMConvResponse,
    ProductCreate, ProductUpdate, ProductResponse,
    BarcodeCreate, BarcodeUpdate, BarcodeResponse,
    AttrDefCreate, AttrDefUpdate, AttrDefResponse,
    AttrValueCreate, AttrValueUpdate, AttrValueResponse,
    ProductUOMCreate, ProductUOMUpdate, ProductUOMResponse,
    ProductTypeCreate, ProductTypeUpdate, ProductTypeResponse,
)
from modules.inventory.models.stock_movement import (
    StockMovementCreate, StockMovementResponse,
)
from modules.inventory.models.warehouse import (
    WarehouseCreate, WarehouseUpdate, WarehouseResponse,
)
from modules.inventory.models.stock_level import (
    StockLevelCreate, StockLevelUpdate, StockLevelResponse,
)
from modules.inventory.models.stock_transfer import (
    StockTransferLineCreate, StockTransferLineUpdate, StockTransferLineResponse,
    StockTransferCreate, StockTransferUpdate, StockTransferResponse,
    StockTransferDispatchLine, StockTransferDispatch,
    StockTransferLossDetail, StockTransferReceiveLine, StockTransferReceive,
    ReplenishmentSuggestionItem, ReplenishmentSuggestionResponse,
    ReplenishmentGenerateItem, ReplenishmentGenerateRequest, ReplenishmentGenerateResponse,
)
from modules.inventory.models.predictive_demand import (
    ConfidenceInterval, WeeklyForecastPoint, WeeklyDemandProjection,
    HistoricalSalesAggregation, SeasonalTrendAdjustment,
    SKUForecastParameters, DemandForecastResponse,
)
from modules.inventory.models.predictive_forecast import (
    ConfidenceInterval as ConfidenceInterval_PF,
)
from modules.inventory.models.spoilage_prevention import (
    BatchShelfLifeMetrics, SpoilageSeverityEnum, BatchSpoilageItem, SpoilageRiskAlert,
    SpoilageRiskReport, SpoilageRiskSummaryResponse, PromotionRecommendation,
    BatchDiscountPromotionProposal, ApplyPromotionRequest, ApplyPromotionResponse,
)
