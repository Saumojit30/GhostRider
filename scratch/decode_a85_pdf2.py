import base64
import zlib

with open("dataset/evidence/documents/delivery_correction_attachment.pdf", "rb") as f:
    data = f.read()

s_idx = data.find(b"16 0 obj")
stream_start = data.find(b"stream\n", s_idx) + 7
stream_end = data.find(b"endstream", stream_start)
stream_bytes = data[stream_start:stream_end].strip()

a85 = base64.a85decode(stream_bytes, adobe=True)
decomp = zlib.decompress(a85)
print("SUCCESSFULLY DECOMPRESSED PDF PAGE 1!")
print(decomp.decode('latin1', errors='ignore'))
