# Razer Huntsman Mini — stock firmware reverse engineering (for the QMK port)

Target: `HuntsmanMini_dev1_v1.12.00` (ANSI/US build). `dev2_v1.32.00` (Nordic build) was diffed: it differs in
**3 bytes only** (version byte `0x0C`→`0x20` at `0x08010481`, and the Esc key's base/FN usages swapped:
`0x08010C45` 0x29→0x35, `0x08011035` 0x35→0x29). Everything below applies to both.

Method: static analysis only (Ghidra 12.1.2 headless via pyghidra and capstone). Nothing was sent to any USB device.
Confidence levels: **High** = read directly from the disassembly or register writes. **Medium** = strong inference
from code plus data. **Low** = educated guess.

The firmware is an STM32CubeL1 HAL + ST USB Device library application built with Keil/ARMCC. It uses `__scatterload`
with LZ-compressed `.data`, and RAM-resident flash routines.

---

## 0. TL;DR

| Item | Finding | Conf. |
|---|---|---|
| **Enter Razer bootloader** | `cpsid i` → `*(uint32_t*)0x20007FFC = 0xAAAAAAAA` → `DSB` → `SCB->AIRCR = 0x05FA0004 \| (AIRCR & 0x700)` (SYSRESETREQ) → spin. Function `0x0800935C`. It is triggered by Razer command **class 0x00, id 0x04 (set device mode), arg0 = 0x01**. | High (app side) |
| Startup | `SystemInit` only sets `VTOR = 0x08004000`. There is no magic or key check that jumps to the bootloader, no app CRC or signature check, and no option-byte or RDP access. | High |
| Clock | HSE **12 MHz crystal** (not bypass) → PLL ×8 = 96 MHz → /3 → **SYSCLK 32 MHz**. AHB/APB1/APB2 are /1. **VOS range 1 (1.8 V)**. Flash **1 WS + ACC64**, no prefetch. USB 48 MHz = PLLVCO/2. | High |
| Matrix | **8×8**. Rows (driven, **active LOW**): `PB0 PB1 PB10 PB11 PB12 PB13 PB14 PB15`. Cols (sense, **LOW = pressed**): `PC6 PC7 PC8 PC9 PA8 PA9 PA10 PA15`. Plain **digital IDR**; the ADC is not used for switches. TIM3 interrupt every **125 µs** scans one row, so a full scan takes 1 ms. Cols are precharged by driving them high, then released with a pull-up that is on only while the key was released (hysteresis). | High |
| RGB | **One IS31FL3733** at 7-bit **0x50** (8-bit 0xA0) on **I2C1: PB6 = SCL, PB7 = SDA, AF4, 400 kHz**. **PC13** = SDB/LED-enable (active high). 63 LED positions (61 ANSI + 2 ISO), 12 SW × 16 CS. | High |
| SPI1, DMA1 Ch2/3, EXTI1/2, I2C2 | **Not used.** These are CubeMX IRQ stubs. Their clocks are never enabled and their handles are never initialised. | High |
| USB | 4 HID interfaces, all `bInterval = 1` (1000 Hz). The Razer 90-byte feature report is on **interface 2**. D+ pull-up is the **internal one, `SYSCFG_PMC.USB_PU`**. | High |
| IWDG | Started by the app in software: prescaler /4, reload 0xFFF (~0.44 s). Refreshed in the main loop. | High |
| Data EEPROM | Three CRC16-protected blocks at `0x08080000` (49 B), `0x08080100` (38 B) and `0x08080300` (14 B). Profiles and macros live in **flash** at `0x08022000` and `0x08027000–0x0803FFFF`. | High |

---

## 1. Bootloader entry (priority #1)

### 1.1 What the app does (exact)

`enter_razer_bootloader` @ **0x0800935C** (raw listing; Ghidra's decompiler drops the store because the function
never returns):

```
0800935c  cpsid   i
0800935e  ldr     r1, =0x20007FFC
08009360  mov.w   r0, #0xAAAAAAAA
08009364  str     r0, [r1]                 ; *(u32*)0x20007FFC = 0xAAAAAAAA
08009366  dsb     sy
0800936a  ldr     r0, =0xE000ED0C          ; SCB->AIRCR
0800936c  ldr     r1, [r0]
0800936e  ldr     r2, =0x05FA0004          ; VECTKEY | SYSRESETREQ
08009370  and     r1, r1, #0x700           ; keep PRIGROUP
08009374  orrs    r1, r2
08009376  str     r1, [r0]
08009378  dsb     sy
0800937c  b       .                        ; wait for reset
```

* The magic location is the **last 32-bit word of the 32 KB SRAM**, `0x20007FFC`. The app's initial SP is
  `0x20006998`, and the app's linker map never uses `0x20006998–0x20007FFF`. That keeps the area free for the
  bootloader handshake. (High)
* The app never touches RTC backup registers, option bytes or the bootloader flash (`0x08000000–0x08003FFF`).
  Data EEPROM is not part of the handshake: nothing is written to EEPROM on this path. (High)
* The only other software reset in the app is `deferred_save_and_reset` (`0x0800D7B4`). It does a plain
  SYSRESETREQ **without** the magic and reboots into the app. It is used by command 0x00/0x0B arg0 = 0. (High)
* The bootloader side is **inferred**, because the bootloader is not in the updater package. It presumably checks
  `*(u32*)0x20007FFC == 0xAAAAAAAA`, clears it, and stays in its USB DFU mode (`1532:110E`). SRAM survives a system
  reset on STM32L1. (Medium. This needs confirmation by dumping `0x08000000` via SWD, if RDP allows.)

### 1.2 How it is reached (Razer 90-byte protocol)

The path is `USBD_HID_EP0_RxReady` @ `0x0800838C`. It takes a SET_REPORT (`bmRequestType` 0x21, `bRequest` 0x09)
with `wValue` high byte = 3 (Feature), `wIndex` = **2** and `wLength` = **0x5A**. It copies the 90 bytes to
`0x20000C60` and calls `razer_cmd_dispatch` (`0x0800D3B4`) **inside the USB interrupt**.

The buffer layout is the OpenRazer one:

| byte | 0 | 1 | 2-3 | 4 | 5 | 6 | 7 | 8..87 | 88 | 89 |
|---|---|---|---|---|---|---|---|---|---|---|
| field | status | transaction id | remaining | proto | data_size | **class** | **id** | args | CRC (XOR of 2..87) | 0 |

Validation done by the firmware:

* The incoming CRC is **not checked**. The CRC is only computed for the response.
* The transaction ID is not checked.
* The report must arrive on interface 2 with length exactly 90.

Class dispatch:

| Class | Handler |
|---|---|
| 0x00 | `0x0800CD40` device |
| 0x02 | `0x0800C610` key/debounce settings |
| 0x03 | `0x0800CF24` LED (refused in demo mode) |
| 0x05 | `0x0800D464` profiles |
| 0x06 | `0x0800D054` storage/macros |
| 0x0F | `0x0800C948` matrix effects (refused in demo mode) |
| 0xF0 | `0x0800D604` raw flash and EEPROM read/write, **only when device mode == 2** |

Class 0x00 (`0x0800CD40`) commands:

| id | meaning |
|---|---|
| 0x02 / 0x82 | set / get 22-byte serial (EEPROM block A + 6) |
| **0x04** | **set device mode** (`arg0` = mode, `arg1` = param). The mode is stored at `0x2000029D`. **mode 0x01 → `enter_razer_bootloader`** (call at `0x0800CE84`). Mode 0x03 = driver mode. Mode 0x02 = factory mode (unlocks class 0xF0). |
| 0x84 | get device mode |
| 0x06 / 0x86 | set / get 2 bytes at EEPROM block A + 4/5 |
| 0x81 / 0x87 | firmware version (`01 0C 00 00` = 1.12.00) |
| 0x83 | returns `00 60` (unknown) |
| 0x0B | arg0 = 0 → reboot (no magic). arg0 = 1, arg1 = 0 → reset lighting/profile block. arg0 = 1, arg1 = 1 → full factory reset. |

The official updater does the same. `FWUpdaterDLL.dll!EnterDeviceMode` (`0x10002AF0`, x86) builds a 91-byte
feature report (report ID 0) with:

* transaction id = 0
* data_size = 2
* class = 0x00
* id = 0x04
* arg0 = mode, arg1 = 0

It also exports `DFUErase`, `DFUProgram`, `DFUVerify` and `DFUExit` for the bootloader side, which is not analysed
here.

Exact packet to enter the bootloader (90 bytes, report ID 0 prepended on Windows):

```
00 1F 00 00 00 02 00 04 01 00  [78 x 00]  07 00      ; CRC = 02^00^04^01 = 0x07
```

**Do not send this from the analysis host while the keyboards are attached.** Documented for later, deliberate use
only. Expect the SET_REPORT to fail on the host side: the MCU resets inside the data-stage callback, before the
status stage.

### 1.3 What QMK must do

```c
// keyboards/razer/huntsman_mini/huntsman_mini.c  (BOOTLOADER = custom)
void bootloader_jump(void) {
    __disable_irq();
    *(volatile uint32_t *)0x20007FFCU = 0xAAAAAAAAU;   // Razer bootloader stay-in-DFU magic
    __DSB();
    NVIC_SystemReset();                                   // AIRCR = 0x05FA0004
}
```

* Keep QMK's linker map from relying on `0x20007FFC`. The safest option is to end `ram0` at `0x20007FF0`. QMK only
  writes the word right before reset, but reserving it removes any chance of an accidental match.
* An optional "official-updater recovery" path: if QMK keeps VID/PID `1532:0257` and answers a 90-byte feature report
  on interface 2 with class 0x00 / id 0x04 / arg0 = 1, then Razer's updater could put the board back into its
  bootloader by itself.

---

## 2. Boot-time behaviour

Reset path: `Reset_Handler` (`0x0800413C`) → `SystemInit` (`0x08007FE0`) → `__scatterload` (`0x080041C4`) →
`main` (`0x0800C2C4`). `SystemInit` resets the RCC to MSI defaults and sets **`SCB->VTOR = 0x08004000`**.
Nothing else happens before `main`.

`main` order:

1. `HAL_Init`: NVIC grouping 4 bits pre-emption; enables the COMP, SYSCFG and PWR clocks.
2. `SystemClock_Config`
3. `MX_GPIO_Init`
4. `MX_ADC_Init` (PA0)
5. `MX_I2C1_Init`
6. `MX_IWDG_Init`
7. `MX_TIM3_Init`
8. `settings_load_from_eeprom`
9. `detect_layout_PA0adc_PA1`
10. `lamparray_load_positions`
11. `matrix_gpio_init` and `matrix_state_init`
12. `matrix_attach_scan_isr`
13. **`boot_combo` check**
14. `leds_hw_init`
15. `MX_USB_DEVICE_Init`
16. Busy-wait (kicking the IWDG) until USB is configured.
17. **Start TIM3**, so the matrix scan starts only after enumeration.
18. Main loop.

Findings:

* **No bootloader key-combo and no magic check in the app.** The only power-on key check is `0x0800A0C0`. It scans
  all rows once and compares them with the pattern at `0x08011986` = `FF FE FF FF FE FF FF F7` (active low), which
  is **Esc + Caps Lock + Space**. If they match, it **toggles a persistent "demo/test" flag**: EEPROM block B
  byte `0x22` (`0x08080122`) = `0x55` ('U'). In that mode the board scans and lights up without a USB host, and LED
  commands from the host are refused. This is not the bootloader. (High)
* **No self-CRC or signature of the app image.** The CRC peripheral is never referenced. `crc16_ccitt`
  (`0x08009DB8`, poly 0x1021, init 0xFFFF) is only used on the EEPROM blocks and on the flash profile and macro
  records. The app never reads `0x08000000–0x08003FFF`. (High)
* **Option bytes, RDP, UID and DBGMCU are never touched.** There is no OPTKEY (`0xFBEAD9C8` / `0x24252627`), no
  `FLASH_OBR` read, and no `0x1FF80000`, `0x1FF800D0` or `0xE0042000` access. The PEKEY and PRGKEY are used only
  for data EEPROM and app-data flash writes. The RDP level is unknown and needs SWD. (High)
* The layout/SKU strap (`0x0800B98C`) reads the ADC on PA0 (10-bit; thresholds 128 and 511 counts) and the GPIO
  level of PA1:

  | Code | ADC on PA0 | PA1 | Meaning |
  |---|---|---|---|
  | 1 | low | 0 | ANSI, 61 lamps (Medium) |
  | 2 | low | 1 | ISO, 62 lamps (Medium) |
  | 3 | high | 0 | unknown |
  | 4 | high | 1 | unknown |
  | 5 | mid | 0 | unknown |

  The code is used for the Windows Dynamic Lighting (LampArray) layout only.

---

## 3. Clock tree (`SystemClock_Config` @ 0x08007F5C, `HAL_RCC_*`)

| Setting | Value | Evidence |
|---|---|---|
| PWR_CR.VOS | `01` = **Range 1, 1.8 V** | `PWR_CR = (PWR_CR & ~0x1800) \| 0x0800` |
| Oscillators | HSE **ON (crystal, not bypass)**, HSI ON (needed by the ADC), LSI ON (IWDG), LSE off | OscInit.OscillatorType = 0x0B, HSEState = 1. `RCC_CR \|= HSEON` path at `0x080065E4`. The bypass path (`HSEState == 5`) is not taken. |
| HSE frequency | **12 MHz** | Compiled `HSE_VALUE` = 12000000 in `HAL_RCC_GetSysClockFreq` (`0x080064D4`). 12 MHz × 8 = 96 MHz, which the PLLVCO must be for USB. GPIOH clock enabled (PH0/PH1 = OSC_IN/OUT). |
| PLL | SRC = HSE (`0x00010000`), **MUL = ×8** (`0x000C0000`), **DIV = /3** (`0x00800000`) → 96 MHz VCO, 32 MHz out, USB 48 MHz | OscInit.PLL fields |
| SYSCLK, HCLK, PCLK1, PCLK2 | **32 MHz** each (SW = PLL, HPRE/PPRE1/PPRE2 = /1) | ClkInit = {0x0F, 3, 0, 0, 0} |
| Flash | `ACR = ACC64 \| LATENCY=1` (1 WS), **no PRFTEN** | `HAL_RCC_ClockConfig(&clk, FLASH_LATENCY_1)` writes ACR \|= 4 then LATENCY |
| SysTick | 1 kHz (HCLK/1000), priority 1. In USB suspend it is re-programmed to 20 Hz. | `0x08007FC8`, `suspend_handler` |
| MCU package | **LQFP64 (STM32L151RC)** — Medium | PC6–PC9 are used (they exist only on packages of 64 pins or more). The GPIOD clock is enabled. |

---

## 4. Pin map

| Pin | Function | Stock configuration | Evidence | Conf. |
|---|---|---|---|---|
| PA0 | ADC_IN0, SKU/layout analog strap | Analog | `HAL_ADC_MspInit` `0x080046C4` (pin 0x0001, mode 3). ADC ch0, 10-bit. Read once in `0x0800B98C`. | High |
| PA1 | Layout digital strap | Input pull-up | `MX_GPIO_Init` (GPIOA mask 0x8702, input, PU). `GPIOA_IDR & 2` at `0x0800B99C`. | High |
| PA8, PA9, PA10, PA15 | **Matrix cols 4–7** (sense) | Input-PU in MX_GPIO_Init, then output-high / input toggled by the scan | Col table `0x08010420`. `GPIOA_IDR` bits 8–10 and 15 in `0x0800BA7E`. | High |
| PA11, PA12 | USB DM/DP | Default. D+ pull-up via **`SYSCFG_PMC.USB_PU`** | `HAL_PCDEx_SetConnectionState` `0x08005764`, called from `USBD_LL_Start` | High |
| PA13, PA14 | SWDIO, SWCLK | Never reconfigured, so SWD stays usable | No MODER writes | High |
| PB0, PB1, PB10, PB11, PB12, PB13, PB14, PB15 | **Matrix rows 0–7** (drive, active LOW) | Output push-pull, very high speed, idle HIGH | `WritePin(GPIOB,0xFC03,1)` and `Init(OUTPUT_PP)` in `0x08007960`. Row table `0x080103C0`. BSRR in the scan ISR. | High |
| PB6 | I2C1_SCL | AF4, open-drain, internal pull-up, very high speed | `HAL_I2C_MspInit` `0x0800540C` (pins 0xC0, mode 0x12, AF 4) | High |
| PB7 | I2C1_SDA | Same as PB6 | Same as PB6 | High |
| PC0 | Unknown (strap?) | Input pull-up. **Never read** in this build. | `MX_GPIO_Init` (GPIOC mask 0x3C1) | High (unused) |
| PC6, PC7, PC8, PC9 | **Matrix cols 0–3** (sense) | Same as PA8 etc. | `GPIOC_IDR` bits 6–9 (`ubfx #6,#4`) | High |
| PC13 | **IS31FL3733 SDB / LED enable**, active high | Output PP. Low at init, pulsed low 10 ms then high 5 ms before chip init. Low in suspend. | `led_enable_PC13_write` `0x0800BDC4`, `leds_hw_init` `0x0800B2C0`, `leds_suspend_resume` `0x0800BE1C` | High (pin). Medium ("SDB" rather than a power FET) |
| PH0, PH1 | 12 MHz HSE crystal | — | GPIOH clock enabled, HSE on | Medium |
| PB10, PB11 as I2C2 | **Not used.** The `HAL_I2C_MspInit` branch for I2C2 is dead code, because `hi2c2` (`0x2000604C`) is never initialised. | — | — | High |

Free and unused pins: PA2–PA7, PB2–PB5, PB8, PB9, PC1–PC5, PC10–PC12, PC14, PC15, PD2.

Peripheral clocks the app enables:

* GPIOA, B, C, D and H
* SYSCFG
* ADC1
* I2C1 (I2C2 only in the dead MSP branch)
* USB
* TIM3
* PWR
* COMP

**SPI1 and DMA1 clocks are never enabled.**

---

## 5. Key matrix (optical switches)

### 5.1 Topology

8 drive rows × 8 sense cols = 64 positions. 63 are used (61 ANSI + ISO `#` + ISO `\`).

The 8×8 table at `0x08010380` maps `[row][col]` to a Razer/IBM "key number". Labels:

| Row | Pin | C6 (c0) | C7 (c1) | C8 (c2) | C9 (c3) | A8 (c4) | A9 (c5) | A10 (c6) | A15 (c7) |
|---|---|---|---|---|---|---|---|---|---|
| r0 | B0 | 0 | ] | Bksp | - | = | P | [ | \ |
| r1 | B1 | Esc | W | E | R | T | Y | U | 9 |
| r2 | B10 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 |
| r3 | B11 | Tab | Q | D | F | G | H | I | O |
| r4 | B12 | Caps | A | S | J | K | L | ; | ' |
| r5 | B13 | C | V | RShift | Enter | / | ISO # | ISO \ | — |
| r6 | B14 | LShift | Z | X | B | N | M | , | . |
| r7 | B15 | LCtrl | LGUI | LAlt | Space | RAlt | **Fn** | App | RCtrl |

Raw key numbers, ready-made QMK `LAYOUT` input, the LED table and `g_led_config` are in
`re/firmware/tables_v1_12.txt` and `re/firmware/qmk_snippets_v1_12.c`.

### 5.2 Scan algorithm (stock)

TIM3 runs at prescaler `SystemCoreClock/1e6 - 1` (= 31) and ARR 124, so it fires **every 125 µs** (NVIC priority 2).
`HAL_TIM_PeriodElapsedCallback` (`0x08006F5C`) calls `matrix_scan_one_row_isr` (`0x0800B9FC`). Each call does the
following:

1. Return unless USB is configured and not suspended (or the demo flag is set).
2. With interrupts disabled: for every column, set the pull-up **only if the stored state says the key is
   released** (`PUPDR` = 01 if released, 00 if pressed). This is press/release hysteresis. Then switch the
   columns from output (driven HIGH = precharged) to input.
3. Busy-wait ~100 loop iterations (~12 µs at 32 MHz) and read `GPIOC_IDR` bits 6-9 and `GPIOA_IDR` bits 8-10 and 15.
   LOW = pressed.
4. Deselect the current row (HIGH), re-enable interrupts, switch the columns back to outputs driven HIGH.
5. Store the row if it changed (the first 8 ticks after start are discarded), advance to the next row and
   **select it (LOW) at the end of the ISR**, so each row's IR emitters settle for a full 125 µs tick before
   that row is read.

The blocking variants (`matrix_read_row_blocking` @ `0x0800BB58`, used at boot) do the same with a ~1000-iteration
settle after selecting the row. The QMK port (`qmk/keyboards/razer/huntsman_mini/matrix.c`) replicates this in a
blocking scan: select row, `wait_us(125)`, set hysteresis pull-ups, columns to input, 12 µs sample, read,
deselect, precharge.

---

## 6. RGB LEDs (IS31FL3733)

`leds_hw_init` (`0x0800B2C0`) → `is31fl3733_init_or_shutdown`:

1. PC13 (SDB) LOW for 10 ms, then HIGH, wait 5 ms.
2. Unlock (`0xFE` = `0xC5`), page 3 (function registers): Configuration `0x00` = `0x05` (normal operation),
   Global Current `0x01` = `0xFF`, SW pull-up `0x0F` = `0x07` (32 kΩ), CS pull-down `0x10` = `0x07` (32 kΩ).
3. Page 1 (PWM): all 192 bytes 0.
4. Page 0 (LED on/off): all 24 bytes `0xFF` (every channel enabled).
5. Leave page 1 selected for PWM updates.

The 63-entry channel map (key → SWr/SWg/SWb, CS) is in `qmk/gen_keyboard.py` (`LEDS`). Colors verified on
hardware with R = SW(3k+2), G = SW(3k+1), B = SW(3k+3).

## 7. USB

Four HID interfaces, all `bInterval = 1`. Interface 2 carries the Razer 90-byte feature report. The D+ pull-up is
the STM32L1 internal one (`SYSCFG_PMC.USB_PU`, `HAL_PCDEx_SetConnectionState` @ `0x08005764`).

## 8. Flash and data EEPROM usage

- App code: `0x08004000`-`0x08011FBB`. A second, identical copy of the app sits at `0x08013000`.
- Profiles/macros in flash at `0x08022000` and `0x08027000`-`0x0803FFFF`.
- Data EEPROM: CRC16-protected blocks at `0x08080000` (49 B: serial at +6), `0x08080100` (38 B) and
  `0x08080300` (14 B).

## 9. QMK port implications (as implemented)

- Clock: HSE 12 MHz, PLL ×8 /3 → 32 MHz, VOS range 1, 1 WS. **Flash prefetch must stay off** (the stock
  firmware leaves it off; with it on, the first fetch after waking from WFI was corrupted → hard fault).
- Matrix: custom (`matrix_pins.custom_lite`), see §5.
- RGB: QMK `is31fl3733` driver at `0x50`, SDB = C13, 32 kΩ pull-up/down, global current `0xFF`.
- I2C1 PB6/PB7 AF4 with internal pull-ups, 400 kHz (I2Cv1).
- Data EEPROM through a small custom driver; initialise it before USB starts (EEPROM writes stall the CPU).
- Bootloader: with the Razer bootloader intact, `bootloader_jump()` would write `0xAAAAAAAA` to `0x20007FFC`
  and reset (§1). On the board this port was developed on, the Razer bootloader is gone and QMK starts the STM32
  factory USB DFU bootloader instead (see `../NOTES.md`).
