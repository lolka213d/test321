#!/usr/bin/env python3
import csv, json, re
from pathlib import Path

csv_path = Path('i18n_candidates.csv')
bak_path = Path('i18n_candidates_20260329154929.bak.json')
out_path = Path('i18n_candidates.json')

if not csv_path.exists():
    print('CSV not found:', csv_path)
    raise SystemExit(1)
if not bak_path.exists():
    print('backup not found:', bak_path)
    raise SystemExit(1)

# load CSV en values
csv_en = {}
with csv_path.open(encoding='utf-8', newline='') as f:
    reader = csv.DictReader(f)
    for row in reader:
        key = row.get('key')
        en = row.get('en', '')
        if key:
            csv_en[key] = en

text = bak_path.read_text(encoding='utf-8', errors='replace')
# find object blocks keyed by "key": { ... }
pattern = re.compile(r'"([^\"]+)":\s*{(.*?)}', re.S)
backup_en = {}
backup_ru = {}
for m in pattern.finditer(text):
    key = m.group(1)
    block = m.group(2)
    # en
    m_en = re.search(r'"en"\s*:\s*"((?:\\.|[^"])*)"', block, re.S)
    if m_en:
        try:
            en_val = json.loads('"' + m_en.group(1) + '"')
        except Exception:
            en_val = m_en.group(1)
        backup_en[key] = en_val
    # ru
    m_ru = re.search(r'"ru"\s*:\s*"((?:\\.|[^"])*)"', block, re.S)
    if m_ru:
        try:
            ru_val = json.loads('"' + m_ru.group(1) + '"')
        except Exception:
            ru_val = m_ru.group(1)
        backup_ru[key] = ru_val

# Build final data
keys = set(csv_en.keys()) | set(backup_en.keys()) | set(backup_ru.keys())
final = {}
for k in sorted(keys):
    en = csv_en.get(k, backup_en.get(k, k))
    ru = backup_ru.get(k)
    if not ru:
        # fall back to backup_en or en
        ru = backup_en.get(k, '') or en
    final[k] = {'en': en, 'ru': ru}

# backup existing out
if out_path.exists():
    out_path.with_suffix('.pre_rebuild.bak').write_text(out_path.read_text(encoding='utf-8'), encoding='utf-8')

out_path.write_text(json.dumps(final, ensure_ascii=False, indent=2), encoding='utf-8')
print('Wrote', out_path, 'keys:', len(final))
