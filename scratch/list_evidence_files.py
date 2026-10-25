import csv
from pathlib import Path

with open('dataset/evidence_files.csv', encoding='utf-8') as f:
    files = list(csv.DictReader(f))

print(f"Total evidence files: {len(files)}")
file_types = {}
for r in files:
    ext = Path(r['file_path']).suffix
    file_types[ext] = file_types.get(ext, 0) + 1

print("File types count:", file_types)

for r in sorted(files, key=lambda x: x['captured_at']):
    print(f"{r['file_id']:<14} {r['captured_at']} {r['source_origin']:<35} {r['file_path']}")
