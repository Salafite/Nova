"""
Accounts Receivable Aging Service re-export for Accounting domain.
"""

from modules.crm.services.aging_service import (
    AgingService,
    aging_service,
    calculate_aging,
    classify_overdue_days,
    parse_date,
)

__all__ = [
    'AgingService',
    'aging_service',
    'calculate_aging',
    'classify_overdue_days',
    'parse_date',
]
