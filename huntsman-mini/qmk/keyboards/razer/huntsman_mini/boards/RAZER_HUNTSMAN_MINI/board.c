// Copyright 2026 almo7aya
// SPDX-License-Identifier: GPL-2.0-or-later
//
// GPIO default setup + early clock init, adapted from ChibiOS os/hal/boards/ST_NUCLEO64_L152RE/board.c
// (ChibiOS, Copyright (C) 2006..2018 Giovanni Di Sirio, Apache License 2.0).

#include "hal.h"
#include "stm32_gpio.h"

typedef struct {
    uint32_t moder;
    uint32_t otyper;
    uint32_t ospeedr;
    uint32_t pupdr;
    uint32_t odr;
    uint32_t afrl;
    uint32_t afrh;
} gpio_setup_t;

#define GPIO_SETUP(p) {VAL_GPIO##p##_MODER, VAL_GPIO##p##_OTYPER, VAL_GPIO##p##_OSPEEDR, VAL_GPIO##p##_PUPDR, VAL_GPIO##p##_ODR, VAL_GPIO##p##_AFRL, VAL_GPIO##p##_AFRH}

static void gpio_init(stm32_gpio_t *gpiop, const gpio_setup_t *config) {
    gpiop->OTYPER  = config->otyper;
    gpiop->OSPEEDR = config->ospeedr;
    gpiop->PUPDR   = config->pupdr;
    gpiop->ODR     = config->odr;
    gpiop->AFRL    = config->afrl;
    gpiop->AFRH    = config->afrh;
    gpiop->MODER   = config->moder;
}

static void stm32_gpio_init(void) {
    rccResetAHB(STM32_GPIO_EN_MASK);
    rccEnableAHB(STM32_GPIO_EN_MASK, true);

    static const gpio_setup_t pa = GPIO_SETUP(A);
    static const gpio_setup_t pb = GPIO_SETUP(B);
    static const gpio_setup_t pc = GPIO_SETUP(C);
    gpio_init(GPIOA, &pa);
    gpio_init(GPIOB, &pb);
    gpio_init(GPIOC, &pc);
#if STM32_HAS_GPIOD
    static const gpio_setup_t pd = GPIO_SETUP(D);
    gpio_init(GPIOD, &pd);
#endif
#if STM32_HAS_GPIOE
    static const gpio_setup_t pe = GPIO_SETUP(E);
    gpio_init(GPIOE, &pe);
#endif
#if STM32_HAS_GPIOF
    static const gpio_setup_t pf = GPIO_SETUP(F);
    gpio_init(GPIOF, &pf);
#endif
#if STM32_HAS_GPIOG
    static const gpio_setup_t pg = GPIO_SETUP(G);
    gpio_init(GPIOG, &pg);
#endif
#if STM32_HAS_GPIOH
    static const gpio_setup_t ph = GPIO_SETUP(H);
    gpio_init(GPIOH, &ph);
#endif
}

void __early_init(void) {
    stm32_gpio_init();
    stm32_clock_init();

    // ChibiOS enables flash prefetch (ACR = ACC64 | PRFTEN | 1WS). With prefetch on, the first fetch after
    // waking from WFI returned garbage on this chip (INVSTATE hard fault on the TIM5 tick vector).
    // The stock firmware runs with ACC64 | 1WS and prefetch off, so do the same.
    FLASH->ACR &= ~FLASH_ACR_PRFTEN;
}

void boardInit(void) {}
