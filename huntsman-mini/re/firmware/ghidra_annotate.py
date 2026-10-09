"""Apply the names/comments learned during RE to the Ghidra project and re-export a named decompilation.

Run after ghidra_setup.py:   python ghidra_annotate.py
Outputs: decomp_hm_v1_12_named.c, listing_hm_v1_12_named.txt (next to this script)
"""
from pathlib import Path

import pyghidra

HERE = Path(__file__).resolve().parent
PROG = "hm_v1_12"

FUNCS = {
    0x0800413C: "Reset_Handler", 0x08007FE0: "SystemInit_VTOR_0x08004000", 0x080041C4: "__scatterload",
    0x0800C2C4: "main", 0x080055AC: "HAL_Init", 0x080055EC: "HAL_MspInit",
    0x08007F5C: "SystemClock_Config_HSE12M_PLLx8_div3_32MHz", 0x08006560: "HAL_RCC_OscConfig",
    0x080062CC: "HAL_RCC_ClockConfig", 0x080064D4: "HAL_RCC_GetSysClockFreq", 0x08007EC8: "RCC_SetFlashLatencyFromMSIRange",
    0x08007960: "MX_GPIO_Init", 0x080078FC: "MX_ADC_Init_PA0", 0x08004540: "HAL_ADC_Init",
    0x080046C4: "HAL_ADC_MspInit_PA0_analog", 0x080043F0: "HAL_ADC_ConfigChannel", 0x080047AE: "HAL_ADC_Start",
    0x08004708: "HAL_ADC_PollForConversion", 0x08004538: "HAL_ADC_GetValue", 0x08008E04: "adc_read_PA0_10bit",
    0x08007A3C: "MX_I2C1_Init_400k", 0x0800502C: "HAL_I2C_Init", 0x0800540C: "HAL_I2C_MspInit_PB6_PB7",
    0x080053AC: "HAL_I2C_MspDeInit", 0x08004D10: "HAL_I2C_DeInit", 0x080052F4: "HAL_I2C_Master_Transmit_IT",
    0x080051C0: "HAL_I2C_Master_Transmit", 0x08007A84: "MX_IWDG_Init_pr4_rl4095", 0x08005540: "HAL_IWDG_Init",
    0x08007AB4: "HAL_IWDG_Refresh", 0x08007AC0: "MX_USB_DEVICE_Init", 0x0800F714: "MX_TIM3_Init_125us",
    0x0800F790: "tim3_start_it", 0x0800F7B0: "tim3_stop_or_start", 0x08006F5C: "HAL_TIM_PeriodElapsedCallback",
    0x08006DBC: "HAL_TIM_Base_Init", 0x08006DF4: "HAL_TIM_Base_Start_IT",
    0x0800B450: "settings_load_from_eeprom", 0x0800B98C: "detect_layout_PA0adc_PA1",
    0x0800B25C: "lamparray_load_positions", 0x0800B128: "matrix_gpio_init", 0x0800B184: "matrix_state_init",
    0x0800BD34: "matrix_attach_scan_isr", 0x0800B9FC: "matrix_scan_one_row_isr", 0x0800B958: "matrix_all_rows_high",
    0x0800BB58: "matrix_read_row_blocking", 0x0800BC0C: "matrix_changed_blocking", 0x0800BCF0: "matrix_suspend_rows",
    0x0800B76C: "matrix_debounce_1ms", 0x0800B8E0: "key_event", 0x0800DA10: "key_action_dispatch",
    0x0800C4B0: "key_action_internal_fn", 0x0800A0C0: "boot_combo_esc_caps_space_toggle_demo",
    0x0800A160: "is_demo_mode", 0x0800B2C0: "leds_hw_init", 0x0800BDC4: "led_enable_PC13_write",
    0x08009668: "is31fl3733_init_or_shutdown", 0x08009838: "is31_write_reg", 0x0800984A: "is31_write_buf",
    0x0800AFF4: "i2c1_write_reg_buf", 0x0800BE5C: "leds_flush", 0x08009D1C: "leds_indicator_overlay",
    0x08009928: "leds_compose_pwm_frame", 0x08009234: "frame_set_key_rgb", 0x0800BDDC: "leds_retry_init",
    0x0800BE1C: "leds_suspend_resume", 0x0800BEDC: "effects_tick_1ms", 0x0800D3B4: "razer_cmd_dispatch",
    0x0800CD40: "razer_cmd_class00_device", 0x0800C610: "razer_cmd_class02", 0x0800CF24: "razer_cmd_class03_led",
    0x0800D464: "razer_cmd_class05_profiles", 0x0800D054: "razer_cmd_class06_storage",
    0x0800C948: "razer_cmd_class0F_matrix_fx", 0x0800D604: "razer_cmd_classF0_factory_memrw",
    0x0800935C: "enter_razer_bootloader_magic_AAAAAAAA_at_20007FFC", 0x0800D6A4: "deferred_save_and_reset_SOF",
    0x0800E794: "request_save", 0x08009DB8: "crc16_ccitt_ffff", 0x0800A420: "data_eeprom_write",
    0x0800AB1C: "flash_write_pages", 0x08008510: "USBD_HID_Setup", 0x0800838C: "USBD_HID_EP0_RxReady",
    0x08008438: "USBD_HID_EP0_TxSent", 0x08008480: "USBD_HID_Init", 0x0800834C: "USBD_HID_DeInit",
    0x08008AE8: "USBD_HID_SOF", 0x08008460: "USBD_HID_GetCfgDesc", 0x08008474: "USBD_HID_GetDevQualDesc",
    0x08005764: "HAL_PCDEx_SetConnectionState_SYSCFG_PMC_USB_PU", 0x08006120: "HAL_PCD_MspInit",
    0x080061A0: "usb_remote_wakeup", 0x0800DC94: "lamparray_feature_handler", 0x0800FDA4: "suspend_handler",
    0x0800F6A8: "tasks_1ms", 0x0800FF08: "usb_configured_reinit", 0x0800F5D0: "flash_records_scan_08027000",
    0x08004D00: "HAL_GetTick", 0x0800559C: "HAL_IncTick", 0x08004918: "HAL_Delay", 0x08004B60: "HAL_GPIO_Init",
    0x08004CF4: "HAL_GPIO_WritePin", 0x08004A40: "HAL_GPIO_DeInit", 0x080056C0: "HAL_NVIC_SetPriority",
    0x080056A8: "HAL_NVIC_EnableIRQ", 0x08005692: "HAL_NVIC_DisableIRQ", 0x08005700: "HAL_NVIC_SetPriorityGrouping",
    0x08006D8C: "HAL_SYSTICK_Config", 0x0800AFC8: "gpio_moder_input", 0x0800AFD6: "gpio_moder_output",
    0x0800AFEA: "gpio_bsrr", 0x0800629C: "HAL_PWR_EnterSLEEPMode", 0x08004160: "memcpy", 0x08004192: "memzero",
    0x08004184: "memset_", 0x080041A8: "memcmp_", 0x08007AF8: "NVIC_SetPriority_raw",
    0x0800B6B0: "usb_configured_or_demo", 0x0800B6C8: "usb_suspended", 0x08004B34: "HAL_GPIO_EXTI_Callback",
    0x0800D7F4: "profile_select", 0x0800E794 + 0: "request_save", 0x08008200: "usbd_serial_string",
    0x080081D8: "usbd_product_string", 0x080081BC: "usbd_manufacturer_string",
}
LABELS = {
    0x20000C60: "razer_report_90", 0x20000CB8: "razer_report_crc", 0x2000029D: "device_mode",
    0x200002A1: "save_flags", 0x20000374: "SystemCoreClock", 0x20005FF8: "hi2c1", 0x20006200: "htim3",
    0x20005AB8: "hiwdg", 0x20005AC4: "hadc", 0x20000285: "matrix_raw_rows", 0x20000990: "key_state_8x8x5",
    0x2000027E: "layout_id", 0x20004568: "is31_pwm_frame_192", 0x200064B0: "lamparray_frame_5x15_rgb",
    0x20000258: "usb_device_descriptor", 0x2000036C: "tim3_callback_ptr", 0x20000338: "profile_flash_base_ptr",
    0x20007FFC: "BOOTLOADER_MAGIC_WORD",
    0x08010380: "matrix_keynum_map_8x8", 0x080103C0: "matrix_row_pins", 0x08010420: "matrix_col_pins",
    0x08010657: "led_map_5x15_keynum_row_col_drv_R_G_B", 0x08010969: "keytable_base", 0x08010D59: "keytable_fn",
    0x08010310: "usb_config_descriptor", 0x080102F0: "hid_report_desc_table", 0x0801198E: "lamparray_attr_ansi",
    0x080119A4: "lamparray_attr_iso", 0x080119BA: "lamp_positions_ansi", 0x08011B65: "lamp_positions_iso",
    0x08011986: "boot_combo_pattern", 0x080104DB: "indicator_led_table", 0x08010484: "eeprom_blockA_defaults",
    0x080104B5: "eeprom_blockB_defaults", 0x08010480: "fw_version_bytes",
}
COMMENTS = {
    0x0800935C: "Razer cmd class 0x00 id 0x04 (set device mode) with arg0==0x01 lands here:\n"
                "cpsid i; *(u32*)0x20007FFC = 0xAAAAAAAA; DSB; AIRCR = VECTKEY|SYSRESETREQ; loop.\n"
                "(Ghidra's decompiler drops the RAM store because the function never returns - see listing.)",
    0x0800B9FC: "TIM3 update ISR (every 125 us) -> one matrix row per call; 8 rows -> 1 ms per full scan.",
}


def main():
    pyghidra.start()
    from ghidra.program.model.symbol import SourceType
    from ghidra.program.model.listing import CodeUnit
    project = pyghidra.open_project(str(HERE / "ghidra_proj"), "huntsman_mini")
    with pyghidra.program_context(project, "/" + PROG) as program:
        space = program.getAddressFactory().getDefaultAddressSpace()
        A = lambda x: space.getAddress(x)
        fm = program.getFunctionManager()
        st = program.getSymbolTable()
        listing = program.getListing()
        with pyghidra.transaction(program, "annotate"):
            for a, n in FUNCS.items():
                f = fm.getFunctionAt(A(a))
                if f is None:
                    from ghidra.app.cmd.function import CreateFunctionCmd
                    CreateFunctionCmd(A(a)).applyTo(program, pyghidra.task_monitor())
                    f = fm.getFunctionAt(A(a))
                if f is not None:
                    f.setName(n, SourceType.USER_DEFINED)
                else:
                    print("no function at", hex(a))
            for a, n in LABELS.items():
                st.createLabel(A(a), n, SourceType.USER_DEFINED)
            for a, c in COMMENTS.items():
                listing.setComment(A(a), CodeUnit.PLATE_COMMENT, c)
        program.save("annotate", pyghidra.task_monitor())
        import ghidra_setup_export as gx
        gx.export(program, pyghidra.task_monitor(), HERE, PROG + "_named")
    project.close()


if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(HERE))
    main()
