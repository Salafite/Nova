import json
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
    try:
        return json.loads(rows[0]['setting_value'])
    except (json.JSONDecodeError, KeyError):
        return None


def _save_subscription(business_id: int, data: dict):
    key = f'subscription_{business_id}'
    existing = SUBSCRIPTION_REPO.list(filters={'setting_key': key})
    if existing:
        SUBSCRIPTION_REPO.update(existing[0]['id'], {'setting_value': json.dumps(data), 'group_name': 'Billing'})
    else:
        SUBSCRIPTION_REPO.create({'setting_key': key, 'setting_value': json.dumps(data), 'group_name': 'Billing'})


def _update_subscription_status_by_customer(customer_id: str, new_status: str):
    rows = SUBSCRIPTION_REPO.list()
    for row in rows:
        try:
            val = json.loads(row['setting_value'])
            if val.get('stripe_customer_id') == customer_id:
                val['status'] = new_status
                val['updated_at'] = datetime.now(timezone.utc).isoformat()
                SUBSCRIPTION_REPO.update(row['id'], {'setting_value': json.dumps(val)})
                return
        except (json.JSONDecodeError, KeyError):
            continue


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
    _update_subscription_status_by_customer(invoice.get('customer', ''), 'active')


def _handle_invoice_payment_failed(invoice):
    _update_subscription_status_by_customer(invoice.get('customer', ''), 'past_due')


def create_settlement_checkout_session(
    customer_id: int,
    amount: float,
    settlement_type: str = 'invoice',
    invoice_id: int | None = None,
    invoice_ids: list | None = None,
    invoice_number: str | None = None,
    customer_name: str | None = None,
    customer_email: str | None = None,
    payment_method_types: list | None = None,
    success_url: str | None = None,
    cancel_url: str | None = None,
) -> dict:
    """Create a Stripe Checkout Session for B2B portal invoice or balance settlement with Card & ACH."""
    stripe = _get_stripe()
    if not stripe:
        return {'error': 'Stripe not configured'}

    try:
        amount_cents = int(round(amount * 100))
        if amount_cents <= 0:
            return {'error': 'Amount must be greater than zero'}

        methods = payment_method_types or ['card', 'us_bank_account']

        if settlement_type == 'invoice' and invoice_number:
            line_item_name = f"Invoice #{invoice_number}"
            line_item_desc = f"Online settlement for Invoice #{invoice_number}" + (f" - {customer_name}" if customer_name else "")
        else:
            line_item_name = f"Account Balance Settlement" + (f" - {customer_name}" if customer_name else "")
            line_item_desc = f"B2B account balance settlement" + (f" for {customer_name}" if customer_name else "")

        metadata = {
            'customer_id': str(customer_id),
            'settlement_type': settlement_type,
            'amount': f"{amount:.2f}",
            'amount_cents': str(amount_cents),
        }
        if customer_name:
            metadata['customer_name'] = customer_name
        if invoice_id is not None:
            metadata['invoice_id'] = str(invoice_id)
        if invoice_number:
            metadata['invoice_number'] = invoice_number
        if invoice_ids:
            metadata['invoice_ids'] = ','.join(str(i) for i in invoice_ids)

        session_params = {
            'mode': 'payment',
            'payment_method_types': methods,
            'line_items': [{
                'price_data': {
                    'currency': 'usd',
                    'product_data': {
                        'name': line_item_name,
                        'description': line_item_desc,
                    },
                    'unit_amount': amount_cents,
                },
                'quantity': 1,
            }],
            'success_url': success_url or 'http://localhost:5173/portal/payment/result?session_id={CHECKOUT_SESSION_ID}&status=success',
            'cancel_url': cancel_url or 'http://localhost:5173/portal/invoices?session_id={CHECKOUT_SESSION_ID}&status=cancelled',
            'metadata': metadata,
            'payment_intent_data': {
                'metadata': metadata,
            },
        }

        if customer_email:
            session_params['customer_email'] = customer_email

        if settlement_type == 'invoice' and invoice_id:
            session_params['client_reference_id'] = f"cust_{customer_id}_inv_{invoice_id}"
        else:
            session_params['client_reference_id'] = f"cust_{customer_id}_balance"

        session = stripe.checkout.Session.create(**session_params)
        return {
            'session_id': session.id,
            'url': session.url,
            'amount': amount,
            'amount_cents': amount_cents,
            'currency': 'usd',
            'settlement_type': settlement_type,
            'invoice_id': invoice_id,
            'payment_method_types': methods,
            'status': getattr(session, 'status', 'open') or 'open',
        }
    except Exception as e:
        return {'error': str(e)}


def get_checkout_session(session_id: str) -> dict:
    """Retrieve details and live payment status for a Stripe Checkout Session."""
    stripe = _get_stripe()
    if not stripe:
        return {'error': 'Stripe not configured'}
    try:
        session = stripe.checkout.Session.retrieve(session_id)
        customer_email = getattr(session, 'customer_email', None)
        if not customer_email and hasattr(session, 'customer_details') and session.customer_details:
            customer_email = getattr(session.customer_details, 'email', None) or session.customer_details.get('email')

        amount_total = None
        raw_total = getattr(session, 'amount_total', None)
        if raw_total is not None:
            amount_total = raw_total / 100.0

        return {
            'session_id': session.id,
            'status': getattr(session, 'status', 'open'),
            'payment_status': getattr(session, 'payment_status', 'unpaid'),
            'payment_intent_id': getattr(session, 'payment_intent', None),
            'amount_total': amount_total,
            'currency': getattr(session, 'currency', 'usd'),
            'customer_email': customer_email,
            'metadata': getattr(session, 'metadata', {}) or {},
        }
    except Exception as e:
        return {'error': str(e)}


_WEBHOOK_HANDLERS = {
    'checkout.session.completed': _handle_checkout_completed,
    'invoice.paid': _handle_invoice_paid,
    'invoice.payment_failed': _handle_invoice_payment_failed,
}

