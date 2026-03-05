# i18n.py
from __future__ import annotations
from typing import Dict
import functools
import threading

# ===== Language list for the sidebar =====
INDIA_LANGS = [
    "English","Hindi","Bengali","Telugu","Marathi","Tamil","Urdu","Gujarati",
    "Kannada","Odia","Punjabi","Malayalam","Assamese","Maithili","Santali",
    "Kashmiri","Nepali","Konkani","Sindhi","Dogri","Manipuri","Bodo","Sanskrit",
    "Bhojpuri",
]

# ===== ISO codes (BCP-47) for googletrans =====
LANG_CODE: Dict[str, str] = {
    "English":"en","Hindi":"hi","Bengali":"bn","Telugu":"te","Marathi":"mr","Tamil":"ta","Urdu":"ur",
    "Gujarati":"gu","Kannada":"kn","Odia":"or","Punjabi":"pa","Malayalam":"ml","Assamese":"as",
    "Maithili":"mai","Santali":"sat","Kashmiri":"ks","Nepali":"ne","Konkani":"gom","Sindhi":"sd",
    "Dogri":"doi","Manipuri":"mni","Bodo":"brx","Sanskrit":"sa","Bhojpuri":"bho",
}

# ===== Translator (lazy singleton) =====
_translator = None
_lock = threading.Lock()

def _get_translator():
    global _translator
    if _translator is not None:
        return _translator
    with _lock:
        if _translator is None:
            try:
                from googletrans import Translator  # 4.0.0rc1
                _translator = Translator()
            except Exception:
                _translator = False
    return _translator

# ===== Cached translate call =====
@functools.lru_cache(maxsize=16384)
def _tx(text: str, code: str) -> str:
    tr = _get_translator()
    if not tr:
        return text
    try:
        return tr.translate(text, dest=code).text
    except Exception:
        return text

# ===== Public entrypoint =====
def t(text: str, lang: str = "English") -> str:
    if not text:
        return ""
    code = LANG_CODE.get(lang, "en")
    if code == "en":
        return text
    return _tx(text, code)
