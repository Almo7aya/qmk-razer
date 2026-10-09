init
halt
echo "lr  [reg lr]"
echo "msp [reg msp]"
echo "psp [reg psp]"
echo "MSP frame: [mdw [lindex [reg msp] 2] 8]"
echo "PSP frame: [mdw [lindex [reg psp] 2] 8]"
echo "BFAR/MMFAR: [mdw 0xE000ED38] [mdw 0xE000ED34]"
resume
shutdown
