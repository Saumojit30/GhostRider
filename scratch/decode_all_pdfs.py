import base64
import zlib
import re
import glob

def extract_pdf_texts(pdf_path):
    with open(pdf_path, "rb") as f:
        data = f.read()
    
    extracted = []
    # Find all streams with ASCII85 + Flate or just Flate
    for m in re.finditer(b"<<(.*?)/Length\\s+(\\d+)(.*?)>>\\s*stream\r?\n", data, re.DOTALL):
        dict_part = m.group(1) + m.group(3)
        length = int(m.group(2))
        s_start = m.end()
        raw_stream = data[s_start : s_start + length]
        
        # Check filters
        if b"ASCII85Decode" in dict_part and b"FlateDecode" in dict_part:
            try:
                a85 = base64.a85decode(raw_stream.strip(), adobe=True)
                decomp = zlib.decompress(a85)
                # extract Tj strings
                for tm in re.finditer(r"\((.*?)\)\s*Tj", decomp.decode('latin1', errors='ignore')):
                    extracted.append(tm.group(1))
            except Exception as e:
                pass
        elif b"FlateDecode" in dict_part:
            try:
                decomp = zlib.decompress(raw_stream)
                for tm in re.finditer(r"\((.*?)\)\s*Tj", decomp.decode('latin1', errors='ignore')):
                    extracted.append(tm.group(1))
            except Exception:
                pass
    return extracted

for p in glob.glob("dataset/evidence/documents/*.pdf"):
    txts = extract_pdf_texts(p)
    print(f"=== {p} ({len(txts)} text nodes) ===")
    print("Sample:", txts[:10])
