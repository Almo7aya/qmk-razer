// Copyright 2026 almo7aya
// SPDX-License-Identifier: GPL-2.0-or-later
//
// Optical switch matrix for the Razer Huntsman Mini, replicating the stock firmware's scan
// (matrix_scan_one_row_isr @ 0x0800B9FC in v1.12):
//   rows    PB0 PB1 PB10..PB15, push-pull, idle HIGH, LOW = row selected (powers that row's IR emitters)
//   columns PC6..PC9 PA8 PA9 PA10 PA15, kept as outputs driven HIGH between reads (precharge)
// Per row: select it and let the emitters settle, then switch the columns to inputs, with the pull-up
// enabled only on columns whose key is currently released (press/release hysteresis), wait a short
// sample window and read: LOW = pressed. Then deselect the row and precharge the columns again.

#include "quantum.h"
#include "matrix.h"
#include "atomic_util.h"

static const uint8_t row_pins[MATRIX_ROWS] = {0, 1, 10, 11, 12, 13, 14, 15}; // GPIOB

#define ROWS_B_MASK 0xFC03U // PB0 PB1 PB10-PB15
#define COLS_C_MASK 0x03C0U // PC6-PC9   -> cols 0-3
#define COLS_A_MASK 0x8700U // PA8-PA10  -> cols 4-6, PA15 -> col 7

// 2-bit-per-pin register masks (MODER/PUPDR/OSPEEDR) for a set of pins
static uint32_t field_mask(uint16_t pins, uint32_t value) {
    uint32_t m = 0;
    for (uint8_t i = 0; i < 16; i++) {
        if (pins & (1U << i)) {
            m |= value << (i * 2U);
        }
    }
    return m;
}

static uint32_t moder_c_mask, moder_a_mask, moder_c_out, moder_a_out;
static uint32_t pupd_col_bit[MATRIX_COLS]; // PUPDR pull-up bits for each column
static stm32_gpio_t *const col_port[MATRIX_COLS] = {GPIOC, GPIOC, GPIOC, GPIOC, GPIOA, GPIOA, GPIOA, GPIOA};
static const uint8_t col_pin[MATRIX_COLS] = {6, 7, 8, 9, 8, 9, 10, 15};

static inline matrix_row_t read_cols(void) {
    uint32_t c    = GPIOC->IDR;
    uint32_t a    = GPIOA->IDR;
    uint8_t  high = ((c >> 6) & 0x0FU) | (((a >> 8) & 0x07U) << 4) | (((a >> 15) & 0x01U) << 7);
    return (matrix_row_t)~high; // LOW = pressed
}

void matrix_init_custom(void) {
    moder_c_mask = field_mask(COLS_C_MASK, 3U);
    moder_a_mask = field_mask(COLS_A_MASK, 3U);
    moder_c_out  = field_mask(COLS_C_MASK, 1U);
    moder_a_out  = field_mask(COLS_A_MASK, 1U);
    for (uint8_t c = 0; c < MATRIX_COLS; c++) {
        pupd_col_bit[c] = 1U << (col_pin[c] * 2U);
    }

    ATOMIC_BLOCK_FORCEON {
        // Rows: push-pull outputs, deselected (HIGH)
        GPIOB->BSRR.W    = ROWS_B_MASK;
        GPIOB->OSPEEDR = (GPIOB->OSPEEDR & ~field_mask(ROWS_B_MASK, 3U)) | field_mask(ROWS_B_MASK, 3U);
        GPIOB->MODER   = (GPIOB->MODER & ~field_mask(ROWS_B_MASK, 3U)) | field_mask(ROWS_B_MASK, 1U);

        // Columns: ODR HIGH, very high speed, outputs (precharged)
        GPIOC->BSRR.W    = COLS_C_MASK;
        GPIOA->BSRR.W    = COLS_A_MASK;
        GPIOC->OSPEEDR |= moder_c_mask;
        GPIOA->OSPEEDR |= moder_a_mask;
        GPIOC->MODER   = (GPIOC->MODER & ~moder_c_mask) | moder_c_out;
        GPIOA->MODER   = (GPIOA->MODER & ~moder_a_mask) | moder_a_out;
    }
}

bool matrix_scan_custom(matrix_row_t current_matrix[]) {
    bool changed = false;

    for (uint8_t r = 0; r < MATRIX_ROWS; r++) {
        const uint32_t row_bit = 1U << row_pins[r];

        // Pull-ups only on columns whose key is currently released
        uint32_t pupd_c = 0, pupd_a = 0;
        for (uint8_t c = 0; c < MATRIX_COLS; c++) {
            if (!(current_matrix[r] & (1U << c))) {
                if (col_port[c] == GPIOC) {
                    pupd_c |= pupd_col_bit[c];
                } else {
                    pupd_a |= pupd_col_bit[c];
                }
            }
        }

        GPIOB->BSRR.W = row_bit << 16; // select row (LOW)
        wait_us(OPTICAL_ROW_SETTLE_US);

        matrix_row_t row;
        ATOMIC_BLOCK_FORCEON {
            GPIOC->PUPDR = (GPIOC->PUPDR & ~moder_c_mask) | pupd_c;
            GPIOA->PUPDR = (GPIOA->PUPDR & ~moder_a_mask) | pupd_a;
            GPIOC->MODER &= ~moder_c_mask; // columns -> inputs (still charged HIGH)
            GPIOA->MODER &= ~moder_a_mask;
            chSysPolledDelayX(US2RTC(REALTIME_COUNTER_CLOCK, OPTICAL_COL_SAMPLE_US));
            row = read_cols();
            GPIOB->BSRR.W = row_bit;          // deselect row
            GPIOC->MODER |= moder_c_out;    // precharge columns HIGH again
            GPIOA->MODER |= moder_a_out;
        }

        if (current_matrix[r] != row) {
            current_matrix[r] = row;
            changed           = true;
        }
    }
    return changed;
}
