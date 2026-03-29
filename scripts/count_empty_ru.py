#!/usr/bin/env python3
import json
from pathlib import Path
p = Path('i18n_candidates.json')
if not p.exists():
    print('no file')
    raise SystemExit(1)

data = json.load(open(p, encoding='utf-8'))
empty = [k for k,v in data.items() if not v.get('ru')]
print('total_keys', len(data))
print('empty_ru_count', len(empty))
if len(empty) <= 20:
    print('empty_keys:', empty)
