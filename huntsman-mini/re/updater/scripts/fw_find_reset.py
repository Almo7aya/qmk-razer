import struct, re
b = open(r"Z:\projects\github\qmk-razer\huntsman-mini\stock\firmware\HuntsmanMini_dev1_v1.12.00.bin","rb").read()
base = 0x08004000
def find(val):
    out=[]
    pat = struct.pack("<I", val)
    for m in re.finditer(re.escape(pat), b):
        out.append(hex(base+m.start()))
    return out
for name,val in [("AIRCR key|SYSRESETREQ",0x05FA0004),("AIRCR addr",0xE000ED0C),("RTC_BKP0R",0x40002850),("PWR_CR",0x40007000),("RCC_CSR",0x40023834),("DATA_EEPROM",0x08080000),("SCB_VTOR",0xE000ED08), ("RAM_end-4",0x20007FFC),("RAM_end-8",0x20007FF8)]:
    print(name, hex(val), find(val))
