"""Connector Factory and Discovery Registry for Nova Legacy Migration Bridge.

Provides centralized connector instantiation, schema parameter validation,
and connector metadata discovery for legacy database systems and file dumps.
"""

from dataclasses import dataclass, field
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Type, Union

from pydantic import BaseModel, ValidationError

from modules.migration.connectors.base import BaseConnector
from modules.migration.connectors.csv_dump import CsvDumpConnector
from modules.migration.connectors.sqlserver import SQLServerConnector
from modules.migration.models.migration import (
    ConnectorConfig,
    CsvDumpConnectionConfig,
    SQLServerConnectionConfig,
)

logger = logging.getLogger(__name__)


@dataclass
class ConnectorRegistration:
    """Registry entry metadata for a legacy data connector."""
    source_type: str
    display_name: str
    connector_class: Type[BaseConnector]
    config_model: Optional[Type[BaseModel]] = None
    description: str = ""
    aliases: List[str] = field(default_factory=list)
    is_database: bool = True
    required_params: List[str] = field(default_factory=list)
    optional_params: List[str] = field(default_factory=list)
    default_port: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert connector registration metadata to a dictionary."""
        return {
            "type": self.source_type,
            "source_type": self.source_type,
            "display_name": self.display_name,
            "description": self.description,
            "aliases": list(self.aliases),
            "is_database": self.is_database,
            "required_params": list(self.required_params),
            "optional_params": list(self.optional_params),
            "default_port": self.default_port,
            "config_model": self.config_model.__name__ if self.config_model else None,
            "connector_class": self.connector_class.__name__,
        }


# Global registry dictionaries
_CONNECTOR_REGISTRY: Dict[str, ConnectorRegistration] = {}
_ALIAS_MAP: Dict[str, str] = {}


def register_connector(
    source_type: str,
    connector_class: Type[BaseConnector],
    display_name: Optional[str] = None,
    config_model: Optional[Type[BaseModel]] = None,
    description: str = "",
    aliases: Optional[List[str]] = None,
    is_database: bool = True,
    required_params: Optional[List[str]] = None,
    optional_params: Optional[List[str]] = None,
    default_port: Optional[int] = None,
) -> None:
    """Register a connector class in the global factory registry.
    
    Args:
        source_type: Primary identifier (e.g. 'sqlserver', 'csv_dump')
        connector_class: BaseConnector subclass
        display_name: Human-friendly display label
        config_model: Pydantic model class for parameter validation
        description: Description of the connector capabilities
        aliases: Alternative identifiers (e.g. ['mssql', 'sql_server'])
        is_database: True for direct database connections, False for file dumps
        required_params: List of required parameter names
        optional_params: List of optional parameter names
        default_port: Default network port if applicable
    """
    normalized_type = source_type.lower().strip()
    alias_list = [a.lower().strip() for a in (aliases or []) if a.strip()]

    registration = ConnectorRegistration(
        source_type=normalized_type,
        display_name=display_name or source_type.replace("_", " ").title(),
        connector_class=connector_class,
        config_model=config_model,
        description=description,
        aliases=alias_list,
        is_database=is_database,
        required_params=required_params or [],
        optional_params=optional_params or [],
        default_port=default_port,
    )

    _CONNECTOR_REGISTRY[normalized_type] = registration
    _ALIAS_MAP[normalized_type] = normalized_type

    for alias in alias_list:
        _ALIAS_MAP[alias] = normalized_type

    logger.debug("Registered migration connector: %s (aliases: %s)", normalized_type, alias_list)


def unregister_connector(source_type: str) -> bool:
    """Unregister a connector from the registry.
    
    Args:
        source_type: Primary identifier or alias
        
    Returns:
        bool: True if found and removed, False otherwise
    """
    normalized = source_type.lower().strip()
    primary_type = _ALIAS_MAP.get(normalized, normalized)

    if primary_type in _CONNECTOR_REGISTRY:
        _CONNECTOR_REGISTRY.pop(primary_type)
        # Remove from alias map
        keys_to_remove = [k for k, v in _ALIAS_MAP.items() if v == primary_type]
        for k in keys_to_remove:
            _ALIAS_MAP.pop(k, None)
        return True
    return False


def normalize_source_type(source_type: str) -> str:
    """Resolve an alias or raw source_type string to the registered primary source_type."""
    if not source_type:
        return ""
    clean = source_type.lower().strip()
    return _ALIAS_MAP.get(clean, clean)


def is_supported_connector(source_type: str) -> bool:
    """Check if a source_type is supported by the connector registry."""
    if not source_type:
        return False
    primary = normalize_source_type(source_type)
    return primary in _CONNECTOR_REGISTRY


def get_connector_class(source_type: str) -> Type[BaseConnector]:
    """Retrieve the connector class for a source_type.
    
    Raises:
        ValueError: If source_type is unsupported or not found
    """
    primary = normalize_source_type(source_type)
    if primary not in _CONNECTOR_REGISTRY:
        supported = ", ".join(sorted(_CONNECTOR_REGISTRY.keys()))
        raise ValueError(
            f"Unsupported connector source_type '{source_type}'. "
            f"Supported connectors: [{supported}]"
        )
    return _CONNECTOR_REGISTRY[primary].connector_class


def list_supported_connectors() -> List[Dict[str, Any]]:
    """List metadata for all registered connectors.
    
    Returns:
        List of connector metadata dictionaries.
    """
    return [reg.to_dict() for reg in _CONNECTOR_REGISTRY.values()]


def validate_connection_params(
    source_type: str,
    params: Union[Dict[str, Any], BaseModel],
    raise_on_error: bool = False,
) -> Dict[str, Any]:
    """Validate connection parameters for a given connector type.
    
    Args:
        source_type: Connector identifier (e.g. 'sqlserver', 'csv_dump')
        params: Dictionary of parameters or Pydantic config model
        raise_on_error: If True, raises ValueError on validation failure
        
    Returns:
        Dict with keys:
            - 'valid' (bool): True if validation passed
            - 'errors' (List[str]): List of validation error messages
            - 'cleaned_params' (Dict[str, Any]): Normalized parameter dictionary
    """
    primary = normalize_source_type(source_type)
    if primary not in _CONNECTOR_REGISTRY:
        supported = ", ".join(sorted(_CONNECTOR_REGISTRY.keys()))
        err_msg = (
            f"Unsupported connector source_type '{source_type}'. "
            f"Supported connectors: [{supported}]"
        )
        if raise_on_error:
            raise ValueError(err_msg)
        return {"valid": False, "errors": [err_msg], "cleaned_params": {}}

    reg = _CONNECTOR_REGISTRY[primary]
    errors: List[str] = []

    # Extract dict from Pydantic model if provided
    if hasattr(params, "model_dump"):
        raw_dict = params.model_dump()
    elif hasattr(params, "dict"):
        raw_dict = params.dict()
    elif isinstance(params, dict):
        raw_dict = dict(params)
    else:
        raw_dict = {}

    cleaned_params: Dict[str, Any] = dict(raw_dict)

    # If config_model is registered, validate against Pydantic schema
    if reg.config_model is not None:
        try:
            validated_model = reg.config_model(**raw_dict)
            if hasattr(validated_model, "model_dump"):
                cleaned_params = validated_model.model_dump()
            else:
                cleaned_params = validated_model.dict()
        except ValidationError as ve:
            for error in ve.errors():
                loc = " -> ".join(str(l) for l in error.get("loc", []))
                msg = error.get("msg", "invalid")
                errors.append(f"Parameter '{loc}': {msg}")
        except Exception as ex:
            errors.append(f"Validation error: {str(ex)}")

    # Specific sanity checks for standard connectors
    if primary == "sqlserver":
        db_name = cleaned_params.get("database", "").strip()
        if not db_name:
            errors.append("Parameter 'database' is required and cannot be empty for SQL Server.")
        port = cleaned_params.get("port")
        if port is not None:
            try:
                port_num = int(port)
                if port_num < 1 or port_num > 65535:
                    errors.append(f"Invalid port number {port_num}. Must be between 1 and 65535.")
            except (ValueError, TypeError):
                errors.append(f"Port must be an integer, got: {port}")

    elif primary == "csv_dump":
        dump_path = cleaned_params.get("dump_path")
        zip_path = cleaned_params.get("zip_file_path")
        in_memory = cleaned_params.get("in_memory_files") or cleaned_params.get("files")
        
        # In-memory virtual files or path or mock
        pass

    is_valid = len(errors) == 0

    if raise_on_error and not is_valid:
        raise ValueError(f"Connection parameter validation failed for '{primary}': {'; '.join(errors)}")

    return {
        "valid": is_valid,
        "errors": errors,
        "cleaned_params": cleaned_params,
    }


def get_connector(
    source_type: Optional[str] = None,
    config: Optional[Union[Dict[str, Any], BaseModel]] = None,
    **kwargs: Any,
) -> BaseConnector:
    """Factory function to instantiate and configure a legacy data connector.
    
    Supports direct arguments, config dictionaries, or Pydantic config models.
    
    Args:
        source_type: Source type identifier (e.g. 'sqlserver', 'csv_dump', 'mssql', 'csv')
        config: Optional configuration dictionary or Pydantic model
        **kwargs: Additional or override parameters passed to connector constructor
        
    Returns:
        BaseConnector: Configured connector instance
        
    Raises:
        ValueError: If source_type is missing or unsupported
    """
    resolved_type = source_type

    # Extract source_type from config if not provided explicitly
    if resolved_type is None and config is not None:
        if isinstance(config, ConnectorConfig):
            resolved_type = config.source_type
        elif hasattr(config, "source_type"):
            resolved_type = getattr(config, "source_type")
        elif isinstance(config, dict) and "source_type" in config:
            resolved_type = config["source_type"]

    # Extract source_type from kwargs if still None
    if resolved_type is None and "source_type" in kwargs:
        resolved_type = kwargs.pop("source_type")

    if not resolved_type:
        supported = ", ".join(sorted(_CONNECTOR_REGISTRY.keys()))
        raise ValueError(
            f"source_type is required to instantiate a connector. "
            f"Supported connectors: [{supported}]"
        )

    primary_type = normalize_source_type(str(resolved_type))
    if primary_type not in _CONNECTOR_REGISTRY:
        supported = ", ".join(sorted(_CONNECTOR_REGISTRY.keys()))
        raise ValueError(
            f"Unsupported connector source_type '{resolved_type}'. "
            f"Supported connectors: [{supported}]"
        )

    registration = _CONNECTOR_REGISTRY[primary_type]
    connector_cls = registration.connector_class

    # Prepare configuration arguments
    init_kwargs: Dict[str, Any] = {}

    if config is not None:
        if isinstance(config, ConnectorConfig):
            if primary_type == "sqlserver" and config.sqlserver is not None:
                init_kwargs["config"] = config.sqlserver
            elif primary_type == "csv_dump" and config.csv_dump is not None:
                init_kwargs["config"] = config.csv_dump
            else:
                init_kwargs["config"] = config.custom_options
        else:
            init_kwargs["config"] = config

    # Merge explicit kwargs
    init_kwargs.update(kwargs)

    try:
        return connector_cls(**init_kwargs)
    except Exception as ex:
        logger.error(
            "Failed to instantiate connector '%s' with class %s: %s",
            primary_type,
            connector_cls.__name__,
            str(ex),
            exc_info=True,
        )
        raise


def create_connector_from_config(
    config: Union[ConnectorConfig, Dict[str, Any]],
    **kwargs: Any,
) -> BaseConnector:
    """Create a connector directly from a ConnectorConfig model or dictionary.
    
    Args:
        config: ConnectorConfig model or dictionary containing 'source_type'
        **kwargs: Additional parameters overriding config
        
    Returns:
        BaseConnector: Instantiated connector
    """
    if isinstance(config, ConnectorConfig):
        return get_connector(source_type=config.source_type, config=config, **kwargs)
    elif isinstance(config, dict):
        src_type = config.get("source_type", "sqlserver")
        return get_connector(source_type=src_type, config=config, **kwargs)
    else:
        raise TypeError(f"Expected ConnectorConfig or dict, got: {type(config)}")


# ==============================================================================
# Initialize Default Built-in Connectors
# ==============================================================================

register_connector(
    source_type="sqlserver",
    connector_class=SQLServerConnector,
    display_name="Microsoft SQL Server",
    config_model=SQLServerConnectionConfig,
    description="Direct connection to legacy Microsoft SQL Server instances with schema discovery and chunk streaming.",
    aliases=["mssql", "sql_server", "ms_sql"],
    is_database=True,
    required_params=["database"],
    optional_params=[
        "host",
        "port",
        "user",
        "password",
        "trust_server_certificate",
        "driver",
        "timeout",
        "schema_name",
        "connection_string",
    ],
    default_port=1433,
)

register_connector(
    source_type="csv_dump",
    connector_class=CsvDumpConnector,
    display_name="CSV & SQL Dump Archive",
    config_model=CsvDumpConnectionConfig,
    description="Multi-table CSV files, ZIP archives, SQL dump scripts, and in-memory tabular datasets.",
    aliases=["csv", "dump", "sql_dump", "zip", "csv_directory"],
    is_database=False,
    required_params=[],
    optional_params=[
        "dump_path",
        "zip_file_path",
        "delimiter",
        "encoding",
        "quote_char",
        "has_header",
        "in_memory_files",
    ],
    default_port=None,
)
