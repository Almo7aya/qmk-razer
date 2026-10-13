"""Fingerprint a firmware image: memory layout, Cortex-M vector table, peripheral-address histogram, strings.

Usage: python tools/fingerprint_fw.py <file.hex|file.bin> [--base 0x08000000]
"""
import argparse
import math
import re
import struct
from collections import Counter
from pathlib import Path

from intelhex import IntelHex


def load(path, base):
    if path.suffix.lower() == ".hex":
        ih = IntelHex(str(path))
        segs = ih.segments()
        lo, hi = ih.minaddr(), ih.maxaddr() + 1
        ih.padding = 0xFF
        return lo, ih.tobinstr(start=lo, end=hi - 1), segs
    data = path.read_bytes()
    return base, data, [(base, base + len(data))]


def entropy(b):
    c = Counter(b)
    return -sum(n / len(b) * math.log2(n / len(b)) for n in c.values()) if b else 0.0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("file")
    ap.add_argument("--base", type=lambda s: int(s, 0), default=0x08000000)
    a = ap.parse_args()
    p = Path(a.file)
    lo, img, segs = load(p, a.base)
    print(f"{p.name}: 0x{lo:08X}-0x{lo + len(img):08X} ({len(img)} bytes), entropy {entropy(img):.2f} bits/byte")
    for s, e in segs[:12]:
        print(f"  segment 0x{s:08X}-0x{e:08X} ({e - s} bytes)")

    sp, reset = struct.unpack_from("<II", img, 0)
    print(f"vector table @0x{lo:08X}: SP=0x{sp:08X} Reset=0x{reset:08X}")
    words = struct.unpack_from(f"<{len(img) // 4}I", img[: len(img) // 4 * 4])
    nvec = 0
    for i, v in enumerate(words[:300]):
        if i < 2:
            continue
        if v == 0 or (lo <= (v & ~1) < lo + len(img) and v & 1):
            nvec = i + 1
        else:
            break
    print(f"plausible vector entries: {nvec} (16 core + {max(0, nvec - 16)} IRQs)")

    hist = Counter()
    for w in words:
        if 0x40000000 <= w < 0x60000000 or 0xE0000000 <= w < 0xE0100000 or 0x1FF00000 <= w < 0x20000000:
            hist[w & 0xFFFFF000] += 1
    print("most referenced peripheral/system pages (literal pool words):")
    for page, n in hist.most_common(25):
        print(f"  0x{page:08X} x{n}")

    strings = re.findall(rb"[\x20-\x7e]{6,}", img)
    print(f"{len(strings)} ASCII strings; first/interesting ones:")
    keep = [s.decode() for s in strings if re.search(rb"(?i)razer|nxp|stm|gd32|wch|nuvoton|lpc|usb|hid|fsl|hal|keil|iar|gcc|ver|v\d|\.c\b|bootloader|ry|talia|analog|hall|adc", s)]
    for s in (keep or [s.decode() for s in strings])[:40]:
        print("  ", s[:100])


main()
