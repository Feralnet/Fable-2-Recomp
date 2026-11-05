# Fable II recomp — PORT CAPABILITY INVENTORY

**Why this page exists.** On 2026-11-04 we spent hours rediscovering tools the port already
had — an AV probe, a guest function tracer, a UI state classifier, a focus-free synthetic
gamepad, a screenshot channel — each found by accident, late, after the problem it would
have answered had already been solved the hard way. Marcus, verbatim:

> *"can we make sure we know what all we have access to in the port i feel like we're just
> finding tools we should have had ages ago"*

**This page is the answer. Read it BEFORE diagnosing anything in this port.** If a capability
below covers your problem, using it is not optional — re-deriving it by hand is the waste
this page exists to prevent. When you add a tool, add it here in the same pass.

---

## 1. Input & control — drive the game with no human and no focus

| capability | what it is | use when |
|---|---|---|
| `src/input/remote_control_server.h` | **localhost TCP JSON-lines server** (`127.0.0.1:8791`, tries 8791–8799). Commands: `ping info auth press release stick state clear script get_state screenshot cvar enable disable` | **any** test that needs to reach gameplay, press a button, or change a cvar live |
| `src/input/remote_gamepad_driver.h` | synthetic XInput pad fed by the server. **NOT gated on window focus** — *"the AI harness must be able to drive the game even while the window is not in the foreground"*. OR-merges with the real pad, so a human can play while inputs inject | reaching menus/cutscenes/gameplay with **no operator and no focus steal** |
| `src/input/remote_input_state.h` | the shared snapshot handoff (server → driver) | understanding the plumbing |
| `tools/fable2_control.py` | **CLI client.** `ping · press A --hold 120 · state --buttons A,RT --ly 1000 · get-state · cvar <name> · cvar set <name> <val> · screenshot <file.png> · script --file repro.json · raw '{...}'` | the normal way to talk to the server |
| `tools/remote_smoke.cmd` | smoke test: waits for the port, pings, presses, checks state, clears | first thing to run when a build's channel seems dead |
| `plans/ai-remote-input-control.md` | the full design + protocol reference. **§0 says Implemented & verified**, 37/37 protocol checks, and end-to-end proof that a synthetic `A` on the title drove a real screen transition | the authoritative spec |
| `src/input/keyboard_gamepad.h` | host keyboard → guest gamepad map (`keyboard_gamepad_map` in the config) | a human at the keyboard |
| `src/input/mouse_look.h` | direct mouse-to-camera look | mouse-look work; see `plans/plan-direct-mouse-1to1.md` |

> ### ⚠️ The gate that hid all of this
> `CMakeLists.txt:129` — `FABLE2_REMOTE_CONTROL` is defined **only when
> `CMAKE_BUILD_TYPE STREQUAL "Debug"`**. The comment is explicit: *"it must NOT ship in
> Release / RelWithDebInfo builds."* **Our working build is Release — so the entire remote
> channel, and its `screenshot`/`cvar`/`get_state` commands, are compiled out of it.**
> To use them, build Debug — or, for a *local test* build only, add `RelWithDebInfo` to that
> condition deliberately and record it as a patch. **Do not ship either.**

---

## 2. Capture & visual evidence

| capability | what it is | use when |
|---|---|---|
| `src/diagnostics/fable2_screenshot.h` | **guest-frame capture hotkey, marked "Release-safe"** | you need a frame and want it in a Release build |
| `src/diagnostics/fable2_frame_capture.h` | save the game's rendered frame as PNG | same, programmatic |
| remote `{"cmd":"screenshot","path":…}` | reads the renderer's guest output **from the GPU — captures the game's own frame even while other windows cover it** | automated capture during a test |
| `REX_PRESENT_DUMP_FINAL` (+ `_START/_EVERY/_COUNT`) | dumps the **finished back buffer** (post-effect, pre-Present) as PPM | **proving a present-path effect ran** — the guest-output capture cannot show this |
| `src/diagnostics/fable2_deadbeef_overlay.h` | host-side ImGui overlay drawing "DEADBEEF" | is the host overlay path alive at all? |
| `src/diagnostics/fable2_deadbeef.h` + `FABLE2_DEADBEEF` / `_EVERY` | "DEADBEEF" UI-**text** canary; `fable2_text_append.h` / `FABLE2_TEXT_APPEND` appends it to every UI text element | is this text the game's, or ours? |

---

## 3. Diagnosis — find out what it is actually doing

| capability | what it is | use when |
|---|---|---|
| `src/diagnostics/fable2_av_probe.h` | **app-side VEH that logs guest state at every access violation** | any AV/crash — this exists so you do not have to reconstruct it with `+seh` |
| `src/core/fable2_func_trace.h` + `FABLE2_FUNC_TRACE`, `_FILTER`, `_LOG`, `_SUBS_ONLY`, `_SUMMARY`, `FABLE2_TRACE_DELAY/DUR/FILTER/WINDOW` | **guest function-call tracing**; runner `tools/fable2-functrace.cmd` | **"does this code actually execute?"** — e.g. whether newly recompiled functions are ever entered |
| `src/diagnostics/fable2_stall_dump.h` | render-thread stall detector | suspected stalls/hangs on the present thread |
| `src/diagnostics/fable2_hotfuncs.h` + `FABLE2_HOTFUNCS` | hot-call counters | find the per-frame hot path |
| `src/diagnostics/fable2_state_probe.h` | **evidence-based UI state classifier** — exposed as the remote **`game_state`** | **know which screen you are on** (menu vs loading vs gameplay) — answers the "are we actually in the game?" question *mechanically* |
| `src/diagnostics/fable2_heap_scan.h` + `FABLE2_HEAP_SCAN`, `_PTR`, `_TIMES` | find a string/pointer in guest memory at runtime | locating a value without a debugger |
| `src/diagnostics/alloc_watch.h` | cross-module state for the table-zeroing monitor | allocation-integrity work |
| `src/diagnostics/fps_meter.h` / `fps_probe.h` + `FABLE2_FPS_METER` | per-frame rate meter; the second one was built to find the 30 fps cap | fps verification; see `docs/FPS_CAP_INVESTIGATION.md` |
| `REX_UI_DRAWERS_DETECT` | the drawer-walk hexdump used to prove the `+0x1E8` collision | present/drawer-walk investigation |
| `FABLE2_XAM_TRACE` | traces XAM (input/system) calls | input-path work |
| `src/core/fable2_address_scan.{h,cpp}` | makes the game's aligned address-space scan skip | address-scan hangs |

---

## 4. UI / text / rendering probes (an unusually deep suite)

| capability | what it is |
|---|---|
| `fable2_ui_render_probe.h` + `FABLE2_UIR*` (a large family: `_DELAY _DUR _FUNC_TRACE _SKIP _SUPPRESS` and the `_IN_*` input-capture set) | UI-render identification by timeline + ablation; captures the inputs of candidate UI-render functions |
| `fable2_ui_input_probe.h` | captures the **inputs** of candidate UI-render call sites |
| `fable2_ui_text_dump.h` / `fable2_text_probe.h` (`FABLE2_TEXT_PROBE`, `_DELAY`, `_DUR`) | crash-safe per-frame UI text list; runtime UI-widget tree probe |
| `fable2_glyph_probe.h` (`FABLE2_GLYPH_PROBE*`), `fable2_font_probe.h` (`FABLE2_FONT_PROBE*`), `fable2_list_dump.h` | glyph table + atlas UVs, glyph/character probes, safe text-object dumps |
| `fable2_menu_probe.h` | strong overrides for the main-menu input path |
| `fable2_modmenu.h` + `FABLE2_MODMENU`, `_SCANLOG` | replaces the main-menu "Downloadable Content" item with a mod menu (see `plans/main-menu-mod-item.md`) |
| `fable2_state_probe.h` | see §3 |
| `FABLE2_UISTRETCH`, `FABLE2_ULTRAWIDE`, `FABLE2_MOVE_X`, `FABLE2_UIFILL` | UI-stretch / ultrawide / layout knobs — the ultrawide work lives here |

---

## 5. Scripting & patch surfaces

| capability | what it is | use when |
|---|---|---|
| `src/core/fable2_f5_lua.h` | **F5 host command: run an external Lua file in the in-game Lua** | script a step from inside the game instead of from outside |
| `src/core/fable2_patches.h` / `.cpp` + `docs/patches.md` | runtime guest-image patch system (Xenia `patch.toml` format); `tools/apply_recomp_patches.py` mirrors them into emitted C++ | changing guest behaviour without touching `.text` |
| `src/core/hotfunc/*` + `docs/hotfunc_overrides.md` | **native reimplementations of hot guest functions** (frame, entity, player, refcount, subsystems, vblank `FrameLimiterWait`, `Yield`, zlib `NativeInflate`, `LookStickProcess`...) with `FABLE2_`-style override knobs; generator `tools/make_hotfunc_overrides.py` | perf work — read this before inventing a new hot path |
| `src/core/xex_verify.h`, `dir_manifest_heal.h` | startup integrity check; manifest healing | "the dump is wrong" problems |

---

## 6. Config & cvar surface

- **Config:** `fable2_config.toml` beside the exe, read every launch; missing keys fall back to
  built-in defaults; a syntax error is logged and shown in a dialog rather than fatal
  (`src/core/fable2_config.{h,cpp}`).
- **`[input] keyboard_gamepad_map`** — the host→guest pad map (`LMB:X,RMB:Y,…Escape:Pause,M:Select,…`).
- **The cvar names below exist in the binaries.** Any of them can be set from the environment,
  or live via the remote `cvar` command *when the remote channel is compiled in*.

```
FABLE2_DEADBEEF FABLE2_DEADBEEF_EVERY FABLE2_FONT_PROBE FABLE2_FONT_PROBE_EVERY
FABLE2_FPS_METER FABLE2_FUNC_TRACE FABLE2_FUNC_TRACE_FILTER FABLE2_FUNC_TRACE_LOG
FABLE2_FUNC_TRACE_SUBS_ONLY FABLE2_FUNC_TRACE_SUMMARY FABLE2_GLYPH_PROBE
FABLE2_GLYPH_PROBE_EVERY FABLE2_HEAP_SCAN FABLE2_HEAP_SCAN_PTR FABLE2_HEAP_SCAN_TIMES
FABLE2_HOTFUNCS FABLE2_MODMENU FABLE2_MODMENU_SCANLOG FABLE2_MOVE_X
FABLE2_PRIMARY_SLOT_REMAP FABLE2_TA_PROBE FABLE2_TA_SHIFT FABLE2_TEXT_APPEND
FABLE2_TEXT_APPEND_EVERY FABLE2_TEXT_PROBE FABLE2_TEXT_PROBE_DELAY FABLE2_TEXT_PROBE_DUR
FABLE2_TRACE_DELAY FABLE2_TRACE_DUR FABLE2_TRACE_FILTER FABLE2_TRACE_WINDOW
FABLE2_UIFILL FABLE2_UIR FABLE2_UIR_DELAY FABLE2_UIR_DUR FABLE2_UIR_FUNC_TRACE
FABLE2_UIR_IN FABLE2_UIR_IN_ADDRS FABLE2_UIR_IN_ANCHOR FABLE2_UIR_IN_BYTES
FABLE2_UIR_IN_CAP FABLE2_UIR_IN_DELAY FABLE2_UIR_IN_DUMP FABLE2_UIR_IN_DUR
FABLE2_UIR_IN_HITCAP FABLE2_UIR_IN_HOP FABLE2_UIR_IN_PAT FABLE2_UIR_IN_PATSCAN
FABLE2_UIR_IN_PERCAP FABLE2_UIR_IN_PTS FABLE2_UIR_IN_RATE FABLE2_UIR_IN_STRIDE
FABLE2_UIR_SKIP FABLE2_UIR_SUPPRESS FABLE2_UISTRETCH FABLE2_ULTRAWIDE FABLE2_XAM_TRACE
REX_LOG_LEVEL REX_UI_DRAWERS_DETECT
```
*(61 distinct tokens; this list was extracted mechanically and can be re-extracted the same way.)*

---

## 7. Tools & docs — what already exists

**`tools/`:** `fable2_control.py` (remote CLI) · `remote_smoke.cmd` · `fable2-functrace.cmd` ·
`run_profiler.cmd` · `crash_capture.cmd` · `fable2-uncapped.cmd` · `fable2.cmd` ·
`StartWithoutAudio.cmd` · `dump-guest.py` · `xref-guest.py` · `apply_recomp_patches.py` ·
`make_hotfunc_overrides.py` · `check_manifest_collisions.py` · `package_release.py` ·
`prepare_*.py`/`stage_*.py` · `bnk.lua` · `repro`

**`docs/`:** `FPS_CAP_INVESTIGATION.md` · `ICON_BUTTON_A_NOTES.md` · `patches.md` ·
`RUNTIME_FIXES.md` · `hotfunc_overrides.md` · `main_menu_crash_fix.md` ·
`two_controller_black_menu_fix.md` · `GERMAN_GOTY_SUPPORT.md` · `FABLE2_UPSCALING_SPIKE.md`
(our work) · `UPSTREAM-REPORT-presenter-layout-collision.md`

**`plans/` (11):** `ai-remote-input-control` · `plan-direct-mouse-1to1` · `main-menu-mod-item` ·
`disable-motion-blur` · `f5-guest-null-av` · `av-clean-builds` · `hero-dog-realtime-texture-morphing` ·
`hero-dog-shifty-texture-mipmap` · `hero-dog-texture-readback` · `process-game-frame-hand-tune`

**Build knobs seen in the working cache:** `FABLE2_BUILD_PROFILE` · `FABLE2_CODEGEN_TOOL` ·
`FABLE2_NO_PE_CLEAN` · `FABLE2_PROFILER_FRIENDLY` (option, §"Profiler-friendly build") ·
`REXGLUE_RECOMP_DEBUG_INFO` · `REXGLUE_SDK_ROOT`.

---

## 8. What this page would have saved, on 2026-11-04 alone

| problem we solved the hard way | tool that already existed |
|---|---|
| hours of chase on an `EXCEPTION_ACCESS_VIOLATION` | `fable2_av_probe.h` — a VEH that logs guest state at every AV |
| "do the 222 newly recompiled functions actually run?" — we were about to build coverage instrumentation | `FABLE2_FUNC_TRACE` — guest function tracing, with a runner script |
| "is this the menu or gameplay?" — the question that invalidated a day of tests | `fable2_state_probe.h` — a UI state classifier, exposed as the remote `game_state` |
| reaching gameplay with no operator input | the whole remote-control channel (§1) |
| "this box cannot screenshot" (a false conclusion that cost a mis-call) | `fable2_screenshot.h` ("Release-safe"), `fable2_frame_capture.h`, and the remote `screenshot` command |

---

## 9. The rule this page is really about

**Inventory a port's own capabilities before diagnosing anything in it.** Not after, not
alongside — first. A recomp port is usually the most heavily instrumented thing in the
project, because its author needed all of it; the instruments are the *cheap* path and
re-deriving them is the expensive one.

**When you next touch a different port, do this same pass on it and write the same page.**

---

## 10. Driving the menus with the remote pad — MEASURED 2026-11-04

Recorded because the port's own protocol doc does not cover menu gesture timing, and it cost
a long trial-and-error loop to learn. All of this is via `tools/fable2_control.py` on a
`RelWithDebInfo` build (the channel is `Debug`/`RelWithDebInfo` only — see the gate in §1).

**The path into the game, confirmed end to end with no human and no window focus:**
boot → *press-Ⓐ* prompt (`press A`) → **main menu** (`press A`) → **New Game** (`press A`) →
**gender select** (two hero cards) → the game.

| gesture | behaviour |
|---|---|
| **D-pad `Up`/`Down`** | **works for menu navigation** — use this |
| **left stick** (`StkLy` ±32767, and `StickUp`/`StickDown`) | **did not move the selection** in these menus |
| **`press X --hold 120`** | too short — **no movement** |
| **`press X --hold 300`** | **two steps** (~150 ms per step) |
| **`press X --hold 2500`** | runs to the **end** of the list and stops there |
| a press issued **while another button is still held** | **swallowed** — `clear` first |

So: to step *one* item, hold **between ~120 and ~300 ms** and make sure nothing else is held;
to reach a known end of a list, hold long and then step off it. `get-state` confirms what is
actually held — check it, because a long hold keeps the button down after the call returns.

**Reliable recipe for "get past the menus into gameplay":** press `A` on the menu (which
takes *New Game*), then `A` on the gender-select cards.

### The state classifier is not an oracle here

`fable2_control.py game-state` (documented states: `PreMainMenu` / `PressAScreen` /
`MainMenuMovie` / `MainMenu` / `?`) returned **`{"code":0,"name":"Unknown","front_end":"DefaultScenario"}`
for the entire session — 28 samples across a 140 s run, through the press-Ⓐ prompt, the main
menu, and gender select. **Do not treat it as a gate or a verification.** Use a frame.

### Capturing frames

`fable2_control.py screenshot <path>` writes the game's own guest output (1280×720) and works
while other windows cover it. The PNG is **uncompressed**, so **every capture is exactly
2,765,798 bytes** — constant size is expected and is *not* a sign of a stuck capture. `avg_luma`
in the reply is the real content signal.

**And when you look at a frame, ask neutrally — "What is on this screen?"** Naming the items
you expect, or offering a choice between hypotheses, biases the reading and produces
contradictory answers about the same screen. A neutral ask gives trustworthy *layout* and
unreliable *names* (it read this menu correctly while calling the game three different titles).
