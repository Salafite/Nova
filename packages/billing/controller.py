from fastapi import APIRouter, Depends, HTTPException, Request
from packages.auth.deps import get_current_user
from packages.billing.stripe_service import (
    create_checkout_session,
    create_portal_session,
    handle_webhook,
    get_subscription_status,
)

router = APIRouter(prefix='/api/billing', tags=['Billing'])


@router.post('/create-checkout')
def checkout(body: dict, user: dict = Depends(get_current_user)):
    business_id = user.get('business_id', 1)
    success_url = body.get('success_url', 'http://localhost:5173/admin/subscription')
    cancel_url = body.get('cancel_url', 'http://localhost:5173/admin/subscription')
    result = create_checkout_session(business_id, success_url, cancel_url)
    if result.get('error'):
        raise HTTPException(400, result['error'])
    return result


@router.post('/create-portal')
def portal(body: dict, user: dict = Depends(get_current_user)):
    business_id = user.get('business_id', 1)
    return_url = body.get('return_url', 'http://localhost:5173/admin/subscription')
    result = create_portal_session(business_id, return_url)
    if result.get('error'):
        raise HTTPException(400, result['error'])
    return result


@router.post('/webhook')
async def webhook(request: Request):
    payload = await request.body()
    sig_header = request.headers.get('stripe-signature', '')
    result = handle_webhook(payload, sig_header)
    if result.get('error'):
        raise HTTPException(400, result['error'])
    return result


@router.get('/subscription')
def subscription(user: dict = Depends(get_current_user)):
    business_id = user.get('business_id', 1)
    return get_subscription_status(business_id)
