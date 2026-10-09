# Write the 256-byte boot stub (copy of the stock app's vector table) into the erased page at 0x08000000.
# No erase is issued: page 0 is already erased (STM32L1 erased state = 0x00). Verifies, then resets into the app.
# Run from the repo root: openocd -f swd/huntsman_mini.cfg -f swd/write_boot_stub.tcl
init
halt
echo "page 0 before: [mdw 0x08000000 4]"
flash write_image huntsman-mini/recovery/boot_stub_vectors_256.bin 0x08000000 bin
verify_image huntsman-mini/recovery/boot_stub_vectors_256.bin 0x08000000 bin
echo "page 0 after:  [mdw 0x08000000 4]"
echo "page 1 (untouched): [mdw 0x08000100 4]"
reset run
shutdown
