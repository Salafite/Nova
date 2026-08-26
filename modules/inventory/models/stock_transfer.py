"""
Nova ERP — Stock Transfers & Inter-Branch Replenishment Pydantic Models (Inventory Domain)
"""
from datetime import date
from typing import Optional
from modules.warehouse.models.stock_transfer import (
    StockTransferLineCreate,
    StockTransferLineUpdate,
    StockTransferLineResponse,
    StockTransferCreate,
    StockTransferUpdate,
    StockTransferResponse,
    StockTransferDispatchLine,
    StockTransferDispatch,
    StockTransferLossDetail,
    StockTransferReceiveLine,
    StockTransferReceive,
    ReplenishmentSuggestionItem,
    ReplenishmentSuggestionResponse,
    ReplenishmentGenerateItem,
    ReplenishmentGenerateRequest,
    ReplenishmentGenerateResponse,
)

__all__ = [
    "StockTransferLineCreate",
    "StockTransferLineUpdate",
    "StockTransferLineResponse",
    "StockTransferCreate",
    "StockTransferUpdate",
    "StockTransferResponse",
    "StockTransferDispatchLine",
    "StockTransferDispatch",
    "StockTransferLossDetail",
    "StockTransferReceiveLine",
    "StockTransferReceive",
    "ReplenishmentSuggestionItem",
    "ReplenishmentSuggestionResponse",
    "ReplenishmentGenerateItem",
    "ReplenishmentGenerateRequest",
    "ReplenishmentGenerateResponse",
]
