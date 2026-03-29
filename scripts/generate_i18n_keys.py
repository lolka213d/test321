#!/usr/bin/env python3
"""Generate i18n key template from i18n_catalog.csv

Produces two files at repo root:
- i18n_candidates.json: { key: {"en": ..., "ru": ""} }
- i18n_candidates.csv: key,en
"""
from pathlib import Path
import csv
import json
import re
import hashlib

ROOT = Path(__file__).resolve().parents[1]
IN = ROOT / 'i18n_catalog.csv'
OUT_JSON = ROOT / 'i18n_candidates.json'
OUT_CSV = ROOT / 'i18n_candidates.csv'


def slugify(s):
    s = s.lower()
    s = re.sub(r"\s+", "_", s)
    s = re.sub(r"[^a-z0-9_]+", "", s)
    s = re.sub(r"_+", "_", s)
    s = s.strip("_")
    if not s:
        s = 's'
    if len(s) > 40:
        s = s[:40].rstrip("_")
    return s


def short_hash(s):
    return hashlib.md5(s.encode('utf-8')).hexdigest()[:8]


def main():
    if not IN.exists():
        print("i18n_catalog.csv not found. Run scripts/extract_ui_strings.py first.")
        return

    strings = []
    with IN.open(encoding='utf-8', newline='') as f:
        r = csv.reader(f)
        headers = next(r, None)
        for row in r:
            if len(row) < 4:
                continue
            s = row[3].strip()
            if not s:
                continue
            strings.append(s)

    # dedupe preserving order
    seen = set()
    uniq = []
    for s in strings:
        if s in seen:
            continue
        seen.add(s)
        uniq.append(s)

    mapping = {}
    for s in uniq:
        base = slugify(s)
        key = base
        if key in mapping:
            key = f"{base}_{short_hash(s)}"
        else:
            # guard against accidental common short keys
            if sum(1 for ch in key if ch.isalpha()) < 3:
                key = f"{base}_{short_hash(s)}"
        mapping[key] = {"en": s, "ru": ""}

    with OUT_JSON.open('w', encoding='utf-8') as f:
        json.dump(mapping, f, ensure_ascii=False, indent=2)

    with OUT_CSV.open('w', encoding='utf-8', newline='') as f:
        w = csv.writer(f)
        w.writerow(['key', 'en'])
        for k, v in mapping.items():
            w.writerow([k, v['en']])

    print(f"Wrote {len(mapping)} keys → {OUT_JSON} and {OUT_CSV}")


if __name__ == '__main__':
    main()
