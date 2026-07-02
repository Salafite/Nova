"""
FastAPI dependency for request-scoped translation.

Usage:
    from packages.localization.deps import get_translator_from_request
    from packages.localization import Translator

    @router.get('/example')
    def example(t: Translator = Depends(get_translator_from_request)):
        return {'message': t('not_found')}
"""

from fastapi import Request, Depends
from packages.localization import Translator, get_translator


def get_translator_from_request(request: Request) -> Translator:
    lang = request.headers.get('Accept-Language', 'en')
    if lang and ',' in lang:
        lang = lang.split(',')[0].split(';')[0].strip()
    return get_translator(lang)
