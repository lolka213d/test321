#!/usr/bin/env python3
from pathlib import Path
import json
p = Path('i18n_candidates.json')
if not p.exists():
    print('File not found:', p)
    raise SystemExit(1)
raw = p.read_text(encoding='utf-8', errors='replace')
# backup
bak = p.parent / (p.stem + '.repair2.bak')
bak.write_text(raw, encoding='utf-8')
text = raw
# remove stray escaped-closing-quote patterns prior to newline
count_fix = 0
while True:
    new = text.replace('\\"\n', '"\n')
    if new == text:
        break
    text = new
    count_fix += 1
print('replaced \\"\\n occurrences:', count_fix)
# escape raw newlines inside JSON string literals
out = []
in_string = False
escaped = False
for ch in text:
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
# validate
try:
    json.loads(fixed)
except Exception as e:
    # write a diagnostic copy
    diag = p.parent / (p.stem + '.repair2.failed.json')
    diag.write_text(fixed, encoding='utf-8')
    print('JSON still invalid after repair:', e)
    print('Diagnostic file written to', diag)
    raise
# write fixed
p.write_text(fixed, encoding='utf-8')
print('Repaired and validated JSON; backup at', bak)
