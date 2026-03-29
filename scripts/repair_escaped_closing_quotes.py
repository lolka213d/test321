#!/usr/bin/env python3
from pathlib import Path
p = Path('i18n_candidates.json')
if not p.exists():
    print('File not found:', p)
    raise SystemExit(1)
raw = p.read_text(encoding='utf-8', errors='replace')
# backup
bak = p.parent / (p.stem + '.repair.bak')
bak.write_text(raw, encoding='utf-8')
new = raw.replace('\\"\n','"\n')
if new == raw:
    print('No matches for \\\\"\\n pattern; nothing changed')
else:
    p.write_text(new, encoding='utf-8')
    print('Replaced occurrences of \\\\"\\n with \"\\n; backup at', bak)
    # quick validate
    import json
    try:
        json.loads(new)
        print('JSON parses OK after repair')
    except Exception as e:
        print('JSON still invalid:', e)
