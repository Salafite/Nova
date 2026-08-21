from typing import Optional
from pydantic import create_model
from modules.core.models.base import AuditMixin, TenantMixin


def crud_model(name: str, fields: list, audit: bool = True, tenant: bool = True):
    """Generate (Create, Update, Response) Pydantic models for a domain entity.

    `fields` is a list of (field_name, type, default_or_Field) tuples.
    Use ``...`` as the default to mark a field required.
    Pass a ``Field(...)`` or ``Field(default, ...)`` instance for constraints.
    """
    create_kwargs = {}
    update_kwargs = {}
    response_kwargs = {'id': (int, ...)}

    if tenant:
        create_kwargs['business_id'] = (Optional[int], None)
        update_kwargs['business_id'] = (Optional[int], None)

    for fname, ftype, default in fields:
        create_kwargs[fname] = (ftype, default)
        response_kwargs[fname] = (ftype, default)
        update_kwargs[fname] = (Optional[ftype], None)

    if audit:
        base = AuditMixin
    elif tenant:
        base = TenantMixin
    else:
        base = None

    Create = create_model(f'{name}Create', **create_kwargs)
    Update = create_model(f'{name}Update', **update_kwargs)
    Response = create_model(f'{name}Response', __base__=base, **response_kwargs)


    return Create, Update, Response

