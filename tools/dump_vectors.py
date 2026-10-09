import struct, sys
from collections import Counter
img = open(sys.argv[1], 'rb').read()
w = struct.unpack_from(f"<{len(img)//4}I", img)
print("vector table (index: value):")
for i in range(0, 80, 8):
    print(f"  {i:3d}: " + " ".join(f"{v:08X}" for v in w[i:i+8]))
cands = {
 0x08080000: "L1 data EEPROM base", 0x08080FFF: "L1 EEPROM end (4K)", 0x08081FFF: "L1 EEPROM end (8K)",
 0x1FF80050: "L1 Cat1/2 UID", 0x1FF800D0: "L1 Cat3+ UID", 0x1FF8004C: "L1 Cat1/2 FLASH_SIZE", 0x1FF800CC: "L1 Cat3+ FLASH_SIZE",
 0x1FF80000: "L1 option bytes", 0xE0042000: "DBGMCU_IDCODE", 0x1FFF7A10: "F2/F4 UID", 0x1FFF7A22: "F4 flash size",
 0x50000000: "USB OTG FS", 0x40006000: "USB packet SRAM (L1/F1/F0/F3)", 0x40005C40: "USB_CNTR", 0x40005C44: "USB_ISTR",
 0x40005C4C: "USB_DADDR", 0x40005C50: "USB_BTABLE", 0x40007C00: "COMP/RI (L1)", 0x40010000: "SYSCFG(L1)/TIM1(F4)", 0x40010400: "EXTI(L1)/TIM8(F4)",
 0x40013800: "USART1(L1)/SYSCFG(F4)", 0x40012000: "ADC1(F4)", 0x40026000: "DMA1(F4)", 0x40026008: "?", 0x40026400:"DMA1(L1)",
 0x89ABCDEF: "L1 PEKEY1", 0x02030405: "L1 PEKEY2", 0x8C9DAEBF: "L1 PRGKEY1", 0x13141516: "L1 PRGKEY2", 0xFBEAD9C8: "L1 OPTKEY1", 0x24252627: "L1 OPTKEY2",
 0x45670123: "F-series KEY1", 0xCDEF89AB: "F-series KEY2", 0x08192A3B: "F4 OPTKEY1", 0x4C5D6E7F: "F4 OPTKEY2",
}
c = Counter(w)
# also check unaligned constants (literal pools are aligned, but be safe)
for a, name in cands.items():
    aligned = c.get(a, 0)
    anywhere = img.count(struct.pack('<I', a))
    if anywhere:
        print(f"  0x{a:08X} {name:32s} aligned={aligned} anywhere={anywhere}")
