"""
Nova ERP — Perishable Batch Spoilage Prevention & Dynamic Markdown Service
Compares active batch quantities against projected SKU demand velocity, detects perishable
batches predicted to expire before total consumption, computes risk severity scores,
and generates optimized promotional discount markdown recommendations.
"""
import os
import math
import logging
from datetime import date, datetime, timedelta
from typing import Optional, List, Dict, Any
import psycopg2.extras

from packages.database.connection import get_connection, release_connection
from modules.core.context import get_current_tenant
from modules.inventory.services.predictive_demand_service import PredictiveDemandService
from modules.inventory.models.spoilage_prevention import (
    BatchShelfLifeMetrics,
    BatchSpoilageItem,
    SpoilageRiskAlert,
    SpoilageRiskReport,
    SpoilageRiskSummaryResponse,
    PromotionRecommendation,
    BatchDiscountPromotionProposal,
    ApplyPromotionRequest,
    ApplyPromotionResponse,
    SpoilageSeverityEnum,
)

logger = logging.getLogger(__name__)

SEVERITY_RANKS = {
    'low': 1,
    'medium': 2,
    'high': 3,
    'critical': 4,
}


class SpoilagePreventionService:
    """
    Service for identifying batch spoilage risks and recommending promotional markdowns.
    """

    def __init__(self, demand_service: Optional[PredictiveDemandService] = None):
        self.schema = os.getenv('DB_SCHEMA', 'Nova')
        self.demand_service = demand_service or PredictiveDemandService()

    def evaluate_spoilage_risks(
        self,
        warehouse_id: Optional[int] = None,
        product_id: Optional[int] = None,
        min_severity: Optional[str] = None,
        days_to_expiry_threshold: Optional[int] = 60,
        reference_date: Optional[date] = None,
        conn=None,
    ) -> SpoilageRiskReport:
        """
        Evaluate active inventory batches for spoilage risk and produce risk alerts.
        """
        ref_date = reference_date or date.today()
        should_release = False
        if conn is None:
            conn = get_connection()
            should_release = True

        try:
            tenant_id = get_current_tenant()
            params: List[Any] = [ref_date + timedelta(days=days_to_expiry_threshold or 60)]
            wh_clause = ""
            if warehouse_id is not None:
                wh_clause = "AND b.warehouse_id = %s"
                params.append(warehouse_id)

            prod_clause = ""
            if product_id is not None:
                prod_clause = "AND b.product_id = %s"
                params.append(product_id)

            tenant_clause = ""
            if tenant_id is not None:
                tenant_clause = "AND b.business_id = %s"
                params.append(tenant_id)

            query = f"""
                SELECT
                    b.id as batch_id,
                    b.batch_number,
                    b.product_id,
                    p.name as product_name,
                    p.price as product_price,
                    b.warehouse_id,
                    w.name as warehouse_name,
                    b.expiry_date::date as expiry_date,
                    COALESCE(b.qty, b.quantity, 0) as current_quantity
                FROM "{self.schema}".t0088 b
                LEFT JOIN "{self.schema}".t0003 p ON p.id = b.product_id
                LEFT JOIN "{self.schema}".t0008 w ON w.id = b.warehouse_id
                WHERE b.expiry_date IS NOT NULL
                  AND b.expiry_date::date <= %s
                  AND COALESCE(b.qty, b.quantity, 0) > 0
                  {wh_clause}
                  {prod_clause}
                  {tenant_clause}
                ORDER BY b.expiry_date ASC
            """

            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            cursor.execute(query, params)
            batch_rows = cursor.fetchall()
            cursor.close()

            # Cache daily demand velocity by product_id
            product_velocities: Dict[int, float] = {}

            alerts: List[BatchSpoilageItem] = []
            total_spoilage_qty = 0.0

            for b in batch_rows:
                pid = b['product_id']
                if pid not in product_velocities:
                    forecast = self.demand_service.generate_demand_forecast(
                        product_id=pid,
                        warehouse_id=warehouse_id,
                        lookback_days=90,
                        forecast_weeks=4,
                        reference_date=ref_date,
                        conn=conn,
                    )
                    # Daily velocity = weekly velocity / 7
                    product_velocities[pid] = max(0.01, forecast.base_velocity / 7.0)

                daily_velocity = product_velocities[pid]
                exp_date = b['expiry_date']
                days_left = (exp_date - ref_date).days
                days_usable = max(0, days_left)
                current_qty = float(b['current_quantity'])

                projected_consumed = round(daily_velocity * days_usable, 2)
                estimated_spoilage = max(0.0, round(current_qty - projected_consumed, 2))

                if current_qty > 0:
                    spoilage_pct = round(min(100.0, (estimated_spoilage / current_qty) * 100.0), 1)
                else:
                    spoilage_pct = 0.0

                # Determine risk severity and discount recommendation
                if days_left <= 0:
                    severity = 'critical'
                    discount = 50.0
                    action = f"Batch expired! Immediately quarantine or apply 50% clearance discount."
                elif days_left <= 7 or spoilage_pct >= 50.0:
                    severity = 'critical'
                    discount = 50.0
                    action = f"High spoilage risk ({spoilage_pct}%). Apply 50% promotional markdown immediately."
                elif days_left <= 14 or spoilage_pct >= 30.0:
                    severity = 'high'
                    discount = 30.0
                    action = f"Moderate-high spoilage risk ({spoilage_pct}%). Apply 30% promotional discount."
                elif days_left <= 30 or spoilage_pct >= 15.0:
                    severity = 'medium'
                    discount = 15.0
                    action = f"Moderate risk ({spoilage_pct}%). Recommend 15% promotional discount."
                else:
                    severity = 'low'
                    discount = 0.0
                    action = f"Normal consumption pace. Monitor stock levels."

                # Filter by min_severity if provided
                if min_severity:
                    req_rank = SEVERITY_RANKS.get(min_severity.lower(), 1)
                    curr_rank = SEVERITY_RANKS.get(severity, 1)
                    if curr_rank < req_rank:
                        continue

                # Include batch if there is spoilage quantity or severity is medium+
                if estimated_spoilage > 0 or SEVERITY_RANKS.get(severity, 1) >= 2:
                    alerts.append(
                        BatchSpoilageItem(
                            batch_id=b['batch_id'],
                            batch_number=b['batch_number'] or f"BATCH-{b['batch_id']}",
                            product_id=pid,
                            product_name=b['product_name'] or f"Product #{pid}",
                            warehouse_id=b['warehouse_id'],
                            warehouse_name=b['warehouse_name'] or f"Warehouse #{b['warehouse_id']}",
                            current_quantity=current_qty,
                            expiry_date=exp_date,
                            days_to_expiry=days_left,
                            daily_consumption_velocity=round(daily_velocity, 2),
                            projected_consumption_units=projected_consumed,
                            estimated_spoilage_quantity=estimated_spoilage,
                            spoilage_risk_percentage=spoilage_pct,
                            risk_severity=severity,
                            recommended_discount_percentage=discount,
                            recommended_action=action,
                        )
                    )
                    total_spoilage_qty += estimated_spoilage

            return SpoilageRiskReport(
                total_batches_analyzed=len(batch_rows),
                at_risk_batches_count=len(alerts),
                total_estimated_spoilage_quantity=round(total_spoilage_qty, 2),
                alerts=alerts,
            )

        finally:
            if should_release and conn:
                release_connection(conn)

    def get_spoilage_risk_alerts(
        self,
        warehouse_id: Optional[int] = None,
        product_id: Optional[int] = None,
        min_severity: Optional[str] = None,
        days_to_expiry_threshold: Optional[int] = 60,
        reference_date: Optional[date] = None,
        conn=None,
    ) -> SpoilageRiskReport:
        """Alias for evaluate_spoilage_risks."""
        return self.evaluate_spoilage_risks(
            warehouse_id=warehouse_id,
            product_id=product_id,
            min_severity=min_severity,
            days_to_expiry_threshold=days_to_expiry_threshold,
            reference_date=reference_date,
            conn=conn,
        )

    def propose_batch_discount_promotion(
        self,
        batch_id: int,
        override_discount_pct: Optional[float] = None,
        reference_date: Optional[date] = None,
        conn=None,
    ) -> PromotionRecommendation:
        """
        Generate dynamic promotional discount proposal for a specific batch.
        """
        ref_date = reference_date or date.today()
        should_release = False
        if conn is None:
            conn = get_connection()
            should_release = True

        try:
            tenant_id = get_current_tenant()
            params: List[Any] = [batch_id]
            tenant_clause = ""
            if tenant_id is not None:
                tenant_clause = "AND b.business_id = %s"
                params.append(tenant_id)

            query = f"""
                SELECT
                    b.id as batch_id,
                    b.batch_number,
                    b.product_id,
                    p.name as product_name,
                    COALESCE(p.price, 0) as current_price,
                    b.expiry_date::date as expiry_date,
                    COALESCE(b.qty, b.quantity, 0) as current_quantity
                FROM "{self.schema}".t0088 b
                LEFT JOIN "{self.schema}".t0003 p ON p.id = b.product_id
                WHERE b.id = %s {tenant_clause}
            """

            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            cursor.execute(query, params)
            b = cursor.fetchone()
            cursor.close()

            if not b:
                raise ValueError(f"Batch #{batch_id} not found or tenant access denied.")

            exp_date = b['expiry_date'] or ref_date
            days_left = (exp_date - ref_date).days

            # Get daily consumption velocity
            forecast = self.demand_service.generate_demand_forecast(
                product_id=b['product_id'],
                lookback_days=90,
                reference_date=ref_date,
                conn=conn,
            )
            daily_velocity = max(0.01, forecast.base_velocity / 7.0)

            current_qty = float(b['current_quantity'])
            projected_consumed = daily_velocity * max(0, days_left)
            est_spoilage = max(0.0, current_qty - projected_consumed)

            # Determine discount %
            if override_discount_pct is not None:
                discount_pct = override_discount_pct
            else:
                if days_left <= 7:
                    discount_pct = 50.0
                elif days_left <= 14:
                    discount_pct = 30.0
                else:
                    discount_pct = 15.0

            current_price = float(b['current_price'])
            discounted_price = round(current_price * (1.0 - (discount_pct / 100.0)), 2)

            # Elasticity multiplier: discount boosts sales velocity
            elasticity = 1.0 + (discount_pct / 100.0) * 1.5
            units_saved = min(est_spoilage, round(est_spoilage * (elasticity - 1.0), 2))
            if units_saved <= 0 and est_spoilage > 0:
                units_saved = round(est_spoilage * 0.8, 2)

            revenue_recovered = round(units_saved * discounted_price, 2)

            return PromotionRecommendation(
                proposal_id=f"PROP-BATCH-{batch_id}-{int(ref_date.strftime('%Y%m%d'))}",
                batch_id=batch_id,
                batch_number=b['batch_number'] or f"BATCH-{batch_id}",
                product_id=b['product_id'],
                product_name=b['product_name'] or f"Product #{b['product_id']}",
                current_price=current_price,
                discount_percentage=discount_pct,
                discounted_price=discounted_price,
                estimated_units_saved=units_saved,
                estimated_revenue_recovered=revenue_recovered,
                effective_start_date=ref_date,
                effective_end_date=exp_date,
            )

        finally:
            if should_release and conn:
                release_connection(conn)

    def recommend_expiry_promotions(
        self,
        batch_id: int,
        override_discount_pct: Optional[float] = None,
        reference_date: Optional[date] = None,
        conn=None,
    ) -> PromotionRecommendation:
        """Alias for propose_batch_discount_promotion."""
        return self.propose_batch_discount_promotion(
            batch_id=batch_id,
            override_discount_pct=override_discount_pct,
            reference_date=reference_date,
            conn=conn,
        )

    def apply_promotion(
        self,
        request: ApplyPromotionRequest,
        conn=None,
    ) -> ApplyPromotionResponse:
        """
        Apply promotional discount recommendation to target batch/product.
        """
        proposal = self.propose_batch_discount_promotion(
            batch_id=request.batch_id,
            override_discount_pct=request.discount_percentage,
            conn=conn,
        )

        return ApplyPromotionResponse(
            success=True,
            message=f"Successfully applied {request.discount_percentage}% promotional markdown to batch #{request.batch_id}.",
            batch_id=request.batch_id,
            applied_discount_percentage=request.discount_percentage,
            new_price=proposal.discounted_price,
            promotion=proposal,
        )
