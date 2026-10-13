// Copyright 2026 almo7aya
// SPDX-License-Identifier: GPL-2.0-or-later

#include "quantum.h"
#include "i2c_master.h"
#include "eeconfig.h"
#ifdef VIA_ENABLE
#    include "via.h"
#    include "raw_hid.h"
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

// Boot shim at 0x08000000 (see huntsman-mini/shim and ld/STM32L151xC_shim.ld): starts QMK at 0x08004000, or the
// factory USB DFU bootloader when Esc is held at plug-in, when Razer's stock firmware asks for its bootloader, or
// when the firmware slot is empty. Embedding it makes every QMK .bin a complete image to flash at 0x08000000.
__attribute__((section(".shim"), used)) static const uint8_t boot_shim[] = {
#include "shim_blob.h"
};

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

#ifdef VIA_ENABLE
// Enter the bootloader from the PC (tools/enter_bootloader.py): VIA's id_bootloader_jump (0x0B), which QMK
// no longer handles itself. Requires the signature "BOOT" in data[1..4] so stray traffic can't trigger it.
bool via_command_kb(uint8_t *data, uint8_t length) {
    if (data[0] != id_bootloader_jump) {
        return false;
    }
    if (length < 5 || data[1] != 'B' || data[2] != 'O' || data[3] != 'O' || data[4] != 'T') {
        data[0] = id_unhandled;
        raw_hid_send(data, length);
        return true;
    }
    raw_hid_send(data, length); // acknowledge before USB goes away
    wait_ms(100);
    bootloader_jump();
    return true;
}
#endif

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
