"""Build a flashable stock-firmware image for the Huntsman Mini with the boot shim in front.

Takes YOUR OWN SWD flash backup (huntsman-mini/dumps/*_flash_08000000_256K.bin, made before installing QMK)
and replaces its first 16 KB (the damaged Razer bootloader / vector stub) with the boot shim, so Razer's app at
0x08004000 boots and Esc-at-plug-in / Razer's "enter bootloader" command still reach the factory USB DFU
bootloader. The result contains Razer's firmware: keep it local, never publish it.

Usage: python tools/make_stock_image.py [backup.bin] [out.bin]
Flash with QMK Toolbox (DFU) or dfu-util at 0x08000000.
"""
import struct
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SHIM = REPO / "huntsman-mini/shim/build/shim.bin"
backup = Path(sys.argv[1]) if len(sys.argv) > 1 else REPO / "huntsman-mini/dumps/pre_qmk_flash_08000000_256K.bin"
out = Path(sys.argv[2]) if len(sys.argv) > 2 else REPO / "huntsman-mini/dumps/stock_with_shim.bin"

shim = SHIM.read_bytes()
img = bytearray(backup.read_bytes())
assert len(img) == 0x40000, f"expected a 256 KB flash backup, got {len(img)} bytes"
assert len(shim) <= 0x4000

sp, reset = struct.unpack_from("<II", img, 0x4000)
assert 0x20000000 < sp <= 0x20008000 and 0x08004000 < reset < 0x08040000, (
    f"no valid app vector table at 0x08004000 in the backup (SP=0x{sp:08X}, reset=0x{reset:08X})")

img[:0x4000] = shim + bytes(0x4000 - len(shim))

# Trim trailing erased (0x00) flash to the next 2 KB boundary to keep the DFU download short
end = len(img)
while end > 0x4000 and img[end - 1] == 0:
    end -= 1
end = (end + 0x7FF) & ~0x7FF
out.write_bytes(img[:end])
print(f"stock app SP=0x{sp:08X} reset=0x{reset:08X}; wrote {out} ({end} bytes)")
