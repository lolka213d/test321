#!/usr/bin/env python3
from pathlib import Path
import json
p = Path('i18n_candidates.json')
if not p.exists():
    print('File not found:', p)
    raise SystemExit(1)
raw = p.read_text(encoding='utf-8', errors='replace')

out = []
in_string = False
escaped = False
for ch in raw:
    if ch == '"' and not escaped:
        in_string = not in_string
        out.append(ch)
        escaped = False
        continue
    if ch == '\\' and not escaped:
        out.append(ch)
        escaped = True
        continue
    if ch == '\n':
        if in_string:
            out.append('\\n')
        else:
            out.append(ch)
        escaped = False
        continue
    if ch == '\r':
        if in_string:
            out.append('\\r')
        else:
            out.append(ch)
        escaped = False
        continue
    out.append(ch)
    escaped = False

fixed = ''.join(out)
# backup
bak = p.parent / (p.stem + '.escaped.bak')
bak.write_text(raw, encoding='utf-8')

try:
    json.loads(fixed)
except Exception as e:
    print('JSON still invalid after escaping newlines:', e)
    print('Backup saved to', bak)
    raise

p.write_text(fixed, encoding='utf-8')
print('Escaped newlines in strings; backup at', bak)
