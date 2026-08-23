from unittest.mock import patch, MagicMock


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


def test_handle_checkout_completed_settlement():
    from packages.billing.stripe_service import _handle_checkout_completed
    session = {
        'id': 'cs_test_settle',
        'metadata': {'customer_id': '10', 'settlement_type': 'invoice', 'invoice_id': '5', 'amount': '250.00'},
        'amount_total': 25000,
        'payment_intent': 'pi_test_123',
    }
    with patch('modules.portal.services.stripe_settlement_service.StripeSettlementService.reconcile_checkout_session') as mock_reconcile:
        _handle_checkout_completed(session)
        mock_reconcile.assert_called_once()
        call_arg = mock_reconcile.call_args[0][0]
        assert call_arg['metadata']['customer_id'] == '10'


def test_handle_payment_intent_succeeded_settlement():
    from packages.billing.stripe_service import _handle_payment_intent_succeeded
    pi = {
        'id': 'pi_test_settle_456',
        'metadata': {'customer_id': '10', 'settlement_type': 'invoice', 'invoice_id': '5', 'amount': '250.00'},
        'amount': 25000,
    }
    with patch('modules.portal.services.stripe_settlement_service.StripeSettlementService.reconcile_payment_intent') as mock_reconcile:
        _handle_payment_intent_succeeded(pi)
        mock_reconcile.assert_called_once()
        call_arg = mock_reconcile.call_args[0][0]
        assert call_arg['id'] == 'pi_test_settle_456'


def test_handle_payment_intent_succeeded_ignored_without_portal_metadata():
    from packages.billing.stripe_service import _handle_payment_intent_succeeded
    pi = {
        'id': 'pi_test_other_789',
        'metadata': {'some_other_key': 'foo'},
        'amount': 10000,
    }
    with patch('modules.portal.services.stripe_settlement_service.StripeSettlementService.reconcile_payment_intent') as mock_reconcile:
        _handle_payment_intent_succeeded(pi)
        mock_reconcile.assert_not_called()


def test_create_settlement_checkout_session_not_configured():
    from packages.billing.stripe_service import create_settlement_checkout_session
    result = create_settlement_checkout_session(customer_id=1, amount=100.0)
    assert result == {'error': 'Stripe not configured'}


def test_create_settlement_checkout_session_invalid_amount():
    with patch('packages.billing.stripe_service.STRIPE_SECRET_KEY', 'sk_test'), \
         patch('packages.billing.stripe_service._get_stripe') as mock_get:
        mock_get.return_value = MagicMock()
        from packages.billing.stripe_service import create_settlement_checkout_session
        result = create_settlement_checkout_session(customer_id=1, amount=0.0)
        assert result == {'error': 'Amount must be greater than zero'}


def test_create_settlement_checkout_session_invoice_success():
    with patch('packages.billing.stripe_service.STRIPE_SECRET_KEY', 'sk_test'), \
         patch('packages.billing.stripe_service._get_stripe') as mock_get:
        mock_stripe = MagicMock()
        mock_get.return_value = mock_stripe
        mock_session = MagicMock()
        mock_session.id = 'cs_test_settle_inv'
        mock_session.url = 'https://checkout.stripe.com/pay/cs_test_settle_inv'
        mock_session.status = 'open'
        mock_stripe.checkout.Session.create.return_value = mock_session

        from packages.billing.stripe_service import create_settlement_checkout_session
        result = create_settlement_checkout_session(
            customer_id=10,
            amount=350.50,
            settlement_type='invoice',
            invoice_id=42,
            invoice_number='INV-2026-00042',
            customer_name='Acme Diner',
            customer_email='diner@acme.com',
            payment_method_types=['card', 'us_bank_account'],
        )

        assert result['session_id'] == 'cs_test_settle_inv'
        assert result['url'] == 'https://checkout.stripe.com/pay/cs_test_settle_inv'
        assert result['amount'] == 350.50
        assert result['amount_cents'] == 35050
        assert result['settlement_type'] == 'invoice'
        assert result['invoice_id'] == 42
        assert result['payment_method_types'] == ['card', 'us_bank_account']

        call_kwargs = mock_stripe.checkout.Session.create.call_args[1]
        assert call_kwargs['mode'] == 'payment'
        assert call_kwargs['customer_email'] == 'diner@acme.com'
        assert call_kwargs['client_reference_id'] == 'cust_10_inv_42'
        assert call_kwargs['metadata']['customer_id'] == '10'
        assert call_kwargs['metadata']['invoice_id'] == '42'


def test_create_settlement_checkout_session_balance_success():
    with patch('packages.billing.stripe_service.STRIPE_SECRET_KEY', 'sk_test'), \
         patch('packages.billing.stripe_service._get_stripe') as mock_get:
        mock_stripe = MagicMock()
        mock_get.return_value = mock_stripe
        mock_session = MagicMock()
        mock_session.id = 'cs_test_settle_bal'
        mock_session.url = 'https://checkout.stripe.com/pay/cs_test_settle_bal'
        mock_session.status = 'open'
        mock_stripe.checkout.Session.create.return_value = mock_session

        from packages.billing.stripe_service import create_settlement_checkout_session
        result = create_settlement_checkout_session(
            customer_id=10,
            amount=1200.0,
            settlement_type='balance',
            invoice_ids=[1, 2, 3],
            customer_name='Acme Diner',
        )

        assert result['session_id'] == 'cs_test_settle_bal'
        assert result['amount'] == 1200.0
        assert result['amount_cents'] == 120000
        assert result['settlement_type'] == 'balance'

        call_kwargs = mock_stripe.checkout.Session.create.call_args[1]
        assert call_kwargs['client_reference_id'] == 'cust_10_balance'
        assert call_kwargs['metadata']['invoice_ids'] == '1,2,3'


def test_create_settlement_checkout_session_api_error():
    with patch('packages.billing.stripe_service.STRIPE_SECRET_KEY', 'sk_test'), \
         patch('packages.billing.stripe_service._get_stripe') as mock_get:
        mock_stripe = MagicMock()
        mock_get.return_value = mock_stripe
        mock_stripe.checkout.Session.create.side_effect = Exception('Stripe card declined / gateway error')

        from packages.billing.stripe_service import create_settlement_checkout_session
        result = create_settlement_checkout_session(customer_id=10, amount=100.0)
        assert result == {'error': 'Stripe card declined / gateway error'}


def test_get_checkout_session_not_configured():
    from packages.billing.stripe_service import get_checkout_session
    result = get_checkout_session('cs_test_123')
    assert result == {'error': 'Stripe not configured'}


def test_get_checkout_session_success():
    with patch('packages.billing.stripe_service.STRIPE_SECRET_KEY', 'sk_test'), \
         patch('packages.billing.stripe_service._get_stripe') as mock_get:
        mock_stripe = MagicMock()
        mock_get.return_value = mock_stripe
        mock_session = MagicMock()
        mock_session.id = 'cs_test_retrieve'
        mock_session.status = 'complete'
        mock_session.payment_status = 'paid'
        mock_session.payment_intent = 'pi_test_999'
        mock_session.amount_total = 75000
        mock_session.currency = 'usd'
        mock_session.customer_email = 'buyer@acme.com'
        mock_session.metadata = {'customer_id': '10', 'invoice_id': '42'}
        mock_stripe.checkout.Session.retrieve.return_value = mock_session

        from packages.billing.stripe_service import get_checkout_session
        result = get_checkout_session('cs_test_retrieve')

        assert result['session_id'] == 'cs_test_retrieve'
        assert result['status'] == 'complete'
        assert result['payment_status'] == 'paid'
        assert result['payment_intent_id'] == 'pi_test_999'
        assert result['amount_total'] == 750.0
        assert result['customer_email'] == 'buyer@acme.com'
        assert result['metadata'] == {'customer_id': '10', 'invoice_id': '42'}


def test_get_checkout_session_error():
    with patch('packages.billing.stripe_service.STRIPE_SECRET_KEY', 'sk_test'), \
         patch('packages.billing.stripe_service._get_stripe') as mock_get:
        mock_stripe = MagicMock()
        mock_get.return_value = mock_stripe
        mock_stripe.checkout.Session.retrieve.side_effect = Exception('Session not found')

        from packages.billing.stripe_service import get_checkout_session
        result = get_checkout_session('cs_invalid')
        assert result == {'error': 'Session not found'}

