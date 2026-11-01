import zlib, struct, os, shutil

def crop_png(in_path, out_path, pad=12):
    with open(in_path, 'rb') as f:
        data = f.read()

    pos = 8
    idat_chunks = []
    w, h, depth, colortype = 0, 0, 0, 0
    while pos < len(data):
        length, = struct.unpack('>I', data[pos:pos+4])
        chunk_type = data[pos+4:pos+8]
        chunk_data = data[pos+8:pos+8+length]
        pos += 12 + length
        if chunk_type == b'IHDR':
            w, h, depth, colortype = struct.unpack('>IIBB', chunk_data[:10])
        elif chunk_type == b'IDAT':
            idat_chunks.append(chunk_data)
        elif chunk_type == b'IEND':
            break

    raw = zlib.decompress(b''.join(idat_chunks))
    bpp = 4
    stride = 1 + w * bpp
    img = bytearray(w * h * bpp)

    def paeth(a, b, c):
        p = a + b - c
        pa = abs(p - a)
        pb = abs(p - b)
        pc = abs(p - c)
        if pa <= pb and pa <= pc: return a
        if pb <= pc: return b
        return c

    for y in range(h):
        filter_type = raw[y * stride]
        r_start = y * stride + 1
        curr_row = raw[r_start : r_start + w * bpp]
        out_start = y * w * bpp
        prev_row_start = (y - 1) * w * bpp
        for x in range(w * bpp):
            c = curr_row[x]
            left = img[out_start + x - bpp] if x >= bpp else 0
            up = img[prev_row_start + x] if y > 0 else 0
            upleft = img[prev_row_start + x - bpp] if (y > 0 and x >= bpp) else 0
            if filter_type == 0: val = c
            elif filter_type == 1: val = (c + left) & 0xff
            elif filter_type == 2: val = (c + up) & 0xff
            elif filter_type == 3: val = (c + ((left + up) >> 1)) & 0xff
            elif filter_type == 4: val = (c + paeth(left, up, upleft)) & 0xff
            img[out_start + x] = val

    min_x, max_x = w, 0
    min_y, max_y = h, 0
    for y in range(h):
        for x in range(w):
            idx = (y * w + x) * 4
            a = img[idx + 3]
            if a > 20:
                if x < min_x: min_x = x
                if x > max_x: max_x = x
                if y < min_y: min_y = y
                if y > max_y: max_y = y

    min_x = max(0, min_x - pad)
    min_y = max(0, min_y - pad)
    max_x = min(w - 1, max_x + pad)
    max_y = min(h - 1, max_y + pad)

    new_w = max_x - min_x + 1
    new_h = max_y - min_y + 1

    cropped_raw = bytearray()
    for y in range(min_y, max_y + 1):
        cropped_raw.append(0)
        start_idx = (y * w + min_x) * 4
        end_idx = start_idx + new_w * 4
        cropped_raw.extend(img[start_idx:end_idx])

    compressed = zlib.compress(bytes(cropped_raw), level=9)

    def make_chunk(chunk_type, chunk_payload):
        crc = zlib.crc32(chunk_type + chunk_payload) & 0xffffffff
        return struct.pack('>I', len(chunk_payload)) + chunk_type + chunk_payload + struct.pack('>I', crc)

    png_data = bytearray(b'\x89PNG\r\n\x1a\n')
    ihdr = struct.pack('>IIBBBBB', new_w, new_h, 8, 6, 0, 0, 0)
    png_data.extend(make_chunk(b'IHDR', ihdr))
    png_data.extend(make_chunk(b'IDAT', compressed))
    png_data.extend(make_chunk(b'IEND', b''))

    with open(out_path, 'wb') as f:
        f.write(png_data)

if __name__ == "__main__":
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    logos_dir = os.path.join(base_dir, 'logos')
    static_logos_dir = os.path.join(base_dir, 'static', 'logos')
    for fname in ['athena purple.png', 'athena red.png', 'athena blue.png']:
        in_p = os.path.join(logos_dir, fname)
        if os.path.exists(in_p):
            crop_png(in_p, in_p)
            shutil.copy2(in_p, os.path.join(static_logos_dir, fname))
