import os

POSTHOG_API_KEY = os.environ.get('POSTHOG_API_KEY', '')
POSTHOG_HOST = os.environ.get('POSTHOG_HOST', 'https://app.posthog.com')

_client = None


def _get_client():
    global _client
    if _client is None and POSTHOG_API_KEY:
        from posthog import Posthog
        _client = Posthog(POSTHOG_API_KEY, host=POSTHOG_HOST)
    return _client


def capture_event(distinct_id: str, event: str, properties: dict = None):
    client = _get_client()
    if client:
        client.capture(distinct_id, event, properties or {})


def identify_user(distinct_id: str, properties: dict = None):
    client = _get_client()
    if client:
        client.identify(distinct_id, properties or {})
