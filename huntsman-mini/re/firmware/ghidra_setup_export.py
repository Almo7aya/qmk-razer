"""Shared exporter: decompile every function + flat annotated listing (used by ghidra_setup / ghidra_annotate)."""
from pathlib import Path

BASE = 0x08004000


def export(program, mon, outdir: Path, name: str):
    from ghidra.app.decompiler import DecompInterface, DecompileOptions
    from ghidra.program.model.listing import CodeUnit
    di = DecompInterface()
    di.setOptions(DecompileOptions())
    di.openProgram(program)
    fm = program.getFunctionManager()
    out = []
    for f in fm.getFunctions(True):
        r = di.decompileFunction(f, 60, mon)
        c = r.getDecompiledFunction().getC() if r and r.getDecompiledFunction() \
            else f"/* decompile failed: {r.getErrorMessage()} */"
        out.append(f"// ===== {f.getName()} @ {f.getEntryPoint()} =====\n{c}\n")
    (outdir / f"decomp_{name}.c").write_text("".join(out), encoding="utf-8")
    lst = program.getListing()
    st = program.getSymbolTable()
    lines = []
    for cu in lst.getCodeUnits(True):
        a = cu.getAddress()
        o = a.getOffset()
        if not (BASE <= o < 0x08020000 or 0x20000000 <= o < 0x20000400):
            continue
        sym = st.getPrimarySymbol(a)
        if sym is not None and not sym.getName().startswith("DAT_"):
            lines.append(f"{sym.getName()}:")
        plate = cu.getComment(CodeUnit.PLATE_COMMENT)
        if plate:
            lines.extend("  ;; " + ln for ln in str(plate).splitlines())
        refs = [str(r.getToAddress()) for r in cu.getReferencesFrom()]
        rs = " ; " + ",".join(refs) if refs else ""
        lines.append(f"  {a}: {cu.toString():48s}{rs}")
    (outdir / f"listing_{name}.txt").write_text("\n".join(lines), encoding="utf-8")
    print("functions:", fm.getFunctionCount())
