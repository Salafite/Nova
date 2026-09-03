from typing import Optional, List, Dict, Any
from datetime import date, datetime
from modules.core.services.base import CrudService
from modules.sales.repositories.volume_pricing_repo import (
    VolumePricingRepository,
    VolumeTierBreakRepository,
    CustomerGroupPriceListRepository,
    CustomerContractRepository,
)


class VolumePricingService(CrudService):
    def __init__(self, repo: Optional[VolumePricingRepository] = None):
        self.vp_repo = repo or VolumePricingRepository()
        super().__init__(self.vp_repo)
        self.tier_break_svc = CrudService(self.vp_repo.tier_break_repo)
        self.group_mapping_svc = CrudService(self.vp_repo.group_mapping_repo)
        self.contract_svc = CrudService(self.vp_repo.contract_repo)

    def get_tier_breaks(self, price_list_id: int, product_id: int, conn=None) -> List[Dict[str, Any]]:
        return self.vp_repo.get_tier_breaks(price_list_id, product_id, conn=conn)

    def resolve_tier_price(
        self,
        price_list_id: int,
        product_id: int,
        quantity: float,
        base_unit_price: float,
        conn=None,
    ) -> Dict[str, Any]:
        """
        Evaluate volume pricing tier breaks for a given price list, product, and quantity.
        Returns calculated unit price, discount details, and tier information.
        """
        tier_breaks = self.get_tier_breaks(price_list_id, product_id, conn=conn)
        applicable_tier = None

        for tb in sorted(tier_breaks, key=lambda x: float(x.get('min_quantity') or x.get('min_qty') or 0.0), reverse=True):
            min_q = float(tb.get('min_quantity') or tb.get('min_qty') or 0.0)
            max_q_val = tb.get('max_quantity') if tb.get('max_quantity') is not None else tb.get('max_qty')
            max_q = float(max_q_val) if max_q_val is not None else None

            if quantity >= min_q:
                if max_q is None or quantity <= max_q:
                    applicable_tier = tb
                    break

        if not applicable_tier:
            return {
                'base_unit_price': base_unit_price,
                'final_unit_price': base_unit_price,
                'discount_amount': 0.0,
                'discount_percentage': 0.0,
                'tier_applied': None,
            }

        discount_type = applicable_tier.get('discount_type') or applicable_tier.get('pricing_type') or 'FixedPrice'
        unit_price = applicable_tier.get('unit_price')
        discount_percent = float(applicable_tier.get('discount_percentage') or applicable_tier.get('discount_percent') or 0.0)
        discount_amt = float(applicable_tier.get('discount_amount') or 0.0)

        final_price = base_unit_price
        calculated_discount_amt = 0.0
        calculated_discount_pct = 0.0

        if discount_type in ('FixedPrice', 'Fixed Price') and unit_price is not None:
            final_price = float(unit_price)
            calculated_discount_amt = round(base_unit_price - final_price, 2)
            if base_unit_price > 0:
                calculated_discount_pct = round((calculated_discount_amt / base_unit_price) * 100.0, 2)
        elif discount_type in ('Percentage', 'Percentage Discount') or discount_percent > 0:
            calculated_discount_pct = discount_percent
            calculated_discount_amt = round(base_unit_price * (discount_percent / 100.0), 2)
            final_price = round(base_unit_price - calculated_discount_amt, 2)
        elif discount_type in ('FixedAmount', 'Fixed Discount') or discount_amt > 0:
            calculated_discount_amt = discount_amt
            final_price = max(0.0, round(base_unit_price - discount_amt, 2))
            if base_unit_price > 0:
                calculated_discount_pct = round((calculated_discount_amt / base_unit_price) * 100.0, 2)

        return {
            'base_unit_price': base_unit_price,
            'final_unit_price': max(0.0, final_price),
            'discount_amount': max(0.0, calculated_discount_amt),
            'discount_percentage': max(0.0, calculated_discount_pct),
            'tier_applied': applicable_tier,
        }

    def resolve_customer_group_price_list(self, customer_group: str, conn=None) -> Optional[int]:
        mapping = self.vp_repo.get_customer_group_mapping(customer_group, conn=conn)
        return mapping.get('price_list_id') if mapping else None

    def get_contract_price(
        self,
        customer_id: int,
        product_id: int,
        quantity: float = 1.0,
        as_of_date: Optional[date] = None,
        conn=None,
    ) -> Optional[Dict[str, Any]]:
        contract = self.vp_repo.get_customer_contract(customer_id, product_id, eval_date=as_of_date, conn=conn)
        if not contract:
            return None

        min_ord_qty = float(contract.get('min_order_quantity') or 1.0)
        if quantity < min_ord_qty:
            return None

        return contract


volume_pricing_service = VolumePricingService()
