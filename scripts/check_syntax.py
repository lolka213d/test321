#!/usr/bin/env python3
import os, py_compile, sys
errs = []
for dirpath, dirnames, filenames in os.walk('.'):
    # skip common irrelevant folders
    if any(p in dirpath for p in ('.git', '__pycache__')):
        continue
    for fn in filenames:
        if not fn.endswith('.py'):
            continue
        fp = os.path.join(dirpath, fn)
        try:
            py_compile.compile(fp, doraise=True)
        except Exception as e:
            errs.append((fp, str(e)))

for e in errs[:200]:
    print('ERR:', e[0], e[1])
print('TOTAL_ERRORS', len(errs))
sys.exit(1 if errs else 0)
