from pathlib import Path
p = Path('i18n_candidates.json')
s = p.read_text(encoding='utf-8', errors='replace')
idx = 15570
start = max(0, idx-20)
end = min(len(s), idx+40)
segment = s[start:end]
print('SEGMENT repr:')
print(repr(segment))
print('\nCHAR BY CHAR:')
for i,ch in enumerate(segment):
    print(start+i, i, ord(ch), repr(ch))
