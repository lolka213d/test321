#!/usr/bin/env python3
from pathlib import Path
p = Path('i18n_candidates.json')
if not p.exists():
    print('File not found:', p)
    raise SystemExit(1)

s = p.read_text(encoding='utf-8', errors='replace')
lines = s.splitlines(True)
found = False
for lineno, line in enumerate(lines, start=1):
    for col, ch in enumerate(line, start=1):
        if ord(ch) < 32 and ch not in ('\n','\r','\t'):
            print(f"Control char U+{ord(ch):04X} at line {lineno} col {col} repr={repr(ch)}")
            start = max(0, col-20)
            end = min(len(line), col+20)
            print('Line snippet (escaped):', line[start:end].encode('unicode_escape'))
            found = True
if not found:
    print('No non-whitespace control characters found')
