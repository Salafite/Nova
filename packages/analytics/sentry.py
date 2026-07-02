import os

SENTRY_DSN = os.environ.get('SENTRY_DSN', '')


def init_sentry(app_type='fastapi'):
    if not SENTRY_DSN:
        return
    import sentry_sdk
    from sentry_sdk.integrations.fastapi import FastApiIntegration
    sentry_sdk.init(
        dsn=SENTRY_DSN,
        integrations=[FastApiIntegration()],
        traces_sample_rate=0.1,
        release=os.environ.get('RELEASE_VERSION', 'dev'),
    )


def set_user_context(user_id: int, role: str = None):
    if not SENTRY_DSN:
        return
    import sentry_sdk
    with sentry_sdk.configure_scope() as scope:
        scope.set_user({'id': str(user_id)})
        if role:
            scope.set_tag('user_role', role)
