// Copyright 2026 almo7aya
// SPDX-License-Identifier: GPL-2.0-or-later
//
// Boot shim for the Razer Huntsman Mini (STM32L151RCT6), living where the Razer bootloader used to be
// (0x08000000-0x08003FFF). Firmware (QMK or Razer's stock app) sits at APP_ADDR = 0x08004000.
//
// At reset it starts the STM32 factory USB DFU bootloader (0483:DF11) when:
//   1. the Razer "enter bootloader" magic is set (0xAAAAAAAA at 0x20007FFC; Razer's firmware writes it for
//      its updater, e.g. tools/razer_bl.py enter-bl), or
//   2. Esc is held while plugging in (matrix row 1 = PB1, column 0 = PC6; optical switch), or
//   3. the firmware slot doesn't hold a plausible vector table (erased or half-written flash).
// Otherwise it starts the firmware. Any fault in here reboots into DFU.
//
// Runs on the reset clock (MSI ~2.1 MHz) and uses no RAM besides the stack.

#include <stdint.h>

#ifndef APP_ADDR
#    define APP_ADDR 0x08004000U
#endif
#define FLASH_END 0x08040000U
#define RAM_START 0x20000000U
#define RAM_END 0x20008000U
#define SYSTEM_MEMORY 0x1FF00000U
#define RAZER_MAGIC_ADDR 0x20007FFCU
#define RAZER_MAGIC 0xAAAAAAAAU

#define REG(a) (*(volatile uint32_t *)(a))
#define RCC_AHBENR REG(0x4002381CU)
#define RCC_APB2ENR REG(0x40023820U)
#define SYSCFG_MEMRMP REG(0x40010000U)
#define SCB_VTOR REG(0xE000ED08U)
#define SCB_AIRCR REG(0xE000ED0CU)

#define GPIOB 0x40020400U
#define GPIOC 0x40020800U
#define MODER(p) REG((p) + 0x00U)
#define PUPDR(p) REG((p) + 0x0CU)
#define IDR(p) REG((p) + 0x10U)
#define BSRR(p) REG((p) + 0x18U)

#define ROWS_B 0xFC03U // PB0 PB1 PB10-PB15
#define ESC_ROW_PIN 1U // PB1
#define ESC_COL_PIN 6U // PC6

extern uint32_t __stack_top;

// ~5 us per iteration at the 2.1 MHz reset clock (volatile loop)
static void delay(uint32_t n) {
    for (volatile uint32_t i = 0; i < n; i++) {
    }
}

static uint32_t mask2(uint32_t pins, uint32_t v) {
    uint32_t m = 0;
    for (uint32_t i = 0; i < 16; i++) {
        if (pins & (1U << i)) {
            m |= v << (i * 2U);
        }
    }
    return m;
}

static __attribute__((noreturn)) void jump(uint32_t sp, uint32_t pc) {
    __asm volatile("msr msp, %0\n\tbx %1" : : "r"(sp), "r"(pc));
    __builtin_unreachable();
}

static __attribute__((noreturn)) void enter_dfu(void) {
    // Map system memory at 0x00000000 like a BOOT0 boot, so the ROM's vector table is in effect
    RCC_APB2ENR |= 1U; // SYSCFGEN
    (void)RCC_APB2ENR;
    SYSCFG_MEMRMP = 1U;
    SCB_VTOR      = 0U;
    jump(REG(SYSTEM_MEMORY), REG(SYSTEM_MEMORY + 4U));
}

// Esc (row PB1, column PC6) held? Rows are driven LOW to power their IR emitters; the column is precharged
// HIGH, then read as an input with pull-up: LOW = light reaches the receiver = key pressed.
static int esc_held(void) {
    RCC_AHBENR |= 0x6U; // GPIOB, GPIOC
    (void)RCC_AHBENR;

    BSRR(GPIOB)  = ROWS_B; // all rows deselected (HIGH)
    MODER(GPIOB) = (MODER(GPIOB) & ~mask2(ROWS_B, 3U)) | mask2(ROWS_B, 1U);
    BSRR(GPIOB)  = (1U << ESC_ROW_PIN) << 16; // select Esc's row (LOW)

    int hits = 0;
    // Delays are generous: after a DFU "leave" this runs on the ROM's faster clock, not the 2.1 MHz reset clock.
    // A long sample window is harmless with the pull-up on (released keys stay HIGH).
    for (int s = 0; s < 3; s++) {
        delay(2000); // ~10 ms at 2.1 MHz: emitter settle / sample spacing
        BSRR(GPIOC)  = 1U << ESC_COL_PIN;
        MODER(GPIOC) = (MODER(GPIOC) & ~(3U << (ESC_COL_PIN * 2U))) | (1U << (ESC_COL_PIN * 2U));
        PUPDR(GPIOC) = (PUPDR(GPIOC) & ~(3U << (ESC_COL_PIN * 2U))) | (1U << (ESC_COL_PIN * 2U));
        MODER(GPIOC) &= ~(3U << (ESC_COL_PIN * 2U));
        delay(20); // ~100 us sample window at 2.1 MHz
        if (!(IDR(GPIOC) & (1U << ESC_COL_PIN))) {
            hits++;
        }
    }

    // Back to reset state
    MODER(GPIOB) &= ~mask2(ROWS_B, 3U);
    MODER(GPIOC) &= ~(3U << (ESC_COL_PIN * 2U));
    PUPDR(GPIOC) &= ~(3U << (ESC_COL_PIN * 2U));
    RCC_AHBENR &= ~0x6U;
    return hits == 3;
}

static __attribute__((noreturn)) void start_app(void) {
    const uint32_t sp = REG(APP_ADDR);
    const uint32_t pc = REG(APP_ADDR + 4U);
    const int      ok = (sp > RAM_START) && (sp <= RAM_END) && ((sp & 3U) == 0U) && (pc & 1U) && ((pc & ~1U) >= APP_ADDR + 8U) && ((pc & ~1U) < FLASH_END);
    if (!ok) {
        enter_dfu();
    }
    RCC_APB2ENR |= 1U;
    (void)RCC_APB2ENR;
    SYSCFG_MEMRMP = 0U; // main flash at 0x00000000 (the ROM's DFU "leave" can leave system memory mapped)
    SCB_VTOR      = APP_ADDR;
    jump(sp, pc);
}

void Reset_Handler(void) {
    if (REG(RAZER_MAGIC_ADDR) == RAZER_MAGIC) {
        REG(RAZER_MAGIC_ADDR) = 0U;
        enter_dfu();
    }
    if (esc_held()) {
        enter_dfu();
    }
    start_app();
}

// Any fault: set the magic and reset, so the next boot goes straight to DFU from a clean state
void Fault_Handler(void) {
    REG(RAZER_MAGIC_ADDR) = RAZER_MAGIC;
    SCB_AIRCR             = 0x05FA0004U;
    for (;;) {
    }
}

__attribute__((section(".vectors"), used)) const void *const vectors[16] = {
    &__stack_top, (void *)Reset_Handler, (void *)Fault_Handler, (void *)Fault_Handler, (void *)Fault_Handler, (void *)Fault_Handler, (void *)Fault_Handler, 0, 0, 0, 0, (void *)Fault_Handler, (void *)Fault_Handler, 0, (void *)Fault_Handler, (void *)Fault_Handler,
};
