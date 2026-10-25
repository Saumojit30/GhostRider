import glob

def read_png_chunks(path):
    with open(path, "rb") as f:
        data = f.read()
    chunks = []
    idx = 8
    while idx < len(data):
        length = int.from_bytes(data[idx:idx+4], "big")
        ctype = data[idx+4:idx+8].decode('ascii', errors='ignore')
        cdata = data[idx+8:idx+8+length]
        if 'tEXt' in ctype or 'zTXt' in ctype or 'iTXt' in ctype:
            chunks.append((ctype, cdata))
        idx += 8 + length + 4
    return chunks

for p in glob.glob("dataset/evidence/images/*.png"):
    c = read_png_chunks(p)
    if c:
        print(f"=== {p} ===")
        for ct, cd in c:
            print(f"  {ct}: {cd[:200]}")
