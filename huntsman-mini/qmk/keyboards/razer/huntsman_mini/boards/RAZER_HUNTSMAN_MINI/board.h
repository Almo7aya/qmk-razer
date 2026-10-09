// Copyright 2026 almo7aya
// SPDX-License-Identifier: GPL-2.0-or-later
//
// Board: Razer Huntsman Mini I/O board 651000043740_20200416_V1.1, MCU STM32L151RCT6 (LQFP64), 12 MHz crystal.
// Pin usage comes from the stock firmware (see huntsman-mini/docs/stock_firmware_re.md).

#pragma once

#define BOARD_RAZER_HUNTSMAN_MINI
#define BOARD_NAME "Razer Huntsman Mini"

#define STM32_LSECLK 32768U
#define STM32_HSECLK 12000000U

#define STM32L151xC

/* Per-pin register field helpers. */
#define PIN_MODE_INPUT(n)     (0U << ((n) * 2U))
#define PIN_MODE_OUTPUT(n)    (1U << ((n) * 2U))
#define PIN_MODE_ALTERNATE(n) (2U << ((n) * 2U))
#define PIN_MODE_ANALOG(n)    (3U << ((n) * 2U))
#define PIN_ODR_LOW(n)        (0U << (n))
#define PIN_ODR_HIGH(n)       (1U << (n))
#define PIN_OSPEED_VERYLOW(n) (0U << ((n) * 2U))
#define PIN_OSPEED_HIGH(n)    (3U << ((n) * 2U))
#define PIN_PUPDR_FLOATING(n) (0U << ((n) * 2U))
#define PIN_PUPDR_PULLUP(n)   (1U << ((n) * 2U))
#define PIN_PUPDR_PULLDOWN(n) (2U << ((n) * 2U))

/* Unused ports/pins: input with pull-down. */
#define ALL_PULLDOWN 0xAAAAAAAAU

/*
 * GPIOA
 * PA0  layout strap (analog)      PA1  layout strap (pull-up)
 * PA8  PA9 PA10 PA15 matrix cols 4-7 (input pull-up, reconfigured by matrix.c)
 * PA11 PA12 USB (left as inputs, the USB peripheral takes over)
 * PA13 SWDIO, PA14 SWCLK (must stay AF0 or SWD is lost)
 */
#define VAL_GPIOA_MODER   (PIN_MODE_ANALOG(0) | PIN_MODE_ALTERNATE(13) | PIN_MODE_ALTERNATE(14))
#define VAL_GPIOA_OTYPER  0x00000000U
#define VAL_GPIOA_OSPEEDR (PIN_OSPEED_HIGH(8) | PIN_OSPEED_HIGH(9) | PIN_OSPEED_HIGH(10) | PIN_OSPEED_HIGH(13) | PIN_OSPEED_HIGH(14) | PIN_OSPEED_HIGH(15))
#define VAL_GPIOA_PUPDR   (PIN_PUPDR_FLOATING(0) | PIN_PUPDR_PULLUP(1) | PIN_PUPDR_PULLDOWN(2) | PIN_PUPDR_PULLDOWN(3) | \
                           PIN_PUPDR_PULLDOWN(4) | PIN_PUPDR_PULLDOWN(5) | PIN_PUPDR_PULLDOWN(6) | PIN_PUPDR_PULLDOWN(7) | \
                           PIN_PUPDR_PULLUP(8) | PIN_PUPDR_PULLUP(9) | PIN_PUPDR_PULLUP(10) | PIN_PUPDR_FLOATING(11) | \
                           PIN_PUPDR_FLOATING(12) | PIN_PUPDR_PULLUP(13) | PIN_PUPDR_PULLDOWN(14) | PIN_PUPDR_PULLUP(15))
#define VAL_GPIOA_ODR     0x00000000U
#define VAL_GPIOA_AFRL    0x00000000U
#define VAL_GPIOA_AFRH    0x00000000U

/*
 * GPIOB
 * PB0 PB1 PB10-PB15 matrix rows (push-pull, idle HIGH = deselected)
 * PB6 SCL, PB7 SDA (I2C1, configured by i2c_init)
 */
#define BOARD_ROWS_B(f) (f(0) | f(1) | f(10) | f(11) | f(12) | f(13) | f(14) | f(15))
#define VAL_GPIOB_MODER   BOARD_ROWS_B(PIN_MODE_OUTPUT)
#define VAL_GPIOB_OTYPER  0x00000000U
#define VAL_GPIOB_OSPEEDR BOARD_ROWS_B(PIN_OSPEED_HIGH)
#define VAL_GPIOB_PUPDR   (PIN_PUPDR_PULLDOWN(2) | PIN_PUPDR_PULLDOWN(3) | PIN_PUPDR_PULLDOWN(4) | PIN_PUPDR_PULLDOWN(5) | \
                           PIN_PUPDR_PULLUP(6) | PIN_PUPDR_PULLUP(7) | PIN_PUPDR_PULLDOWN(8) | PIN_PUPDR_PULLDOWN(9))
#define VAL_GPIOB_ODR     BOARD_ROWS_B(PIN_ODR_HIGH)
#define VAL_GPIOB_AFRL    0x00000000U
#define VAL_GPIOB_AFRH    0x00000000U

/*
 * GPIOC
 * PC0 strap (pull-up, unused)   PC6-PC9 matrix cols 0-3 (input pull-up)
 * PC13 IS31FL3733 SDB (output LOW = driver shut down until QMK enables it)
 */
#define VAL_GPIOC_MODER   PIN_MODE_OUTPUT(13)
#define VAL_GPIOC_OTYPER  0x00000000U
#define VAL_GPIOC_OSPEEDR (PIN_OSPEED_HIGH(6) | PIN_OSPEED_HIGH(7) | PIN_OSPEED_HIGH(8) | PIN_OSPEED_HIGH(9))
#define VAL_GPIOC_PUPDR   (PIN_PUPDR_PULLUP(0) | PIN_PUPDR_PULLDOWN(1) | PIN_PUPDR_PULLDOWN(2) | PIN_PUPDR_PULLDOWN(3) | \
                           PIN_PUPDR_PULLDOWN(4) | PIN_PUPDR_PULLDOWN(5) | PIN_PUPDR_PULLUP(6) | PIN_PUPDR_PULLUP(7) | \
                           PIN_PUPDR_PULLUP(8) | PIN_PUPDR_PULLUP(9) | PIN_PUPDR_PULLDOWN(10) | PIN_PUPDR_PULLDOWN(11) | \
                           PIN_PUPDR_PULLDOWN(12) | PIN_PUPDR_FLOATING(13) | PIN_PUPDR_PULLDOWN(14) | PIN_PUPDR_PULLDOWN(15))
#define VAL_GPIOC_ODR     PIN_ODR_LOW(13)
#define VAL_GPIOC_AFRL    0x00000000U
#define VAL_GPIOC_AFRH    0x00000000U

/* GPIOD-GPIOG: not bonded out on LQFP64 except PD2; all input pull-down. */
#define VAL_GPIOD_MODER   0x00000000U
#define VAL_GPIOD_OTYPER  0x00000000U
#define VAL_GPIOD_OSPEEDR 0x00000000U
#define VAL_GPIOD_PUPDR   ALL_PULLDOWN
#define VAL_GPIOD_ODR     0x00000000U
#define VAL_GPIOD_AFRL    0x00000000U
#define VAL_GPIOD_AFRH    0x00000000U

#define VAL_GPIOE_MODER   0x00000000U
#define VAL_GPIOE_OTYPER  0x00000000U
#define VAL_GPIOE_OSPEEDR 0x00000000U
#define VAL_GPIOE_PUPDR   ALL_PULLDOWN
#define VAL_GPIOE_ODR     0x00000000U
#define VAL_GPIOE_AFRL    0x00000000U
#define VAL_GPIOE_AFRH    0x00000000U

#define VAL_GPIOF_MODER   0x00000000U
#define VAL_GPIOF_OTYPER  0x00000000U
#define VAL_GPIOF_OSPEEDR 0x00000000U
#define VAL_GPIOF_PUPDR   ALL_PULLDOWN
#define VAL_GPIOF_ODR     0x00000000U
#define VAL_GPIOF_AFRL    0x00000000U
#define VAL_GPIOF_AFRH    0x00000000U

#define VAL_GPIOG_MODER   0x00000000U
#define VAL_GPIOG_OTYPER  0x00000000U
#define VAL_GPIOG_OSPEEDR 0x00000000U
#define VAL_GPIOG_PUPDR   ALL_PULLDOWN
#define VAL_GPIOG_ODR     0x00000000U
#define VAL_GPIOG_AFRL    0x00000000U
#define VAL_GPIOG_AFRH    0x00000000U

/* GPIOH: PH0/PH1 are the 12 MHz crystal (HSE takes them over). */
#define VAL_GPIOH_MODER   0x00000000U
#define VAL_GPIOH_OTYPER  0x00000000U
#define VAL_GPIOH_OSPEEDR 0x00000000U
#define VAL_GPIOH_PUPDR   0x00000000U
#define VAL_GPIOH_ODR     0x00000000U
#define VAL_GPIOH_AFRL    0x00000000U
#define VAL_GPIOH_AFRH    0x00000000U

#if !defined(_FROM_ASM_)
#    ifdef __cplusplus
extern "C" {
#    endif
void boardInit(void);
#    ifdef __cplusplus
}
#    endif
#endif
