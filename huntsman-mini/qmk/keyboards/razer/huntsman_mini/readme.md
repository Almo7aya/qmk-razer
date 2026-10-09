# Razer Huntsman Mini

QMK port for the Razer Huntsman Mini (RZ03-0339), a 60% keyboard with Razer optical switches and per-key RGB.

* Keyboard Maintainer: almo7aya
* Hardware Supported: Razer Huntsman Mini, I/O board `651000043740_20200416_V1.1` (STM32L151RCT6, IS31FL3733)
* Hardware Availability: Razer (retail)

Make example for this keyboard (after setting up your build environment):

    make razer/huntsman_mini:default

## Bootloader

Enter the STM32 factory USB DFU bootloader (`0483:DF11`) in one of these ways:

* **Keycode in layout**: Press the key mapped to `QK_BOOT` (Fn + `\` in the default keymaps)
* **Bootmagic reset**: Hold down Esc while plugging in the keyboard (this also clears the EEPROM)

Then flash the `.bin` at `0x08000000` with QMK Toolbox or `dfu-util -a 0 -d 0483:df11 -s 0x08000000:leave -D <file>.bin`.

The stock Razer bootloader cannot be used. For a first install (or recovery) the firmware is written over SWD
through the unpopulated `J1` footprint (ARM 10-pin, 1.27 mm: pin 2 SWDIO, pin 4 SWCLK, pin 3 GND, pin 10 nRESET),
e.g. with a Raspberry Pi Pico running `debugprobe` and OpenOCD (`target/stm32l1.cfg`).

See [build environment setup](https://docs.qmk.fm/#/getting_started_build_tools) and the
[make instructions](https://docs.qmk.fm/#/getting_started_make_guide) for more information. Brand new to QMK?
Start with our [Complete Newbs Guide](https://docs.qmk.fm/#/newbs).
