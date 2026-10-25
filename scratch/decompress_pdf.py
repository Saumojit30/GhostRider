import re
import zlib

with open("dataset/evidence/documents/delivery_correction_attachment.pdf", "rb") as f:
    data = f.read()

for m in re.finditer(b"stream\r?\n(.*?)\r?\nendstream", data, re.DOTALL):
    chunk = m.group(1)
    try:
        decomp = zlib.decompress(chunk)
        print("Decompressed text:", decomp[:300])
    except Exception:
        pass
