"""Generate keyboard.json and led_map.h for the Razer Huntsman Mini QMK port.

Single source of truth: KEYS (matrix position + physical position) and LEDS (IS31FL3733 channels, in the
stock firmware's LED order). Matrix and LED data come from the stock v1.12 firmware
(re/firmware/tables_v1_12.txt, qmk_snippets_v1_12.c).
"""
import json
from pathlib import Path

OUT = Path(__file__).parent / "keyboards" / "razer" / "huntsman_mini"

# name: (row, col) in the 8x8 matrix (rows PB0 PB1 PB10..PB15 drive, cols PC6..PC9 PA8 PA9 PA10 PA15 sense)
MATRIX = {
    "0": (0, 0), "RBRC": (0, 1), "BSPC": (0, 2), "MINS": (0, 3), "EQL": (0, 4), "P": (0, 5), "LBRC": (0, 6), "BSLS": (0, 7),
    "ESC": (1, 0), "W": (1, 1), "E": (1, 2), "R": (1, 3), "T": (1, 4), "Y": (1, 5), "U": (1, 6), "9": (1, 7),
    "1": (2, 0), "2": (2, 1), "3": (2, 2), "4": (2, 3), "5": (2, 4), "6": (2, 5), "7": (2, 6), "8": (2, 7),
    "TAB": (3, 0), "Q": (3, 1), "D": (3, 2), "F": (3, 3), "G": (3, 4), "H": (3, 5), "I": (3, 6), "O": (3, 7),
    "CAPS": (4, 0), "A": (4, 1), "S": (4, 2), "J": (4, 3), "K": (4, 4), "L": (4, 5), "SCLN": (4, 6), "QUOT": (4, 7),
    "C": (5, 0), "V": (5, 1), "RSFT": (5, 2), "ENT": (5, 3), "SLSH": (5, 4), "NUHS": (5, 5), "NUBS": (5, 6),
    "LSFT": (6, 0), "Z": (6, 1), "X": (6, 2), "B": (6, 3), "N": (6, 4), "M": (6, 5), "COMM": (6, 6), "DOT": (6, 7),
    "LCTL": (7, 0), "LGUI": (7, 1), "LALT": (7, 2), "SPC": (7, 3), "RALT": (7, 4), "FN": (7, 5), "APP": (7, 6), "RCTL": (7, 7),
}

# 60% ANSI physical layout: (name, x, y, w) in key units
ANSI = [
    [("ESC", 0, 1), ("1", 1, 1), ("2", 2, 1), ("3", 3, 1), ("4", 4, 1), ("5", 5, 1), ("6", 6, 1), ("7", 7, 1),
     ("8", 8, 1), ("9", 9, 1), ("0", 10, 1), ("MINS", 11, 1), ("EQL", 12, 1), ("BSPC", 13, 2)],
    [("TAB", 0, 1.5), ("Q", 1.5, 1), ("W", 2.5, 1), ("E", 3.5, 1), ("R", 4.5, 1), ("T", 5.5, 1), ("Y", 6.5, 1),
     ("U", 7.5, 1), ("I", 8.5, 1), ("O", 9.5, 1), ("P", 10.5, 1), ("LBRC", 11.5, 1), ("RBRC", 12.5, 1), ("BSLS", 13.5, 1.5)],
    [("CAPS", 0, 1.75), ("A", 1.75, 1), ("S", 2.75, 1), ("D", 3.75, 1), ("F", 4.75, 1), ("G", 5.75, 1), ("H", 6.75, 1),
     ("J", 7.75, 1), ("K", 8.75, 1), ("L", 9.75, 1), ("SCLN", 10.75, 1), ("QUOT", 11.75, 1), ("ENT", 12.75, 2.25)],
    [("LSFT", 0, 2.25), ("Z", 2.25, 1), ("X", 3.25, 1), ("C", 4.25, 1), ("V", 5.25, 1), ("B", 6.25, 1), ("N", 7.25, 1),
     ("M", 8.25, 1), ("COMM", 9.25, 1), ("DOT", 10.25, 1), ("SLSH", 11.25, 1), ("RSFT", 12.25, 2.75)],
    [("LCTL", 0, 1.25), ("LGUI", 1.25, 1.25), ("LALT", 2.5, 1.25), ("SPC", 3.75, 6.25), ("RALT", 10, 1.25),
     ("FN", 11.25, 1.25), ("APP", 12.5, 1.25), ("RCTL", 13.75, 1.25)],
]
# ISO-only keys present in the matrix and LED driver (not on the ANSI board), for LED positions only
ISO_EXTRA = {"NUHS": (12.75, 2, 1), "NUBS": (1.25, 3, 1)}

MODIFIERS = {"ESC", "BSPC", "TAB", "CAPS", "ENT", "LSFT", "RSFT", "LCTL", "LGUI", "LALT", "RALT", "FN", "APP", "RCTL"}

# Stock LED order with IS31FL3733 channels as (R, G, B) = (SWr_CSc, SWg_CSc, SWb_CSc)
def rgb(sw_r, sw_g, sw_b, cs):
    return (f"SW{sw_r}_CS{cs}", f"SW{sw_g}_CS{cs}", f"SW{sw_b}_CS{cs}")

LEDS = (
    [(k, rgb(5, 4, 6, cs)) for k, cs in zip(
        ["ESC", "1", "2", "3", "4", "5", "6", "7", "8", "9", "0", "MINS", "EQL"], range(1, 14))]
    + [("BSPC", rgb(5, 4, 6, 15))]
    + [(k, rgb(8, 7, 9, cs)) for k, cs in zip(
        ["TAB", "Q", "W", "E", "R", "T", "Y", "U", "I", "O", "P", "LBRC", "RBRC", "BSLS"], range(1, 15))]
    + [(k, rgb(11, 10, 12, cs)) for k, cs in zip(
        ["CAPS", "A", "S", "D", "F", "G", "H", "J", "K", "L", "SCLN", "QUOT"], range(1, 13))]
    + [("NUHS", rgb(8, 7, 9, 16)), ("ENT", rgb(11, 10, 12, 14)),
       ("LSFT", rgb(2, 1, 3, 1)), ("NUBS", rgb(2, 1, 3, 16))]
    + [(k, rgb(2, 1, 3, cs)) for k, cs in zip(
        ["Z", "X", "C", "V", "B", "N", "M", "COMM", "DOT", "SLSH", "RSFT", "LCTL", "LGUI", "LALT"], range(2, 16))]
    + [("SPC", rgb(5, 4, 6, 14)), ("RALT", rgb(11, 10, 12, 15)), ("FN", rgb(11, 10, 12, 16)),
       ("APP", rgb(11, 10, 12, 13)), ("RCTL", rgb(8, 7, 9, 15))]
)


def main():
    phys = {}
    layout = []
    for y, row in enumerate(ANSI):
        for name, x, w in row:
            phys[name] = (x, y, w)
            entry = {"label": name, "matrix": list(MATRIX[name]), "x": x, "y": y}
            if w != 1:
                entry["w"] = w
            layout.append(entry)
    phys.update(ISO_EXTRA)
    assert len(layout) == 61

    leds = []
    seen = set()
    for name, _ in LEDS:
        assert name not in seen, name
        seen.add(name)
        x, y, w = phys[name]
        cx, cy = x + w / 2, y + 0.5
        leds.append({
            "matrix": list(MATRIX[name]),
            "x": round(224 * (cx - 0.5) / 14),
            "y": round(64 * (cy - 0.5) / 4),
            "flags": 1 if name in MODIFIERS else 4,
        })
    assert len(leds) == 63 and seen == set(MATRIX), set(MATRIX) - seen

    kb = {
        "manufacturer": "Razer",
        "keyboard_name": "Huntsman Mini",
        "maintainer": "almo7aya",
        "processor": "cortex-m3",
        "bootloader": "custom",
        # VIA rejects QMK's placeholder VID 0xFEED; 0x1532 (Razer) would pull in Razer's filter drivers/Synapse.
        # 0x5248 ("RH") is an arbitrary ID for this personal build.
        "usb": {"vid": "0x5248", "pid": "0x0257", "device_version": "1.0.0", "polling_interval": 1},
        # Esc-at-plug-in is handled by the boot shim (works with QMK and stock). VIA force-enables QMK Bootmagic
        # anyway; keep it on Esc too, so it's only a fallback (it also clears the EEPROM).
        "bootmagic": {"matrix": list(MATRIX["ESC"])},
        "features": {
            "extrakey": True,
            "mousekey": True,
            "nkro": True,
            "rgb_matrix": True,
        },
        "matrix_size": {"rows": 8, "cols": 8},
        "matrix_pins": {"custom_lite": True},
        "debounce": 3,
        "rgb_matrix": {
            "driver": "is31fl3733",
            "max_brightness": 200,
            "sleep": True,
            "animations": {
                "breathing": True, "cycle_all": True, "cycle_left_right": True, "cycle_up_down": True,
                "rainbow_moving_chevron": True, "cycle_out_in": True, "cycle_spiral": True,
                "typing_heatmap": True, "solid_reactive_simple": True, "solid_reactive_multiwide": True,
                "solid_splash": True, "splash": True, "multisplash": True,
            },
            "default": {"animation": "cycle_left_right", "val": 128},
            "layout": leds,
        },
        "community_layouts": ["60_ansi"],
        "layouts": {"LAYOUT_60_ansi": {"layout": layout}},
    }
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "keyboard.json").write_text(json.dumps(kb, indent=4) + "\n")

    # VIA v3 definition (load in usevia.app -> Settings -> Show Design tab -> Design -> Load draft definition)
    keymap_rows = []
    for row in ANSI:
        kle = []
        for name, _x, w in row:
            if w != 1:
                kle.append({"w": w})
            r, c = MATRIX[name]
            kle.append(f"{r},{c}")
        keymap_rows.append(kle)
    via = {
        "name": "Razer Huntsman Mini (QMK)",
        "vendorId": kb["usb"]["vid"],
        "productId": kb["usb"]["pid"],
        "matrix": kb["matrix_size"],
        "keycodes": ["qmk_lighting"],
        "menus": ["qmk_rgb_matrix"],
        "layouts": {"keymap": keymap_rows},
    }
    via_path = Path(__file__).parent / "via" / "razer_huntsman_mini.json"
    via_path.parent.mkdir(exist_ok=True)
    via_path.write_text(json.dumps(via, indent=2) + "\n")
    print(f"wrote {via_path}")

    lines = ["// Generated by huntsman-mini/qmk/gen_keyboard.py - do not edit.",
             "// IS31FL3733 @ 0x50, {driver, R, G, B}, same order as keyboard.json rgb_matrix.layout", ""]
    for name, (r, g, b) in LEDS:
        lines.append(f"    {{0, {r}, {g}, {b}}}, /* {name} */")
    (OUT / "led_map.h").write_text("\n".join(lines) + "\n")
    print(f"wrote {OUT / 'keyboard.json'} ({len(layout)} keys, {len(leds)} LEDs) and led_map.h")


main()
