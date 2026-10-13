"""Switch a Razer Huntsman Mini into the STM32 factory USB DFU bootloader (0483:DF11) from the PC.

Works with either firmware, as long as the boot shim (huntsman-mini/shim) is installed:
  QMK  (5248:0257): VIA raw-HID command 0x0B with signature "BOOT" (handled in huntsman_mini.c)
  stock (1532:0257): Razer's "enter bootloader" command (class 0x00, id 0x04, mode 1); the stock firmware sets
                     the 0xAAAAAAAA magic and resets, and the shim starts DFU instead of the old Razer bootloader.
Only these two IDs are ever opened. Close Razer Synapse first when the stock firmware is running.

Usage: python tools/enter_bootloader.py
Then flash with QMK Toolbox or dfu-util at 0x08000000.
"""
import subprocess
import sys
import time
from pathlib import Path

import hid

sys.path.insert(0, str(Path(__file__).resolve().parent))
import razer_bl  # noqa: E402  (Razer HID framing)

QMK_VID, QMK_PID = 0x5248, 0x0257
RAZER_VID, RAZER_PID = 0x1532, 0x0257  # Huntsman Mini only (never the V3 Pro Mini, 1532:02B0)
VIA_USAGE_PAGE, VIA_USAGE = 0xFF60, 0x61
VIA_BOOTLOADER_JUMP = 0x0B


def dfu_present():
    out = subprocess.run(
        ["powershell", "-NoProfile", "-Command",
         "Get-PnpDevice -PresentOnly | Where-Object { $_.InstanceId -match '^USB\\\\VID_0483&PID_DF11\\\\' } | "
         "Select-Object -ExpandProperty Status"],
        capture_output=True, text=True).stdout
    return "OK" in out


def wait_dfu(timeout=15.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if dfu_present():
            return True
        time.sleep(0.5)
    return False


def via_jump():
    devs = [d for d in hid.enumerate(QMK_VID, QMK_PID) if d["usage_page"] == VIA_USAGE_PAGE and d["usage"] == VIA_USAGE]
    if not devs:
        return False
    dev = hid.device()
    dev.open_path(devs[0]["path"])
    report = bytearray(32)
    report[0] = VIA_BOOTLOADER_JUMP
    report[1:5] = b"BOOT"
    dev.write(bytes([0x00]) + bytes(report))
    reply = dev.read(32, 500)
    dev.close()
    if reply and reply[0] == 0xFF:
        sys.exit("QMK answered 'unhandled': this build has no PC bootloader command (press Fn + Backslash instead)")
    print("QMK: bootloader command sent")
    return True


def razer_jump():
    if not razer_bl.find(RAZER_PID):
        return False
    dev = razer_bl.open_dev(RAZER_PID)
    try:
        razer_bl.transact(dev, 0x00, 0x04, 0x02, bytes([0x01, 0x00]), timeout=0.5, poll=0.02)
    except (IOError, TimeoutError):
        pass  # the keyboard resets before acknowledging
    dev.close()
    print("stock firmware: Razer 'enter bootloader' command sent")
    return True


def main():
    if dfu_present():
        print("already in the bootloader (0483:DF11)")
        return
    if not (via_jump() or razer_jump()):
        sys.exit("no Huntsman Mini found (QMK 5248:0257 or stock 1532:0257)")
    if wait_dfu():
        print("in the bootloader: STM32 BOOTLOADER (0483:DF11)")
    else:
        sys.exit("the bootloader did not appear (is the boot shim installed?)")


if __name__ == "__main__":
    main()
