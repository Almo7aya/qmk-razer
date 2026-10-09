import struct, sys
from capstone import Cs, CS_ARCH_ARM, CS_MODE_THUMB, CS_MODE_MCLASS
b = open(r"Z:\projects\github\qmk-razer\huntsman-mini\stock\firmware\HuntsmanMini_dev1_v1.12.00.bin","rb").read()
base = 0x08004000
md = Cs(CS_ARCH_ARM, CS_MODE_THUMB | CS_MODE_MCLASS)
md.skipdata = True
targets = [int(x,16) for x in sys.argv[1:]]
for ins in md.disasm(b, base):
    if ins.mnemonic in ("bl", "b.w", "b", "blx") or ins.mnemonic.startswith("b"):
        for t in targets:
            if ins.op_str == "#0x%x" % t:
                print("%08x: %s %s" % (ins.address, ins.mnemonic, ins.op_str))
