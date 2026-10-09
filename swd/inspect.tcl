# READ-ONLY runtime inspection: where is the CPU, and what state are clocks/USB in.
# Run from the repo root: openocd -f swd/huntsman_mini.cfg -f swd/inspect.tcl
init
foreach i {1 2 3} {
    halt
    echo "sample $i: [reg pc] [reg lr] [reg sp]"
    resume
    sleep 50
}
halt
echo "xPSR/IPSR: [reg xPSR]"
echo "RCC_CR      (0x40023800): [mdw 0x40023800]"
echo "RCC_CFGR    (0x40023808): [mdw 0x40023808]"
echo "PWR_CR      (0x40007000): [mdw 0x40007000]"
echo "FLASH_ACR   (0x40023C00): [mdw 0x40023C00]"
echo "SYSCFG_PMC  (0x40010004): [mdw 0x40010004]"
echo "USB_CNTR    (0x40005C40): [mdw 0x40005C40]"
echo "USB_ISTR    (0x40005C44): [mdw 0x40005C44]"
echo "USB_DADDR   (0x40005C4C): [mdw 0x40005C4C]"
echo "RCC_APB1ENR (0x40023824): [mdw 0x40023824]"
echo "SCB_CFSR    (0xE000ED28): [mdw 0xE000ED28]"
echo "SCB_HFSR    (0xE000ED2C): [mdw 0xE000ED2C]"
resume
shutdown
