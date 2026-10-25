import glob, sqlite3, os

for p in glob.glob('dataset/evidence/databases/*.sql'):
    conn = sqlite3.connect(':memory:')
    try:
        with open(p, 'r', encoding='utf-8') as f:
            conn.executescript(f.read())
        tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
        for t in tables:
            try:
                rows = conn.execute(f'SELECT * FROM "{t}"').fetchall()
                for r in rows:
                    for target in ['6645', '5569']:
                        if target in str(r):
                            print(f'Found {target} in {p} table {t}: {r}')
            except Exception:
                pass
    except Exception as e:
        pass
