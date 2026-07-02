"""
Nova ERP Backend Localization / i18n Module

Provides server-side translation support matching the frontend locale file format.
Loads JSON translation files and provides a `_()` function for backend use.

Usage in any controller or service:
    from packages.localization import get_translator
    t = get_translator(lang='ar-EG')
    msg = t('not_found')  # "غير موجود"
    msg = t('record_not_found', entity='Product')  # "Product not found" / "المنتج غير موجود"
"""

import json
import os
import re
from typing import Optional

_LOCALE_DIR = os.path.join(os.path.dirname(__file__), 'locales')

_catalog_cache = {}

_AVAILABLE_LOCALES = {}

_LOCALE_MAP = {
    'en-US': 'en', 'en': 'en',
    'ar-EG': 'ar', 'ar': 'ar',
}

def _normalize_lang(lang: str) -> str:
    return _LOCALE_MAP.get(lang, 'en')

def _load_locale(lang: str) -> dict:
    normalized = _normalize_lang(lang)
    if normalized in _catalog_cache:
        return _catalog_cache[normalized]
    path = os.path.join(_LOCALE_DIR, f'{normalized}.json')
    if not os.path.exists(path):
        _catalog_cache[normalized] = {}
        return {}
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    _catalog_cache[normalized] = data
    return data


def get_available_locales():
    if _AVAILABLE_LOCALES:
        return _AVAILABLE_LOCALES
    locales = {}
    for fname in os.listdir(_LOCALE_DIR):
        if fname.endswith('.json'):
            code = fname[:-5]
            if code == 'en':
                locales[code] = {'name': 'English', 'nameNative': 'English', 'dir': 'ltr'}
            elif code == 'ar':
                locales[code] = {'name': 'Arabic', 'nameNative': 'العربية', 'dir': 'rtl'}
    _AVAILABLE_LOCALES.update(locales)
    return _AVAILABLE_LOCALES


class Translator:
    def __init__(self, lang: str = 'en'):
        self.lang = _normalize_lang(lang)
        self.dict = _load_locale(lang)

    def t(self, key: str, **kwargs) -> str:
        msg = self.dict.get(key, '')
        if not msg:
            return key
        if kwargs:
            for k, v in kwargs.items():
                msg = msg.replace('{' + k + '}', str(v))
        return msg

    def __call__(self, key: str, **kwargs) -> str:
        return self.t(key, **kwargs)


def get_translator(lang: Optional[str] = None) -> Translator:
    """
    Get a Translator instance for the given language code.
    Falls back to 'en' if the requested locale is not available.
    """
    if lang and _load_locale(lang):
        return Translator(lang)
    return Translator('en')
