"""Razer Huntsman Mini (1532:0257) HID tool: app-mode queries and Razer bootloader (1532:110E) flashing.

Protocol: huntsman-mini/docs/razer_bootloader_protocol.md. Windows only (uses hid.dll to pick the HID
collection with 91-byte feature reports, exactly like Razer's updater).

Subcommands, from harmless to destructive:
  list                     show matching HID collections (no device I/O)
  info                     app mode: read firmware version and serial (read-only)          [tested]
  enter-bl                 app mode: reboot into the Razer bootloader                       [tested]
  bl-info                  bootloader: identify command, prints the raw response            [tested]
  exit                     bootloader: leave the bootloader and run the application
  flash HEX --i-understand bootloader: erase + write (vector table last) + verify, then exit [UNTESTED]
  read OUT --i-want-to-brick-it
                           bootloader: read flash. DO NOT USE: on a Huntsman Mini this command made the
                           Razer bootloader erase its own vector table; the board no longer booted at all
                           and had to be recovered over SWD. Kept only to document what happened.

Close Razer Synapse and stop the Razer services first: they use the same feature-report channel.
"""
import argparse
import ctypes
import ctypes.wintypes as wt
import sys
import time
from pathlib import Path

import hid
from intelhex import IntelHex

RAZER_VID = 0x1532
APP_PID = 0x0257
BL_PID = 0x110E
REPORT_LEN = 90  # Razer report, without the HID report ID byte

APP_START = 0x08004000  # everything below is the Razer bootloader: never erased or written
FLASH_END = 0x08040000  # STM32L151xC: 256 KB
CHUNK = 64  # bytes per write/read, same as the updater

STATUS = {0x00: "new", 0x01: "busy", 0x02: "ok", 0x03: "fail", 0x04: "timeout", 0x05: "not supported"}


# --- picking the right HID collection (FeatureReportByteLength == 91) --------------------------------

class HIDP_CAPS(ctypes.Structure):
    _fields_ = [
        ("Usage", wt.USHORT), ("UsagePage", wt.USHORT),
        ("InputReportByteLength", wt.USHORT), ("OutputReportByteLength", wt.USHORT),
        ("FeatureReportByteLength", wt.USHORT), ("Reserved", wt.USHORT * 17),
        ("NumberLinkCollectionNodes", wt.USHORT),
        ("NumberInputButtonCaps", wt.USHORT), ("NumberInputValueCaps", wt.USHORT),
        ("NumberInputDataIndices", wt.USHORT),
        ("NumberOutputButtonCaps", wt.USHORT), ("NumberOutputValueCaps", wt.USHORT),
        ("NumberOutputDataIndices", wt.USHORT),
        ("NumberFeatureButtonCaps", wt.USHORT), ("NumberFeatureValueCaps", wt.USHORT),
        ("NumberFeatureDataIndices", wt.USHORT),
    ]


def feature_len(path: bytes) -> int:
    """FeatureReportByteLength of a HID collection, opened with zero access (no I/O to the device)."""
    k32 = ctypes.WinDLL("kernel32", use_last_error=True)
    hiddll = ctypes.WinDLL("hid")
    k32.CreateFileW.restype = wt.HANDLE
    h = k32.CreateFileW(path.decode(), 0, 3, None, 3, 0, None)  # share r/w, OPEN_EXISTING
    if h in (None, wt.HANDLE(-1).value):
        return -1
    try:
        pp = ctypes.c_void_p()
        if not hiddll.HidD_GetPreparsedData(wt.HANDLE(h), ctypes.byref(pp)):
            return -1
        caps = HIDP_CAPS()
        ok = hiddll.HidP_GetCaps(pp, ctypes.byref(caps)) == 0x00110000
        hiddll.HidD_FreePreparsedData(pp)
        return caps.FeatureReportByteLength if ok else -1
    finally:
        k32.CloseHandle(wt.HANDLE(h))


def find(pid):
    return [d for d in hid.enumerate(RAZER_VID, pid) if feature_len(d["path"]) == REPORT_LEN + 1]


def open_dev(pid, wait=0.0):
    deadline = time.monotonic() + wait
    while True:
        devs = find(pid)
        if devs:
            break
        if time.monotonic() >= deadline:
            sys.exit(f"no 1532:{pid:04X} collection with 91-byte feature reports found")
        time.sleep(0.25)
    if len(devs) > 1:
        print(f"note: {len(devs)} candidate collections, using the first")
    d = hid.device()
    d.open_path(devs[0]["path"])
    return d


# --- Razer report framing --------------------------------------------------------------------------

def build(cls, cmd, size, args=b"", txid=0x00):
    r = bytearray(REPORT_LEN)
    r[1] = txid
    r[5] = size
    r[6] = cls
    r[7] = cmd
    r[8:8 + len(args)] = args
    crc = 0
    for b in r[2:88]:
        crc ^= b
    r[88] = crc
    return r


def transact(dev, cls, cmd, size, args=b"", txid=0x00, timeout=1.0, poll=0.002, echo=0):
    """Send one command and wait for its response. `echo` = number of leading arg bytes the response must
    repeat, so a stale response from the previous identical command isn't mistaken for this one."""
    req = build(cls, cmd, size, args, txid)
    if dev.send_feature_report(bytes([0x00]) + bytes(req)) < 0:
        raise IOError(f"send failed for {cls:02X}/{cmd:02X}")
    deadline = time.monotonic() + timeout
    last = None
    errors = 0
    while time.monotonic() < deadline:
        time.sleep(poll)
        try:
            raw = bytes(dev.get_feature_report(0x00, REPORT_LEN + 1))
        except OSError:
            errors += 1  # the updater also just keeps polling when HidD_GetFeature fails
            continue
        resp = raw[1:] if len(raw) == REPORT_LEN + 1 else raw
        if len(resp) < REPORT_LEN or resp[1] != txid or resp[6] != cls or resp[7] != cmd:
            continue
        last = resp
        if resp[0] in (0x00, 0x01):
            continue
        if echo and resp[8:8 + echo] != req[8:8 + echo]:
            continue
        if resp[0] != 0x02:
            raise IOError(f"{cls:02X}/{cmd:02X} returned status {resp[0]:02X} ({STATUS.get(resp[0], '?')})")
        return resp
    state = f"last status {last[0]:02X}, args {bytes(last[8:16]).hex(' ')}" if last else "no matching response"
    raise TimeoutError(f"{cls:02X}/{cmd:02X} timed out ({state}, {errors} get errors)")


def be32(v):
    return v.to_bytes(4, "big")


# --- bootloader operations ------------------------------------------------------------------------

def check_app_range(start, end):
    if not (APP_START <= start < end <= FLASH_END):
        sys.exit(f"refusing range 0x{start:08X}-0x{end:08X}: must stay within 0x{APP_START:08X}-0x{FLASH_END:08X}")


def bl_read(dev, addr, n):
    resp = transact(dev, 0x10, 0x83, 5, bytes([n]) + be32(addr), echo=5)
    return resp[13:13 + n]


def bl_write(dev, addr, data):
    check_app_range(addr, addr + len(data))
    transact(dev, 0x10, 0x02, 8, bytes([len(data)]) + be32(addr) + data, timeout=2.0)


def bl_erase(dev, start, end):
    check_app_range(start, end)
    transact(dev, 0x10, 0x01, 8, be32(start) + be32(end), timeout=15.0, poll=0.01)


def load_hex(path):
    ih = IntelHex(str(path))
    start, end = ih.minaddr(), ih.maxaddr() + 1
    check_app_range(start, end)
    ih.padding = 0xFF  # same fill as the updater's DataDefault()
    return start, ih.tobinstr(start=start, end=end - 1)


# --- subcommands ----------------------------------------------------------------------------------

def cmd_list(a):
    for pid, name in ((APP_PID, "app"), (BL_PID, "bootloader")):
        for d in hid.enumerate(RAZER_VID, pid):
            fl = feature_len(d["path"])
            mark = "  <- 91-byte feature reports" if fl == REPORT_LEN + 1 else ""
            print(f"{name:10s} 1532:{pid:04X} if={d['interface_number']} usage={d['usage_page']:04X}:{d['usage']:04X} "
                  f"feature_len={fl}{mark}")


def cmd_info(a):
    dev = open_dev(APP_PID)
    v = transact(dev, 0x00, 0x81, 0x02, txid=a.txid, timeout=1.0, poll=0.02)
    print(f"firmware version: v{v[8]}.{v[9]:02d}")
    s = transact(dev, 0x00, 0x82, 0x16, txid=a.txid, timeout=1.0, poll=0.02)
    print(f"serial: {bytes(s[8:30]).split(b'\0')[0].decode(errors='replace')}")
    dev.close()


def cmd_enter_bl(a):
    dev = open_dev(APP_PID)
    try:
        transact(dev, 0x00, 0x04, 0x02, bytes([0x01, 0x00]), txid=a.txid, timeout=0.5, poll=0.02)
    except (IOError, TimeoutError) as e:
        print(f"(no clean ack, expected if it reset immediately: {e})")
    dev.close()
    print("waiting for the bootloader (1532:110E)...")
    open_dev(BL_PID, wait=20.0).close()
    print("bootloader is up")


def cmd_bl_info(a):
    dev = open_dev(BL_PID)
    r = transact(dev, 0x10, 0x80, 9)
    print("response args:", r[8:8 + 16].hex(" "))
    dev.close()


def cmd_read(a):
    if not a.i_want_to_brick_it:
        sys.exit("refusing: 0x10/0x83 outside an erase/write session made the Razer bootloader erase itself "
                 "(see huntsman-mini/NOTES.md). Pass --i-want-to-brick-it only if you can recover over SWD.")
    dev = open_dev(BL_PID)
    out = bytearray()
    for addr in range(a.start, a.end, CHUNK):
        n = min(CHUNK, a.end - addr)
        out += bl_read(dev, addr, n)
        print(f"\rread 0x{addr + n:08X}", end="")
    print()
    Path(a.out).write_bytes(out)
    print(f"wrote {len(out)} bytes to {a.out}")
    dev.close()


def cmd_exit(a):
    dev = open_dev(BL_PID)
    try:
        transact(dev, 0x10, 0x05, 0x00, timeout=0.5)
    except (IOError, TimeoutError) as e:
        print(f"(no clean ack, expected if it jumped immediately: {e})")
    dev.close()


def cmd_flash(a):
    if not a.i_understand:
        sys.exit("flash erases the application; pass --i-understand to proceed")
    start, img = load_hex(a.hex)
    end = start + len(img)
    print(f"image 0x{start:08X}-0x{end:08X} ({len(img)} bytes)")
    chunks = [(start + off, img[off:off + CHUNK]) for off in range(0, len(img), CHUNK)]
    head, rest = chunks[0], chunks[1:]  # vector table goes last

    dev = open_dev(BL_PID)
    print("erasing...")
    bl_erase(dev, start, end)
    for i, (addr, data) in enumerate(rest, 1):
        bl_write(dev, addr, data)
        print(f"\rwrite {i}/{len(rest)}", end="")
    print()
    for i, (addr, data) in enumerate(rest, 1):
        got = bl_read(dev, addr, len(data))
        if got != data:
            sys.exit(f"verify failed at 0x{addr:08X}; vector table not written, device stays in the bootloader")
        print(f"\rverify {i}/{len(rest)}", end="")
    print()
    bl_write(dev, *head)
    if bl_read(dev, head[0], len(head[1])) != head[1]:
        sys.exit(f"verify failed at 0x{head[0]:08X} (vector table)")
    print("vector table written and verified")
    dev.close()
    if not a.no_exit:
        cmd_exit(a)
        print("exit sent; the keyboard should re-enumerate")


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--txid", type=lambda s: int(s, 0), default=0x00, help="transaction id for app-mode commands")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("list").set_defaults(fn=cmd_list)
    sub.add_parser("info").set_defaults(fn=cmd_info)
    sub.add_parser("enter-bl").set_defaults(fn=cmd_enter_bl)
    sub.add_parser("bl-info").set_defaults(fn=cmd_bl_info)
    r = sub.add_parser("read")
    r.add_argument("out")
    r.add_argument("--start", type=lambda s: int(s, 0), default=APP_START)
    r.add_argument("--end", type=lambda s: int(s, 0), default=FLASH_END)
    r.add_argument("--i-want-to-brick-it", action="store_true")
    r.set_defaults(fn=cmd_read)
    sub.add_parser("exit").set_defaults(fn=cmd_exit)
    f = sub.add_parser("flash")
    f.add_argument("hex")
    f.add_argument("--i-understand", action="store_true")
    f.add_argument("--no-exit", action="store_true")
    f.set_defaults(fn=cmd_flash)
    a = p.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
