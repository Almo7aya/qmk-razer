# Simulate QK_BOOT: set the bootloader marker at the end of RAM, then system reset. Only RAM is written.
init
halt
mww 0x20007FFC 0xDEADBEEF
echo "marker: [mdw 0x20007FFC]"
reset run
shutdown
