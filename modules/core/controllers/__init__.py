import importlib
from pathlib import Path

_all_routers = None


def _load_all_routers():
    global _all_routers
    if _all_routers is not None:
        return _all_routers

    _all_routers = []
    modules_dir = Path(__file__).parent.parent.parent
    for f in sorted(modules_dir.rglob('controllers/T*I.py')):
        if f.stem.startswith('T') and f.stem.endswith('I'):
            module_path = f.relative_to(modules_dir.parent).with_suffix('').parts
            import_path = '.'.join(module_path)
            module = importlib.import_module(import_path)
            if hasattr(module, 'router'):
                _all_routers.append(module.router)

    try:
        from modules.purchasing.controllers.restock_controller import router as restock_router
        _all_routers.append(restock_router)
    except Exception:
        pass

    try:
        from modules.inventory.controllers.replenishment_controller import router as replenishment_router
        _all_routers.append(replenishment_router)
    except Exception:
        pass

    try:
        from modules.accounting.controllers.bank_reconciliation_controller import router as bank_reconciliation_router
        _all_routers.append(bank_reconciliation_router)
    except Exception:
        pass

    return _all_routers


def __getattr__(name: str):
    if name == 'all_routers':
        return _load_all_routers()
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")


