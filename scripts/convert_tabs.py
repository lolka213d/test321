#!/usr/bin/env python3
import os, sys, py_compile

root = os.path.dirname(os.path.dirname(__file__))
changed = []
skipped = []

for dirpath, dirnames, filenames in os.walk(root):
    # skip hidden VCS and caches
    if any(part in ('.git', '__pycache__') for part in dirpath.split(os.sep)):
        continue
    for fn in filenames:
        if not fn.endswith('.py'):
            continue
        fp = os.path.join(dirpath, fn)
        try:
            with open(fp, 'rb') as fh:
                b = fh.read()
            try:
                txt = b.decode('utf-8')
            except Exception:
                txt = b.decode('latin-1')
            if '\t' in txt:
                new = txt.replace('\t', '    ')
                with open(fp, 'wb') as fh:
                    fh.write(new.encode('utf-8'))
                changed.append(fp)
        except Exception as e:
            skipped.append((fp, str(e)))

# Try compiling changed files
errors = []
for fp in changed:
    try:
        py_compile.compile(fp, doraise=True)
    except Exception as e:
        errors.append((fp, str(e)))

print('CHANGED', len(changed))
for c in changed[:200]:
    print('CHANGED:', c)
print('SKIPPED', len(skipped))
for s in skipped[:50]:
    print('SKIP:', s[0], s[1])
print('COMPILE_ERRORS', len(errors))
for e in errors[:50]:
    print('ERR:', e[0], e[1])

if errors:
    sys.exit(2)
sys.exit(0)
