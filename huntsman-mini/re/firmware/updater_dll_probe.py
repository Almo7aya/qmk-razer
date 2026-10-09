"""Static look at FWUpdaterDLL.dll (x86) exports: disassemble a named export with capstone.

Usage: python updater_dll_probe.py <ExportName> [nbytes]
Only reads the file; never loads/executes it.
"""
import struct
import sys
from pathlib import Path

import capstone

DLL = Path(__file__).resolve().parents[2] / "stock/updater_extracted/FWUpdaterDLL.dll"
d = DLL.read_bytes()
pe = struct.unpack_from("<I", d, 0x3C)[0]
nsec = struct.unpack_from("<H", d, pe + 6)[0]
optsz = struct.unpack_from("<H", d, pe + 20)[0]
opt = pe + 24
imagebase = struct.unpack_from("<I", d, opt + 28)[0]
exp_rva, exp_sz = struct.unpack_from("<II", d, opt + 96)
secs = []
for i in range(nsec):
    o = opt + optsz + 40 * i
    name = d[o:o + 8].rstrip(b"\0").decode()
    vsz, va, rsz, raw = struct.unpack_from("<IIII", d, o + 8)
    secs.append((name, va, vsz, raw, rsz))


def rva2off(rva):
    for name, va, vsz, raw, rsz in secs:
        if va <= rva < va + max(vsz, rsz):
            return rva - va + raw
    raise ValueError(hex(rva))


def exports():
    o = rva2off(exp_rva)
    nfun, nnames, afun, aname, aord = struct.unpack_from("<IIIII", d, o + 20)
    out = {}
    for i in range(nnames):
        nrva = struct.unpack_from("<I", d, rva2off(aname) + 4 * i)[0]
        nm = d[rva2off(nrva):].split(b"\0", 1)[0].decode()
        ordi = struct.unpack_from("<H", d, rva2off(aord) + 2 * i)[0]
        frva = struct.unpack_from("<I", d, rva2off(afun) + 4 * ordi)[0]
        out[nm] = frva
    return out


if __name__ == "__main__":
    ex = exports()
    if len(sys.argv) < 2:
        for k, v in sorted(ex.items(), key=lambda kv: kv[1]):
            print(f"{imagebase + v:08X} {k}")
        sys.exit()
    name = sys.argv[1]
    n = int(sys.argv[2], 0) if len(sys.argv) > 2 else 0x200
    rva = ex[name]
    md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
    off = rva2off(rva)
    for ins in md.disasm(d[off:off + n], imagebase + rva):
        print(f"{ins.address:08X}: {ins.mnemonic:8s} {ins.op_str}")
