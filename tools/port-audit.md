## Appendix A.1 — the port's own cvars (live-settable through the remote channel)

Count: **8**

| cvar | type | default | category |
|---|---|---|---|
| `f5_lua_path` | STRING | `"scripts/recomp/F5.lua"` | Input |
| `keyboard_gamepad_map` | STRING | `""` | Input |
| `mouse_look` | BOOL | `true` | Input |
| `mouse_look_scale` | INT32 | `256` | Input |
| `mouse_unlock_key` | STRING | `"F4"` | Input |
| `screenshot_dir` | STRING | `"screenshots"` | Diagnostics |
| `screenshot_key` | STRING | `""` | Diagnostics |
| `skipHash` | BOOL | `false` | Launch |

## Appendix A.2 — SDK cvars inherited by every build

Count: **237**. These are the emulator's own knobs and they are live-settable
through the same `cvar` command. Grouped by category.


### Audio

| cvar | default |
|---|---|
| `audio_maxqframes` | `8` |
| `audio_mute` | `false` |
| `ffmpeg_verbose` | `false` |

### Category

| cvar | default |
|---|---|
| `my_cmd` | `[]() { DoThing(); }` |
| `my_flag` | `false` |
| `my_int` | `42` |
| `my_string` | `"default"` |

### Clock

| cvar | default |
|---|---|
| `clock_no_scaling` | `false` |
| `clock_source_raw` | `false` |

### Codegen

| cvar | default |
|---|---|
| `backward_scan_limit` | `64` |
| `max_blocks_per_function` | `10000` |
| `max_discovery_iterations` | `1000` |
| `max_eh_ip_map_entries` | `200` |
| `max_eh_states` | `100` |
| `max_eh_try_blocks` | `50` |
| `max_file_size_bytes` | `1048576` |
| `max_jump_table_entries` | `512` |
| `max_resolve_iterations` | `100` |
| `max_seh_scope_entries` | `100` |
| `max_vtable_iterations` | `100` |
| `progress_log_frequency` | `100` |

### Console

| cvar | default |
|---|---|
| `echo` | `ConsoleEcho` |
| `find` | `ConsoleFind` |

### Debug

| cvar | default |
|---|---|
| `debug_overlay` | `false` |

### Display

| cvar | default |
|---|---|
| `resolution` | `""` |
| `video_mode_height` | `720` |
| `video_mode_refresh_rate` | `60.0` |
| `video_mode_width` | `1280` |

### Filesystem

| cvar | default |
|---|---|
| `allow_game_relative_writes` | `false` |
| `dump_path` | `""` |
| `dump_source` | `""` |

### GPU

| cvar | default |
|---|---|
| `anisotropic_override` | `3` |
| `async_pipeline_wait` | `true` |
| `async_pipeline_wait_timeout_ms` | `5000` |
| `async_shader_compilation` | `true` |
| `backend` | `"d3d12"` |
| `clear_memory_page_state` | `true` |
| `depth_float24_convert_in_pixel_shader` | `false` |
| `depth_float24_round` | `false` |
| `depth_transfer_not_equal_test` | `true` |
| `direct_host_resolve` | `true` |
| `draw_resolution_scale_x` | `1` |
| `draw_resolution_scale_y` | `1` |
| `dump_shaders` | `""` |
| `execute_unclipped_draw_vs_on_cpu` | `false` |
| `execute_unclipped_draw_vs_on_cpu_for_psi_render_backend` | `true` |
| `execute_unclipped_draw_vs_on_cpu_with_scissor` | `false` |
| `force_convert_line_loops_to_strips` | `false` |
| `force_convert_quad_lists_to_triangle_lists` | `false` |
| `force_convert_triangle_fans_to_lists` | `false` |
| `frame_limit` | `0` |
| `gamma_render_target_as_unorm16` | `true` |
| `gpu_3d_to_2d_texture` | `true` |
| `gpu_allow_invalid_fetch_constants` | `false` |
| `gpu_debug_markers` | `false` |
| `gpu_plugin` | `""` |
| `guest_vblank_pacing` | `true` |
| `half_pixel_offset` | `true` |
| `mrt_edram_used_range_clamp_to_min` | `true` |
| `native_2x_msaa` | `true` |
| `native_stencil_value_output` | `true` |
| `non_seamless_cube_map` | `false` |
| `occlusion_query_enable` | `true` |
| `pre_mask_resolve_l2_block` | `true` |
| `primitive_processor_cache_min_indices` | `0` |
| `query_occlusion_fake_sample_count` | `1000` |
| `readback_memexport` | `true` |
| `readback_memexport_fast` | `true` |
| `readback_memexport_fast_wait` | `true` |
| `readback_resolve` | `"none"` |
| `readback_resolve_force_addresses` | `""` |
| `readback_resolve_half_pixel_offset` | `true` |
| `resolution_scale` | `1` |
| `resolve_resolution_scale_fill_half_pixel_offset` | `true` |
| `scale` | `1` |
| `snorm16_render_target_full_range` | `true` |
| `store_shaders` | `true` |
| `swap_post_effect` | `"none"` |
| `texture_cache_memory_limit_hard` | `768` |
| `texture_cache_memory_limit_render_to_texture` | `24` |
| `texture_cache_memory_limit_soft` | `384` |
| `texture_cache_memory_limit_soft_lifetime` | `30` |
| `use_fuzzy_alpha_epsilon` | `false` |
| `vsync` | `true` |

### GPU/D3D12

| cvar | default |
|---|---|
| `d3d12_bindless` | `true` |
| `d3d12_dxbc_disasm` | `false` |
| `d3d12_dxbc_disasm_dxilconv` | `false` |
| `d3d12_pipeline_creation_threads` | `-1` |
| `d3d12_readback_memexport` | `false` |
| `d3d12_readback_resolve` | `false` |
| `d3d12_submit_on_primary_buffer_end` | `true` |
| `d3d12_tessellation_wireframe` | `false` |
| `d3d12_tiled_shared_memory` | `true` |
| `depth_bias_shader` | `""` |
| `depth_bias_shader_units` | `0` |
| `native_stencil_value_output_d3d12_intel` | `false` |
| `render_target_path_d3d12` | `""` |

### GPU/Shader

| cvar | default |
|---|---|
| `draw_resolution_scaled_texture_offsets` | `true` |
| `dxbc_source_map` | `false` |
| `dxbc_switch` | `true` |

### GPU/Vulkan

| cvar | default |
|---|---|
| `render_target_path_vulkan` | `""` |
| `vulkan_async_skip_incomplete_frames` | `true` |
| `vulkan_dynamic_rendering` | `true` |
| `vulkan_force_convert_quad_lists_to_triangle_lists` | `false` |
| `vulkan_force_expand_point_sprites_in_vs` | `false` |
| `vulkan_force_expand_rectangle_lists_in_vs` | `false` |
| `vulkan_pipeline_creation_threads` | `-1` |
| `vulkan_readback_memexport` | `false` |
| `vulkan_readback_resolve` | `false` |
| `vulkan_shared_memory_upload_first` | `false` |
| `vulkan_sparse_shared_memory` | `true` |
| `vulkan_submit_on_primary_buffer_end` | `true` |
| `vulkan_tessellation_wireframe` | `false` |

### Input

| cvar | default |
|---|---|
| `guide_button` | `false` |
| `hid_mappings_file` | `"gamecontrollerdb.txt"` |
| `input_backend` | `"sdl"` |
| `mnk_mode` | `false` |
| `mnk_mouse` | `false` |
| `mnk_sensitivity` | `1.0` |

### Input/Keybinds/Controller

| cvar | default |
|---|---|
| `keybind_dpad_down` | `"Shift+Down"` |
| `keybind_dpad_left` | `"Shift+Left"` |
| `keybind_dpad_right` | `"Shift+Right"` |
| `keybind_dpad_up` | `"Shift+Up"` |
| `keybind_guide` | `""` |
| `keybind_left_shoulder` | `"1"` |
| `keybind_lstick_down` | `"S"` |
| `keybind_lstick_left` | `"A"` |
| `keybind_lstick_press` | `"F"` |
| `keybind_lstick_right` | `"D"` |
| `keybind_lstick_up` | `"W"` |
| `keybind_right_shoulder` | `"3"` |
| `keybind_rstick_down` | `"Down"` |
| `keybind_rstick_left` | `"Left"` |
| `keybind_rstick_press` | `"K"` |
| `keybind_rstick_right` | `"Right"` |
| `keybind_rstick_up` | `"Up"` |
| `keybind_x` | `"L"` |
| `keybind_y` | `"P"` |

### Kernel

| cvar | default |
|---|---|
| `cl` | `""` |
| `diag_load_profile` | `false` |
| `diag_load_profile_sample` | `false` |
| `diag_stall_ms` | `250` |
| `diag_wait_min_ms` | `100` |
| `faster_loading` | `false` |
| `headless` | `false` |
| `idle_boost` | `16.0` |
| `idle_boost_window_s` | `30` |
| `ignore_thread_affinities` | `true` |
| `ignore_thread_priorities` | `true` |
| `kernel_cert_monitor` | `false` |
| `kernel_debug_monitor` | `false` |
| `kernel_pix` | `false` |
| `license_mask` | `0` |
| `load_timer` | `false` |
| `load_timer_quiet_s` | `5` |
| `load_timer_start_mb` | `20` |
| `log_high_frequency_kernel_calls` | `false` |
| `stall_boost` | `8.0` |
| `stall_boost_max_s` | `15` |
| `user_country` | `103` |
| `user_language` | `1` |

### Log

| cvar | default |
|---|---|
| `log_file` | `""` |
| `log_flush_interval` | `0` |
| `log_level` | `"info"` |
| `log_noisy` | `false` |
| `log_verbose` | `false` |

### Memory

| cvar | default |
|---|---|
| `protect_on_release` | `false` |
| `protect_zero` | `true` |
| `scribble_heap` | `false` |
| `writable_executable_memory` | `true` |

### Perf

| cvar | default |
|---|---|
| `perf_log_csv` | `""` |

### Runtime

| cvar | default |
|---|---|
| `cache_root` | `""` |
| `game_data_root` | `""` |
| `metadata_root` | `""` |
| `update_data_root` | `""` |
| `user_data_root` | `""` |

### Test

| cvar | default |
|---|---|
| `test_args_cmd` | `[](std::string_view a) { g_args_cmd_received = std::string(a); }` |
| `test_bool_flag` | `false` |
| `test_debug_flag` | `false` |
| `test_double_flag` | `3.14` |
| `test_enum_flag` | `"low"` |
| `test_init_only_flag` | `"initial"` |
| `test_int32_flag` | `42` |
| `test_int64_flag` | `1000000000LL` |
| `test_noarg_cmd` | `[]() { ++g_noarg_cmd_calls; }` |
| `test_ranged_flag` | `5` |
| `test_restart_flag` | `false` |
| `test_string_flag` | `"default"` |
| `test_uint32_flag` | `42u` |
| `test_uint64_flag` | `999999999999ULL` |
| `test_validated_flag` | `"valid"` |

### TestCategory

| cvar | default |
|---|---|
| `test_category_flag` | `"value"` |

### UI/D3D12

| cvar | default |
|---|---|
| `d3d12_adapter` | `-1` |
| `d3d12_allow_variable_refresh_rate_and_tearing` | `true` |
| `d3d12_break_on_error` | `false` |
| `d3d12_break_on_warning` | `false` |
| `d3d12_debug` | `false` |
| `d3d12_queue_priority` | `1` |

### UI/Presenter

| cvar | default |
|---|---|
| `host_present_from_non_ui_thread` | `true` |
| `pace_to_guest_vblank` | `false` |
| `present_allow_overscan_cutoff` | `false` |
| `present_cas_additional_sharpness` | `rex::ui::Presenter::GuestOutputPaintConfig::kCasAdditionalSharpnessDefault` |
| `present_dither` | `false` |
| `present_dump_final` | `""` |
| `present_dump_final_count` | `3` |
| `present_dump_final_every` | `0` |
| `present_dump_final_start` | `60` |
| `present_effect` | `"bilinear"` |
| `present_fsr_max_upsampling_passes` | `rex::ui::Presenter::GuestOutputPaintConfig::kFsrMaxUpscalingPassesMax` |
| `present_fsr_quality_mode` | `"auto"` |
| `present_fsr_sharpness_reduction` | `rex::ui::Presenter::GuestOutputPaintConfig::kFsrSharpnessReductionDefault` |
| `present_letterbox` | `true` |
| `present_render_pass_clear` | `true` |
| `present_safe_area_x` | `90` |
| `present_safe_area_y` | `90` |

### UI/Vulkan

| cvar | default |
|---|---|
| `vulkan_allow_present_mode_fifo_relaxed` | `true` |
| `vulkan_allow_present_mode_immediate` | `true` |
| `vulkan_allow_present_mode_mailbox` | `true` |
| `vulkan_device` | `-1` |
| `vulkan_log_debug_messages` | `true` |
| `vulkan_prefer_fill_mode_non_solid` | `true` |
| `vulkan_prefer_fragment_stores_and_atomics` | `true` |
| `vulkan_prefer_geometry_shader` | `true` |
| `vulkan_prefer_vertex_pipeline_stores_and_atomics` | `true` |
| `vulkan_require_fill_mode_non_solid` | `!REX_PLATFORM_MAC` |
| `vulkan_require_fragment_stores_and_atomics` | `true` |
| `vulkan_require_geometry_shader` | `!REX_PLATFORM_MAC` |
| `vulkan_require_vertex_pipeline_stores_and_atomics` | `true` |
| `vulkan_validation_enabled` | `false` |

### UI/Window

| cvar | default |
|---|---|
| `fullscreen` | `true` |
| `fullscreen_exclusive` | `false` |
| `monitor` | `0` |
| `video_driver` | `""` |
| `window_height` | `0` |
| `window_width` | `0` |

### crt

| cvar | default |
|---|---|
| `rexcrt_heap_enable` | `false` |
| `rexcrt_heap_size_mb` | `256` |

## Appendix A.3 — environment variables / debug probes

Count: **100**. These are **launch-time only** — they are read at startup, not
settable through the `cvar` command, and most must be present in the *title's*
environment (verify with `/proc/<pid>/environ`, not by assuming).

- `FABLE2_DEADBEEF`
- `FABLE2_DEADBEEF_EVERY`
- `FABLE2_DEADBEEF_LOG`
- `FABLE2_DEADBEEF_OVERLAY`
- `FABLE2_DEADBEEF_SCALE`
- `FABLE2_FONT_PROBE`
- `FABLE2_FONT_PROBE_EVERY`
- `FABLE2_FPS_METER`
- `FABLE2_FUNC_TRACE`
- `FABLE2_FUNC_TRACE_FILTER`
- `FABLE2_FUNC_TRACE_LOG`
- `FABLE2_FUNC_TRACE_SUBS_ONLY`
- `FABLE2_FUNC_TRACE_SUMMARY`
- `FABLE2_GLYPH_PROBE`
- `FABLE2_GLYPH_PROBE_EVERY`
- `FABLE2_HEAP_SCAN`
- `FABLE2_HEAP_SCAN_PTR`
- `FABLE2_HEAP_SCAN_TIMES`
- `FABLE2_HOTFUNCS`
- `FABLE2_MODMENU`
- `FABLE2_MODMENU_LOG`
- `FABLE2_MODMENU_SCANLOG`
- `FABLE2_MOVE_X`
- `FABLE2_MOVE_Y`
- `FABLE2_PRIMARY_SLOT_REMAP`
- `FABLE2_STATE_PROBE`
- `FABLE2_TA_ADV`
- `FABLE2_TA_CHAROFF`
- `FABLE2_TA_PROBE`
- `FABLE2_TA_SHIFT`
- `FABLE2_TA_XOFF`
- `FABLE2_TEXTOBJ_DUMP`
- `FABLE2_TEXT_APPEND`
- `FABLE2_TEXT_APPEND_EVERY`
- `FABLE2_TEXT_PROBE`
- `FABLE2_TEXT_PROBE_DELAY`
- `FABLE2_TEXT_PROBE_DUR`
- `FABLE2_TRACE_DELAY`
- `FABLE2_TRACE_DUR`
- `FABLE2_TRACE_FILTER`
- `FABLE2_TRACE_WINDOW`
- `FABLE2_UIFILL`
- `FABLE2_UIR`
- `FABLE2_UIR_DELAY`
- `FABLE2_UIR_DUR`
- `FABLE2_UIR_FUNC_TRACE`
- `FABLE2_UIR_IN`
- `FABLE2_UIR_IN_ADDRS`
- `FABLE2_UIR_IN_ANCHOR`
- `FABLE2_UIR_IN_BYTES`
- `FABLE2_UIR_IN_CAP`
- `FABLE2_UIR_IN_DELAY`
- `FABLE2_UIR_IN_DUMP`
- `FABLE2_UIR_IN_DUR`
- `FABLE2_UIR_IN_HITCAP`
- `FABLE2_UIR_IN_HOP`
- `FABLE2_UIR_IN_PAT`
- `FABLE2_UIR_IN_PATSCAN`
- `FABLE2_UIR_IN_PERCAP`
- `FABLE2_UIR_IN_PTS`
- `FABLE2_UIR_IN_RATE`
- `FABLE2_UIR_IN_STRIDE`
- `FABLE2_UIR_SKIP`
- `FABLE2_UIR_SUPPRESS`
- `FABLE2_UISTRETCH`
- `FABLE2_UI_TEXT_DUMP`
- `FABLE2_UI_TEXT_DUMP_END`
- `FABLE2_UI_TEXT_DUMP_FRAMES`
- `FABLE2_UI_TEXT_DUMP_INTERVAL`
- `FABLE2_UI_TEXT_DUMP_START`
- `FABLE2_ULTRAWIDE`
- `FABLE2_VC_DUMP`
- `FABLE2_VC_DUMP_EVERY`
- `FABLE2_VC_DUMP_HI`
- `FABLE2_VC_DUMP_LO`
- `FABLE2_VC_DUMP_PER_FRAME`
- `FABLE2_XAM_TRACE`
- `REX_LOAD_`
- `REX_LOAD_U16`
- `REX_LOAD_U32`
- `REX_LOAD_U64`
- `REX_LOAD_U8`
- `REX_LOG_LEVEL`
- `REX_MM_LOAD_`
- `REX_MM_LOAD_U16`
- `REX_MM_LOAD_U32`
- `REX_MM_STORE_`
- `REX_MM_STORE_U16`
- `REX_MM_STORE_U32`
- `REX_MM_STORE_U64`
- `REX_MM_STORE_U8`
- `REX_STORE_`
- `REX_STORE_U16`
- `REX_STORE_U32`
- `REX_STORE_U64`
- `REX_STORE_U8`
- `REX_TEST_INT32_FLAG`
- `REX_UI_DRAWERS_DETECT`
- `REX_UI_DRAWERS_FIX`
- `REX_VULKAN_SDK`

## Appendix A.4 — enum-valued cvars worth knowing

Values pulled from the source where the default is a choice, not a number.

| cvar | values |
|---|---|
| `draw_resolution_scale_x` | default `1` |
| `draw_resolution_scale_y` | default `1` |
| `gpu_plugin` | default `""` |
| `present_effect` | default `"bilinear"` |
| `present_effect` | `bilinear`, `cas`, `fsr`, `fsr2`, `fsr3` — **`cas`/`fsr*` are only accepted when the runtime is FSR-armed** |
