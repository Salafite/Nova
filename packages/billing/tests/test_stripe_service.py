from unittest.mock import patch, MagicMock, PropertyMock
import pytest
import json


def test_create_checkout_session_not_configured():
    from packages.billing.stripe_service import create_checkout_session
    result = create_checkout_session(1, 'http://success', 'http://cancel')
    assert result == {'error': 'Stripe not configured'}


def test_create_checkout_session_success():
    with patch('packages.billing.stripe_service.STRIPE_SECRET_KEY', 'sk_test'), \
         patch('packages.billing.stripe_service.STRIPE_PRICE_ID', 'price_123'), \
         patch('packages.billing.stripe_service._get_stripe') as mock_get:
        mock_stripe = MagicMock()
        mock_get.return_value = mock_stripe
        mock_session = MagicMock()
        mock_session.url = 'https://checkout.stripe.com/test'
        mock_session.id = 'cs_test_123'
        mock_stripe.checkout.Session.create.return_value = mock_session

        from packages.billing.stripe_service import create_checkout_session
        result = create_checkout_session(1, 'http://success', 'http://cancel')

    assert result['url'] == 'https://checkout.stripe.com/test'
    assert result['session_id'] == 'cs_test_123'


def test_create_checkout_session_error():
    with patch('packages.billing.stripe_service.STRIPE_SECRET_KEY', 'sk_test'), \
         patch('packages.billing.stripe_service.STRIPE_PRICE_ID', 'price_123'), \
         patch('packages.billing.stripe_service._get_stripe') as mock_get:
        mock_stripe = MagicMock()
        mock_get.return_value = mock_stripe
        mock_stripe.checkout.Session.create.side_effect = Exception('API error')

        from packages.billing.stripe_service import create_checkout_session
        result = create_checkout_session(1, 'http://success', 'http://cancel')

    assert result['error'] == 'API error'


def test_create_portal_session_not_configured():
    from packages.billing.stripe_service import create_portal_session
    result = create_portal_session(1, 'http://return')
    assert result == {'error': 'Stripe not configured'}


def test_create_portal_session_no_subscription():
    with patch('packages.billing.stripe_service.STRIPE_SECRET_KEY', 'sk_test'), \
         patch('packages.billing.stripe_service._get_subscription', return_value=None):
        from packages.billing.stripe_service import create_portal_session
        result = create_portal_session(1, 'http://return')

    assert result == {'error': 'No active subscription'}


def test_create_portal_session_success():
    with patch('packages.billing.stripe_service.STRIPE_SECRET_KEY', 'sk_test'), \
         patch('packages.billing.stripe_service._get_subscription', return_value={'stripe_customer_id': 'cus_123'}), \
         patch('packages.billing.stripe_service._get_stripe') as mock_get:
        mock_stripe = MagicMock()
        mock_get.return_value = mock_stripe
        mock_session = MagicMock()
        mock_session.url = 'https://portal.stripe.com/test'
        mock_stripe.billing_portal.Session.create.return_value = mock_session

        from packages.billing.stripe_service import create_portal_session
        result = create_portal_session(1, 'http://return')

    assert result['url'] == 'https://portal.stripe.com/test'


def test_get_subscription_status_none():
    with patch('packages.billing.stripe_service._get_subscription', return_value=None):
        from packages.billing.stripe_service import get_subscription_status
        result = get_subscription_status(1)

    assert result == {'status': 'none', 'plan': 'Free'}


def test_get_subscription_status_active():
    with patch('packages.billing.stripe_service._get_subscription', return_value={
        'status': 'active', 'stripe_customer_id': 'cus_123', 'updated_at': '2025-01-01T00:00:00',
    }):
        from packages.billing.stripe_service import get_subscription_status
        result = get_subscription_status(1)

    assert result['status'] == 'active'
    assert result['plan'] == 'Professional'
    assert result['stripe_customer_id'] == 'cus_123'


def test_handle_webhook_not_configured():
    from packages.billing.stripe_service import handle_webhook
    result = handle_webhook(b'{}', 'sig')
    assert result == {'error': 'Stripe not configured'}


def test_handle_webhook_invalid_payload():
    with patch('packages.billing.stripe_service.STRIPE_SECRET_KEY', 'sk_test'), \
         patch('packages.billing.stripe_service.STRIPE_WEBHOOK_SECRET', 'whsec_test'), \
         patch('stripe.Webhook.construct_event', side_effect=ValueError('bad')):
        from packages.billing.stripe_service import handle_webhook
        result = handle_webhook(b'bad', 'sig')

    assert result == {'error': 'Invalid payload'}


def test_handle_webhook_invalid_signature():
    with patch('packages.billing.stripe_service.STRIPE_SECRET_KEY', 'sk_test'), \
         patch('packages.billing.stripe_service.STRIPE_WEBHOOK_SECRET', 'whsec_test'), \
         patch('stripe.Webhook.construct_event', side_effect=Exception('bad sig')):
        import stripe as stripe_lib
        with patch.object(stripe_lib.error, 'SignatureVerificationError', Exception, create=True):
            from packages.billing.stripe_service import handle_webhook
            result = handle_webhook(b'bad', 'sig')

    assert result == {'error': 'Invalid signature'}


def test_handle_webhook_valid_event():
    with patch('packages.billing.stripe_service.STRIPE_SECRET_KEY', 'sk_test'), \
         patch('packages.billing.stripe_service.STRIPE_WEBHOOK_SECRET', 'whsec_test'), \
         patch('stripe.Webhook.construct_event') as mock_construct:
        mock_event = MagicMock()
        mock_event.__getitem__.side_effect = lambda k: {
            'type': 'checkout.session.completed',
            'data': {'object': {}},
        }[k]
        mock_construct.return_value = mock_event
        mock_handler = MagicMock()
        with patch('packages.billing.stripe_service._WEBHOOK_HANDLERS', {
            'checkout.session.completed': mock_handler,
        }):
            from packages.billing.stripe_service import handle_webhook
            result = handle_webhook(b'{}', 'sig')

    assert result == {'received': True}
    mock_handler.assert_called_once_with({})


def test_handle_checkout_completed():
    from packages.billing.stripe_service import _handle_checkout_completed
    session = {'metadata': {'business_id': '42'}, 'customer': 'cus_42', 'subscription': 'sub_42'}
    with patch('packages.billing.stripe_service._save_subscription') as mock_save:
        _handle_checkout_completed(session)

    mock_save.assert_called_once()
    args, _ = mock_save.call_args
    assert args[0] == 42
    assert args[1]['stripe_customer_id'] == 'cus_42'
    assert args[1]['stripe_subscription_id'] == 'sub_42'
    assert args[1]['status'] == 'active'


def test_handle_invoice_paid():
    from packages.billing.stripe_service import _handle_invoice_paid
    with patch('packages.billing.stripe_service._update_subscription_status_by_customer') as mock_update:
        _handle_invoice_paid({'customer': 'cus_42'})
    mock_update.assert_called_once_with('cus_42', 'active')


def test_handle_invoice_payment_failed():
    from packages.billing.stripe_service import _handle_invoice_payment_failed
    with patch('packages.billing.stripe_service._update_subscription_status_by_customer') as mock_update:
        _handle_invoice_payment_failed({'customer': 'cus_42'})
    mock_update.assert_called_once_with('cus_42', 'past_due')
