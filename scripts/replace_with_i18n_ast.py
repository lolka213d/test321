#!/usr/bin/env python3
"""
Replace literal UI strings in Python source files with i18n.t('<key>') calls.
Usage:
  python scripts/replace_with_i18n_ast.py [--apply] FILE1 [FILE2 ...]

By default runs as dry-run and reports matches. Pass --apply to write changes (backups created).

Notes:
- Uses `i18n_candidates.json` (repo root) mapping en -> key to find replacement keys.
- Handles plain string literals and simple f-strings (JoinedStr) where formatted values are simple attribute access or names.
- Adds `from test321 import i18n` to files when changes are applied and import missing.
"""
import ast
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
I18N_JSON = ROOT / 'i18n_candidates.json'

if not I18N_JSON.exists():
    print('Error: i18n_candidates.json not found at', I18N_JSON)
    sys.exit(1)

data = json.loads(I18N_JSON.read_text(encoding='utf-8'))
# build en->key mapping. If duplicate ENs exist, first wins.
en_to_key = {}
for k, v in data.items():
    en = v.get('en')
    if en and en not in en_to_key:
        en_to_key[en] = k

# Helper: build template and root variables from node
if not hasattr(ast, 'unparse'):
    print('Requires Python 3.9+ for ast.unparse')
    sys.exit(1)


def template_and_roots_from_node(node):
    # returns (template_str, [root_var_names]) or (None, None)
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value, []
    if isinstance(node, ast.JoinedStr):
        parts = []
        roots = []
        for v in node.values:
            if isinstance(v, ast.Constant) and isinstance(v.value, str):
                parts.append(v.value)
            elif isinstance(v, ast.FormattedValue):
                expr = v.value
                expr_src = ast.unparse(expr).strip()
                parts.append('{' + expr_src + '}')
                # extract root name if it's a simple attribute or name
                root = None
                tmp = expr
                while isinstance(tmp, ast.Attribute):
                    tmp = tmp.value
                if isinstance(tmp, ast.Name):
                    root = tmp.id
                if root and root not in roots:
                    roots.append(root)
            else:
                # unsupported formatted part
                return None, None
        return ''.join(parts), roots
    return None, None


def make_i18n_call(key, roots):
    func = ast.Attribute(value=ast.Name(id='i18n', ctx=ast.Load()), attr='t', ctx=ast.Load())
    call_args = [ast.Constant(value=key)]
    keywords = [ast.keyword(arg=r, value=ast.Name(id=r, ctx=ast.Load())) for r in roots]
    return ast.Call(func=func, args=call_args, keywords=keywords)


class I18nTransformer(ast.NodeTransformer):
    def __init__(self, en_to_key):
        super().__init__()
        self.en_to_key = en_to_key
        self.modified = 0

    def visit_Assign(self, node: ast.Assign):
        # target like bl_label = '...'
        replaced = False
        for t in node.targets:
            if isinstance(t, ast.Name) and t.id in ('bl_label', 'bl_description'):
                template, roots = template_and_roots_from_node(node.value)
                if template and template in self.en_to_key:
                    key = self.en_to_key[template]
                    node.value = make_i18n_call(key, roots)
                    self.modified += 1
                    replaced = True
        return self.generic_visit(node) if not replaced else node

    def visit_Call(self, node: ast.Call):
        changed = False
        # keywords like text=..., label=..., bl_label=..., bl_description
        for kw in node.keywords:
            if kw.arg in ('text', 'label', 'bl_label', 'bl_description'):
                if isinstance(kw.value, (ast.Constant, ast.JoinedStr)):
                    template, roots = template_and_roots_from_node(kw.value)
                    if template and template in self.en_to_key:
                        key = self.en_to_key[template]
                        kw.value = make_i18n_call(key, roots)
                        changed = True
        # positional first-arg for .label(...) or .operator(...)
        if node.args:
            if isinstance(node.func, ast.Attribute) and node.func.attr in ('label', 'operator'):
                first = node.args[0]
                if isinstance(first, (ast.Constant, ast.JoinedStr)):
                    template, roots = template_and_roots_from_node(first)
                    if template and template in self.en_to_key:
                        key = self.en_to_key[template]
                        node.args[0] = make_i18n_call(key, roots)
                        changed = True
        if changed:
            self.modified += 1
        return self.generic_visit(node)


def ensure_i18n_import(src_text):
    # ensure "from test321 import i18n" exists; otherwise insert after module docstring or after imports
    if 'from test321 import i18n' in src_text or '\nimport i18n' in src_text:
        return src_text
    lines = src_text.splitlines(True)
    insert_at = 0
    # skip shebang
    if lines and lines[0].startswith('#!'):
        insert_at = 1
    # skip module docstring
    if insert_at < len(lines) and lines[insert_at].lstrip().startswith(('"""', "'''")):
        # find end of docstring
        delim = lines[insert_at].lstrip()[:3]
        i = insert_at + 1
        while i < len(lines) and delim not in lines[i]:
            i += 1
        insert_at = i + 1
    # otherwise, try insert after last import
    for i, line in enumerate(lines):
        if line.startswith('import ') or line.startswith('from '):
            insert_at = i + 1
    lines.insert(insert_at, 'from test321 import i18n\n')
    return ''.join(lines)


def process_file(path: Path, apply=False):
    src = path.read_text(encoding='utf-8')
    try:
        tree = ast.parse(src)
    except Exception as e:
        print('Failed to parse', path, e)
        return 0, 'parse_error'
    tr = I18nTransformer(en_to_key)
    new_tree = tr.visit(tree)
    if tr.modified == 0:
        return 0, 'no_changes'
    ast.fix_missing_locations(new_tree)
    new_src = ast.unparse(new_tree)
    # ensure import
    if apply:
        new_src = ensure_i18n_import(new_src)
        # backup
        bak = path.with_suffix(path.suffix + '.i18n.bak')
        bak.write_text(src, encoding='utf-8')
        path.write_text(new_src, encoding='utf-8')
        return tr.modified, f'applied ({bak.name})'
    else:
        return tr.modified, 'dry_run'


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--apply', action='store_true', help='Write changes')
    ap.add_argument('files', nargs='+', help='Files or globs to process')
    args = ap.parse_args()

    targets = []
    for f in args.files:
        p = Path(f)
        if '*' in f or '?' in f:
            targets.extend(list(Path('.').glob(f)))
        elif p.is_file():
            targets.append(p)
        else:
            # try glob in repo root
            targets.extend(list(Path('.').glob(f)))
    if not targets:
        print('No target files found')
        sys.exit(1)

    total_changed = 0
    summary = []
    for t in targets:
        changed, status = process_file(t, apply=args.apply)
        summary.append((str(t), changed, status))
        total_changed += changed
    print('Summary:')
    for s in summary:
        print(f'  {s[0]}: changes={s[1]} status={s[2]}')
    print('Total replacements:', total_changed)
