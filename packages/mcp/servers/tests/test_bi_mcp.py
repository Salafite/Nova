import io
import base64
from datetime import date, datetime
from unittest.mock import patch, MagicMock

from packages.mcp.servers import bi_mcp
from packages.mcp.servers.bi_mcp import register_tools, _parse_date
from modules.bi.models.executive_analytics import (
    ExecutiveMarginSummary,
    CategoryMarginResponse,
    CategoryMarginItem,
    SkuMarginResponse,
    SkuMarginItem,
    CustomerProfitabilityResponse,
    CustomerProfitabilityItem,
    QuadrantSummaryItem,
    DeliveryFulfillmentSummaryResponse,
    DeliveryRouteMetricItem,
    WarehouseDeliveryMetricItem,
)
from modules.sales.models.commission import (
    CommissionStatementResponse,
    CommissionStatementItem,
    CommissionSummaryItem,
)


def _patch(name):
    return patch.object(bi_mcp, name, MagicMock())


class TestBiMcp:
    def setup_method(self):
        from packages.mcp import registry
        registry._tools.clear()
        registry._resources.clear()
        registry._prompts.clear()

    # -----------------------------------------------------------------------
    # Helper & Standard BI Tests
    # -----------------------------------------------------------------------

    def test_parse_date_helper(self):
        assert _parse_date(None) is None
        assert _parse_date(date(2026, 8, 15)) == date(2026, 8, 15)
        assert _parse_date("2026-08-15") == date(2026, 8, 15)
        assert _parse_date("not-a-date") is None
        assert _parse_date(12345) is None

    def test_list_kpis(self):
        with _patch("_kpi_def_svc"):
            bi_mcp._kpi_def_svc.list.return_value = [{"kpi_name": "Revenue"}]
            assert bi_mcp._list_kpis()[0]["kpi_name"] == "Revenue"

    def test_get_kpi_values(self):
        with _patch("_kpi_val_svc"):
            bi_mcp._kpi_val_svc.list.return_value = [{"actual_value": 100}]
            assert bi_mcp._get_kpi_values(kpi_id=1)[0]["actual_value"] == 100

    def test_list_dashboards(self):
        with _patch("_dash_svc"):
            bi_mcp._dash_svc.list.return_value = [{"dashboard_name": "Sales"}]
            assert bi_mcp._list_dashboards()[0]["dashboard_name"] == "Sales"

    def test_get_widgets(self):
        with _patch("_widget_svc"):
            bi_mcp._widget_svc.list.return_value = [{"title": "Chart"}]
            assert bi_mcp._get_widgets(dashboard_id=1)[0]["title"] == "Chart"

    # -----------------------------------------------------------------------
    # Executive Margin Summary Tests
    # -----------------------------------------------------------------------

    def test_get_executive_margin_summary_pydantic_response(self):
        summary_model = ExecutiveMarginSummary(
            period="Monthly",
            date_from=date(2026, 1, 1),
            date_to=date(2026, 1, 31),
            gross_sales=100000.0,
            discount_amount=5000.0,
            net_revenue=95000.0,
            cogs=65000.0,
            freight_cost=5000.0,
            gross_profit=25000.0,
            gross_margin_pct=26.32,
            total_orders=150,
            total_customers=40,
            average_order_value=633.33,
            low_margin_order_count=8,
            target_margin_pct=20.0,
        )
        with _patch("_executive_analytics_svc"):
            bi_mcp._executive_analytics_svc.get_margin_summary.return_value = summary_model
            result = bi_mcp._get_executive_margin_summary(
                period="Monthly",
                date_from="2026-01-01",
                date_to="2026-01-31",
                product_id=10,
                brand="Artisan",
                sales_rep_id=3,
                customer_id=12,
                warehouse_id=2,
                delivery_route="Route-A",
            )
            assert isinstance(result, dict)
            assert result["gross_sales"] == 100000.0
            assert result["net_revenue"] == 95000.0
            assert result["gross_profit"] == 25000.0
            assert result["gross_margin_pct"] == 26.32
            assert result["low_margin_order_count"] == 8

            call_args = bi_mcp._executive_analytics_svc.get_margin_summary.call_args[1]["filters"]
            assert call_args["period"] == "Monthly"
            assert call_args["date_from"] == date(2026, 1, 1)
            assert call_args["date_to"] == date(2026, 1, 31)
            assert call_args["product_id"] == 10
            assert call_args["brand"] == "Artisan"
            assert call_args["sales_rep_id"] == 3
            assert call_args["customer_id"] == 12
            assert call_args["warehouse_id"] == 2
            assert call_args["delivery_route"] == "Route-A"

    def test_get_executive_margin_summary_dict_fallback(self):
        dict_payload = {
            "period": "Monthly",
            "gross_sales": 50000.0,
            "net_revenue": 48000.0,
            "gross_profit": 12000.0,
            "gross_margin_pct": 25.0,
        }
        with _patch("_executive_analytics_svc"):
            bi_mcp._executive_analytics_svc.get_margin_summary.return_value = dict_payload
            result = bi_mcp._get_executive_margin_summary(period="Monthly")
            assert result == dict_payload

    # -----------------------------------------------------------------------
    # Product Category & SKU Margin Tests
    # -----------------------------------------------------------------------

    def test_get_product_category_margins_categories_only(self):
        cat_resp = CategoryMarginResponse(
            period="Monthly",
            total_categories=2,
            low_margin_category_count=1,
            items=[
                CategoryMarginItem(
                    category_id=1,
                    category_name="Beverages",
                    gross_sales=60000.0,
                    net_revenue=58000.0,
                    gross_profit=18000.0,
                    gross_margin_pct=31.03,
                    revenue_share_pct=60.0,
                    units_sold=2000.0,
                    order_count=80,
                    is_low_margin=False,
                    status="Healthy",
                ),
                CategoryMarginItem(
                    category_id=2,
                    category_name="Dairy",
                    gross_sales=40000.0,
                    net_revenue=38000.0,
                    gross_profit=4500.0,
                    gross_margin_pct=11.84,
                    revenue_share_pct=40.0,
                    units_sold=1500.0,
                    order_count=50,
                    is_low_margin=True,
                    status="Low Margin Alert",
                ),
            ],
        )
        with _patch("_executive_analytics_svc"):
            bi_mcp._executive_analytics_svc.get_category_margins.return_value = cat_resp
            result = bi_mcp._get_product_category_margins(
                period="Monthly",
                min_margin_pct=10.0,
                max_margin_pct=40.0,
                include_skus=False,
            )
            assert isinstance(result, dict)
            assert result["total_categories"] == 2
            assert result["low_margin_category_count"] == 1
            assert len(result["items"]) == 2
            assert "skus" not in result

            call_args = bi_mcp._executive_analytics_svc.get_category_margins.call_args[1]["filters"]
            assert call_args["min_margin_pct"] == 10.0
            assert call_args["max_margin_pct"] == 40.0

    def test_get_product_category_margins_with_skus(self):
        cat_resp = CategoryMarginResponse(
            period="Monthly",
            total_categories=1,
            low_margin_category_count=0,
            items=[
                CategoryMarginItem(
                    category_id=1,
                    category_name="Beverages",
                    gross_sales=50000.0,
                    net_revenue=50000.0,
                    gross_profit=15000.0,
                    gross_margin_pct=30.0,
                    revenue_share_pct=100.0,
                )
            ],
        )
        sku_resp = SkuMarginResponse(
            period="Monthly",
            total_skus=1,
            low_margin_sku_count=0,
            items=[
                SkuMarginItem(
                    product_id=101,
                    sku_code="BEV-001",
                    product_name="Cold Brew Coffee 1L",
                    category_id=1,
                    category_name="Beverages",
                    brand_name="RoastCo",
                    units_sold=500.0,
                    avg_selling_price=10.0,
                    unit_cost=7.0,
                    gross_sales=5000.0,
                    discount_amount=0.0,
                    net_revenue=5000.0,
                    cogs=3500.0,
                    freight_cost=200.0,
                    gross_profit=1300.0,
                    gross_margin_pct=26.0,
                    is_low_margin=False,
                )
            ],
        )
        with _patch("_executive_analytics_svc"):
            bi_mcp._executive_analytics_svc.get_category_margins.return_value = cat_resp
            bi_mcp._executive_analytics_svc.get_sku_margins.return_value = sku_resp
            result = bi_mcp._get_product_category_margins(
                period="Monthly",
                include_skus=True,
                limit=50,
            )
            assert isinstance(result, dict)
            assert "skus" in result
            assert len(result["skus"]) == 1
            assert result["skus"][0]["sku_code"] == "BEV-001"
            assert result["skus"][0]["gross_profit"] == 1300.0
            bi_mcp._executive_analytics_svc.get_sku_margins.assert_called_once()

    # -----------------------------------------------------------------------
    # Customer Profitability Matrix Tests
    # -----------------------------------------------------------------------

    def test_get_customer_profitability_matrix(self):
        matrix_resp = CustomerProfitabilityResponse(
            period="Monthly",
            date_from=date(2026, 1, 1),
            date_to=date(2026, 1, 31),
            total_customers=4,
            revenue_median_threshold=25000.0,
            margin_threshold_pct=15.0,
            quadrants=[
                QuadrantSummaryItem(
                    quadrant="Core Stars",
                    quadrant_code="Q1",
                    description="High Volume, High Margin",
                    customer_count=1,
                    total_net_revenue=50000.0,
                    total_gross_profit=15000.0,
                    avg_margin_pct=30.0,
                    revenue_share_pct=50.0,
                    profit_share_pct=60.0,
                ),
                QuadrantSummaryItem(
                    quadrant="Volume Risks",
                    quadrant_code="Q2",
                    description="High Volume, Low Margin",
                    customer_count=1,
                    total_net_revenue=30000.0,
                    total_gross_profit=3000.0,
                    avg_margin_pct=10.0,
                    revenue_share_pct=30.0,
                    profit_share_pct=12.0,
                ),
                QuadrantSummaryItem(
                    quadrant="High Potential",
                    quadrant_code="Q3",
                    description="Low Volume, High Margin",
                    customer_count=1,
                    total_net_revenue=15000.0,
                    total_gross_profit=5000.0,
                    avg_margin_pct=33.33,
                    revenue_share_pct=15.0,
                    profit_share_pct=20.0,
                ),
                QuadrantSummaryItem(
                    quadrant="Unprofitable / Drain",
                    quadrant_code="Q4",
                    description="Low Volume, Low Margin",
                    customer_count=1,
                    total_net_revenue=5000.0,
                    total_gross_profit=400.0,
                    avg_margin_pct=8.0,
                    revenue_share_pct=5.0,
                    profit_share_pct=1.6,
                ),
            ],
            customers=[
                CustomerProfitabilityItem(
                    customer_id=1,
                    customer_code="CUST-001",
                    customer_name="Grand Hotel Dining",
                    customer_group="Hospitality",
                    sales_rep_id=2,
                    sales_rep_name="Alice Smith",
                    order_count=12,
                    gross_sales=52000.0,
                    discount_amount=2000.0,
                    net_revenue=50000.0,
                    cogs=32000.0,
                    freight_cost=3000.0,
                    gross_profit=15000.0,
                    gross_margin_pct=30.0,
                    average_order_value=4166.67,
                    quadrant="Core Stars",
                    quadrant_code="Q1",
                    recommendation="Protect and expand relationship",
                )
            ],
        )
        with _patch("_customer_profitability_svc"):
            bi_mcp._customer_profitability_svc.get_customer_profitability_matrix.return_value = matrix_resp
            result = bi_mcp._get_customer_profitability_matrix(
                period="Monthly",
                date_from="2026-01-01",
                date_to="2026-01-31",
                quadrant="Q1",
                margin_threshold_pct=18.0,
                revenue_threshold=30000.0,
                sales_rep_id=2,
            )
            assert isinstance(result, dict)
            assert result["total_customers"] == 4
            assert result["margin_threshold_pct"] == 15.0
            assert len(result["quadrants"]) == 4
            assert len(result["customers"]) == 1
            assert result["customers"][0]["quadrant_code"] == "Q1"
            assert result["customers"][0]["gross_profit"] == 15000.0

            call_kwargs = bi_mcp._customer_profitability_svc.get_customer_profitability_matrix.call_args[1]
            assert call_kwargs["margin_threshold_pct"] == 18.0
            assert call_kwargs["revenue_threshold"] == 30000.0
            assert call_kwargs["filters"]["quadrant"] == "Q1"
            assert call_kwargs["filters"]["sales_rep_id"] == 2

    # -----------------------------------------------------------------------
    # Sales Rep Commission Tests
    # -----------------------------------------------------------------------

    def test_calculate_sales_rep_commissions_single_rep(self):
        stmt_resp = CommissionStatementResponse(
            sales_rep_id=5,
            sales_rep_name="Bob Jones",
            sales_rep_email="bob@nova-erp.com",
            period_start=date(2026, 1, 1),
            period_end=date(2026, 1, 31),
            rule_name="Standard Tiered Gross Margin Rule",
            total_booked_sales=80000.0,
            total_collected_amount=75000.0,
            total_cogs=50000.0,
            total_freight_cost=3000.0,
            total_discounts_granted=2000.0,
            total_realized_gross_margin=20000.0,
            average_realized_margin_pct=26.67,
            gross_commission_earned=1000.0,
            total_discount_penalties=100.0,
            net_commission_payable=900.0,
            paid_commission_amount=0.0,
            pending_commission_amount=900.0,
            items=[
                CommissionStatementItem(
                    invoice_id=201,
                    invoice_number="INV-2026-001",
                    order_number="SO-1001",
                    customer_id=10,
                    customer_name="Fresh Bistro",
                    invoice_total=40000.0,
                    collected_cash=40000.0,
                    cogs=27000.0,
                    freight_cost=1500.0,
                    discount_amount=1000.0,
                    realized_gross_margin=10500.0,
                    realized_margin_pct=26.25,
                    commission_rate=5.0,
                    gross_commission=525.0,
                    discount_penalty=50.0,
                    net_commission=475.0,
                    status="Pending",
                )
            ],
        )
        with _patch("_commission_svc"):
            bi_mcp._commission_svc.calculate_statement.return_value = stmt_resp
            result = bi_mcp._calculate_sales_rep_commissions(
                sales_rep_id=5,
                period_start="2026-01-01",
                period_end="2026-01-31",
                rule_id=1,
                include_pending=True,
            )
            assert isinstance(result, dict)
            assert result["sales_rep_id"] == 5
            assert result["total_collected_amount"] == 75000.0
            assert result["total_realized_gross_margin"] == 20000.0
            assert result["net_commission_payable"] == 900.0
            assert len(result["items"]) == 1

            call_kwargs = bi_mcp._commission_svc.calculate_statement.call_args[1]
            assert call_kwargs["sales_rep_id"] == 5
            assert call_kwargs["period_start"] == date(2026, 1, 1)
            assert call_kwargs["period_end"] == date(2026, 1, 31)
            assert call_kwargs["rule_id"] == 1
            assert call_kwargs["include_pending"] is True

    def test_calculate_sales_rep_commissions_all_reps(self):
        summaries = [
            CommissionSummaryItem(
                sales_rep_id=1,
                sales_rep_name="Alice Smith",
                sales_rep_email="alice@nova.com",
                total_invoices=15,
                total_collected=120000.0,
                total_gross_margin=36000.0,
                avg_margin_pct=30.0,
                gross_commission=1800.0,
                discount_penalty=100.0,
                net_commission=1700.0,
                paid_commission=1000.0,
                pending_commission=700.0,
            ),
            CommissionSummaryItem(
                sales_rep_id=2,
                sales_rep_name="Bob Jones",
                sales_rep_email="bob@nova.com",
                total_invoices=8,
                total_collected=60000.0,
                total_gross_margin=15000.0,
                avg_margin_pct=25.0,
                gross_commission=750.0,
                discount_penalty=50.0,
                net_commission=700.0,
                paid_commission=0.0,
                pending_commission=700.0,
            ),
        ]
        with _patch("_commission_svc"):
            bi_mcp._commission_svc.get_commission_summaries.return_value = summaries
            result = bi_mcp._calculate_sales_rep_commissions(
                sales_rep_id=None,
                period_start="2026-01-01",
                period_end="2026-01-31",
            )
            assert isinstance(result, list)
            assert len(result) == 2
            assert result[0]["sales_rep_name"] == "Alice Smith"
            assert result[0]["net_commission"] == 1700.0
            assert result[1]["sales_rep_name"] == "Bob Jones"
            assert result[1]["net_commission"] == 700.0

            call_kwargs = bi_mcp._commission_svc.get_commission_summaries.call_args[1]
            assert call_kwargs["period_start"] == date(2026, 1, 1)
            assert call_kwargs["period_end"] == date(2026, 1, 31)
            assert call_kwargs["sales_rep_id"] is None

    # -----------------------------------------------------------------------
    # Delivery Fulfillment Metrics Tests
    # -----------------------------------------------------------------------

    def test_get_delivery_fulfillment_metrics_with_warehouses(self):
        delivery_resp = DeliveryFulfillmentSummaryResponse(
            period="Monthly",
            date_from=date(2026, 1, 1),
            date_to=date(2026, 1, 31),
            total_routes=2,
            total_deliveries=120,
            overall_on_time_rate=95.0,
            overall_completion_rate=98.33,
            total_freight_cost=6000.0,
            avg_freight_cost_per_order=50.0,
            routes=[
                DeliveryRouteMetricItem(
                    delivery_route="Route-North",
                    warehouse_id=1,
                    warehouse_name="Central Hub",
                    total_deliveries=70,
                    completed_deliveries=69,
                    on_time_deliveries=67,
                    delayed_deliveries=2,
                    on_time_delivery_rate=97.1,
                    route_completion_rate=98.57,
                    total_freight_cost=3500.0,
                    avg_freight_per_delivery=50.0,
                    total_qty_ordered=1400.0,
                    total_qty_shipped=1380.0,
                    fulfillment_variance_pct=1.43,
                )
            ],
        )
        warehouse_metrics = [
            WarehouseDeliveryMetricItem(
                warehouse_id=1,
                warehouse_name="Central Hub",
                location="North Industrial Zone",
                total_deliveries=70,
                completed_deliveries=69,
                on_time_deliveries=67,
                delayed_deliveries=2,
                on_time_delivery_rate=97.1,
                route_completion_rate=98.57,
                total_freight_cost=3500.0,
                avg_freight_per_delivery=50.0,
                total_qty_shipped=1380.0,
            )
        ]
        with _patch("_delivery_analytics_svc"):
            bi_mcp._delivery_analytics_svc.get_delivery_fulfillment_summary.return_value = delivery_resp
            bi_mcp._delivery_analytics_svc.get_warehouse_efficiency.return_value = warehouse_metrics
            result = bi_mcp._get_delivery_fulfillment_metrics(
                period="Monthly",
                delivery_route="Route-North",
                warehouse_id=1,
                include_warehouses=True,
            )
            assert isinstance(result, dict)
            assert result["total_routes"] == 2
            assert result["overall_on_time_rate"] == 95.0
            assert len(result["routes"]) == 1
            assert "warehouses" in result
            assert len(result["warehouses"]) == 1
            assert result["warehouses"][0]["warehouse_name"] == "Central Hub"

    def test_get_delivery_fulfillment_metrics_without_warehouses(self):
        delivery_resp = DeliveryFulfillmentSummaryResponse(
            period="Monthly",
            total_routes=1,
            total_deliveries=50,
            overall_on_time_rate=92.0,
            overall_completion_rate=96.0,
            total_freight_cost=2500.0,
            avg_freight_cost_per_order=50.0,
            routes=[],
        )
        with _patch("_delivery_analytics_svc"):
            bi_mcp._delivery_analytics_svc.get_delivery_fulfillment_summary.return_value = delivery_resp
            result = bi_mcp._get_delivery_fulfillment_metrics(
                period="Monthly",
                include_warehouses=False,
            )
            assert isinstance(result, dict)
            assert result["total_deliveries"] == 50
            assert "warehouses" not in result
            bi_mcp._delivery_analytics_svc.get_warehouse_efficiency.assert_not_called()

    # -----------------------------------------------------------------------
    # Report Export Engine Tests
    # -----------------------------------------------------------------------

    def test_export_executive_analytics_report_pdf(self):
        fake_pdf_bytes = b"%PDF-1.4 sample executive financial report pdf content"
        fake_stream = io.BytesIO(fake_pdf_bytes)

        with _patch("_pdf_export_svc"):
            bi_mcp._pdf_export_svc.generate_pdf.return_value = fake_stream
            result = bi_mcp._export_executive_analytics_report(
                format="pdf",
                period="Quarterly",
                confidentiality_notice="STRICTLY CONFIDENTIAL",
            )
            assert result["format"] == "pdf"
            assert result["content_type"] == "application/pdf"
            assert result["size_bytes"] == len(fake_pdf_bytes)
            assert result["status"] == "generated"
            assert "Executive_Analytics_Report_Quarterly" in result["filename"]
            assert base64.b64decode(result["data_base64"]) == fake_pdf_bytes

            call_kwargs = bi_mcp._pdf_export_svc.generate_pdf.call_args[1]
            assert call_kwargs["confidentiality_notice"] == "STRICTLY CONFIDENTIAL"
            assert call_kwargs["filters"]["period"] == "Quarterly"

    def test_export_executive_analytics_report_excel(self):
        fake_xlsx_bytes = b"PK\x03\x04 fake excel workbook byte stream"
        fake_stream = io.BytesIO(fake_xlsx_bytes)

        with _patch("_excel_export_svc"):
            bi_mcp._excel_export_svc.generate_workbook.return_value = fake_stream
            result = bi_mcp._export_executive_analytics_report(
                format="excel",
                period="YTD",
            )
            assert result["format"] == "excel"
            assert result["content_type"] == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            assert result["size_bytes"] == len(fake_xlsx_bytes)
            assert result["status"] == "generated"
            assert "Executive_Analytics_YTD" in result["filename"]
            assert base64.b64decode(result["data_base64"]) == fake_xlsx_bytes

    def test_export_executive_analytics_report_json(self):
        summary_model = ExecutiveMarginSummary(
            period="Monthly",
            date_from=date(2026, 1, 1),
            date_to=date(2026, 1, 31),
            gross_sales=100000.0,
            gross_profit=25000.0,
            gross_margin_pct=25.0,
        )
        cat_resp = CategoryMarginResponse(total_categories=1, items=[])
        matrix_resp = CustomerProfitabilityResponse(total_customers=5, quadrants=[], customers=[])
        summaries = [
            CommissionSummaryItem(
                sales_rep_id=1,
                sales_rep_name="Alice",
                net_commission=1200.0,
            )
        ]
        delivery_resp = DeliveryFulfillmentSummaryResponse(total_routes=2, routes=[])

        with (
            _patch("_executive_analytics_svc"),
            _patch("_customer_profitability_svc"),
            _patch("_commission_svc"),
            _patch("_delivery_analytics_svc"),
        ):
            bi_mcp._executive_analytics_svc.get_margin_summary.return_value = summary_model
            bi_mcp._executive_analytics_svc.get_category_margins.return_value = cat_resp
            bi_mcp._customer_profitability_svc.get_customer_profitability_matrix.return_value = matrix_resp
            bi_mcp._commission_svc.get_commission_summaries.return_value = summaries
            bi_mcp._delivery_analytics_svc.get_delivery_fulfillment_summary.return_value = delivery_resp

            result = bi_mcp._export_executive_analytics_report(
                format="json",
                period="Monthly",
            )
            assert result["format"] == "json"
            assert result["period"] == "Monthly"
            assert result["date_from"] == "2026-01-01"
            assert result["date_to"] == "2026-01-31"
            assert "CONFIDENTIAL" in result["confidentiality_notice"]
            assert result["executive_summary"]["gross_sales"] == 100000.0
            assert result["executive_summary"]["gross_profit"] == 25000.0
            assert result["category_margins"]["total_categories"] == 1
            assert result["customer_profitability"]["total_customers"] == 5
            assert len(result["commissions"]) == 1
            assert result["commissions"][0]["sales_rep_name"] == "Alice"
            assert result["delivery_fulfillment"]["total_routes"] == 2

    # -----------------------------------------------------------------------
    # Tool & Resource Registration Tests
    # -----------------------------------------------------------------------

    def test_register_tools_and_schemas(self):
        register_tools()
        from packages.mcp.registry import get_tools
        tools = get_tools()
        names = [t.name for t in tools]

        # Standard BI tools
        assert "list_kpis" in names
        assert "get_kpi_values" in names
        assert "list_dashboards" in names
        assert "get_dashboard_widgets" in names

        # Executive Analytics tools
        assert "get_executive_margin_summary" in names
        assert "get_product_category_margins" in names
        assert "get_customer_profitability_matrix" in names
        assert "calculate_sales_rep_commissions" in names
        assert "get_delivery_fulfillment_metrics" in names
        assert "export_executive_analytics_report" in names

        # Validate schema properties of executive tools
        tool_dict = {t.name: t for t in tools}

        margin_tool = tool_dict["get_executive_margin_summary"]
        assert "period" in margin_tool.input_schema["properties"]
        assert "brand" in margin_tool.input_schema["properties"]
        assert "sales_rep_id" in margin_tool.input_schema["properties"]

        cat_tool = tool_dict["get_product_category_margins"]
        assert "include_skus" in cat_tool.input_schema["properties"]
        assert "min_margin_pct" in cat_tool.input_schema["properties"]

        cust_tool = tool_dict["get_customer_profitability_matrix"]
        assert "quadrant" in cust_tool.input_schema["properties"]
        assert "margin_threshold_pct" in cust_tool.input_schema["properties"]

        comm_tool = tool_dict["calculate_sales_rep_commissions"]
        assert "sales_rep_id" in comm_tool.input_schema["properties"]
        assert "include_pending" in comm_tool.input_schema["properties"]

        deliv_tool = tool_dict["get_delivery_fulfillment_metrics"]
        assert "delivery_route" in deliv_tool.input_schema["properties"]
        assert "include_warehouses" in deliv_tool.input_schema["properties"]

        export_tool = tool_dict["export_executive_analytics_report"]
        assert "format" in export_tool.input_schema["properties"]
        assert "confidentiality_notice" in export_tool.input_schema["properties"]

    def test_executive_margin_resource_registered_and_callable(self):
        register_tools()
        from packages.mcp.registry import list_resources, read_resource
        resources = list_resources()
        uris = [r.uri for r in resources]
        assert "nova://bi/executive-margin" in uris

        with _patch("_executive_analytics_svc"):
            bi_mcp._executive_analytics_svc.get_margin_summary.return_value = {
                "gross_margin_pct": 28.5,
                "gross_profit": 57000.0,
            }
            res = read_resource("nova://bi/executive-margin")
            assert res["gross_margin_pct"] == 28.5
            assert res["gross_profit"] == 57000.0
