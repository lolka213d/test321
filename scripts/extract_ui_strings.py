#!/usr/bin/env python3
"""Extract user-facing UI strings into i18n_catalog.csv.

Searches .py, .html, .txt files for common UI patterns (bl_label, layout.label, self.report, print, etc.)
and writes a CSV with file, line, pattern, and extracted string.
"""
from pathlib import Path
import re
import csv
import ast
import sys

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'i18n_catalog.csv'

PY_PATTERNS = [
    (r'bl_label', re.compile(r'bl_label\s*=\s*(?P<lit>(?:[rubfRUBF]{,2})?["\'].*?["\'])')),
    (r'bl_description', re.compile(r'bl_description\s*=\s*(?P<lit>(?:[rubfRUBF]{,2})?["\'].*?["\'])')),
    (r'layout.label', re.compile(r'layout\.label\s*\(\s*text\s*=\s*(?P<lit>(?:[rubfRUBF]{,2})?["\'].*?["\'])')),
    (r'label(text=', re.compile(r'label\s*\(\s*text\s*=\s*(?P<lit>(?:[rubfRUBF]{,2})?["\'].*?["\'])')),
    (r'layout.operator text=', re.compile(r'layout\.operator\([^)]*?text\s*=\s*(?P<lit>(?:[rubfRUBF]{,2})?["\'].*?["\'])')),
    (r'text=', re.compile(r'\btext\s*=\s*(?P<lit>(?:[rubfRUBF]{,2})?["\'].*?["\'])')),
    (r'self.report', re.compile(r'self\.report\s*\([^,]+,\s*(?P<lit>(?:[rubfRUBF]{,2})?["\'].*?["\'])')),
    (r'print(', re.compile(r'\bprint\s*\(\s*(?P<lit>(?:f|F|r|u|b|R|U|B|fr|rf|FR|RF)?["\'].*?["\'])')),
]

HTML_TXT_PATTERNS = [
    re.compile(r"[\">](?P<t>[^<>\n]{3,200})[<\n]")
]

def extract_literal(lit):
    # Try to eval normal string literals, fallback to stripping prefixes and quotes
    try:
        return ast.literal_eval(lit)
    except Exception:
        # remove common prefixes like f, r, u, b
        s = lit
        while s and s[0].lower() in 'frub':
            s = s[1:]
        if len(s) >= 2 and s[0] in ('"', "'") and s[-1] == s[0]:
            return s[1:-1]
        return s


def scan_py(path):
    out = []
    text = path.read_text(encoding='utf-8', errors='ignore')
    for i, line in enumerate(text.splitlines(), start=1):
        for name, pat in PY_PATTERNS:
            m = pat.search(line)
            if m:
                lit = m.group('lit')
                val = extract_literal(lit)
                out.append((str(path.relative_to(ROOT)), i, name, val, line.strip()))
    return out


def scan_html_txt(path):
    out = []
    text = path.read_text(encoding='utf-8', errors='ignore')
    for i, line in enumerate(text.splitlines(), start=1):
        for pat in HTML_TXT_PATTERNS:
            m = pat.search(line)
            if m:
                t = m.group('t').strip()
                if t:
                    out.append((str(path.relative_to(ROOT)), i, 'html/text', t, line.strip()))
    return out


def main():
    rows = []
    exts_py = ['.py']
    exts_html = ['.html', '.htm', '.txt']
    for p in ROOT.rglob('*'):
        if p.is_file():
            try:
                if p.suffix.lower() in exts_py:
                    rows.extend(scan_py(p))
                elif p.suffix.lower() in exts_html:
                    rows.extend(scan_html_txt(p))
            except Exception as e:
                print(f"Skipping {p}: {e}")

    # deduplicate exact matches
    seen = set()
    unique = []
    for r in rows:
        key = (r[0], r[1], r[2], r[3])
        if key in seen:
            continue
        seen.add(key)
        unique.append(r)

    with OUT.open('w', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        w.writerow(['file', 'line', 'pattern', 'string', 'source_line'])
        for r in unique:
            w.writerow(r)

    print(f"Extracted {len(unique)} candidate strings → {OUT}")


if __name__ == '__main__':
    main()
