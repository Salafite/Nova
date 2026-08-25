"""Pydantic data models for the Automated Legacy ERP Database Connector and Migration Bridge.

Defines typed schemas for:
1. Legacy connection configurations (SQL Server, CSV/Dump, generic)
2. Schema discovery and table/column metadata
3. Entity mapping and field translation rules
4. Data cleansing options and phantom product detection
5. Dry-run simulation requests, results, and row validation errors
6. Comprehensive customer balance and inventory reconciliation reports
7. One-click commit and instant rollback payloads and batch tracking models
"""

from datetime import date, datetime
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field

from modules.core.models.base import AuditMixin, TenantMixin


# ==============================================================================
# 1. Connection Configurations and Testing
# ==============================================================================

class SQLServerConnectionConfig(BaseModel):
    """Connection parameters for legacy Microsoft SQL Server instances."""
    host: str = "localhost"
    port: int = 1433
    database: str
    user: str = "sa"
    password: str = ""
    trust_server_certificate: bool = True
    driver: Optional[str] = None
    timeout: int = 30
    schema_name: str = "dbo"


class CsvDumpConnectionConfig(BaseModel):
    """Configuration parameters for multi-table CSV files and SQL dump archives."""
    dump_path: Optional[str] = None
    delimiter: Optional[str] = None  # None triggers auto-detection (, ; \t |)
    encoding: Optional[str] = None   # None triggers auto-detection (utf-8, cp1252, windows-1256)
    quote_char: str = '"'
    has_header: bool = True
    zip_file_path: Optional[str] = None


class ConnectorConfig(BaseModel):
    """Generic legacy database connector configuration wrapper."""
    source_type: str = "sqlserver"  # sqlserver | csv_dump | mysql | postgres
    sqlserver: Optional[SQLServerConnectionConfig] = None
    csv_dump: Optional[CsvDumpConnectionConfig] = None
    custom_options: Dict[str, Any] = Field(default_factory=dict)


class ConnectionTestRequest(BaseModel):
    """Request payload to test connectivity to a legacy database or file dump."""
    source_type: str = "sqlserver"
    config: Dict[str, Any] = Field(default_factory=dict)


class ConnectionTestResponse(BaseModel):
    """Response returned from testing legacy data source connection."""
    success: bool
    message: str
    latency_ms: float = 0.0
    server_version: Optional[str] = None
    database_name: Optional[str] = None
    tables_count: int = 0
    tables: List[str] = Field(default_factory=list)
    details: Dict[str, Any] = Field(default_factory=dict)
    error: Optional[str] = None


# ==============================================================================
# 2. Schema Discovery and Preview Models
# ==============================================================================

class ColumnMetadata(BaseModel):
    """Metadata schema for a column in a legacy table."""
    name: str
    data_type: str = "VARCHAR"
    is_nullable: bool = True
    is_primary_key: bool = False
    is_foreign_key: bool = False
    foreign_table: Optional[str] = None
    foreign_column: Optional[str] = None
    max_length: Optional[int] = None
    precision: Optional[int] = None
    scale: Optional[int] = None
    default_value: Optional[str] = None
    ordinal_position: Optional[int] = None
    raw_type: Optional[str] = None


class TableMetadata(BaseModel):
    """Metadata schema for a legacy database table or CSV dataset."""
    table_name: str
    columns: List[ColumnMetadata] = Field(default_factory=list)
    column_names: List[str] = Field(default_factory=list)
    primary_key: List[str] = Field(default_factory=list)
    foreign_keys: List[Dict[str, Any]] = Field(default_factory=list)
    row_count_estimate: Optional[int] = None
    description: Optional[str] = None


class SchemaDiscoveryRequest(BaseModel):
    """Request payload to introspect legacy schema tables and column definitions."""
    source_type: str = "sqlserver"
    config: Dict[str, Any] = Field(default_factory=dict)
    table_filter: Optional[List[str]] = None


class SchemaDiscoveryResponse(BaseModel):
    """Introspection result containing legacy table schemas and column mappings."""
    success: bool
    database_name: Optional[str] = None
    tables_count: int = 0
    tables: List[str] = Field(default_factory=list)
    schemas: Dict[str, TableMetadata] = Field(default_factory=dict)
    error: Optional[str] = None


class TablePreviewRequest(BaseModel):
    """Request to fetch a sampled preview slice from a legacy table."""
    source_type: str = "sqlserver"
    config: Dict[str, Any] = Field(default_factory=dict)
    table_name: str
    limit: int = 50
    columns: Optional[List[str]] = None


class TablePreviewResponse(BaseModel):
    """Sampled rows and column names from a legacy table."""
    table_name: str
    columns: List[str] = Field(default_factory=list)
    total_rows_estimate: Optional[int] = None
    sample_rows: List[Dict[str, Any]] = Field(default_factory=list)
    row_count: int = 0


# ==============================================================================
# 3. Entity Mapping and Field Translation Rules
# ==============================================================================

class FieldMappingRule(BaseModel):
    """Single field mapping rule from a legacy column to a Nova entity attribute."""
    source_field: str
    target_field: str
    target_type: Optional[str] = None  # string, int, float, decimal, bool, date, datetime
    default_value: Optional[Any] = None
    transform: Optional[str] = None    # uppercase, lowercase, trim, strip_non_numeric, round_2
    is_required: bool = False


class TableMappingRule(BaseModel):
    """Mapping configuration between a legacy table and a target Nova T-code entity."""
    entity_type: str                  # products, customers, suppliers, price_lists, inventory_opening, etc.
    target_tcode: str                 # T0003, T0010, T0011, T0083, T0009, T0090, etc.
    target_table: str                 # t0003, t0010, t0011, t0083, t0009, t0090, etc.
    source_table: str
    primary_key_field: Optional[str] = None
    field_mappings: Dict[str, str] = Field(default_factory=dict)
    advanced_field_rules: List[FieldMappingRule] = Field(default_factory=list)
    filter_clause: Optional[str] = None
    enabled: bool = True


class MigrationMappingConfig(BaseModel):
    """Full migration mapping specification across multiple entities."""
    mappings: Dict[str, TableMappingRule] = Field(default_factory=dict)
    auto_fuzzy_match: bool = True
    custom_overrides: Dict[str, Dict[str, str]] = Field(default_factory=dict)

    @property
    def table_mappings(self) -> Dict[str, TableMappingRule]:
        return self.mappings


# ==============================================================================
# 4. Data Cleansing and Phantom Product Options
# ==============================================================================

class DataCleansingConfig(BaseModel):
    """Automated sanitization, normalization, and phantom product rules."""
    enable_phantom_detection: bool = True
    phantom_inactivity_months: int = 12
    phantom_zero_stock_check: bool = True
    phantom_action: str = "flag"       # flag | skip | isolate
    deduplicate_skus: bool = True
    deduplicate_barcodes: bool = True
    duplicate_resolution: str = "skip" # skip | overwrite | suffix
    sanitize_phone_numbers: bool = True
    sanitize_email_addresses: bool = True
    default_uom: str = "PCS"
    default_category: str = "General"
    default_warehouse: str = "Main Warehouse"
    auto_create_missing_lookups: bool = True
    clamp_negative_stock: bool = True
    normalize_text_casing: bool = True


class CleansingLogItem(BaseModel):
    """Record of a single data cleansing or normalization action taken."""
    entity_type: str
    source_key: Optional[str] = None
    rule: str
    field_name: Optional[str] = None
    original_value: Any = None
    cleansed_value: Any = None
    action_taken: str
    message: str


class CleansingSummary(BaseModel):
    """Metrics and statistics summary from automated cleansing run."""
    total_records_processed: int = 0
    phantom_products_detected: int = 0
    phantom_products_skipped: int = 0
    duplicates_resolved: int = 0
    contacts_sanitized: int = 0
    lookups_auto_created: int = 0
    clamped_numeric_values: int = 0
    discovered_lookups: Dict[str, List[str]] = Field(default_factory=dict)
    logs_sample: List[CleansingLogItem] = Field(default_factory=list)


# ==============================================================================
# 5. Dry-Run Simulation and Row Validation Models
# ==============================================================================

class DryRunRequest(BaseModel):
    """Payload to trigger a complete dry-run migration simulation."""
    source_type: str = "sqlserver"
    connection_config: Dict[str, Any] = Field(default_factory=dict)
    mapping_config: Optional[MigrationMappingConfig] = None
    cleansing_config: Optional[DataCleansingConfig] = None
    selected_entities: Optional[List[str]] = None
    sample_limit: Optional[int] = None
    tenant_id: Optional[int] = None


class RowValidationError(BaseModel):
    """Row-level validation or schema transformation error."""
    row_index: int
    source_key: Optional[str] = None
    entity_type: str
    target_table: Optional[str] = None
    field_name: Optional[str] = None
    error_type: str  # missing_required | invalid_type | fk_not_found | duplicate | constraint
    message: str
    raw_data: Optional[Dict[str, Any]] = None
    severity: str = "error"  # error | warning


class DryRunResult(BaseModel):
    """Result of a dry-run migration simulation with metrics and reconciliation summary."""
    batch_key: str
    batch_id: Optional[int] = None
    success: bool
    total_source_rows: int = 0
    valid_rows_count: int = 0
    warning_rows_count: int = 0
    error_rows_count: int = 0
    phantom_products_count: int = 0
    execution_duration_ms: float = 0.0
    entity_summaries: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    cleansing_summary: Optional[CleansingSummary] = None
    validation_errors: List[RowValidationError] = Field(default_factory=list)
    sample_transformed: Dict[str, List[Dict[str, Any]]] = Field(default_factory=dict)
    reconciliation_summary: Optional[Dict[str, Any]] = None
    ready_for_commit: bool = False

    @property
    def total_records_processed(self) -> int:
        return self.total_source_rows

    @property
    def valid_records_count(self) -> int:
        return self.valid_rows_count

    @property
    def error_records_count(self) -> int:
        return self.error_rows_count


# ==============================================================================
# 6. Reconciliation Report Structures
# ==============================================================================

class CustomerBalanceItem(BaseModel):
    """Line-by-line reconciliation entry for a customer opening balance."""
    customer_key: str
    customer_name: str
    legacy_balance: float
    nova_balance: float
    delta: float
    is_matched: bool
    notes: Optional[str] = None


class CustomerBalanceReconciliation(BaseModel):
    """Reconciliation summary comparing legacy receivables against Nova opening balances."""
    total_legacy_receivables: float = 0.0
    total_nova_receivables: float = 0.0
    total_receivables_delta: float = 0.0
    customers_count: int = 0
    matched_count: int = 0
    mismatched_count: int = 0
    discrepancies: List[CustomerBalanceItem] = Field(default_factory=list)
    top_variances: List[CustomerBalanceItem] = Field(default_factory=list)
    is_reconciled: bool = True

    @property
    def is_balanced(self) -> bool:
        return self.is_reconciled

    @property
    def delta_total(self) -> float:
        return self.total_receivables_delta


class WarehouseStockItem(BaseModel):
    """Reconciliation entry for a product inventory stock level and valuation."""
    product_key: str
    sku: str
    product_name: str
    warehouse_name: str
    legacy_quantity: float
    nova_quantity: float
    quantity_delta: float
    unit_cost: float = 0.0
    legacy_valuation: float = 0.0
    nova_valuation: float = 0.0
    valuation_delta: float = 0.0
    is_negative_stock: bool = False
    is_matched: bool = True
    status: str = "OK"  # OK | Mismatch | NegativeStock | MissingInTarget


class WarehouseReconciliationSummary(BaseModel):
    """Stock quantity and valuation breakdown for a single warehouse."""
    warehouse_name: str
    legacy_total_quantity: float = 0.0
    nova_total_quantity: float = 0.0
    quantity_delta: float = 0.0
    legacy_total_valuation: float = 0.0
    nova_total_valuation: float = 0.0
    valuation_delta: float = 0.0
    item_count: int = 0
    mismatched_count: int = 0


class InventoryReconciliation(BaseModel):
    """Reconciliation summary comparing legacy stock quantities and valuation against Nova."""
    total_legacy_quantity: float = 0.0
    total_nova_quantity: float = 0.0
    total_quantity_delta: float = 0.0
    total_legacy_valuation: float = 0.0
    total_nova_valuation: float = 0.0
    total_valuation_delta: float = 0.0
    negative_stock_count: int = 0
    warehouse_summaries: Dict[str, WarehouseReconciliationSummary] = Field(default_factory=dict)
    discrepancies: List[WarehouseStockItem] = Field(default_factory=list)
    is_reconciled: bool = True

    @property
    def is_balanced(self) -> bool:
        return self.is_reconciled

    @property
    def quantity_delta_total(self) -> float:
        return self.total_quantity_delta

    @property
    def valuation_delta_total(self) -> float:
        return self.total_valuation_delta


class EntityCountReconciliation(BaseModel):
    """Entity-level count verification (source vs staged vs cleansed vs errors)."""
    entity_type: str
    source_count: int = 0
    staged_count: int = 0
    phantom_count: int = 0
    cleansed_count: int = 0
    error_count: int = 0
    committed_count: int = 0
    match_status: str = "Matched"  # Matched | CleanedWithDeltas | ErrorsPresent


class ReconciliationReport(BaseModel):
    """Full comprehensive opening balance, inventory, and entity reconciliation report."""
    batch_key: str
    report_date: Optional[datetime] = None
    overall_status: str = "Passed"  # Passed | PassedWithWarnings | Failed
    customer_balance: Optional[CustomerBalanceReconciliation] = None
    inventory: Optional[InventoryReconciliation] = None
    entity_counts: Dict[str, EntityCountReconciliation] = Field(default_factory=dict)
    phantom_summary: Optional[Dict[str, Any]] = None
    unresolved_errors_count: int = 0
    recommendations: List[str] = Field(default_factory=list)


# ==============================================================================
# 7. Commit, Rollback and Batch Record Tracking Models
# ==============================================================================

class CommitMigrationRequest(BaseModel):
    """Request to commit staged migration batch into active Nova tables."""
    batch_id: int
    business_id: Optional[int] = None
    force: bool = False


class CommitMigrationResponse(BaseModel):
    """Response returned upon committing migration batch."""
    batch_id: int
    batch_key: str
    status: str = "Committed"
    total_inserted: int = 0
    inserted_rows: Optional[int] = None
    inserted_by_entity: Dict[str, int] = Field(default_factory=dict)
    execution_time_ms: float = 0.0
    completed_at: Optional[datetime] = None
    message: str = "Migration committed successfully"

    def model_post_init(self, __context: Any) -> None:
        if self.inserted_rows is None:
            self.inserted_rows = self.total_inserted


class RollbackMigrationRequest(BaseModel):
    """Request to roll back a committed or preview migration batch."""
    batch_id: int
    reason: Optional[str] = None
    business_id: Optional[int] = None


class RollbackMigrationResponse(BaseModel):
    """Response returned upon rolling back migration records."""
    batch_id: int
    batch_key: str
    status: str = "RolledBack"
    total_deleted: int = 0
    deleted_rows: Optional[int] = None
    deleted_by_entity: Dict[str, int] = Field(default_factory=dict)
    execution_time_ms: float = 0.0
    completed_at: Optional[datetime] = None
    message: str = "Migration batch rolled back successfully"

    def model_post_init(self, __context: Any) -> None:
        if self.deleted_rows is None:
            self.deleted_rows = self.total_deleted


class MigrationBatchResponse(AuditMixin):
    """Response schema representing a record in table Nova.t0104."""
    id: int
    batch_key: str
    entity_type: str
    source_type: str = "csv_dump"
    total_rows: int = 0
    inserted_rows: int = 0
    status: str = "Preview"  # Preview | Committed | RolledBack
    dry_run_completed: bool = False
    connection_config: Optional[Dict[str, Any]] = None
    reconciliation_summary: Optional[Dict[str, Any]] = None
    execution_log: Optional[Dict[str, Any]] = None
    error_details: Optional[Dict[str, Any]] = None


class MigrationBatchItemResponse(BaseModel):
    """Response schema representing an individual migrated record in Nova.t0104_items."""
    id: int
    batch_id: int
    entity_type: str
    target_table: str
    target_id: int
    source_key: Optional[str] = None
    status: str = "Inserted"  # Inserted | RolledBack
    business_id: Optional[int] = None
    created_at: Optional[datetime] = None


class MigrationBatchListResponse(BaseModel):
    """Paginated list of migration batches."""
    items: List[MigrationBatchResponse] = Field(default_factory=list)
    total: int = 0
    page: int = 1
    page_size: int = 50
