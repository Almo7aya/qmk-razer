# First SWD session: READ-ONLY. No erase, no write, no option-byte changes.
# Run: openocd -f swd/huntsman_mini.cfg -f swd/probe_readonly.tcl
# (OpenOCD 0.12 returns mdw/reg output instead of printing it inside scripts, hence the echo [...] wrappers.)
init
halt

echo "=== core state ==="
echo [reg pc]
echo [reg sp]
echo [reg xpsr]

echo "=== DBGMCU_IDCODE (0xE0042000): DEV_ID 0x427/0x436 = STM32L1 Cat3 ==="
echo [mdw 0xE0042000]

echo "=== FLASH_OBR (0x40023C1C): RDPRT byte 0xAA = level 0, 0xCC = level 2, anything else = level 1 ==="
echo [mdw 0x40023C1C]
echo "=== FLASH_SR (0x40023C18), FLASH_PECR (0x40023C04), FLASH_ACR (0x40023C00) ==="
echo [mdw 0x40023C18]
echo [mdw 0x40023C04]
echo [mdw 0x40023C00]

echo "=== flash size register (Cat3: 0x1FF800CC, KB) and option bytes (0x1FF80000) ==="
echo [mdw 0x1FF800CC]
echo [mdw 0x1FF80000 4]

echo "=== start of Razer bootloader region (0x08000000) ==="
echo [mdw 0x08000000 8]
echo "=== end of bootloader region (0x08003FE0) ==="
echo [mdw 0x08003FE0 8]
echo "=== start of app region (0x08004000), stock v1.12 begins 20006998 0800413D ==="
echo [mdw 0x08004000 8]
echo "=== middle of app (0x0800C000) and end of flash (0x0803FFE0) ==="
echo [mdw 0x0800C000 4]
echo [mdw 0x0803FFE0 8]
echo "=== data EEPROM (0x08080000, 0x08080100) ==="
echo [mdw 0x08080000 8]
echo [mdw 0x08080100 8]
echo "=== RAM magic word (0x20007FFC) ==="
echo [mdw 0x20007FFC]

shutdown
