#!/usr/bin/env python3
from pathlib import Path
p = Path('i18n_candidates.json')
if not p.exists():
    print('File not found:', p)
    raise SystemExit(1)

s = p.read_text(encoding='utf-8', errors='replace')
lineno = 1
colno = 0
in_string = False
escaped = False
problems = []
for i, ch in enumerate(s):
    colno += 1
    if ch == '\n':
        lineno += 1
        colno = 0
    if ch == '"' and not escaped:
        in_string = not in_string
    if in_string and ch == '\n':
        # newline inside an open JSON string -> invalid
        problems.append((lineno, colno, i))
    if ch == '\\' and not escaped:
        escaped = True
    else:
        escaped = False

if not problems:
    print('No unescaped newline found inside JSON string literals')
else:
    print('Found unescaped newlines inside JSON strings at:')
    for lineno, colno, idx in problems[:20]:
        print(f'  line {lineno}, col {colno}, idx {idx}')
