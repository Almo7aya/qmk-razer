#!/bin/sh
# Build the boot shim (run on the Linux build host: needs arm-none-eabi-gcc).
#   shim.bin           at 0x08000000, starts firmware at 0x08004000 (the real one)
#   test_dfu.bin       at 0x08010000, points at an empty slot -> must enter DFU   (hardware test, page 0 untouched)
#   test_app.bin       at 0x08010000, points at 0x08000000    -> must start QMK / DFU with Esc held
set -eu
cd "$(dirname "$0")"
CFLAGS="-mcpu=cortex-m3 -mthumb -Os -ffreestanding -nostdlib -fno-builtin -Wall -Wextra -Werror -fno-common"

build() { # name origin app_addr
    cat > "$1.ld" <<EOF
MEMORY { flash (rx) : ORIGIN = $2, LENGTH = 16K }
__stack_top = 0x20007000;
SECTIONS {
    .vectors : { KEEP(*(.vectors)) } > flash
    .text : { *(.text*) *(.rodata*) } > flash
    /DISCARD/ : { *(.data*) *(.bss*) *(.ARM.*) *(.comment) }
}
EOF
    arm-none-eabi-gcc $CFLAGS -DAPP_ADDR=$3 -T "$1.ld" -o "$1.elf" shim.c
    arm-none-eabi-objcopy -O binary "$1.elf" "$1.bin"
    rm -f "$1.ld"
    echo "$1: $(stat -c %s "$1.bin") bytes @ $2, app $3"
}

build shim 0x08000000 0x08004000U
build test_dfu 0x08010000 0x08030000U
build test_app 0x08010000 0x08000000U
arm-none-eabi-objdump -d shim.elf > shim.lst
