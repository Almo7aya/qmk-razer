"""Label the J1 debug-footprint pads and the GND reference pad on the PCB photo."""
from collections import deque
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).parent
im = Image.open(HERE / "photo_2026-10-09_21-03-29.jpg").convert("RGB")

J1_BOX = (1585, 795, 1705, 965)  # original-resolution search window around J1
GND_PAD = (624, 797)             # GND test pad next to the "US" box


def is_copper(p):
    r, g, b = p
    return r > 150 and 70 < g < 170 and b < 110 and r - b > 90


def find_pads(box):
    x0, y0, x1, y1 = box
    px = im.load()
    seen = set()
    blobs = []
    for y in range(y0, y1):
        for x in range(x0, x1):
            if (x, y) in seen or not is_copper(px[x, y]):
                continue
            q = deque([(x, y)])
            seen.add((x, y))
            pts = []
            while q:
                cx, cy = q.popleft()
                pts.append((cx, cy))
                for nx, ny in ((cx + 1, cy), (cx - 1, cy), (cx, cy + 1), (cx, cy - 1)):
                    if x0 <= nx < x1 and y0 <= ny < y1 and (nx, ny) not in seen and is_copper(px[nx, ny]):
                        seen.add((nx, ny))
                        q.append((nx, ny))
            if len(pts) > 40:
                blobs.append((sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts), len(pts)))
    return blobs


pads = find_pads(J1_BOX)
print(f"found {len(pads)} copper blobs in J1 window")
for x, y, n in sorted(pads, key=lambda p: (p[0] > 1645, -p[1])):
    print(f"  ({x:.0f}, {y:.0f}) area={n}")

# Glare merges two right-column pads into one blob, so use the grid fitted to the clean blobs:
# left column (5 clean blobs) and the right column's top two + bottom (square, larger) pad.
left_xy = [(1637, 940), (1632, 911), (1628, 885), (1624, 858), (1618, 832)]   # L1 (bottom) .. L5 (top)
right_xy = [(1670, 938), (1666, 911), (1661, 884), (1655, 858), (1651, 830)]  # R1 (bottom, square) .. R5
# ARM 10-pin debug numbering, pin 1 = square pad (R1): odd pins up the right column, even pins up the left.
labels = {str(2 * i): (x, y, 0) for i, (x, y) in enumerate(left_xy, 1)}
labels.update({str(2 * i - 1): (x, y, 0) for i, (x, y) in enumerate(right_xy, 1)})
EXPECTED = {"1": "3.3V (VTref)", "2": "SWDIO", "3": "GND", "4": "SWCLK", "5": "GND",
            "6": "SWO", "7": "n/c", "8": "n/c", "9": "GND", "10": "nRESET"}

try:
    font = ImageFont.truetype("arialbd.ttf", 26)
    small = ImageFont.truetype("arialbd.ttf", 40)
except OSError:
    font = small = ImageFont.load_default()

# Zoomed view of J1, upscaled 4x, labels beside each pad.
zx0, zy0, zx1, zy1 = 1480, 760, 1800, 1000
S = 4
zoom = im.crop((zx0, zy0, zx1, zy1)).resize(((zx1 - zx0) * S, (zy1 - zy0) * S), Image.LANCZOS)
d = ImageDraw.Draw(zoom)
for k, (x, y, _) in labels.items():
    cx, cy = (x - zx0) * S, (y - zy0) * S
    d.ellipse((cx - 30, cy - 30, cx + 30, cy + 30), outline=(0, 255, 255), width=4)
    tx = cx - 110 if int(k) % 2 == 0 else cx + 40
    d.rectangle((tx - 4, cy - 18, tx + 52, cy + 18), fill=(0, 0, 0))
    d.text((tx, cy - 15), k, font=font, fill=(0, 255, 255))
d.text((20, 15), "J1 pin numbers (pin 1 = square pad)", font=font, fill=(255, 255, 0))
lx, ly = zoom.width - 330, 40
d.rectangle((lx - 10, ly - 10, zoom.width - 10, ly + 10 * 34 + 10), fill=(0, 0, 0))
d.text((lx, ly - 6), "expected (to verify):", font=font, fill=(255, 255, 0))
for i in range(1, 11):
    d.text((lx, ly + i * 32), f"{i:>2}  {EXPECTED[str(i)]}", font=font, fill=(0, 255, 255))
zoom.save(HERE / "J1_pads_labeled.png")

# Overview: where J1 and the GND reference pad are on the board.
ov = im.copy()
d = ImageDraw.Draw(ov)
d.rectangle(J1_BOX, outline=(0, 255, 255), width=8)
d.text((J1_BOX[0] - 10, J1_BOX[1] - 60), "J1", font=small, fill=(0, 255, 255))
gx, gy = GND_PAD
d.ellipse((gx - 30, gy - 30, gx + 30, gy + 30), outline=(255, 60, 60), width=8)
d.text((gx - 60, gy + 40), "GND (black probe)", font=small, fill=(255, 60, 60))
ov = ov.resize((ov.width // 2, ov.height // 2), Image.LANCZOS)
ov.save(HERE / "board_overview_labeled.png")
print("wrote J1_pads_labeled.png and board_overview_labeled.png")
