"""Headless Ghidra (pyghidra) decompilation of FWUpdaterDLL.dll.

Static analysis only: imports the DLL into a local Ghidra project under
re/updater/ghidra/, runs auto-analysis, and writes C pseudo-code for every
exported function plus everything they call (transitively, depth-limited)
to re/updater/FWUpdaterDLL_decompiled.c.

Usage:  python decompile_fwupdaterdll.py
Requires GHIDRA_INSTALL_DIR to be set.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
RE_DIR = os.path.dirname(HERE)  # re/updater
ROOT = os.path.abspath(os.path.join(RE_DIR, "..", ".."))  # huntsman-mini
DLL = os.path.join(ROOT, "stock", "updater_extracted", "FWUpdaterDLL.dll")
PROJ_DIR = os.path.join(RE_DIR, "ghidra")
OUT = os.path.join(RE_DIR, "FWUpdaterDLL_decompiled.c")
MAX_DEPTH = int(os.environ.get("DECOMP_DEPTH", "4"))

import pyghidra

pyghidra.start()

from ghidra.app.decompiler import DecompInterface, DecompileOptions  # noqa: E402
from ghidra.util.task import ConsoleTaskMonitor  # noqa: E402

os.makedirs(PROJ_DIR, exist_ok=True)

with pyghidra.open_program(DLL, project_location=PROJ_DIR, project_name="FWUpdaterDLL", analyze=True) as flat:
    program = flat.getCurrentProgram()
    fm = program.getFunctionManager()
    st = program.getSymbolTable()
    monitor = ConsoleTaskMonitor()

    ifc = DecompInterface()
    ifc.setOptions(DecompileOptions())
    ifc.openProgram(program)

    exports = []
    it = st.getExternalEntryPointIterator()
    while it.hasNext():
        addr = it.next()
        f = fm.getFunctionAt(addr)
        syms = st.getSymbols(addr)
        names = [s.getName() for s in syms]
        exports.append((addr, f, names))

    seen = set()
    order = []

    def visit(func, depth):
        if func is None or func.isThunk() and func.getThunkedFunction(True) is not None and func.getThunkedFunction(True).isExternal():
            return
        if func.isExternal():
            return
        key = func.getEntryPoint().getOffset()
        if key in seen:
            return
        seen.add(key)
        order.append((func, depth))
        if depth >= MAX_DEPTH:
            return
        for callee in func.getCalledFunctions(monitor):
            visit(callee, depth + 1)

    for addr, f, names in exports:
        visit(f, 0)

    with open(OUT, "w", encoding="utf-8") as fh:
        fh.write("/* FWUpdaterDLL.dll - Ghidra decompilation (exports + callees, depth<=%d) */\n" % MAX_DEPTH)
        fh.write("/* image base: %s */\n\n" % program.getImageBase())
        fh.write("/* ---- Exports ---- */\n")
        for addr, f, names in exports:
            fh.write("/* %s  %s */\n" % (addr, ", ".join(names)))
        fh.write("\n")
        for func, depth in order:
            res = ifc.decompileFunction(func, 120, monitor)
            fh.write("\n/* ================================================================ */\n")
            fh.write("/* %s @ %s  (depth %d) */\n" % (func.getName(), func.getEntryPoint(), depth))
            if res is not None and res.decompileCompleted():
                fh.write(res.getDecompiledFunction().getC())
            else:
                fh.write("/* decompile failed: %s */\n" % (res.getErrorMessage() if res else "null"))
    print("wrote", OUT, "functions:", len(order))
