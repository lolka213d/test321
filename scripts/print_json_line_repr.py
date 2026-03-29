#!/usr/bin/env python3
from pathlib import Path
p = Path('i18n_candidates.json')
text = p.read_text(encoding='utf-8', errors='replace')
lines = text.splitlines(True)
for num in range(552, 566):
    if num-1 < len(lines):
        print(f"LINE {num}: repr ->", repr(lines[num-1]))
    else:
        print(f"LINE {num}: (no line)")
