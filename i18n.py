DEFAULT_LANG = 'en'

def _get_pref_lang():
    try:
        import bpy
        # get_add_on_preferences is in oauth.lib and uses ADDON_NAME
        from test321.oauth.lib.get_add_on_preferences import get_add_on_preferences
        prefs = get_add_on_preferences(bpy.context.preferences)
        lang = getattr(prefs, 'language', None)
        if lang:
            return lang
    except Exception:
        pass
    return DEFAULT_LANG

translations = {
    'en': {
        'importing_models': 'Importing models...',
        'applied_animation': "Applied '{action}' to '{armature}'",
        'skipped_tracks': 'Skipped {n} tracks (no matching bone)',
        'please_select_mesh': 'Please select a mesh object.',
        'error_applying_scale': 'Error applying special mesh scale: {err}'
    },
    'ru': {
        'importing_models': 'Импорт моделей...',
        'applied_animation': "Применено '{action}' к '{armature}'",
        'skipped_tracks': 'Пропущено {n} треков (нет соответствующей кости)',
        'please_select_mesh': 'Пожалуйста, выберите объект типа Mesh.',
        'error_applying_scale': 'Ошибка применения масштаба: {err}'
    }
}

# If a generated candidates JSON exists, merge it into translations as EN defaults
try:
    import json
    from pathlib import Path
    cand = Path(__file__).resolve().parents[0] / 'i18n_candidates.json'
    if not cand.exists():
        # check repo root too
        cand = Path(__file__).resolve().parents[1] / 'i18n_candidates.json'
    if cand.exists():
        with cand.open(encoding='utf-8') as f:
            data = json.load(f)
        for k, v in data.items():
            en = v.get('en')
            ru = v.get('ru', '')
            if en and k not in translations.get('en', {}):
                translations.setdefault('en', {})[k] = en
            if k not in translations.get('ru', {}):
                translations.setdefault('ru', {})[k] = ru if ru is not None else ''
except Exception:
    pass


def set_lang(lang):
    global DEFAULT_LANG
    if lang in translations:
        DEFAULT_LANG = lang
        return True
    return False


def t(key, **kwargs):
    # language precedence: explicit _lang > addon preferences > DEFAULT_LANG
    lang = kwargs.pop('_lang', None) or _get_pref_lang() or DEFAULT_LANG
    text = translations.get(lang, translations['en']).get(key, translations['en'].get(key, key))
    if kwargs:
        try:
            return text.format(**kwargs)
        except Exception:
            return text
    return text
