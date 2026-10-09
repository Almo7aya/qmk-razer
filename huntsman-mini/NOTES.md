# Razer Huntsman Mini (RZ03-0339) — QMK port notes

## Device facts (from this PC)

| | |
|---|---|
| USB ID (app) | `1532:0257`, bcdDevice `0x0200` |
| USB ID (Razer bootloader) | `1532:110E` per updater metadata (`BLPID`), bootloader version `2.0`; the bundled WinUSB INF (`rzrbtldr.inf`) only lists `1532:110D` |
| Stock firmware | v1.12.00 (official updater), v1.32.00 for the Nordic-layout SKU |
| Razer control interface | HID feature report, 91 bytes incl. report ID (`FeatureReportLen=91`) — same 90-byte protocol OpenRazer documents |

## MCU: STM32L151xC (Cat. 3) — Cortex-M3, 256 KB flash, 32 KB RAM, 8 KB data EEPROM, USB FS device

Identified by static analysis of the stock firmware (`stock/firmware/*.hex`):

- App image is linked at `0x08004000` → STM32 flash at `0x08000000` with a **16 KB Razer bootloader** in front.
- Flash controller accesses hit `0x40023C04` (`FLASH_PECR`) and `0x40023C18` (`FLASH_SR`) and use the
  L1-only unlock keys `PEKEY 0x89ABCDEF/0x02030405` and `PRGKEY 0x8C9DAEBF/0x13141516`.
- Uses the L1 data EEPROM at `0x08080000`.
- USB is the FS device peripheral at `0x40005C00` (no OTG at `0x50000000`); dedicated handlers on IRQ 19/20/42
  = `USB_HP` / `USB_LP` / `USB_FS_WKUP` in the L1 vector table.
- Vector table has 57 IRQ slots with zero (reserved) entries exactly at LCD(24), SDIO(45), UART4/5(48/49), AES(55)
  — the `startup_stm32l151xc.s` layout.
- Initial SP `0x20006998` (fits 32 KB RAM).

Peripherals with dedicated IRQ handlers: EXTI1, EXTI2, DMA1 Ch2/Ch3 (= SPI1 RX/TX on L1), TIM3, I2C1, I2C2, SPI1, USB.
I2C1+I2C2 are probably the RGB LED driver ICs (to be confirmed).

## QMK / ChibiOS support status

- QMK has **no `MCU = STM32L151` preset** in `platforms/chibios/mcu_selection.mk`, but a keyboard can define the MCU
  manually (`MCU_SERIES = STM32L1xx`, custom ld script, board files).
- QMK's ChibiOS fork has the **STM32L1xx HAL port** (`os/hal/ports/STM32/STM32L1xx`), `startup_stm32l1xx.mk`, and
  ld scripts for L151x6 / L152xB / L152xE (no L151xC — need a custom one, trivial).
- QMK already ships an L0/L1 data-EEPROM driver (`platforms/chibios/drivers/eeprom/eeprom_stm32_L0_L1.c`).

## Files

- `stock/HuntsmanMini_FWUpdater_v1.12.00.exe` — official updater (Authenticode: Razer USA Ltd., valid)
- `stock/updater_extracted/` — contents of the self-extracting zip (`CustomerFWU2Point5.exe` is .NET,
  `FWUpdaterDLL.dll` is native, firmware is in `DeviceUpdater.resources`)
- `stock/firmware/` — extracted Intel HEX + flat binaries (bin starts at `0x08004000`)
- `../tools/extract_razer_fw.ps1` — re-run the extraction on any Razer CustomerFWU updater

## QMK port status (2026-10-09)

Source: `qmk/keyboards/razer/huntsman_mini/` (generated parts from `qmk/gen_keyboard.py`), built remotely with
`tools/remote_build.ps1` (server, not this PC), flashed with `swd/flash_qmk.tcl`. VIA definition:
`qmk/via/razer_huntsman_mini.json`.

- First boot hard-faulted (INVSTATE) on the TIM5 tick vector right after the idle thread's WFI. Cause: ChibiOS
  enables flash prefetch (ACR = 0x7); the stock firmware runs with prefetch off (ACR = 0x5). Fix: clear PRFTEN in
  `__early_init` (board.c) and `CORTEX_ENABLE_WFI_IDLE FALSE` (config.h).
- EEPROM vs USB: data-EEPROM writes stall the CPU (~3 ms/word). A full settings rewrite (~500 words) during USB
  enumeration made Windows fail (code 10, or no device at all). Fixed by doing eeconfig/VIA init in
  `keyboard_pre_init_kb()`, which runs before USB starts, plus a custom EEPROM driver (`eeprom_l1.c`) that skips
  unchanged/blank words. Worst case (2 KB of junk) now enumerates OK after ~6 s; normal boot ~1.7 s.
- Bootloader: `QK_BOOT` (Fn+`\`) and Bootmagic (Esc held at plug-in) start the STM32 **factory USB DFU bootloader**
  (`0483:DF11`, system memory 0x1FF00000, works with the 12 MHz crystal). The jump remaps system memory to 0x0,
  resets VTOR, stops SysTick, clears NVIC and re-enables interrupts (ChibiOS crt0 runs with `cpsid i`; without
  `__enable_irq()` the ROM's USB never answers). Tested end to end via a RAM marker over SWD.
- **USB DFU flashing verified 2026-10-09** with QMK Toolbox (dfu-util 0.11, `-s 0x08000000:leave`): flash verified
  over SWD, QMK restarts by itself. The ROM's "leave" jumps to the app without a reset, so SYSCFG_MEMRMP stays at
  system memory until the next reset; harmless because ChibiOS sets VTOR to 0x08000000. The initial
  `dfuERROR / firmware is corrupt` status is normal for the ROM bootloader and is cleared by dfu-util.
- Recovery if a future build can't reach QK_BOOT/Bootmagic: SWD via J1 (`swd/flash_qmk.tcl`).
- Backups: `dumps/pre_qmk_*` = stock (with boot stub) right before the first QMK flash; `dumps/qmk_try1_*` = the
  crashing first QMK build.

## Razer bootloader (answered — details in `docs/razer_bootloader_protocol.md`)

- **Entry from the app:** stock FW (`0x0800935C`) does `cpsid i; *(u32*)0x20007FFC = 0xAAAAAAAA; NVIC_SystemReset()`,
  triggered by Razer command `0x00/0x04` args `01 00`. QMK's `bootloader_jump()` must do the same.
- **Protocol:** same 90-byte HID feature report as app mode (interface 2 in app mode — verified on this PC with
  `tools/razer_bl.py list`). Bootloader class `0x10`: `0x80` identify, `0x01` erase(start,end), `0x02` write 64 B,
  `0x83` read 64 B, `0x05` exit.
- **No signature/encryption/CRC** in the updater; verification is read-back. Image goes to `0x08004000+`.
- Note STM32L1 flash erases to `0x00`, not `0xFF`; the updater pads gaps with `0xFF` (written explicitly).

## INCIDENT 2026-10-09: board stopped booting after a bootloader read

Sequence: stage 0 `info` OK (FW v1.12) → `enter-bl` OK (`1532:110E`, bcdDevice `0x0257`) →
`bl-info` OK (args `07 33 00 00 00 00 00 02 57`) → first `read` (`0x10/0x83`, 64 B @ `0x08004000`, no prior
erase/write in that session) → `get_feature_report` failed and the bootloader dropped off USB.
After that, the board shows **no lights and no USB activity at all** on any host (Windows PnP log and Linux `lsusb`),
across several cables. Plug-in combos (Fn, Esc, Esc+Caps+Space, Fn+Esc) do nothing.

Takeaways:
- **Never send `0x10/0x83` (read) to this bootloader outside an erase → write → verify sequence.** The official updater
  only ever issues it after programming. The likely explanation is an anti-readout measure that wipes or locks the
  chip, but this is unconfirmed.
- Recovery needs SWD (Pi Pico as CMSIS-DAP probe, see `../swd/`). PA13/PA14 are never reconfigured by the stock app.

**Recovered 2026-10-09 via SWD.** Findings (`swd/probe_readonly.tcl`, logs in `logs/`):
- DEV_ID `0x427` (Cat.3), **RDP level 0** (`FLASH_OBR = 0x007800AA`), no WRP. SWD has full access.
- The bootloader read zeroed page 0 (vector table) and the last 11 pages of the 16 KB bootloader region; the CPU was
  locked up (PC = 0). App at `0x08004000` and data EEPROM were untouched. A second identical copy of the v1.12 app
  sits at `0x08013000`.
- Full backup (dumped twice, identical): `dumps/swd_flash_08000000_256K.bin`, `dumps/swd_eeprom_08080000_8K.bin`,
  `dumps/swd_optbytes_1FF80000.bin`.
- Fix: `swd/write_boot_stub.tcl` wrote the stock app's first 256 vector-table bytes to page 0
  (`recovery/boot_stub_vectors_256.bin`). The app sets VTOR = 0x08004000 itself. Board enumerates as `1532:0257` again.
  There is no working Razer bootloader any more: flash over SWD from now on.

## Hardware: I/O board `651000043740_20200416_V1.1` (photos in `photos/`)

- U1 = **STM32L151RCT6** (marking confirmed), Y1 = 12 MHz crystal, U2 = 3.3 V LDO, USB-C on the same board.
- **J1 = unpopulated ARM 10-pin (1.27 mm) SWD footprint**, pin 1 = square pad. Verified with a multimeter (board powered,
  bricked state): 1 = 3.30 V (VTref), 2 = 3.22 V (**SWDIO**, pull-up), 4 = 0.18 V (**SWCLK**, pull-down),
  10 = 3.29 V (**nRESET**), 3/5/9 = 0 V (GND), 6/7/8 = 0 V. Numbered picture: `photos/J1_pads_labeled.png`.
- Left-side pads go to the switch board flex: `R-0..R-7` rows, `S-C`/`S-1..S-7` sense columns, `SDA`/`SCL`
  (IS31FL3733), `RESET`/`INT` (LED driver SDB/INTB, presumably), `GND`, `3V3`.
- Probe wiring (Pico 2 W running `debugprobe_on_pico2.uf2`): J1-4 SWCLK → Pico GP2 (pin 4), J1-2 SWDIO → GP3 (pin 5),
  J1-3 GND → Pico GND (pin 3), J1-10 nRESET → GP1 (pin 2). J1-1 (3.3 V) left unconnected.

## Flashing plan (lowest risk first)

Prerequisite: quit Razer Synapse and stop the Razer services (they use the same HID channel).

| Stage | What | Flash writes | Recovery if it goes wrong |
|---|---|---|---|
| 0 | `razer_bl.py info` — read FW version/serial in app mode (validates our framing/CRC) | none | n/a |
| 1 | `enter-bl`, `bl-info`, `read` the app region, compare with v1.12.00, try reading `0x08000000` (bootloader backup), `exit` | none | unplug/replug; official updater |
| 2 | `flash` the **stock** v1.12.00 HEX with our tool (tests erase/write/verify + vector-table-last) | app only | official updater |
| 3 | `flash` a minimal QMK build with failsafes (see below) | app only | official updater, if the bootloader is reachable |

QMK failsafes for the first builds:
- `bootloader_jump()` = Razer magic + reset; reserve RAM word `0x20007FFC` in the linker script.
- In `early_hardware_init_pre()` (runs before ChibiOS clock init): keep a `.noinit` boot-attempt counter, start the
  IWDG, and after N consecutive boots that never reached "USB configured", write the magic and reset into the
  Razer bootloader. That covers hangs in clock/USB init and hard faults (IWDG resets).
- Bootmagic key at plug-in also jumps to the bootloader.

## Open questions

1. Key matrix: optical switch drive/sense pins and scan timing (stock firmware RE in progress).
2. RGB: LED driver chip(s), I2C addresses, LED index map (in progress).
3. Bootloader's own "stay in bootloader" condition (magic only, or also invalid vector table?) — stage 1 may let us
   dump the bootloader to answer this.
4. Readout protection level and SWD pad location (needs the case open).
