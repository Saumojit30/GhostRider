import glob
import sqlite3
import re

for fpath in glob.glob('dataset/evidence/databases/*.sql'):
    with open(fpath, 'r', encoding='utf-8') as f:
        text = f.read()
    tables = re.findall(r"CREATE TABLE ([^\s\(]+)", text)
    print(f"{fpath}: {tables}")
