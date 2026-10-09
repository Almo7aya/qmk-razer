"""Reproduce the Keil/ARMCC __scatterload of the Huntsman Mini app image.

Region table at 0x08011D38..0x08011D68 (4 words per entry: src, dst, len, handler):
  0x08011D68 -> 0x20000000 len 0x1F0   handler 0x08008DE6 (__scatterload_copy)   = RAM-resident code
  0x08011F58 -> 0x200001F0 len 0x18C   handler 0x080041E8 (__decompress1, LZ77)  = .data
  0x08011FBC -> 0x2000037C len 0x661C  handler 0x08008DF6 (__scatterload_zeroinit) = .bss
"""
import struct
import sys
from pathlib import Path

BASE = 0x08004000


def decompress(src: bytes, pos: int, out_len: int) -> bytes:
    out = bytearray()
    while len(out) < out_len:
        b = src[pos]; pos += 1
        lit = b & 7
        if lit == 0:
            lit = src[pos]; pos += 1
        run = b >> 4
        if run == 0:
            run = src[pos]; pos += 1
        for _ in range(lit - 1):
            out.append(src[pos]); pos += 1
        if b & 8:
            off = src[pos]; pos += 1
            p = len(out) - off
            for _ in range(run + 2):
                out.append(out[p]); p += 1
        else:
            out.extend(b"\0" * run)
    return bytes(out[:out_len])


def ram_image(img: bytes):
    """Return list of (dst, bytes) for initialised RAM regions."""
    regions = []
    for a in range(0x08011D38, 0x08011D68, 16):
        src, dst, ln, fn = struct.unpack_from("<4I", img, a - BASE)
        if fn == 0x08008DE6:
            regions.append((dst, img[src - BASE: src - BASE + ln]))
        elif fn == 0x080041E8:
            regions.append((dst, decompress(img, src - BASE, ln)))
        else:
            regions.append((dst, b"\0" * ln))
    return regions


if __name__ == "__main__":
    img = Path(sys.argv[1]).read_bytes()
    for dst, data in ram_image(img):
        print(f"0x{dst:08X} len 0x{len(data):X}")
        if len(data) < 0x400:
            for i in range(0, len(data), 16):
                print(f"  {dst+i:08X}: " + " ".join(f"{x:02X}" for x in data[i:i+16]))
