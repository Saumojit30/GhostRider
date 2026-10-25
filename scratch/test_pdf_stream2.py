with open("dataset/evidence/documents/delivery_correction_attachment.pdf", "rb") as f:
    data = f.read()

s_idx = 63064
e_idx = 64410
raw = data[s_idx:s_idx+20]
print("Raw around stream:", raw)

# find the newline
nl = data.find(b"\n", s_idx)
raw_stream = data[nl+1:e_idx]
import zlib
try:
    d = zlib.decompress(raw_stream)
    print("Decompressed stream:", d)
except Exception as e:
    print("Fail:", e)
