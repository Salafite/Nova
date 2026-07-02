import os
from datetime import datetime, timezone
from modules.core.repositories.base import CrudRepository

STRIPE_SECRET_KEY = os.environ.get('STRIPE_SECRET_KEY', '')
STRIPE_PRICE_ID = os.environ.get('STRIPE_PRICE_ID', '')
STRIPE_WEBHOOK_SECRET = os.environ.get('STRIPE_WEBHOOK_SECRET', '')
SUBSCRIPTION_REPO = CrudRepository('T0100', business_columns=['id', 'setting_key', 'setting_value', 'group_name'])


def _get_stripe():
    if not STRIPE_SECRET_KEY:
        return None
    import stripe
    stripe.api_key = STRIPE_SECRET_KEY
    return stripe


def create_checkout_session(business_id: int, success_url: str, cancel_url: str) -> dict | None:
    stripe = _get_stripe()
    if not stripe:
        return {'error': 'Stripe not configured'}
    try:
        session = stripe.checkout.Session.create(
            mode='subscription',
            line_items=[{'price': STRIPE_PRICE_ID, 'quantity': 1}],
            success_url=success_url,
            cancel_url=cancel_url,
            metadata={'business_id': str(business_id)},
        )
        return {'url': session.url, 'session_id': session.id}
    except Exception as e:
        return {'error': str(e)}


def create_portal_session(business_id: int, return_url: str) -> dict | None:
    stripe = _get_stripe()
    if not stripe:
        return {'error': 'Stripe not configured'}
    try:
        sub = _get_subscription(business_id)
        if not sub:
            return {'error': 'No active subscription'}
        session = stripe.billing_portal.Session.create(
            customer=sub['stripe_customer_id'],
            return_url=return_url,
        )
        return {'url': session.url}
    except Exception as e:
        return {'error': str(e)}


def handle_webhook(payload: bytes, sig_header: str) -> dict:
    stripe = _get_stripe()
    if not stripe:
        return {'error': 'Stripe not configured'}
    try:
        import stripe as stripe_lib
        event = stripe_lib.Webhook.construct_event(payload, sig_header, STRIPE_WEBHOOK_SECRET)
    except ValueError:
        return {'error': 'Invalid payload'}
    except stripe_lib.error.SignatureVerificationError:
        return {'error': 'Invalid signature'}

    handler = _WEBHOOK_HANDLERS.get(event['type'])
    if handler:
        handler(event['data']['object'])
    return {'received': True}


def get_subscription_status(business_id: int) -> dict:
    sub = _get_subscription(business_id)
    if not sub:
        return {'status': 'none', 'plan': 'Free'}
    return {
        'status': sub.get('status', 'inactive'),
        'plan': 'Professional',
        'stripe_customer_id': sub.get('stripe_customer_id', ''),
        'updated_at': sub.get('updated_at', ''),
    }


def _get_subscription(business_id: int) -> dict | None:
    rows = SUBSCRIPTION_REPO.list(filters={'setting_key': f'subscription_{business_id}'})
    if not rows:
        return None
    import json
    try:
        return json.loads(rows[0]['setting_value'])
    except (json.JSONDecodeError, KeyError, IndexError):
        return None


def _save_subscription(business_id: int, data: dict):
    import json
    key = f'subscription_{business_id}'
    existing = SUBSCRIPTION_REPO.list(filters={'setting_key': key})
    if existing:
        SUBSCRIPTION_REPO.update(existing[0]['id'], {'setting_value': json.dumps(data), 'group_name': 'Billing'})
    else:
        SUBSCRIPTION_REPO.create({'setting_key': key, 'setting_value': json.dumps(data), 'group_name': 'Billing'})


def _handle_checkout_completed(session):
    business_id = int(session.get('metadata', {}).get('business_id', 0))
    if not business_id:
        return
    _save_subscription(business_id, {
        'stripe_customer_id': session.get('customer', ''),
        'stripe_subscription_id': session.get('subscription', ''),
        'status': 'active',
        'updated_at': datetime.now(timezone.utc).isoformat(),
    })


def _handle_invoice_paid(invoice):
    customer_id = invoice.get('customer', '')
    rows = SUBSCRIPTION_REPO.list()
    for row in rows:
        import json
        try:
            val = json.loads(row['setting_value'])
            if val.get('stripe_customer_id') == customer_id:
                val['status'] = 'active'
                val['updated_at'] = datetime.now(timezone.utc).isoformat()
                SUBSCRIPTION_REPO.update(row['id'], {'setting_value': json.dumps(val)})
                break
        except (json.JSONDecodeError, KeyError):
            continue


def _handle_invoice_payment_failed(invoice):
    customer_id = invoice.get('customer', '')
    rows = SUBSCRIPTION_REPO.list()
    for row in rows:
        import json
        try:
            val = json.loads(row['setting_value'])
            if val.get('stripe_customer_id') == customer_id:
                val['status'] = 'past_due'
                val['updated_at'] = datetime.now(timezone.utc).isoformat()
                SUBSCRIPTION_REPO.update(row['id'], {'setting_value': json.dumps(val)})
                break
        except (json.JSONDecodeError, KeyError):
            continue


_WEBHOOK_HANDLERS = {
    'checkout.session.completed': _handle_checkout_completed,
    'invoice.paid': _handle_invoice_paid,
    'invoice.payment_failed': _handle_invoice_payment_failed,
}
