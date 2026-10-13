/*
 * STM32L151xC (Cat.3) memory setup: 256 KB flash, 32 KB RAM.
 *   0x08000000-0x08003FFF  boot shim (huntsman-mini/shim, embedded via shim_blob.h): starts the firmware below,
 *                          or the STM32 factory USB DFU bootloader (Esc held at plug-in / Razer magic / empty slot)
 *   0x08004000-0x0803FFFF  QMK. Razer's stock app is linked here too, so the shim can start either one.
 * The .bin built from this starts at 0x08000000 (shim + QMK), so it is always flashed at 0x08000000.
 * Adapted from ChibiOS os/common/startup/ARMCMx/compilers/GCC/ld/STM32L152xE.ld
 * (ChibiOS, Copyright (C) 2006..2018 Giovanni Di Sirio, Apache License 2.0).
 */
MEMORY
{
    shim   (rx) : org = 0x08000000, len = 16k
    flash0 (rx) : org = 0x08004000, len = 240k
    flash1 (rx) : org = 0x00000000, len = 0
    flash2 (rx) : org = 0x00000000, len = 0
    flash3 (rx) : org = 0x00000000, len = 0
    flash4 (rx) : org = 0x00000000, len = 0
    flash5 (rx) : org = 0x00000000, len = 0
    flash6 (rx) : org = 0x00000000, len = 0
    flash7 (rx) : org = 0x00000000, len = 0
    ram0   (wx) : org = 0x20000000, len = 32k
    ram1   (wx) : org = 0x00000000, len = 0
    ram2   (wx) : org = 0x00000000, len = 0
    ram3   (wx) : org = 0x00000000, len = 0
    ram4   (wx) : org = 0x00000000, len = 0
    ram5   (wx) : org = 0x00000000, len = 0
    ram6   (wx) : org = 0x00000000, len = 0
    ram7   (wx) : org = 0x00000000, len = 0
}

SECTIONS
{
    .shim : ALIGN(4)
    {
        KEEP(*(.shim))
    } > shim
}

REGION_ALIAS("VECTORS_FLASH", flash0);
REGION_ALIAS("VECTORS_FLASH_LMA", flash0);
REGION_ALIAS("XTORS_FLASH", flash0);
REGION_ALIAS("XTORS_FLASH_LMA", flash0);
REGION_ALIAS("TEXT_FLASH", flash0);
REGION_ALIAS("TEXT_FLASH_LMA", flash0);
REGION_ALIAS("RODATA_FLASH", flash0);
REGION_ALIAS("RODATA_FLASH_LMA", flash0);
REGION_ALIAS("VARIOUS_FLASH", flash0);
REGION_ALIAS("VARIOUS_FLASH_LMA", flash0);
REGION_ALIAS("RAM_INIT_FLASH_LMA", flash0);
REGION_ALIAS("MAIN_STACK_RAM", ram0);
REGION_ALIAS("PROCESS_STACK_RAM", ram0);
REGION_ALIAS("DATA_RAM", ram0);
REGION_ALIAS("DATA_RAM_LMA", flash0);
REGION_ALIAS("BSS_RAM", ram0);
REGION_ALIAS("HEAP_RAM", ram0);

INCLUDE rules.ld
