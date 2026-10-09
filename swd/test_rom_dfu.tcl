# Test: start the STM32L151 factory (system memory) bootloader without BOOT0, to see if USB DFU works.
# No flash writes: only core/peripheral registers. Any reset or replug returns to QMK.
# Run from the repo root: openocd -f swd/huntsman_mini.cfg -f swd/test_rom_dfu.tcl
init
reset halt
# RCC_APB2ENR.SYSCFGEN, then SYSCFG_MEMRMP.MEM_MODE = 01 (system flash mapped at 0x00000000)
mww 0x40023820 [expr {[lindex [read_memory 0x40023820 32 1] 0] | 0x1}]
mww 0x40010000 0x00000001
mww 0xE000ED08 0x00000000
set sp [lindex [read_memory 0x1FF00000 32 1] 0]
set pc [lindex [read_memory 0x1FF00004 32 1] 0]
echo [format "ROM bootloader: SP=0x%08X entry=0x%08X" $sp $pc]
reg msp $sp
reg pc [expr {$pc & ~1}]
reg xPSR 0x01000000
resume
echo "running factory bootloader"
shutdown
