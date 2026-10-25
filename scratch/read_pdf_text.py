import re

for fname in ['delivery_correction_attachment.pdf', 'account_history_report_20260718.pdf', 'legal_retention_register_20260529.pdf', 'security_retention_extract.pdf']:
    with open(f"dataset/evidence/documents/{fname}", "rb") as f:
        content = f.read().decode('latin1', errors='ignore')
    # search for text in PDF streams or strings
    texts = re.findall(r"\((.*?)\)", content)
    meaningful = [t for t in texts if len(t) > 3 and not re.match(r"^[\d\s\.]+$", t)]
    print(f"=== {fname} ===")
    print("Sample strings:", meaningful[:15])
