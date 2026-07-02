import os

RESEND_API_KEY = os.environ.get('RESEND_API_KEY', '')
FROM_EMAIL = os.environ.get('RESEND_FROM_EMAIL', 'noreply@novaerp.com')

_client = None


def _get_client():
    global _client
    if _client is None and RESEND_API_KEY:
        import resend
        resend.api_key = RESEND_API_KEY
        _client = resend
    return _client


def send_email(to: str, subject: str, html: str):
    client = _get_client()
    if not client:
        return
    client.Emails.send({'from': FROM_EMAIL, 'to': to, 'subject': subject, 'html': html})


def send_welcome(email: str, name: str):
    send_email(email, 'Welcome to Nova ERP',
               f'<h2>Welcome, {name}!</h2><p>Your account is ready. <a href="{os.environ.get("APP_URL", "http://localhost:5173")}/login">Log in here</a>.</p>')


def send_order_confirmed(email: str, order_number: str):
    send_email(email, f'Order {order_number} Confirmed',
               f'<h2>Order Confirmed</h2><p>Order <strong>{order_number}</strong> has been confirmed and is being processed.</p>')


def send_pick_completed(email: str, order_number: str):
    send_email(email, f'Pick Complete for Order {order_number}',
               f'<h2>Pick Completed</h2><p>All items for order <strong>{order_number}</strong> have been picked.</p>')


def send_payment_received(email: str, amount: float):
    send_email(email, 'Payment Received',
               f'<h2>Payment Received</h2><p>We received a payment of <strong>${amount:.2f}</strong>.</p>')


def send_invoice(email: str, invoice_number: str, amount: float):
    send_email(email, f'Invoice {invoice_number}',
               f'<h2>Invoice</h2><p>Invoice <strong>{invoice_number}</strong> for <strong>${amount:.2f}</strong> is attached.</p>')
