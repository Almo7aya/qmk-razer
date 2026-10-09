# Test helper: invalidate QMK's eeconfig magic (data EEPROM word 0) so the next boot does a full EEPROM reset.
# Writes ONLY the data EEPROM word at 0x08080000. Run from the repo root:
#   openocd -f swd/huntsman_mini.cfg -f swd/test_eeprom_reset.tcl
init
halt
echo "before: [mdw 0x08080000 2]"
mww 0x40023C0C 0x89ABCDEF
mww 0x40023C0C 0x02030405
mww 0x08080000 0x00000000
sleep 20
echo "after:  [mdw 0x08080000 2]"
mww 0x40023C04 [expr {[lindex [read_memory 0x40023C04 32 1] 0] | 1}]
reset run
shutdown
