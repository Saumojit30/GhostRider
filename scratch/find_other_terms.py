import glob

terms = ['analytics_5589', 'support_1066', 'data_flow_223', 'backup_6266']

for path in glob.glob('dataset/evidence/**/*.*', recursive=True):
    try:
        with open(path, 'r', encoding='utf-8', errors='ignore') as f:
            c = f.read()
            for t in terms:
                if t in c:
                    print(f"Found {t} in {path}")
                    # show context
                    idx = c.find(t)
                    print(c[max(0, idx-100):min(len(c), idx+150)])
                    print("---")
    except Exception:
        pass
