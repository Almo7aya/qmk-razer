"""Create/refresh a Ghidra project for the Huntsman Mini stock app and export decompilation.

Usage:  python ghidra_setup.py [bin] [progname]
  defaults: ../../stock/firmware/HuntsmanMini_dev1_v1.12.00.bin, hm_v1_12

Creates the project in ./ghidra_proj (next to this script), with:
  * app image @ 0x08004000 (flash), placeholder bootloader block @ 0x08000000
  * RAM @ 0x20000000 (32 KB), data EEPROM @ 0x08080000 (8 KB), factory info / option bytes
  * every STM32L15xC SVD peripheral as a volatile block + register labels
  * Cortex-M SCS block, vector table pointers + named IRQ handler functions
Then runs auto-analysis and writes decomp_<prog>.c and listing_<prog>.txt here.
"""
import struct
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import pyghidra

HERE = Path(__file__).resolve().parent
BIN = Path(sys.argv[1]) if len(sys.argv) > 1 else HERE.parents[1] / "stock/firmware/HuntsmanMini_dev1_v1.12.00.bin"
PROG = sys.argv[2] if len(sys.argv) > 2 else "hm_v1_12"
BASE = 0x08004000
SVD = HERE / "STM32L15xC.svd"

# STM32L151xC vector names (startup_stm32l151xc.s)
VEC = ["SP", "Reset", "NMI", "HardFault", "MemManage", "BusFault", "UsageFault", "R7", "R8", "R9", "R10",
       "SVC", "DebugMon", "R13", "PendSV", "SysTick",
       "WWDG", "PVD", "TAMPER_STAMP", "RTC_WKUP", "FLASH", "RCC", "EXTI0", "EXTI1", "EXTI2", "EXTI3", "EXTI4",
       "DMA1_Ch1", "DMA1_Ch2", "DMA1_Ch3", "DMA1_Ch4", "DMA1_Ch5", "DMA1_Ch6", "DMA1_Ch7", "ADC1",
       "USB_HP", "USB_LP", "DAC", "COMP", "EXTI9_5", "LCD", "TIM9", "TIM10", "TIM11", "TIM2", "TIM3", "TIM4",
       "I2C1_EV", "I2C1_ER", "I2C2_EV", "I2C2_ER", "SPI1", "SPI2", "USART1", "USART2", "USART3", "EXTI15_10",
       "RTC_Alarm", "USB_FS_WKUP", "TIM6", "TIM7", "SDIO", "TIM5", "SPI3", "UART4", "UART5", "DMA2_Ch1",
       "DMA2_Ch2", "DMA2_Ch3", "DMA2_Ch4", "DMA2_Ch5", "AES", "COMP_ACQ"]


def svd_peripherals():
    root = ET.parse(SVD).getroot()
    per = {}
    for p in root.find("peripherals").findall("peripheral"):
        per[p.findtext("name")] = p
    out = []
    for name, p in per.items():
        base = int(p.findtext("baseAddress"), 0)
        src = per[p.get("derivedFrom")] if p.get("derivedFrom") else p
        regs = []
        for r in src.findall("registers/register"):
            regs.append((r.findtext("name"), int(r.findtext("addressOffset"), 0)))
        out.append((name, base, regs))
    return out


def main():
    pyghidra.start()
    from ghidra.program.model.address import AddressSet
    from ghidra.program.model.symbol import SourceType
    from ghidra.program.model.data import PointerDataType, DWordDataType
    from ghidra.app.cmd.disassemble import DisassembleCommand
    from ghidra.app.cmd.function import CreateFunctionCmd
    from ghidra.program.model.listing import CodeUnit
    from java.io import ByteArrayInputStream
    from ghidra.app.decompiler import DecompInterface, DecompileOptions

    data = BIN.read_bytes()
    proj_dir = HERE / "ghidra_proj"
    proj_dir.mkdir(exist_ok=True)
    project = pyghidra.open_project(str(proj_dir), "huntsman_mini", create=True)
    pdata = project.getProjectData()
    root = pdata.getRootFolder()
    if root.getFile(PROG) is not None:
        root.getFile(PROG).delete()

    from ghidra.program.model.lang import LanguageID, CompilerSpecID
    from ghidra.program.util import DefaultLanguageService
    from ghidra.program.database import ProgramDB
    from java.lang import Object
    consumer = Object()
    lang = DefaultLanguageService.getLanguageService().getLanguage(LanguageID("ARM:LE:32:Cortex"))
    cspec = lang.getCompilerSpecByID(CompilerSpecID("default"))
    program = ProgramDB(PROG, lang, cspec, consumer)
    mon = pyghidra.task_monitor()
    space = program.getAddressFactory().getDefaultAddressSpace()
    A = lambda x: space.getAddress(x)
    mem = program.getMemory()
    st = program.getSymbolTable()
    listing = program.getListing()

    tx = program.startTransaction("setup")
    try:
        def ublock(name, addr, size, volatile=False, w=True, x=False):
            b = mem.createUninitializedBlock(name, A(addr), size, False)
            b.setRead(True); b.setWrite(w); b.setExecute(x); b.setVolatile(volatile)
            return b

        b = mem.createInitializedBlock("app", A(BASE), ByteArrayInputStream(data), len(data), mon, False)
        b.setRead(True); b.setWrite(False); b.setExecute(True)
        ublock("bootloader", 0x08000000, 0x4000, w=False, x=True)
        ublock("eeprom", 0x08080000, 0x2000, volatile=True)
        ublock("sysmem_info", 0x1FF00000, 0x1000, w=False)
        ublock("optbytes_factory", 0x1FF80000, 0x100, volatile=True)
        # RAM: reproduce __scatterload (RAM code + decompressed .data), rest uninitialised
        sys.path.insert(0, str(HERE))
        from scatterload import ram_image
        ramregs = ram_image(data)
        end = 0x20000000
        for i, (dst, blob) in enumerate(ramregs[:2]):
            rb = mem.createInitializedBlock(["ram_code", "ram_data"][i], A(dst),
                                            ByteArrayInputStream(bytes(blob)), len(blob), mon, False)
            rb.setRead(True); rb.setWrite(True); rb.setExecute(i == 0)
            end = dst + len(blob)
        ublock("ram_bss", end, 0x20008000 - end)
        ublock("usb_pma", 0x40006000, 0x400, volatile=True)
        ublock("scs", 0xE000E000, 0x1000, volatile=True)
        ublock("dbgmcu", 0xE0042000, 0x100, volatile=True)
        for name, base, regs in sorted(svd_peripherals(), key=lambda p: p[1]):
            if name in ("USB_SRAM", "NVIC", "DBG", "OPAMP", "RI"):
                continue
            try:
                size = 0x300 if name == "ADC" else (0x100 if name == "C_ADC" else 0x400)
                if name == "C_ADC":
                    base_blk = base
                ublock(name, base, size, volatile=True)
            except Exception as e:
                print("block", name, e)
            for rn, off in regs:
                st.createLabel(A(base + off), f"{name}_{rn}", SourceType.IMPORTED)
        for nm, a in {"OB_RDP": 0x1FF80000, "OB_USER": 0x1FF80004, "UID_0": 0x1FF800D0, "UID_1": 0x1FF800D4,
                      "UID_2": 0x1FF800E4, "FLASH_SIZE": 0x1FF800CC, "NVIC_ISER0": 0xE000E100,
                      "NVIC_ICER0": 0xE000E180, "NVIC_ISPR0": 0xE000E200, "NVIC_ICPR0": 0xE000E280,
                      "NVIC_IPR": 0xE000E400, "SCB_CPUID": 0xE000ED00, "SCB_ICSR": 0xE000ED04,
                      "SCB_VTOR": 0xE000ED08, "SCB_AIRCR": 0xE000ED0C, "SCB_SCR": 0xE000ED10,
                      "SCB_CCR": 0xE000ED14, "SCB_SHPR": 0xE000ED18, "SCB_SHCSR": 0xE000ED24,
                      "SYST_CSR": 0xE000E010, "SYST_RVR": 0xE000E014, "SYST_CVR": 0xE000E018,
                      "DBGMCU_IDCODE": 0xE0042000, "DBGMCU_CR": 0xE0042004}.items():
            st.createLabel(A(a), nm, SourceType.IMPORTED)

        # vector table
        nvec = 16 + 57
        entry_pts = []
        for i in range(nvec):
            a = BASE + 4 * i
            v = struct.unpack_from("<I", data, 4 * i)[0]
            listing.createData(A(a), PointerDataType() if i else DWordDataType())
            nm = VEC[i] if i < len(VEC) else f"IRQ{i-16}"
            st.createLabel(A(a), "vec_" + nm, SourceType.IMPORTED)
            if i and v and (BASE <= (v & ~1) < BASE + len(data)):
                entry_pts.append((v & ~1, nm))
        seen = {}
        for a in (0x20000000, 0x2000006C, 0x200000C0, 0x2000011C, 0x2000017C):
            entry_pts.append((a, f"ramfunc_{a:08x}"))
        for a, nm in entry_pts:
            seen.setdefault(a, []).append(nm)
        for a, nms in seen.items():
            fname = (nms[0] + "_Handler") if len(nms) == 1 else "Default_Handler"
            if nms[0].startswith("ramfunc"):
                fname = nms[0]
            st.createLabel(A(a), fname, SourceType.USER_DEFINED)
            DisassembleCommand(A(a), None, True).applyTo(program, mon)
            CreateFunctionCmd(A(a)).applyTo(program, mon)
            st.addExternalEntryPoint(A(a))
    finally:
        program.endTransaction(tx, True)

    print(pyghidra.analyze(program)[-2000:])

    # Second pass: aggressive function start search in unanalysed regions (Thumb push prologues)
    tx = program.startTransaction("prologues")
    try:
        fm = program.getFunctionManager()
        # code pointers stored in initialised .data (USB class / descriptor callback tables etc.)
        tail = data[0x08010100 - BASE:]
        for dst, blob in ramregs[1:2] + [(0x08010100, tail)]:
            for off in range(0, len(blob) - 3, 4):
                w = struct.unpack_from("<I", blob, off)[0]
                if (w & 1) and BASE <= w < 0x08010000:
                    a = A(w & ~1)
                    if fm.getFunctionAt(a) is None:
                        DisassembleCommand(a, None, True).applyTo(program, mon)
                        CreateFunctionCmd(a).applyTo(program, mon)
        for off in range(0, len(data) - 2, 2):
            hw = struct.unpack_from("<H", data, off)[0]
            a = A(BASE + off)
            if (hw & 0xFF00) == 0xB500 or hw == 0xE92D:  # push {..,lr} / push.w
                if listing.getInstructionAt(a) is None and listing.getDataContaining(a) is None \
                        and listing.getInstructionContaining(a) is None:
                    DisassembleCommand(a, None, True).applyTo(program, mon)
                    CreateFunctionCmd(a).applyTo(program, mon)
    finally:
        program.endTransaction(tx, True)
    print(pyghidra.analyze(program)[-1000:])

    root.createFile(PROG, program, mon)
    from ghidra_setup_export import export
    export(program, mon, HERE, PROG)
    program.release(consumer)
    project.close()


main()
