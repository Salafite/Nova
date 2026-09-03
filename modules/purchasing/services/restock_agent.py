import logging
from datetime import date, datetime, timezone
from typing import Optional, List, Dict, Any

from modules.purchasing.services.demand_forecast_service import (
    DemandForecastService,
    DEFAULT_LOOKBACK_DAYS,
    DEFAULT_SAFETY_MARGIN_DAYS,
    DEFAULT_TARGET_COVERAGE_DAYS,
)
from modules.administration.services.notification_service import NotificationService

logger = logging.getLogger(__name__)


class RestockAgentService:
    """Proactive background restock agent service that analyzes demand velocity,
    projects stockouts, evaluates supplier lead times & MOQs, and generates
    structured morning digests with one-click restock recommendations.
    """

    def __init__(
        self,
        forecast_service: Optional[DemandForecastService] = None,
        notification_service: Optional[NotificationService] = None,
    ):
        self.forecast_service = forecast_service or DemandForecastService()
        self.notification_service = notification_service or NotificationService()

    def run_evaluation(
        self,
        warehouse_id: Optional[int] = None,
        days: int = DEFAULT_LOOKBACK_DAYS,
        safety_margin_days: int = DEFAULT_SAFETY_MARGIN_DAYS,
        target_coverage_days: int = DEFAULT_TARGET_COVERAGE_DAYS,
        send_notification: bool = True,
        reference_date: Optional[date] = None,
        target_roles: Optional[List[str]] = None,
        conn=None,
    ) -> Dict[str, Any]:
        """Run a complete demand forecasting evaluation across the product catalog,
        compile at-risk restock recommendations, and optionally dispatch a morning digest notification.
        """
        eval_timestamp = datetime.now(timezone.utc).isoformat()

        # 1. Calculate forecasts across active inventory catalog
        all_forecasts = self.forecast_service.calculate_all_forecasts(
            warehouse_id=warehouse_id,
            days=days,
            safety_margin_days=safety_margin_days,
            target_coverage_days=target_coverage_days,
            only_at_risk=False,
            reference_date=reference_date,
            conn=conn,
        )

        # 2. Filter down to restock recommendations and aggregate draft PO queue by primary supplier
        recommendations = [f for f in all_forecasts if f.get('needs_restock')]
        supplier_draft_pos = self.forecast_service.get_aggregated_supplier_draft_pos(
            warehouse_id=warehouse_id,
            days=days,
            safety_margin_days=safety_margin_days,
            target_coverage_days=target_coverage_days,
            only_at_risk=True,
            reference_date=reference_date,
            conn=conn,
        )

        total_skus_evaluated = len(all_forecasts)
        at_risk_count = len(recommendations)
        critical_count = sum(1 for r in recommendations if r.get('urgency') == 'CRITICAL')
        high_count = sum(1 for r in recommendations if r.get('urgency') == 'HIGH')
        medium_count = sum(1 for r in recommendations if r.get('urgency') == 'MEDIUM')

        total_suggested_qty = round(
            sum(float(r.get('suggested_order_qty', 0.0) or 0.0) for r in recommendations), 2
        )
        total_estimated_spend = round(
            sum(float(r.get('estimated_cost', 0.0) or 0.0) for r in recommendations), 2
        )

        # 3. Format Morning Digest text and summary
        if critical_count > 0:
            digest_title = f"AI Restock Morning Digest: {at_risk_count} SKU{'s' if at_risk_count != 1 else ''} require restock ({critical_count} critical)"
        elif at_risk_count > 0:
            digest_title = f"AI Restock Morning Digest: {at_risk_count} SKU{'s' if at_risk_count != 1 else ''} require restock"
        else:
            digest_title = "AI Restock Morning Digest: All inventory levels healthy"

        digest_message = self.format_digest_message(
            recommendations=recommendations,
            total_evaluated=total_skus_evaluated,
            at_risk_count=at_risk_count,
            critical_count=critical_count,
            high_count=high_count,
            medium_count=medium_count,
            total_suggested_qty=total_suggested_qty,
            total_estimated_spend=total_estimated_spend,
        )

        # 4. Dispatch notification if requested and there are at-risk items
        notifications_sent = []
        if send_notification and at_risk_count > 0:
            try:
                notifications_sent = self.notification_service.notify_roles(
                    roles=target_roles or ['admin', 'purchasing', 'procurement', 'manager'],
                    title=digest_title,
                    message=digest_message,
                    notification_type='Restock',
                    reference_type='restock_digest',
                    reference_id=None,
                    conn=conn,
                )
            except Exception as e:
                logger.error(f"Failed to dispatch restock morning digest notification: {e}")

        return {
            'status': 'success',
            'evaluated_at': eval_timestamp,
            'total_skus_evaluated': total_skus_evaluated,
            'at_risk_count': at_risk_count,
            'critical_count': critical_count,
            'high_count': high_count,
            'medium_count': medium_count,
            'total_suggested_qty': total_suggested_qty,
            'total_estimated_spend': total_estimated_spend,
            'recommendations': recommendations,
            'supplier_draft_pos': supplier_draft_pos,
            'digest_title': digest_title,
            'digest_message': digest_message,
            'notifications_sent': len(notifications_sent),
        }

    def get_recommendations(
        self,
        warehouse_id: Optional[int] = None,
        days: int = DEFAULT_LOOKBACK_DAYS,
        safety_margin_days: int = DEFAULT_SAFETY_MARGIN_DAYS,
        target_coverage_days: int = DEFAULT_TARGET_COVERAGE_DAYS,
        only_at_risk: bool = True,
        conn=None,
    ) -> List[Dict[str, Any]]:
        """Retrieve current restock suggestions on-demand without dispatching notifications."""
        return self.forecast_service.calculate_all_forecasts(
            warehouse_id=warehouse_id,
            days=days,
            safety_margin_days=safety_margin_days,
            target_coverage_days=target_coverage_days,
            only_at_risk=only_at_risk,
            conn=conn,
        )

    def get_supplier_draft_po_queue(
        self,
        warehouse_id: Optional[int] = None,
        days: int = DEFAULT_LOOKBACK_DAYS,
        safety_margin_days: int = DEFAULT_SAFETY_MARGIN_DAYS,
        target_coverage_days: int = DEFAULT_TARGET_COVERAGE_DAYS,
        only_at_risk: bool = True,
        reference_date: Optional[date] = None,
        conn=None,
    ) -> List[Dict[str, Any]]:
        """Retrieve aggregated draft PO suggestions grouped by primary supplier."""
        return self.forecast_service.get_aggregated_supplier_draft_pos(
            warehouse_id=warehouse_id,
            days=days,
            safety_margin_days=safety_margin_days,
            target_coverage_days=target_coverage_days,
            only_at_risk=only_at_risk,
            reference_date=reference_date,
            conn=conn,
        )

    def format_digest_message(
        self,
        recommendations: List[Dict[str, Any]],
        total_evaluated: int,
        at_risk_count: int,
        critical_count: int,
        high_count: int,
        medium_count: int,
        total_suggested_qty: float,
        total_estimated_spend: float,
    ) -> str:
        """Build clean human-readable digest summary with SKU highlights."""
        if at_risk_count == 0:
            return (
                f"Proactive Demand Forecast evaluated {total_evaluated} active SKUs. "
                f"All inventory levels are above reorder thresholds with no stockouts projected."
            )

        lines = [
            f"Proactive Demand Forecast evaluated {total_evaluated} active SKUs.",
            f"• At-Risk SKUs: {at_risk_count} ({critical_count} Critical, {high_count} High, {medium_count} Medium)",
            f"• Total Suggested Restock Spend: ${total_estimated_spend:,.2f} ({total_suggested_qty:.0f} units)",
            "",
            "Top Restock Requisitions:",
        ]

        for idx, rec in enumerate(recommendations[:5], start=1):
            sku = rec.get('sku', '')
            p_name = rec.get('product_name', '')
            urgency = rec.get('urgency', 'MEDIUM')
            days_inv = rec.get('days_of_inventory')
            days_inv_str = f"{days_inv:.1f}d supply" if days_inv is not None else "0d"
            qty = rec.get('suggested_order_qty', 0.0)
            cost = rec.get('estimated_cost', 0.0)
            supplier = rec.get('supplier_name') or 'Default Supplier'
            stockout_date = rec.get('projected_stockout_date') or 'Immediate'

            lines.append(
                f"{idx}. [{urgency}] {sku} ({p_name}): {days_inv_str} left (Stockout: {stockout_date}). "
                f"Order {qty:.0f} units from '{supplier}' (${cost:,.2f})."
            )

        if len(recommendations) > 5:
            lines.append(f"... and {len(recommendations) - 5} more items requiring restock.")

        lines.append("\nReview and approve restock orders in Purchasing -> Restock Suggestions.")
        return "\n".join(lines)
