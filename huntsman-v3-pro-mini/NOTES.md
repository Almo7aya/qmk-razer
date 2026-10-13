# Razer Huntsman V3 Pro Mini (RZ03-0499, USB 1532:02B0) — QMK feasibility notes

Phase 1 (2026-10-13): static analysis of Razer's official updater only. Nothing was sent to the keyboard.

## Updater

`HuntsmanV3ProMini_02B0_FirmwareUpdater_v2.01.00_r1.exe` (Razer support a_id 13707, released 2026-01-27, Authenticode
"Razer USA Ltd." valid). Same `CustomerFWU2Point5` framework as the Huntsman Mini, extracted with
`tools/extract_razer_fw.ps1` (now handles single-device naming and the "Flash FW" sectors). Files are in
`stock/` (private repo only).

| Metadata | Value |
|---|---|
| PID / bcdDevice | `02B0` / 0x0101 |
| Razer bootloader | `1532:110E`, BLVER 2.0 (same family as the Mini's, so assume the same dangerous read command) |
| Main firmware | `DevFWLine*`: 8196 Intel HEX lines, v2.01.00, plaintext |
| Second firmware | `FlashFWType 6`, `FlashFWSector0..36` (36 × 1024 + 544 = 37,408 B), named `Talia_T1_60%_7203_App_FW_v2.1.0_E888780F.enc` |
| Second-chip updater | `Ry_Online_Update_Dll_ouput_v1.0.1.dll` (vendor "TaliaT1SeriesFirmwareUpdater"): `chipGoToBootFirmware`, `appUpdateFirmware`, HID feature reports, `encryption_en` |

## Main MCU: NXP LPC55xx (Cortex-M33), most likely LPC5528-class

Evidence (`tools/fingerprint_fw.py`, `tools/fw_literals.py`):

- MCUXpresso SDK 2.8.2 assert strings: `fsl_flexcomm.c`, `fsl_gint.c`, `fsl_pint.c`, `fsl_utick.c`, `fsl_ctimer.c`,
  `fsl_wwdt.c`, `fsl_spi_dma.c`, `fsl_i2c_dma.c`, ... (LPC54/LPC55 peripheral set).
- Peripherals used (LDR literals + MOVW/MOVT): SYSCON `0x40000000`, IOCON, GINT, INPUTMUX, WWDT, UTICK,
  **ANACTRL `0x40013000`, PMC `0x40020000`, FLASH controller `0x40034000`, USB HS PHY `0x40038000`** (LPC55-only),
  DMA0, FLEXCOMM1 `0x40087000`, FLEXCOMM3 `0x40089000`, GPIO, **USB1 HS device `0x40094000`**, USB RAM `0x40100000`.
- Vector table: 16 + 60 IRQs (LPC55 has 60).
- The app is linked to run **from SRAM** at `0x20000000` (128 KB image, SP `0x04008000` in SRAMX); presumably copied
  from internal flash by Razer's bootloader.
- USB IDs `1532:02B0` / bcdDevice `0x0101` are embedded (offset `0x2001FED6`), so the NXP chip is the USB device
  (high-speed USB with on-chip PHY = the 8 kHz polling).
- Profile names in the image: "Factory Default", "Analog WASD".

## Analog switch sensing: separate chip with encrypted firmware

The 37 KB "Talia ... 7203 App FW" is encrypted: entropy 6.07 bits/byte and the tail repeats one 16-byte block
(AES-ECB-like encryption of padding). It is updated through the keyboard via its own HID protocol. The NXP firmware
talks to it over FLEXCOMM SPI/I2C with DMA. Not decrypted, and not planned to be: a port would keep that chip on
Razer's firmware and talk to it the way Razer's NXP firmware does.

## QMK status

- **No LPC55 support** in QMK, QMK's ChibiOS, or ChibiOS-Contrib (closest: LPC11Uxx, Kinetis, i.MX RT). A port needs
  a new ChibiOS HAL port first: clocks/PMC, IOCON/GPIO (PAL), USB1 high-speed device (IP3511 HS), FLEXCOMM SPI/I2C,
  DMA, timers; the ARMv8-M core port exists in ChibiOS.
- Then the analog chip's protocol must be reverse-engineered from the NXP firmware. Whether QMK can do Rapid
  Trigger / adjustable actuation depends on what that chip reports (raw travel per key, or already-decided key states).
- Unknown until the case is open: SWD/debug pads, and LPC55 protection (CMPA/CFPA settings can disable debug and
  ISP, i.e. a permanent lock).
- Likely losses vs stock: 8 kHz polling (until USB HS works in ChibiOS), Razer's analog/gamepad modes.
