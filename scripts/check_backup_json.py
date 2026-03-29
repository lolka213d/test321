#!/usr/bin/env python3
import json
from pathlib import Path
p = Path('i18n_candidates_20260329154929.bak.json')
if not p.exists():
    print('backup not found', p)
    raise SystemExit(1)
try:
    data = json.load(open(p, encoding='utf-8'))
    print('backup json OK; total keys', len(data))
except Exception as e:
    print('backup json INVALID:', e)
