"""Convert a Razer HEX to bin and fingerprint the MCU from literal pools + vector table."""
import struct
import sys
from collections import Counter
from pathlib import Path


def load_hex(path):
    mem = {}
    base = 0
    for line in Path(path).read_text().split():
        b = bytes.fromhex(line[1:])
        assert sum(b) & 0xFF == 0, line
        n, addr, typ = b[0], (b[1] << 8) | b[2], b[3]
        payload = b[4 : 4 + n]
        if typ == 0:
            for i, v in enumerate(payload):
                mem[base + addr + i] = v
        elif typ == 4:
            base = struct.unpack(">H", payload)[0] << 16
    lo, hi = min(mem), max(mem)
    img = bytearray([0xFF] * (hi - lo + 1))
    for a, v in mem.items():
        img[a - lo] = v
    return lo, img


# STM32F4 (RM0090/RM0383/RM0368) peripheral map; F2 is the same layout.
F4 = {
    0x40000000: "TIM2", 0x40000400: "TIM3", 0x40000800: "TIM4", 0x40000C00: "TIM5",
    0x40001000: "TIM6", 0x40001400: "TIM7", 0x40001800: "TIM12", 0x40001C00: "TIM13", 0x40002000: "TIM14",
    0x40002800: "RTC", 0x40002C00: "WWDG", 0x40003000: "IWDG", 0x40003800: "SPI2", 0x40003C00: "SPI3",
    0x40004400: "USART2", 0x40004800: "USART3", 0x40004C00: "UART4", 0x40005000: "UART5",
    0x40005400: "I2C1", 0x40005800: "I2C2", 0x40005C00: "I2C3 (F4) / USB-FS (F0/F1/F3/L)", 0x40006400: "CAN1",
    0x40007000: "PWR", 0x40007400: "DAC",
    0x40010000: "TIM1", 0x40010400: "TIM8", 0x40011000: "USART1", 0x40011400: "USART6",
    0x40012000: "ADC1", 0x40012300: "ADC common", 0x40012C00: "SDIO", 0x40013000: "SPI1", 0x40013400: "SPI4",
    0x40013800: "SYSCFG", 0x40013C00: "EXTI", 0x40014000: "TIM9", 0x40014400: "TIM10", 0x40014800: "TIM11",
    0x40015000: "SPI5",
    0x40020000: "GPIOA", 0x40020400: "GPIOB", 0x40020800: "GPIOC", 0x40020C00: "GPIOD", 0x40021000: "GPIOE (F4) / RCC (F0/F1/F3)",
    0x40021C00: "GPIOH", 0x40023000: "CRC", 0x40023800: "RCC", 0x40023C00: "FLASH IF", 0x40026000: "DMA1",
    0x40026400: "DMA2", 0x50000000: "USB OTG FS", 0x40040000: "USB OTG HS",
    0xE0042000: "DBGMCU", 0x1FFF7A10: "UID (F2/F4)", 0x1FFF7A22: "FLASH_SIZE (F2/F4)",
    0x1FFFF7E8: "UID (F1)", 0x1FFFF7E0: "FLASH_SIZE (F1)", 0x40022000: "FLASH IF (F0/F1/F3)",
    0x40010800: "GPIOA (F1)", 0x40010C00: "GPIOB (F1)", 0x48000000: "GPIOA (F0/F3/L4/G4)",
}


def periph_for(v):
    best = None
    for b, name in F4.items():
        if b <= v < b + 0x400 and (best is None or b > best[0]):
            best = (b, name)
    return best


def main():
    lo, img = load_hex(sys.argv[1])
    out = Path(sys.argv[1]).with_suffix(".bin")
    out.write_bytes(img)
    print(f"image 0x{lo:08X}-0x{lo+len(img)-1:08X} ({len(img)} bytes) -> {out.name}")

    words = struct.unpack_from(f"<{len(img)//4}I", img)
    # vector table: 16 core + N IRQ
    vt = words[:16 + 100]
    print(f"SP=0x{vt[0]:08X} Reset=0x{vt[1]:08X}")
    # The default handler is the most common vector value
    common = Counter(v for v in vt[16:] if v not in (0, 0xFFFFFFFF)).most_common(1)[0][0]
    n_irq = 0
    for i, v in enumerate(vt[16:]):
        if not (lo <= (v & ~1) < lo + len(img)):
            break
        n_irq = i + 1
    print(f"IRQ vectors present: {n_irq}; default handler 0x{common:08X}")
    used = [(i, v) for i, v in enumerate(vt[16 : 16 + n_irq]) if v != common]
    print("IRQs with dedicated handlers:", ", ".join(f"#{i}" for i, _ in used))

    hits = Counter()
    exact = Counter()
    for w in words:
        p = periph_for(w)
        if p:
            hits[p[1]] += 1
            exact[w] += 1
    print("\nperipheral references (literal pool words):")
    for name, c in hits.most_common():
        print(f"  {c:4d}  {name}")
    print("\nmost common exact peripheral addresses:")
    for w, c in exact.most_common(40):
        print(f"  0x{w:08X} x{c}  {periph_for(w)[1]}")


main()
