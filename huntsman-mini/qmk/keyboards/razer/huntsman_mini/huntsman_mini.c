// Copyright 2026 almo7aya
// SPDX-License-Identifier: GPL-2.0-or-later

#include "quantum.h"
#include "i2c_master.h"
#include "eeconfig.h"
#ifdef VIA_ENABLE
#    include "via.h"
#endif

// Data-EEPROM writes stall the CPU (~3 ms per word). A full (re)initialisation rewrites up to ~500 words,
// and when that ran in keyboard_init() (after USB is up) Windows' enumeration requests timed out.
// keyboard_pre_init_kb() runs before protocol_pre_init() starts USB, so do any EEPROM init here; the
// later checks in keyboard_init() then find valid data and do nothing.
void keyboard_pre_init_kb(void) {
    if (!eeconfig_is_enabled()) {
        eeconfig_init();
    }
#ifdef VIA_ENABLE
    via_init();
#endif
    keyboard_pre_init_user();
}

#ifdef RGB_MATRIX_ENABLE
const is31fl3733_led_t PROGMEM g_is31fl3733_leds[IS31FL3733_LED_COUNT] = {
#    include "led_map.h"
};
#endif

// Replaces QMK's weak i2c_init(): the stock firmware runs I2C1 (PB6/PB7) with the internal pull-ups on.
void i2c_init(void) {
    static bool is_initialised = false;
    if (!is_initialised) {
        is_initialised = true;

        // Release the bus briefly, as QMK's default implementation does
        palSetLineMode(I2C1_SCL_PIN, PAL_MODE_INPUT);
        palSetLineMode(I2C1_SDA_PIN, PAL_MODE_INPUT);
        chThdSleepMilliseconds(10);

        palSetLineMode(I2C1_SCL_PIN, PAL_MODE_ALTERNATE(I2C1_SCL_PAL_MODE) | PAL_STM32_OTYPE_OPENDRAIN | PAL_STM32_PUPDR_PULLUP | PAL_STM32_OSPEED_HIGHEST);
        palSetLineMode(I2C1_SDA_PIN, PAL_MODE_ALTERNATE(I2C1_SDA_PAL_MODE) | PAL_STM32_OTYPE_OPENDRAIN | PAL_STM32_PUPDR_PULLUP | PAL_STM32_OSPEED_HIGHEST);
    }
}

// Bootloader: the Razer bootloader is gone, so QK_BOOT / Bootmagic start the STM32 factory (system memory)
// bootloader, which provides USB DFU (0483:DF11) on this chip with its 12 MHz crystal (tested over SWD).
// bootloader_jump() leaves a marker at the end of RAM and resets; early_hardware_init_pre() then calls
// enter_bootloader_mode_if_requested() before any clock/GPIO setup (EARLY_INIT_PERFORM_BOOTLOADER_JUMP).
#define SYSTEM_MEMORY_ADDR 0x1FF00000U
#define BOOTLOADER_MAGIC 0xDEADBEEFU

extern uint32_t __ram0_end__;
#define BOOTLOADER_MARKER (*(volatile uint32_t *)((uintptr_t)&__ram0_end__ - 4U))

void bootloader_jump(void) {
    BOOTLOADER_MARKER = BOOTLOADER_MAGIC;
    NVIC_SystemReset();
}

void mcu_reset(void) {
    NVIC_SystemReset();
}

void enter_bootloader_mode_if_requested(void) {
    if (BOOTLOADER_MARKER != BOOTLOADER_MAGIC) {
        return;
    }
    BOOTLOADER_MARKER = 0;

    // Map system memory at 0x00000000, as a BOOT0 boot would, so the ROM's own vector table is in effect
    RCC->APB2ENR |= RCC_APB2ENR_SYSCFGEN;
    (void)RCC->APB2ENR;
    SYSCFG->MEMRMP = SYSCFG_MEMRMP_MEM_MODE_0;
    SCB->VTOR      = 0;

    // Hand over a reset-like core state. ChibiOS' crt0 starts with interrupts masked (cpsid i); the ROM
    // bootloader's USB is interrupt driven, so without re-enabling them it never answers the host.
    SysTick->CTRL = 0;
    SysTick->LOAD = 0;
    SysTick->VAL  = 0;
    for (uint32_t i = 0; i < ARRAY_SIZE(NVIC->ICER); i++) {
        NVIC->ICER[i] = 0xFFFFFFFFU;
        NVIC->ICPR[i] = 0xFFFFFFFFU;
    }
    __set_BASEPRI(0);
    __set_CONTROL(0);

    const uint32_t sp    = *(const volatile uint32_t *)SYSTEM_MEMORY_ADDR;
    const uint32_t entry = *(const volatile uint32_t *)(SYSTEM_MEMORY_ADDR + 4U);
    __set_MSP(sp);
    __enable_irq();
    ((void (*)(void))entry)();
    while (true) {
    }
}
