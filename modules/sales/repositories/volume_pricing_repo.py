from typing import Optional, List, Dict, Any
from datetime import date, datetime
from modules.core.repositories.base import CrudRepository


class VolumeTierBreakRepository(CrudRepository):
    def __init__(self):
        super().__init__(
            'T0116',
            business_columns=[
                'id', 'price_list_id', 'product_id', 'min_quantity', 'max_quantity',
                'unit_price', 'discount_percentage', 'discount_type', 'is_active'
            ]
        )


class CustomerGroupPriceListRepository(CrudRepository):
    def __init__(self):
        super().__init__(
            'T0117',
            business_columns=[
                'id', 'customer_group', 'price_list_id', 'priority', 'is_active'
            ]
        )


class CustomerContractRepository(CrudRepository):
    def __init__(self):
        super().__init__(
            'T0118',
            business_columns=[
                'id', 'contract_number', 'customer_id', 'product_id', 'contracted_price',
                'discount_percentage', 'min_order_quantity', 'start_date', 'end_date',
                'status', 'is_active'
            ]
        )


class PromotionalRuleRepository(CrudRepository):
    def __init__(self):
        super().__init__(
            'T0119',
            business_columns=[
                'id', 'code', 'name', 'description', 'promo_type', 'buy_product_id',
                'buy_quantity', 'get_product_id', 'get_quantity', 'get_discount_percentage',
                'customer_group', 'customer_id', 'start_date', 'end_date', 'usage_limit',
                'times_used', 'is_active'
            ]
        )


class VolumePricingRepository(CrudRepository):
    def __init__(self):
        super().__init__(
            'T0116',
            business_columns=[
                'id', 'price_list_id', 'product_id', 'min_quantity', 'max_quantity',
                'unit_price', 'discount_percentage', 'discount_type', 'is_active'
            ]
        )
        self.tier_break_repo = VolumeTierBreakRepository()
        self.group_mapping_repo = CustomerGroupPriceListRepository()
        self.contract_repo = CustomerContractRepository()
        self.promotion_repo = PromotionalRuleRepository()

    def get_tier_breaks(self, price_list_id: int, product_id: int, conn=None) -> List[Dict[str, Any]]:
        """Fetch all active volume tier breaks for a price list and product ordered by min_quantity ASC."""
        filters = {'price_list_id': price_list_id, 'product_id': product_id, 'is_active': True}
        tiers = self.tier_break_repo.list(filters=filters, order_by='min_quantity ASC', conn=conn)
        return tiers

    def get_customer_group_mapping(self, customer_group: str, conn=None) -> Optional[Dict[str, Any]]:
        """Get top priority price list assignment for customer group."""
        if not customer_group:
            return None
        mappings = self.group_mapping_repo.list(
            filters={'customer_group': customer_group, 'is_active': True},
            order_by='priority DESC',
            limit=1,
            conn=conn
        )
        return mappings[0] if mappings else None

    def get_customer_contract(self, customer_id: int, product_id: int, eval_date: Optional[date] = None, conn=None) -> Optional[Dict[str, Any]]:
        """Get active contract price override for customer and product."""
        contracts = self.contract_repo.list(
            filters={'customer_id': customer_id, 'product_id': product_id, 'is_active': True, 'status': 'Active'},
            conn=conn
        )
        if not contracts:
            return None

        current_d = eval_date or date.today()
        for c in contracts:
            st = c.get('start_date')
            et = c.get('end_date')
            if isinstance(st, str):
                st = date.fromisoformat(st)
            if isinstance(et, str):
                et = date.fromisoformat(et)

            if st and current_d < st:
                continue
            if et and current_d > et:
                continue
            return c

        return None
