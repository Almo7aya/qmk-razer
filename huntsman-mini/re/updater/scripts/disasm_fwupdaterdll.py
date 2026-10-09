"""Dump disassembly of selected FWUpdaterDLL.dll functions (static analysis only).

Reuses the Ghidra project created by decompile_fwupdaterdll.py.
Usage: python disasm_fwupdaterdll.py 10002630 10002840 ...   (hex addresses)
       python disasm_fwupdaterdll.py --str 1019b2fc 1019b304 ... (dump UTF-16/ASCII at addr)
Output goes to stdout.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
RE_DIR = os.path.dirname(HERE)
ROOT = os.path.abspath(os.path.join(RE_DIR, "..", ".."))
DLL = os.path.join(ROOT, "stock", "updater_extracted", "FWUpdaterDLL.dll")
PROJ_DIR = os.path.join(RE_DIR, "ghidra")

import pyghidra

pyghidra.start()

args = sys.argv[1:]
mode = "dis"
if args and args[0] == "--str":
    mode = "str"
    args = args[1:]

with pyghidra.open_program(DLL, project_location=PROJ_DIR, project_name="FWUpdaterDLL", analyze=False) as flat:
    program = flat.getCurrentProgram()
    fm = program.getFunctionManager()
    listing = program.getListing()
    mem = program.getMemory()
    af = program.getAddressFactory()
    for a in args:
        addr = af.getDefaultAddressSpace().getAddress(int(a, 16))
        if mode == "str":
            raw = bytearray()
            for i in range(64):
                b = mem.getByte(addr.add(i)) & 0xFF
                raw.append(b)
            print(a, raw.hex(), "| utf16:", raw.decode("utf-16-le", "replace").split("\x00")[0], "| ascii:", raw.split(b"\x00")[0].decode("latin-1"))
            continue
        f = fm.getFunctionContaining(addr)
        print("=" * 70)
        print("FUNCTION", f.getName() if f else "?", f.getEntryPoint() if f else a)
        body = f.getBody() if f else None
        it = listing.getInstructions(body, True)
        while it.hasNext():
            ins = it.next()
            print("  %s  %s" % (ins.getAddress(), ins))
