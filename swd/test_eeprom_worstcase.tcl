# Stress test: fill QMK's 2 KB data-EEPROM area with junk (and invalidate eeconfig), so the next boot must
# rewrite every word. Writes ONLY data EEPROM 0x08080000-0x080807FF. Run from the repo root:
#   openocd -f swd/huntsman_mini.cfg -f swd/test_eeprom_worstcase.tcl
init
halt
mww 0x40023C0C 0x89ABCDEF
mww 0x40023C0C 0x02030405
for {set off 0} {$off < 0x800} {incr off 4} {
    mww [expr {0x08080000 + $off}] [expr {$off == 0 ? 0 : 0xA5A5A5A5}]
    sleep 5
}
echo "filled: [mdw 0x08080000 4] ... [mdw 0x080807F0 4]"
mww 0x40023C04 [expr {[lindex [read_memory 0x40023C04 32 1] 0] | 1}]
reset run
shutdown
