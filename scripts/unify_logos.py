import zlib, struct, os

def read_png(path):
    with open(path, 'rb') as f:
        data = f.read()
    pos = 8
    idat = []
    w, h = 0, 0
    while pos < len(data):
        l, = struct.unpack('>I', data[pos:pos+4])
        t = data[pos+4:pos+8]
        d = data[pos+8:pos+8+l]
        pos += 12 + l
        if t == b'IHDR':
            w, h = struct.unpack('>II', d[:8])
        elif t == b'IDAT':
            idat.append(d)
        elif t == b'IEND':
            break
    raw = zlib.decompress(b''.join(idat))
    stride = 1 + w * 4
    pixels = bytearray(w * h * 4)
    for y in range(h):
        r_start = y * stride + 1
        pixels[y * w * 4 : (y + 1) * w * 4] = raw[r_start : r_start + w * 4]
    return w, h, pixels

def write_png(path, w, h, pixels):
    raw = bytearray()
    for y in range(h):
        raw.append(0)
        start = y * w * 4
        raw.extend(pixels[start : start + w * 4])
    compressed = zlib.compress(bytes(raw), level=9)
    def chunk(t, payload):
        crc = zlib.crc32(t + payload) & 0xffffffff
        return struct.pack('>I', len(payload)) + t + payload + struct.pack('>I', crc)
    out = bytearray(b'\x89PNG\r\n\x1a\n')
    out.extend(chunk(b'IHDR', struct.pack('>IIBBBBB', w, h, 8, 6, 0, 0, 0)))
    out.extend(chunk(b'IDAT', compressed))
    out.extend(chunk(b'IEND', b''))
    with open(path, 'wb') as f:
        f.write(out)

TARGET_W = 1920
TARGET_H = 1000

if __name__ == "__main__":
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    logos_dir = os.path.join(base_dir, 'logos')
    static_logos_dir = os.path.join(base_dir, 'static', 'logos')

    for fname in ['athena purple.png', 'athena red.png', 'athena blue.png']:
        in_path = os.path.join(logos_dir, fname)
        if os.path.exists(in_path):
            w, h, src_pix = read_png(in_path)
            canvas = bytearray(TARGET_W * TARGET_H * 4)
            ox = (TARGET_W - w) // 2
            oy = (TARGET_H - h) // 2
            for y in range(h):
                dst_y = oy + y
                if 0 <= dst_y < TARGET_H:
                    src_start = y * w * 4
                    src_end = src_start + w * 4
                    dst_start = (dst_y * TARGET_W + ox) * 4
                    canvas[dst_start : dst_start + w * 4] = src_pix[src_start:src_end]
            write_png(in_path, TARGET_W, TARGET_H, canvas)
            write_png(os.path.join(static_logos_dir, fname), TARGET_W, TARGET_H, canvas)
            print(f"Unified {fname}: {w}x{h} -> {TARGET_W}x{TARGET_H}")
