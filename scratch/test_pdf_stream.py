with open("dataset/evidence/documents/delivery_correction_attachment.pdf", "rb") as f:
    data = f.read()

idx = 0
while True:
    s_idx = data.find(b"stream", idx)
    if s_idx == -1:
        break
    e_idx = data.find(b"endstream", s_idx)
    raw = data[s_idx:e_idx]
    print(f"Stream at {s_idx}-{e_idx}: length={len(raw)}")
    # let's try decompressing starting after \r?\n
    stream_data = data[s_idx+6:e_idx].strip()
    import zlib
    try:
        d = zlib.decompress(stream_data)
        print("Success! First 200 bytes:", d[:200])
    except Exception as e:
        print("Fail:", e)
    idx = e_idx + 9
