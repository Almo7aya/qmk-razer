# Flash a QMK build over SWD.
# 1) Backs up the current flash and data EEPROM first (for reverting).
# 2) Erases only the sectors the image covers, writes, verifies, and starts QMK.
# Run from the repo root:
#   openocd -f swd/huntsman_mini.cfg -c "set FW huntsman-mini/qmk/build/razer_huntsman_mini_via.bin" -f swd/flash_qmk.tcl
if {![info exists FW]} { set FW huntsman-mini/qmk/build/razer_huntsman_mini_via.bin }
if {![info exists BACKUP_TAG]} { set BACKUP_TAG pre_qmk }
init
reset halt
dump_image huntsman-mini/dumps/${BACKUP_TAG}_flash_08000000_256K.bin 0x08000000 0x40000
dump_image huntsman-mini/dumps/${BACKUP_TAG}_eeprom_08080000_8K.bin 0x08080000 0x2000
echo "backup done ($BACKUP_TAG)"
flash write_image erase $FW 0x08000000 bin
verify_image $FW 0x08000000 bin
echo "written and verified: $FW"
reset run
shutdown
