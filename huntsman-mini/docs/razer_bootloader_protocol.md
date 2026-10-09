# Razer Huntsman Mini (1532:0257): USB bootloader protocol

Static analysis of the official updater `HuntsmanMini_FWUpdater_v1.12.00.exe` (`CustomerFWU2Point5.exe`, a .NET
front-end, plus `FWUpdaterDLL.dll`, a native x86 back-end) and of the stock application firmware.
Decompiled sources: `../re/updater/CustomerFWU2Point5/` (ilspycmd) and `../re/updater/FWUpdaterDLL_decompiled.c` (Ghidra).
Nothing here has been exercised on hardware yet.

Tags: **[confirmed]** read directly from code · **[inferred]** strong deduction · **[unknown]** needs the bootloader binary or hardware.

## 1. Summary

| Item | Value | Source |
|---|---|---|
| App-mode USB ID | `1532:0257` | resources `VID1/PID1` [confirmed] |
| Bootloader USB ID | `1532:110E`, **HID** (no driver needed), opened with bcdDevice filter `0x0257` | resources `BLVID1/BLPID1/BCDPID_BL1`, `BLVER1=2.0` [confirmed] |
| `1532:110D` + `rzrbtldr.inf` (WinUSB) | Not used by this device. Only for bootloader versions 1.0/1.1/3.0 | `appContextDevice`, `FormFWUStep1` branches on `GetBLVer()` [confirmed] |
| Transport | HID feature reports, `HidD_SetFeature` / `HidD_GetFeature`, report ID `0x00`, 91-byte buffer (ID + 90-byte Razer report) | DLL `FUN_10002630` [confirmed] |
| Which HID collection | The one whose `FeatureReportByteLength == 91`. In app mode that is interface 2 (`MI_02`) | DLL `FUN_10003020`/`FUN_10002840` [confirmed]; interface from stock FW report descriptor [confirmed in FW, not checked on HW] |
| Checksum | `report[88] = XOR(report[2..87])` | DLL `FUN_100025d0` [confirmed] |
| Transaction ID | `0x00` for every command | [confirmed] |
| Enter bootloader (app) | class `0x00`, cmd `0x04` (set device mode), size 2, args `01 00` | DLL `EnterDeviceMode(h, 1)` [confirmed] |
| App side of that | `cpsid i`; `*(u32*)0x20007FFC = 0xAAAAAAAA`; `dsb`; `NVIC_SystemReset()` | stock FW `0x0800935C` [confirmed] |
| BL identify | class `0x10`, cmd `0x80`, size 9 | `GetDevPIDInBootloader` [confirmed request; response layout unknown] |
| BL erase | class `0x10`, cmd `0x01`, size 8, args `start:BE32, end:BE32` (end = last address + 1) | `DFUErase` [confirmed] |
| BL write | class `0x10`, cmd `0x02`, size byte 8, args `len:u8, addr:BE32, data[len]`; updater uses `len = 64` | `DFUProgram` [confirmed] |
| BL read | class `0x10`, cmd `0x83`, size 5, args `len:u8, addr:BE32` → response `args[5..5+len)` = data. **Bricks the bootloader if sent outside an update (§5)** | `DFUVerify` [confirmed] |
| BL exit / run app | class `0x10`, cmd `0x05`, size 0 | `DFUExit` [confirmed] |
| Range written by updater | first..last data address of the HEX: `0x08004000`..`0x08011FBC` (57,276 bytes) | `backgroundWorkerProcessFWData` [confirmed] |
| Signature / encryption / CRC | **None.** HEX is plaintext, no checksum command, verification is a byte-for-byte read-back | [confirmed for the updater; whether the bootloader checks anything is unknown] |

## 2. Razer 90-byte report

The DLL builds a 91-byte buffer: `buf[0]` = HID report ID `0x00`, `buf[1..90]` = the Razer report below
(hidapi uses the same layout: first byte = report ID).

| Report offset | Field | Notes |
|---|---|---|
| 0 | status | `0x00` in requests. Responses: `0x00` new, `0x01` busy, `0x02` OK, `0x03` fail, `0x04` timeout, `0x05` not supported |
| 1 | transaction ID | `0x00` |
| 2-3 | remaining packets (BE16) | `0x0000` |
| 4 | protocol type | `0x00` |
| 5 | data size | per command (not always the true arg length, e.g. write always says 8) |
| 6 | command class | |
| 7 | command ID | |
| 8-87 | arguments (80 bytes) | |
| 88 | CRC = XOR of report bytes 2..87 | |
| 89 | reserved | `0x00` |

### 2.1 Transaction routine (`FUN_10002630(handle, buf, n_get, delay_ms)`)

```
repeat up to 3 times:
    sleep(delay_ms)
    compute CRC; HidD_SetFeature(buf, 91)        # up to 3 attempts, sleep(delay_ms) between
    for i in 1..n_get:
        sleep(delay_ms)
        HidD_GetFeature(resp, 91)
        if resp.txid == buf.txid and resp.class == buf.class and resp.cmd == buf.cmd
           and resp.status not in (0x00 new, 0x01 busy):
            if resp.status == 0x02: copy resp into buf; return OK
            else: break                        # failure status -> resend
```

`delay_ms`: 200 for app-mode queries, 2 for every bootloader command on this device
(10 only for PIDs 007E/0C04/0F1D/0F20/0F21). `n_get` = 5 (1 for exit). The updater also retries a failed
write/read chunk up to `MAX_RETRY = 10` times with a 1 ms pause.

## 3. Sequence the updater performs for this device

1. Find `1532:0257`, open the collection with 91-byte feature reports.
2. `0x00/0x04` args `01 00` (enter bootloader). The device resets into the bootloader. The updater polls for
   `1532:110E` (timer: 20 s "enter success", 50 s overall).
3. Open `1532:110E` (bcdDevice `0x0257`, 91-byte feature reports).
4. Convert the HEX to a flat image (`FW.bin`, gaps filled with the default byte), `StartAddr` = first data
   address, `EndAddr` = last data address + 1.
5. Erase: `0x10/0x01 (StartAddr, EndAddr)`; expects status `0x02`.
6. Program: for each 64-byte chunk at `StartAddr + off`: `0x10/0x02 (len, addr, data)`.
7. Verify: for each 64-byte chunk: `0x10/0x83 (len, addr)` and compare `resp.args[5..]`.
8. Exit: `0x10/0x05`, then wait for `1532:0257` to come back.

If the updater starts while the device is already in the bootloader (e.g. after an interrupted update) it
skips step 2 and flashes directly, so an erased or broken app stays in the bootloader and the official
updater remains a recovery path. **[inferred]**: we don't have the bootloader binary, so the exact
"stay in bootloader" condition (magic word only, or also an invalid initial SP/reset vector) is unknown.

## 4. Implications for flashing QMK

- Link QMK at `0x08004000` (flash length 240 KB) and keep the Razer bootloader at `0x08000000` untouched.
- Implement QMK's `bootloader_jump()` exactly like the stock app: write `0xAAAAAAAA` to `0x20007FFC`, then
  `NVIC_SystemReset()`. Reserve that RAM word in the linker script (RAM length 32 KB - 4) so nothing else
  lives there.
- Our flasher should write the first 64-byte chunk (the vector table) **last**, after everything else is
  written and verified. If the flash is interrupted, the image then still has an erased vector table, which
  the bootloader is most likely to treat as "no valid app" **[inferred]**.
## 5. WARNING: do not send `0x10/0x83` (read) outside an update

Tested on hardware: app-mode `0x00/0x04` (enter bootloader) and bootloader `0x10/0x80` (identify) behave as
documented above. The **first `0x10/0x83` read** of `0x08004000`, sent without a preceding erase/write in that
session, made the bootloader drop off USB and **zero its own vector table** (page `0x08000000`) and the last
11 pages of its 16 KB region. The application and data EEPROM were untouched, but nothing boots any more
(the core locks up on reset) and no USB device appears. Most likely an anti-readout measure. Recovery needs SWD
(see `../NOTES.md`). The official updater only ever sends `0x10/0x83` after erasing and programming.
