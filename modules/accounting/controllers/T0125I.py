from typing import Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Query, Response, status

from modules.accounting.models.einvoice import (
    FiscalProfileCreate,
    FiscalProfileUpdate,
    FiscalProfileResponse,
    FISCAL_PROFILE_REPO,
)
from modules.accounting.services.einvoice_service import EInvoiceService
from modules.accounting.services.einvoice_crypto_service import EInvoiceCryptoService
from modules.core.services.base import CrudService
from modules.core.controllers.base import create_crud_router

service = CrudService(FISCAL_PROFILE_REPO)
einvoice_service = EInvoiceService(fiscal_profile_repo=FISCAL_PROFILE_REPO)

router = create_crud_router(
    '/api/T0125I',
    'T0125 - Fiscal Authority Profiles',
    service,
    FiscalProfileCreate,
    FiscalProfileUpdate,
    FiscalProfileResponse,
)


@router.get('/active/current', response_model=FiscalProfileResponse)
def get_current_active_profile():
    """Retrieve the currently active default fiscal authority profile."""
    try:
        profile = einvoice_service.get_active_fiscal_profile()
        if not profile or not profile.get('id'):
            # Return default fallback structure
            return FiscalProfileResponse(
                id=0,
                profile_name=profile.get('profile_name', 'Default Fiscal Profile'),
                authority_code=profile.get('authority_code', 'ZATCA'),
                seller_name=profile.get('seller_name', 'Nova Global Trading LLC'),
                seller_name_ar=profile.get('seller_name_ar', 'شركة نوفا للتجارة العامة'),
                tax_id=profile.get('tax_id', '300012345600003'),
                commercial_registration_number=profile.get('commercial_registration_number', '1010123456'),
                building_number=profile.get('building_number', '1234'),
                street_name=profile.get('street_name', 'King Fahd Road'),
                district=profile.get('district', 'Al Olaya'),
                city=profile.get('city', 'Riyadh'),
                postal_code=profile.get('postal_code', '12211'),
                country_code=profile.get('country_code', 'SA'),
                environment=profile.get('environment', 'Sandbox'),
                is_active=True,
                is_default=True,
            )
        return profile
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get active fiscal profile: {e}")


@router.post('/generate-keypair')
def generate_fiscal_keypair():
    """Generate a new ECDSA secp256k1 keypair for digital signing and certificate generation."""
    try:
        priv_key, pub_key = EInvoiceCryptoService.generate_ecdsa_keypair()
        return {
            "private_key": priv_key,
            "public_key": pub_key,
            "algorithm": "ECDSA_secp256k1",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate keypair: {e}")
