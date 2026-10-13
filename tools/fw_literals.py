"""List peripheral base addresses a Thumb firmware actually uses (PC-relative LDR literals and MOVW/MOVT pairs),
the vector table / image header words, and where the USB VID/PID appears.

Usage: python tools/fw_literals.py <file.hex> [--vid 0x1532 --pid 0x02B0]
"""
import argparse
import struct
from collections import Counter

from capstone import CS_ARCH_ARM, CS_MODE_THUMB, Cs
from capstone.arm import ARM_OP_IMM, ARM_OP_MEM, ARM_OP_REG, ARM_REG_PC
from intelhex import IntelHex

ap = argparse.ArgumentParser()
ap.add_argument("hex")
ap.add_argument("--vid", type=lambda s: int(s, 0), default=0x1532)
ap.add_argument("--pid", type=lambda s: int(s, 0), default=0x02B0)
a = ap.parse_args()

ih = IntelHex(a.hex)
lo = ih.minaddr()
img = ih.tobinstr(start=lo, end=ih.maxaddr())
words = struct.unpack_from(f"<{len(img) // 4}I", img[: len(img) // 4 * 4])

print("vector table / header words:")
for i in range(0, 96, 8):
    print(f"  +0x{i * 4:03X}: " + " ".join(f"{w:08X}" for w in words[i:i + 8]))
default = Counter(words[16:200]).most_common(1)[0][0]
nirq = 0
for i in range(16, 200):
    w = words[i]
    if w == 0 or (lo <= (w & ~1) < lo + len(img) and (w & 1)):
        nirq = i - 15
    else:
        break
used = [i - 16 for i in range(16, 16 + nirq) if words[i] not in (0, default)]
print(f"IRQ vectors: {nirq}, default handler 0x{default:08X}, dedicated: {used}")

md = Cs(CS_ARCH_ARM, CS_MODE_THUMB)
md.detail = True
md.skipdata = True
pages = Counter()
movw = {}


def add(v):
    if 0x40000000 <= v < 0x60000000 or 0xE0000000 <= v < 0xE0100000:
        pages[v & ~0xFFF] += 1


for ins in md.disasm(img, lo):
    if ins.id == 0:  # SKIPDATA placeholder (undecodable bytes)
        continue
    m = ins.mnemonic
    ops = ins.operands
    if m.startswith("ldr") and ops:
        for op in ops:
            if op.type == ARM_OP_MEM and op.mem.base == ARM_REG_PC:
                addr = ((ins.address + 4) & ~3) + op.mem.disp
                if lo <= addr <= lo + len(img) - 4:
                    add(struct.unpack_from("<I", img, addr - lo)[0])
    elif m == "movw" and len(ops) == 2 and ops[0].type == ARM_OP_REG and ops[1].type == ARM_OP_IMM:
        movw[ops[0].reg] = ops[1].imm & 0xFFFF
    elif m == "movt" and len(ops) == 2 and ops[0].type == ARM_OP_REG and ops[1].type == ARM_OP_IMM:
        if ops[0].reg in movw:
            add(((ops[1].imm & 0xFFFF) << 16) | movw.pop(ops[0].reg))

print("peripheral pages used (LDR literals + MOVW/MOVT), count >= 2:")
for page, n in sorted(pages.items()):
    if n >= 2:
        print(f"  0x{page:08X}: {n}")

ids = struct.pack("<HH", a.vid, a.pid)
pos = [i for i in range(len(img) - 3) if img[i:i + 4] == ids]
print(f"VID/PID {a.vid:04X}:{a.pid:04X} bytes at:", ", ".join(f"0x{lo + p:08X}" for p in pos[:10]) or "none")
