#!/usr/bin/env python3
"""
Fill empty 'ru' fields in i18n_candidates.json by copying the English string.
This is an automated fallback pass so every key has a non-empty 'ru' value.
Run: python scripts/fill_i18n_ru.py
"""
from pathlib import Path
from datetime import datetime
import json

ROOT = Path(__file__).resolve().parents[1]
JSN = ROOT / 'i18n_candidates.json'
if not JSN.exists():
    print(f"ERROR: {JSN} not found")
    raise SystemExit(1)

bak = JSN.parent / (JSN.stem + '_' + datetime.now().strftime('%Y%m%d%H%M%S') + '.bak.json')
bak.write_text(JSN.read_text(encoding='utf-8'), encoding='utf-8')

data = json.loads(JSN.read_text(encoding='utf-8'))
filled = 0
for k, v in data.items():
    if not isinstance(v, dict):
        continue
    en = v.get('en', '')
    ru = v.get('ru', None)
    if (ru is None) or (ru == ''):
        data[k]['ru'] = en
        filled += 1

JSN.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
print(f"Filled {filled} keys (set 'ru' = 'en' where empty). Total keys: {len(data)}. Backup: {bak}")
