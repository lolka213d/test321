import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
import i18n

print('Default language:', i18n.DEFAULT_LANG)
print('EN:', i18n.t('importing_models'))
i18n.set_lang('ru')
print('After set RU ->', i18n.DEFAULT_LANG)
print('RU:', i18n.t('importing_models'))
print(i18n.t('applied_animation', action='Walk', armature='Armature1'))
