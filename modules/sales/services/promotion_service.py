from typing import Optional, List, Dict, Any
from datetime import datetime, date
from modules.core.repositories.base import CrudRepository
from modules.core.services.base import CrudService
from modules.sales.models.price_list import PromotionalRewardItem


class PromotionService(CrudService):
    def __init__(self, promo_repo: Optional[CrudRepository] = None):
        self.promo_repo = promo_repo or CrudRepository(
            'T0119',
            business_columns=[
                'id', 'code', 'name', 'description', 'promo_type', 'buy_product_id',
                'buy_quantity', 'get_product_id', 'get_quantity', 'get_discount_percentage',
                'customer_group', 'customer_id', 'start_date', 'end_date', 'usage_limit',
                'times_used', 'is_active'
            ]
        )
        super().__init__(self.promo_repo)

    def list_active_promotions(
        self,
        customer_id: Optional[int] = None,
        customer_group: Optional[str] = None,
        price_list_id: Optional[int] = None,
        as_of_date: Optional[datetime] = None,
        conn=None,
    ) -> List[Dict[str, Any]]:
        """List active promotions matching eligibility criteria and date window."""
        eval_dt = as_of_date or datetime.now()
        rules = self.promo_repo.list(filters={'is_active': True}, conn=conn)

        active_rules = []
        for r in rules:
            st = r.get('start_date')
            et = r.get('end_date')

            if isinstance(st, str):
                try:
                    st = datetime.fromisoformat(st.replace('Z', '+00:00'))
                except Exception:
                    st = None
            elif isinstance(st, date) and not isinstance(st, datetime):
                st = datetime.combine(st, datetime.min.time())

            if isinstance(et, str):
                try:
                    et = datetime.fromisoformat(et.replace('Z', '+00:00'))
                except Exception:
                    et = None
            elif isinstance(et, date) and not isinstance(et, datetime):
                et = datetime.combine(et, datetime.max.time())

            if st and eval_dt < st:
                continue
            if et and eval_dt > et:
                continue

            r_cg = r.get('customer_group')
            if r_cg and customer_group and r_cg.lower() != customer_group.lower():
                continue

            r_cid = r.get('customer_id')
            if r_cid and customer_id and r_cid != customer_id:
                continue

            # Check usage limit
            usage_limit = r.get('usage_limit')
            times_used = r.get('times_used', 0)
            if usage_limit is not None and times_used >= usage_limit:
                continue

            active_rules.append(r)

        return active_rules

    def evaluate_promotions(
        self,
        customer_id: Optional[int] = None,
        customer_group: Optional[str] = None,
        price_list_id: Optional[int] = None,
        line_items: Optional[List[Dict[str, Any]]] = None,
        as_of_date: Optional[datetime] = None,
        conn=None,
    ) -> Dict[str, Any]:
        """
        Evaluate line items against active promotional rules.
        Returns list of PromotionalRewardItem models for Buy-X-Get-Y deals.
        """
        if not line_items:
            return {'rewards': [], 'line_discounts': {}}

        active_rules = self.list_active_promotions(
            customer_id=customer_id,
            customer_group=customer_group,
            price_list_id=price_list_id,
            as_of_date=as_of_date,
            conn=conn,
        )

        rewards: List[PromotionalRewardItem] = []
        line_discounts: Dict[int, Dict[str, float]] = {}

        product_quantities: Dict[int, float] = {}
        for line in line_items:
            pid = line.get('product_id')
            qty = float(line.get('quantity') or line.get('qty') or 0.0)
            if pid:
                product_quantities[pid] = product_quantities.get(pid, 0.0) + qty

        for rule in active_rules:
            promo_type = rule.get('promo_type', 'BuyXGetY')
            buy_pid = rule.get('buy_product_id')
            buy_qty = float(rule.get('buy_quantity') or rule.get('buy_min_qty') or 1.0)
            get_pid = rule.get('get_product_id') or buy_pid
            get_qty = float(rule.get('get_quantity') or rule.get('get_qty') or 1.0)
            get_disc = float(rule.get('get_discount_percentage') or rule.get('discount_percent') or 100.0)

            if promo_type in ('BuyXGetY', 'BUY_X_GET_Y'):
                if buy_pid and buy_pid in product_quantities:
                    purchased_qty = product_quantities[buy_pid]
                    if purchased_qty >= buy_qty and buy_qty > 0:
                        multiplier = int(purchased_qty // buy_qty)
                        total_reward_qty = multiplier * get_qty
                        reward_item = PromotionalRewardItem(
                            promo_id=rule['id'],
                            promo_code=rule.get('code', f"PROMO-{rule['id']}"),
                            promo_name=rule.get('name', 'Promotional Deal'),
                            buy_product_id=buy_pid,
                            reward_product_id=get_pid,
                            reward_quantity=total_reward_qty,
                            reward_discount_percentage=get_disc,
                            notes=f"Buy {buy_qty} Get {get_qty} Promo Applied ({multiplier}x)",
                        )
                        rewards.append(reward_item)

        return {
            'rewards': rewards,
            'line_discounts': line_discounts,
        }


promotion_service = PromotionService()
