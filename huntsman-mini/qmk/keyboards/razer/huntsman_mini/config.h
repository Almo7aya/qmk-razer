// Copyright 2026 almo7aya
// SPDX-License-Identifier: GPL-2.0-or-later

#pragma once

/* Don't sleep the core (WFI) in the ChibiOS idle thread: waking from WFI is where the bad instruction fetch
 * happened with flash prefetch on (see board.c). Costs a little power, irrelevant for a USB keyboard. */
#define CORTEX_ENABLE_WFI_IDLE FALSE

/* STM32L1 has the I2Cv1 peripheral (QMK only selects this automatically for preset MCUs). */
#define USE_I2CV1
#define I2C_DRIVER I2CD1
#define I2C1_SCL_PIN B6
#define I2C1_SDA_PIN B7
#define I2C1_SCL_PAL_MODE 4
#define I2C1_SDA_PAL_MODE 4
#define I2C1_CLOCK_SPEED 400000
#define I2C1_DUTY_CYCLE FAST_DUTY_CYCLE_2

/* IS31FL3733 per-key RGB driver, configured like the stock firmware. */
#define IS31FL3733_I2C_ADDRESS_1 IS31FL3733_I2C_ADDRESS_GND_GND
#define IS31FL3733_SDB_PIN C13
#define IS31FL3733_SW_PULLUP IS31FL3733_PUR_32K_OHM
#define IS31FL3733_CS_PULLDOWN IS31FL3733_PDR_32K_OHM
#define IS31FL3733_GLOBAL_CURRENT 0xFF

/* Data EEPROM (0x08080000, 8 KB on STM32L151xC), custom driver in eeprom_l1.c.
 * 2 KB leaves room for VIA's 4 dynamic layers (512 B) plus macros. */
#define EEPROM_SIZE 2048

/* Start the STM32 factory USB DFU bootloader on QK_BOOT / Bootmagic (see huntsman_mini.c). */
#define EARLY_INIT_PERFORM_BOOTLOADER_JUMP TRUE

/* Optical switch matrix timing (stock firmware: ~125 us row settle, ~12 us column sample window). */
#define OPTICAL_ROW_SETTLE_US 125
#define OPTICAL_COL_SAMPLE_US 12
