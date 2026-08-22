import logging
from typing import Optional, Dict, Any, List, Union
from datetime import date
from ..models.executive_analytics import (
    ExecutiveAnalyticsFilter,
    DeliveryRouteMetricItem,
    DeliveryFulfillmentSummaryResponse,
    WarehouseDeliveryMetricItem,
    CustomerDestinationMetricItem,
    DeliveryVarianceLineItem,
)
from ..repositories.delivery_analytics_repo import (
    DeliveryAnalyticsRepository,
    delivery_analytics_repo as default_repo,
)
from .executive_analytics_service import resolve_date_range

logger = logging.getLogger(__name__)


class DeliveryAnalyticsService:
    def __init__(self, repo: Optional[DeliveryAnalyticsRepository] = None):
        self.repo = repo or default_repo

    def _normalize_filter(
        self,
        filter_input: Union[ExecutiveAnalyticsFilter, Dict[str, Any], None],
    ) -> tuple[ExecutiveAnalyticsFilter, date, date]:
        if filter_input is None:
            flt = ExecutiveAnalyticsFilter()
        elif isinstance(filter_input, dict):
            flt = ExecutiveAnalyticsFilter(**filter_input)
        else:
            flt = filter_input

        start_date, end_date = resolve_date_range(
            period=flt.period,
            date_from=flt.date_from,
            date_to=flt.date_to,
        )
        return flt, start_date, end_date

    def get_delivery_fulfillment_summary(
        self,
        filters: Union[ExecutiveAnalyticsFilter, Dict[str, Any], None] = None,
        conn=None,
    ) -> DeliveryFulfillmentSummaryResponse:
        """
        Computes delivery route fulfillment statistics, on-time delivery (OTD) rates,
        completion rates, freight cost per delivery, and quantity variances.
        """
        flt, start_date, end_date = self._normalize_filter(filters)

        # Retrieve route level data
        route_rows = self.repo.get_route_fulfillment_data(
            date_from=start_date,
            date_to=end_date,
            warehouse_id=flt.warehouse_id,
            delivery_route=flt.delivery_route,
            customer_id=flt.customer_id,
            sales_rep_id=flt.sales_rep_id,
            conn=conn,
        )

        # Retrieve global summary KPIs
        kpi_data = self.repo.get_delivery_summary_kpis(
            date_from=start_date,
            date_to=end_date,
            warehouse_id=flt.warehouse_id,
            delivery_route=flt.delivery_route,
            customer_id=flt.customer_id,
            sales_rep_id=flt.sales_rep_id,
            conn=conn,
        )

        routes: List[DeliveryRouteMetricItem] = []
        for r in route_rows:
            total_deliv = int(r.get('total_deliveries', 0))
            completed = int(r.get('completed_deliveries', 0))
            on_time = int(r.get('on_time_deliveries', 0))
            delayed = int(r.get('delayed_deliveries', 0))
            freight = round(float(r.get('total_freight_cost', 0.0)), 2)
            qty_ord = round(float(r.get('total_qty_ordered', 0.0)), 2)
            qty_ship = round(float(r.get('total_qty_shipped', 0.0)), 2)

            otd_rate = round((on_time / completed * 100.0), 2) if completed > 0 else (
                round((on_time / total_deliv * 100.0), 2) if total_deliv > 0 else 0.0
            )
            comp_rate = round((completed / total_deliv * 100.0), 2) if total_deliv > 0 else 0.0
            avg_freight = round((freight / total_deliv), 2) if total_deliv > 0 else 0.0
            var_pct = round(((qty_ship - qty_ord) / qty_ord * 100.0), 2) if qty_ord > 0 else 0.0

            routes.append(
                DeliveryRouteMetricItem(
                    delivery_route=r.get('delivery_route', 'Unassigned'),
                    warehouse_id=r.get('warehouse_id'),
                    warehouse_name=r.get('warehouse_name'),
                    total_deliveries=total_deliv,
                    completed_deliveries=completed,
                    on_time_deliveries=on_time,
                    delayed_deliveries=delayed,
                    on_time_delivery_rate=otd_rate,
                    route_completion_rate=comp_rate,
                    total_freight_cost=freight,
                    avg_freight_per_delivery=avg_freight,
                    total_qty_ordered=qty_ord,
                    total_qty_shipped=qty_ship,
                    fulfillment_variance_pct=var_pct,
                )
            )

        total_deliveries = int(kpi_data.get('total_deliveries', 0))
        completed_deliveries = int(kpi_data.get('completed_deliveries', 0))
        on_time_deliveries = int(kpi_data.get('on_time_deliveries', 0))
        total_freight_cost = round(float(kpi_data.get('total_freight_cost', 0.0)), 2)
        total_routes = int(kpi_data.get('total_routes', len(routes)))

        overall_on_time_rate = round((on_time_deliveries / completed_deliveries * 100.0), 2) if completed_deliveries > 0 else (
            round((on_time_deliveries / total_deliveries * 100.0), 2) if total_deliveries > 0 else 0.0
        )
        overall_completion_rate = round((completed_deliveries / total_deliveries * 100.0), 2) if total_deliveries > 0 else 0.0
        avg_freight_cost_per_order = round((total_freight_cost / total_deliveries), 2) if total_deliveries > 0 else 0.0

        return DeliveryFulfillmentSummaryResponse(
            period=flt.period,
            date_from=start_date,
            date_to=end_date,
            total_routes=total_routes,
            total_deliveries=total_deliveries,
            overall_on_time_rate=overall_on_time_rate,
            overall_completion_rate=overall_completion_rate,
            total_freight_cost=total_freight_cost,
            avg_freight_cost_per_order=avg_freight_cost_per_order,
            routes=routes,
        )

    def get_warehouse_efficiency(
        self,
        filters: Union[ExecutiveAnalyticsFilter, Dict[str, Any], None] = None,
        conn=None,
    ) -> List[WarehouseDeliveryMetricItem]:
        """
        Computes delivery fulfillment and freight metrics grouped by dispatch warehouse.
        """
        flt, start_date, end_date = self._normalize_filter(filters)

        rows = self.repo.get_warehouse_delivery_data(
            date_from=start_date,
            date_to=end_date,
            warehouse_id=flt.warehouse_id,
            conn=conn,
        )

        items: List[WarehouseDeliveryMetricItem] = []
        for r in rows:
            total_deliv = int(r.get('total_deliveries', 0))
            completed = int(r.get('completed_deliveries', 0))
            on_time = int(r.get('on_time_deliveries', 0))
            delayed = int(r.get('delayed_deliveries', 0))
            freight = round(float(r.get('total_freight_cost', 0.0)), 2)
            qty_ship = round(float(r.get('total_qty_shipped', 0.0)), 2)

            otd_rate = round((on_time / completed * 100.0), 2) if completed > 0 else (
                round((on_time / total_deliv * 100.0), 2) if total_deliv > 0 else 0.0
            )
            comp_rate = round((completed / total_deliv * 100.0), 2) if total_deliv > 0 else 0.0
            avg_freight = round((freight / total_deliv), 2) if total_deliv > 0 else 0.0

            items.append(
                WarehouseDeliveryMetricItem(
                    warehouse_id=int(r.get('warehouse_id')),
                    warehouse_name=r.get('warehouse_name', ''),
                    location=r.get('location'),
                    total_deliveries=total_deliv,
                    completed_deliveries=completed,
                    on_time_deliveries=on_time,
                    delayed_deliveries=delayed,
                    on_time_delivery_rate=otd_rate,
                    route_completion_rate=comp_rate,
                    total_freight_cost=freight,
                    avg_freight_per_delivery=avg_freight,
                    total_qty_shipped=qty_ship,
                )
            )

        return items

    def get_customer_destination_metrics(
        self,
        filters: Union[ExecutiveAnalyticsFilter, Dict[str, Any], None] = None,
        limit: int = 50,
        conn=None,
    ) -> List[CustomerDestinationMetricItem]:
        """
        Computes delivery volume, on-time rates, and freight costs by customer destination.
        """
        flt, start_date, end_date = self._normalize_filter(filters)

        rows = self.repo.get_customer_destination_delivery_data(
            date_from=start_date,
            date_to=end_date,
            warehouse_id=flt.warehouse_id,
            delivery_route=flt.delivery_route,
            customer_id=flt.customer_id,
            limit=limit,
            conn=conn,
        )

        items: List[CustomerDestinationMetricItem] = []
        for r in rows:
            total_deliv = int(r.get('total_deliveries', 0))
            completed = int(r.get('completed_deliveries', 0))
            on_time = int(r.get('on_time_deliveries', 0))
            freight = round(float(r.get('total_freight_cost', 0.0)), 2)
            qty_ship = round(float(r.get('total_qty_shipped', 0.0)), 2)

            otd_rate = round((on_time / completed * 100.0), 2) if completed > 0 else (
                round((on_time / total_deliv * 100.0), 2) if total_deliv > 0 else 0.0
            )
            avg_freight = round((freight / total_deliv), 2) if total_deliv > 0 else 0.0

            items.append(
                CustomerDestinationMetricItem(
                    customer_id=int(r.get('customer_id')),
                    customer_name=r.get('customer_name', ''),
                    customer_code=r.get('customer_code'),
                    delivery_route=r.get('delivery_route'),
                    total_deliveries=total_deliv,
                    completed_deliveries=completed,
                    on_time_delivery_rate=otd_rate,
                    total_freight_cost=freight,
                    avg_freight_per_delivery=avg_freight,
                    total_qty_shipped=qty_ship,
                )
            )

        return items

    def get_delivery_fulfillment_variances(
        self,
        filters: Union[ExecutiveAnalyticsFilter, Dict[str, Any], None] = None,
        limit: int = 100,
        conn=None,
    ) -> List[DeliveryVarianceLineItem]:
        """
        Retrieves line items where shipped quantity differs from ordered quantity.
        """
        flt, start_date, end_date = self._normalize_filter(filters)

        rows = self.repo.get_delivery_variance_details(
            date_from=start_date,
            date_to=end_date,
            warehouse_id=flt.warehouse_id,
            delivery_route=flt.delivery_route,
            limit=limit,
            conn=conn,
        )

        items: List[DeliveryVarianceLineItem] = []
        for r in rows:
            qty_ord = round(float(r.get('qty_ordered', 0.0)), 2)
            qty_ship = round(float(r.get('qty_shipped', 0.0)), 2)
            var_qty = round(float(r.get('variance_qty', qty_ship - qty_ord)), 2)
            var_pct = round((var_qty / qty_ord * 100.0), 2) if qty_ord > 0 else 0.0

            items.append(
                DeliveryVarianceLineItem(
                    delivery_id=int(r.get('delivery_id')),
                    delivery_number=r.get('delivery_number', ''),
                    delivery_route=r.get('delivery_route'),
                    product_id=r.get('product_id'),
                    product_name=r.get('product_name', ''),
                    qty_ordered=qty_ord,
                    qty_shipped=qty_ship,
                    variance_qty=var_qty,
                    variance_pct=var_pct,
                    status=r.get('status', 'Dispatched'),
                )
            )

        return items

    def get_delivery_kpi_gauges(
        self,
        filters: Union[ExecutiveAnalyticsFilter, Dict[str, Any], None] = None,
        conn=None,
    ) -> Dict[str, Any]:
        """
        Returns gauge KPIs and efficiency ratings for executive dashboard display.
        """
        summary = self.get_delivery_fulfillment_summary(filters=filters, conn=conn)

        # Evaluate performance ratings
        if summary.overall_on_time_rate >= 95.0:
            otd_rating = 'Excellent'
        elif summary.overall_on_time_rate >= 85.0:
            otd_rating = 'Good'
        elif summary.overall_on_time_rate >= 70.0:
            otd_rating = 'Needs Attention'
        else:
            otd_rating = 'Critical'

        if summary.overall_completion_rate >= 95.0:
            completion_rating = 'Optimal'
        elif summary.overall_completion_rate >= 85.0:
            completion_rating = 'Standard'
        else:
            completion_rating = 'Lagging'

        return {
            'period': summary.period,
            'date_from': summary.date_from,
            'date_to': summary.date_to,
            'total_routes': summary.total_routes,
            'total_deliveries': summary.total_deliveries,
            'overall_on_time_rate': summary.overall_on_time_rate,
            'otd_rating': otd_rating,
            'overall_completion_rate': summary.overall_completion_rate,
            'completion_rating': completion_rating,
            'total_freight_cost': summary.total_freight_cost,
            'avg_freight_cost_per_order': summary.avg_freight_cost_per_order,
            'target_otd_rate': 95.0,
            'target_completion_rate': 98.0,
        }


# Default singleton instance
delivery_analytics_service = DeliveryAnalyticsService()
