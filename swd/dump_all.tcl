# Full backup over SWD: READ-ONLY. Dumps all flash, data EEPROM and option bytes.
# Run from the repo root: openocd -f swd/huntsman_mini.cfg -f swd/dump_all.tcl
init
halt
dump_image huntsman-mini/dumps/swd_flash_08000000_256K.bin 0x08000000 0x40000
dump_image huntsman-mini/dumps/swd_eeprom_08080000_8K.bin 0x08080000 0x2000
dump_image huntsman-mini/dumps/swd_optbytes_1FF80000.bin 0x1FF80000 0x20
echo "dump complete"
shutdown
