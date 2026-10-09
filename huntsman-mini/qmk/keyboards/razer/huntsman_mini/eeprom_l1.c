// Copyright 2026 almo7aya
// SPDX-License-Identifier: GPL-2.0-or-later
//
// STM32L1 data EEPROM driver (EEPROM_DRIVER = custom), based on QMK's platforms/chibios/drivers/eeprom/
// eeprom_stm32_L0_L1.c with two changes for this board:
//  - erase skips words that are already 0 (the erased state). QMK's driver rewrites all 512 words (~1.7 s),
//    and data EEPROM operations stall instruction fetch, which made USB enumeration fail (Windows code 10)
//    on the first boot after an EEPROM reset.
//  - busy-wait without WFI (WFI idle is disabled on this board, see board.c / config.h).

#include <stdint.h>
#include <stddef.h>
#include <stdbool.h>
#include "hal.h"
#include "eeprom_driver.h"

#define EEPROM_BASE_ADDR 0x08080000U
#define EEPROM_WORD(offset) (*(volatile uint32_t *)(EEPROM_BASE_ADDR + (offset)))
#define EEPROM_BYTE(offset) (*(volatile uint8_t *)(EEPROM_BASE_ADDR + (offset)))

#define FLASH_PEKEY1 0x89ABCDEFU
#define FLASH_PEKEY2 0x02030405U

static inline void eeprom_wait_not_busy(void) {
    while (FLASH->SR & FLASH_SR_BSY) {
    }
}

static inline void eeprom_unlock(void) {
    eeprom_wait_not_busy();
    if (FLASH->PECR & FLASH_PECR_PELOCK) {
        FLASH->PEKEYR = FLASH_PEKEY1;
        FLASH->PEKEYR = FLASH_PEKEY2;
    }
}

static inline void eeprom_lock(void) {
    eeprom_wait_not_busy();
    FLASH->PECR |= FLASH_PECR_PELOCK;
}

void eeprom_driver_init(void) {}

void eeprom_driver_format(bool erase) {
    if (erase) {
        eeprom_driver_erase();
    }
}

void eeprom_driver_erase(void) {
    eeprom_unlock();
    for (uint32_t offset = 0; offset < TOTAL_EEPROM_BYTE_COUNT; offset += sizeof(uint32_t)) {
        if (EEPROM_WORD(offset) != 0) {
            EEPROM_WORD(offset) = 0;
            eeprom_wait_not_busy();
        }
    }
    eeprom_lock();
}

void eeprom_read_block(void *buf, const void *addr, size_t len) {
    uint8_t *dst = (uint8_t *)buf;
    for (size_t i = 0; i < len; i++) {
        uint32_t offset = (uint32_t)addr + i;
        if (offset >= TOTAL_EEPROM_BYTE_COUNT) {
            break;
        }
        dst[i] = EEPROM_BYTE(offset);
    }
}

void eeprom_write_block(const void *buf, void *addr, size_t len) {
    // Word-aligned read-modify-write, only touching words whose value changes
    uint32_t start = (uint32_t)addr;
    if (start >= TOTAL_EEPROM_BYTE_COUNT) {
        return;
    }
    if (len > TOTAL_EEPROM_BYTE_COUNT - start) {
        len = TOTAL_EEPROM_BYTE_COUNT - start;
    }
    uint32_t       end = start + len;
    const uint8_t *src = (const uint8_t *)buf;

    eeprom_unlock();
    for (uint32_t word = start & ~3U; word < end; word += 4) {
        uint32_t old_word = EEPROM_WORD(word);
        uint32_t new_word = old_word;
        for (uint32_t b = 0; b < 4; b++) {
            uint32_t a = word + b;
            if (a >= start && a < end) {
                new_word = (new_word & ~(0xFFU << (b * 8))) | ((uint32_t)src[a - start] << (b * 8));
            }
        }
        if (new_word != old_word) {
            EEPROM_WORD(word) = new_word;
            eeprom_wait_not_busy();
        }
    }
    eeprom_lock();
}
