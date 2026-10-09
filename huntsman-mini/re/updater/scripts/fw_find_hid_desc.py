import re
b = open(r"Z:\projects\github\qmk-razer\huntsman-mini\stock\firmware\HuntsmanMini_dev1_v1.12.00.bin","rb").read()
base = 0x08004000
for m in re.finditer(rb"\x95\x5a", b):
    i = m.start()
    print(hex(base+i), b[max(0,i-40):i+24].hex(" "))
# configuration descriptor search: 09 02 xx xx 04 01
for m in re.finditer(rb"\x09\x02..\x04\x01", b, re.S):
    i = m.start(); tl = b[i+2] | (b[i+3]<<8)
    print("cfg desc at", hex(base+i), "total len", tl)
    d = b[i:i+tl]
    j = 0
    while j < len(d):
        L = d[j]; T = d[j+1] if j+1 < len(d) else 0
        if L == 0: break
        print("   ", d[j:j+L].hex(" "))
        j += L
