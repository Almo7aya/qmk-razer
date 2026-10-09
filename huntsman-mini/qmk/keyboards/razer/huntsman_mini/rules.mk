# STM32L151RCT6 has no QMK MCU preset: describe it to the ChibiOS build directly.
MCU_FAMILY = STM32
MCU_SERIES = STM32L1xx
MCU_LDSCRIPT = STM32L151xC
MCU_STARTUP = stm32l1xx
BOARD = RAZER_HUNTSMAN_MINI
ARMV = 7
USE_FPU = no

# Optical switch matrix (see matrix.c)
SRC += matrix.c

# Data EEPROM driver that skips erasing blank words (see eeprom_l1.c)
EEPROM_DRIVER = custom
SRC += eeprom_l1.c
