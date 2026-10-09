import struct
from capstone import Cs, CS_ARCH_ARM, CS_MODE_THUMB, CS_MODE_MCLASS
b = open(r"Z:\projects\github\qmk-razer\huntsman-mini\stock\firmware\HuntsmanMini_dev1_v1.12.00.bin","rb").read()
base = 0x08004000
md = Cs(CS_ARCH_ARM, CS_MODE_THUMB | CS_MODE_MCLASS)
def dis(start, end):
    print("---- %08x..%08x" % (start, end))
    code = b[start-base:end-base]
    for ins in md.disasm(code, start):
        extra = ""
        if ins.mnemonic.startswith("ldr") and "[pc," in ins.op_str:
            off = int(ins.op_str.split("#")[-1].rstrip("]"), 16)
            addr = ((ins.address + 4) & ~3) + off
            if base <= addr < base+len(b)-4:
                extra = "   ; =0x%08x" % struct.unpack_from("<I", b, addr-base)[0]
        print("%08x: %-8s %s%s" % (ins.address, ins.mnemonic, ins.op_str, extra))
import sys
for a in sys.argv[1:]:
    s, e = a.split(":")
    dis(int(s,16), int(e,16))
