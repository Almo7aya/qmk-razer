"""Decode the static tables of the Huntsman Mini stock app (v1.12.00 / v1.32.00 share layout).

Usage: python extract_tables.py [bin]   -> prints everything; redirect to tables_v1_12.txt
All addresses below were located by following their xrefs in the Ghidra decompilation
(see decomp_hm_v1_12.c); they are build-specific.
"""
import struct
import sys
from pathlib import Path

BASE = 0x08004000
BIN = Path(sys.argv[1]) if len(sys.argv) > 1 else \
    Path(__file__).resolve().parents[2] / "stock/firmware/HuntsmanMini_dev1_v1.12.00.bin"
img = BIN.read_bytes()


def rd(addr, n):
    return img[addr - BASE: addr - BASE + n]


def u32(addr):
    return struct.unpack("<I", rd(addr, 4))[0]


# Razer/IBM "key number" -> label (only the ones used by this board + F-row etc.)
KN = {1: "`", 2: "1", 3: "2", 4: "3", 5: "4", 6: "5", 7: "6", 8: "7", 9: "8", 10: "9", 11: "0", 12: "-", 13: "=",
      14: "JIS_YEN", 15: "BSPC", 16: "TAB", 17: "Q", 18: "W", 19: "E", 20: "R", 21: "T", 22: "Y", 23: "U", 24: "I",
      25: "O", 26: "P", 27: "[", 28: "]", 29: "\\", 30: "CAPS", 31: "A", 32: "S", 33: "D", 34: "F", 35: "G", 36: "H",
      37: "J", 38: "K", 39: "L", 40: ";", 41: "'", 42: "ISO_#", 43: "ENT", 44: "LSFT", 45: "ISO_\\", 46: "Z",
      47: "X", 48: "C", 49: "V", 50: "B", 51: "N", 52: "M", 53: ",", 54: ".", 55: "/", 56: "JIS_RO", 57: "RSFT",
      58: "LCTL", 59: "FN", 60: "LALT", 61: "SPC", 62: "RALT", 64: "RCTL", 110: "ESC", 127: "LGUI", 129: "APP"}
for i in range(12):
    KN[112 + i] = f"F{i+1}"
KN.update({124: "PSCR", 125: "SCRL", 126: "PAUS", 75: "INS", 76: "DEL", 79: "LEFT", 80: "HOME", 81: "END",
           83: "UP", 84: "DOWN", 85: "PGUP", 86: "PGDN", 89: "RGHT"})


def kn(k):
    return KN.get(k, f"k{k:02X}") if k else "--"


ROW_PINS = []
for i in range(8):
    port, mask, pin = struct.unpack("<III", rd(0x080103C0 + 12 * i, 12))
    ROW_PINS.append("P" + "ABCDEH"[[0x40020000, 0x40020400, 0x40020800, 0x40020C00, 0x40021000, 0x40021400].index(port)] + str(pin))
COL_PINS = []
for i in range(8):
    port, mask, pin = struct.unpack("<III", rd(0x08010420 + 12 * i, 12))
    COL_PINS.append("P" + "ABCDEH"[[0x40020000, 0x40020400, 0x40020800, 0x40020C00, 0x40021000, 0x40021400].index(port)] + str(pin))

print("=== Matrix (keymap index table @0x08010380: [drive row r][sense col c] -> key number) ===")
print("row drive pins (active low) :", ROW_PINS)
print("col sense pins (low=pressed):", COL_PINS)
km = rd(0x08010380, 64)
print("        " + "".join(f"{c:>8s}" for c in COL_PINS))
for r in range(8):
    print(f"{ROW_PINS[r]:>4s} r{r} " + "".join(f"{kn(km[r*8+c]):>8s}" for c in range(8)))
print("(raw key numbers)")
for r in range(8):
    print(f"  r{r}: " + " ".join(f"{km[r*8+c]:02X}" for c in range(8)))

print("\n=== Key-action tables (126 x 8 bytes: keynum, type, len, data...) ===")
TYPES = {0x02: "HID kbd [mod,usage]", 0x0A: "consumer [u16 BE]", 0x11: "FN/internal fn#", 0x09: "special", 0x07: "?"}
tables = [0x08010969, 0x08010D59, 0x08011189 - 1, 0x08011578]
names = ["T0 base (default profile)", "T1 FN layer", "T2 (copy)", "T3 (copy)"]
parsed = []
for base, nm in zip(tables, names):
    ents = {}
    for i in range(126):
        e = rd(base + 8 * i, 8)
        if e[0] == 0:
            continue
        ents[e[0]] = e
    parsed.append(ents)
allk = sorted(set().union(*[set(p) for p in parsed]))
print(f"{'key':>6s} | {'T0 base':28s} | {'T1 FN':28s}")
for k in allk:
    def fmt(e):
        if e is None:
            return "-"
        t, ln = e[1], e[2]
        if t == 0x02:
            return f"kbd mod={e[3]:02X} usage={e[4]:02X}"
        if t == 0x0A:
            return f"consumer 0x{e[3]:02X}{e[4]:02X}"
        if t == 0x11:
            return f"fn #{e[3]:02X}"
        return f"type{t:02X} " + e[3:3 + ln].hex()
    print(f"{kn(k):>6s} | {fmt(parsed[0].get(k)):28s} | {fmt(parsed[1].get(k)):28s}")
for j in (2, 3):
    same = parsed[j] == parsed[0]
    print(f"{names[j]} identical to T0: {same}")

print("\n=== Per-key RGB map @0x08010657: 5x15 grid, entry = keynum,row,col,drv,R,G,B (IS31FL3733 PWM reg) ===")
leds = []
for r in range(5):
    for c in range(15):
        e = rd(0x08010657 + 7 * (r * 15 + c), 7)
        if e[0]:
            leds.append((r, c, e))
print(f"{'key':>6s} grid(r,c)  drv   R(reg SWy/CSx)    G               B")
for r, c, e in leds:
    def sc(v):
        return f"0x{v:02X} SW{v>>4 + 0}/CS{(v & 15)}"
    print(f"{kn(e[0]):>6s} ({r},{c:2d})     {e[3]}   0x{e[4]:02X} SW{(e[4]>>4)+1:<2d}CS{(e[4]&15)+1:<3d} "
          f"0x{e[5]:02X} SW{(e[5]>>4)+1:<2d}CS{(e[5]&15)+1:<3d} 0x{e[6]:02X} SW{(e[6]>>4)+1:<2d}CS{(e[6]&15)+1:<3d}")
print(f"LED entries: {len(leds)} (SW/CS printed 1-based as in the IS31FL3733 datasheet)")

print("\n=== Indicator overlay @0x080104DB (drv, R,G,B regs, R,G,B values, status bit) ===")
for i in range(4):
    e = rd(0x080104DB + 8 * i, 8)
    print(" ", e.hex(" "))

print("\n=== LampArray (HID usage page 0x59) ===")
for lay, attr, tab, n in ((1, 0x0801198E, 0x080119BA, 0x3D), (2, 0x080119A4, 0x08011B65, 0x3E)):
    a = rd(attr, 22)
    cnt, w, h, dpt, kind, mui = struct.unpack("<HIIIII", a)
    print(f"layout {lay}: lamps={cnt} bbox={w}x{h}x{dpt} um kind={kind} min_update={mui} us")
    for i in range(n):
        lid, x, y, usage, k = struct.unpack("<BHHBB", rd(tab + 7 * i, 7))
        print(f"   lamp {lid:2d} key {kn(k):>6s} usage 0x{usage:02X} x={x*10:6d}um y={y*10:6d}um")

print("\n=== Boot-time special combo @0x08011986 (row bitmaps, active low) ===")
print("  ", rd(0x08011986, 8).hex(" "))

print("\n=== USB config descriptor @0x08010310 ===")
cfg = rd(0x08010310, 0x6D)
i = 0
while i < len(cfg):
    ln, typ = cfg[i], cfg[i + 1]
    print("  ", cfg[i:i + ln].hex(" "))
    i += ln
print("HID report descriptors (ptr,len) @0x080102F0:")
for j in range(4):
    p, ln = struct.unpack("<II", rd(0x080102F0 + 8 * j, 8))
    print(f"  if{j}: 0x{p:08X} len {ln}")
    rdsc = rd(p, ln)
    print("    " + rdsc.hex(" "))
