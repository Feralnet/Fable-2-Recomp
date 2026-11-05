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

**Reliable recipe for "get past the menus into gameplay":** hold a **sticky** `A` — NOT a
timed press (see the correction below).

**CORRECTION, measured 2026-11-04 ~22:02 — a timed press does not confirm, a sticky hold does.**
The table above is right about *navigation* and wrong about *confirmation*. Three separate
`press A --hold 250` calls against the title screen did **nothing** (returned `ok:true`, no
advance, verified by frame), while a single sticky `state --buttons A` held for 3 s took the
game off the menu and into its opening (the game's own log then shows
`[texture-morph] building hero/dog textures in realtime (GPU) mode` and
`[motion-blur] game requested full-screen motion blur 0.300`). So for a **confirm**, do not
tune a hold duration — set a sticky baseline, wait, and `clear`:

```bash
python3 tools/fable2_control.py state --buttons A   # sticky baseline
sleep 3
python3 tools/fable2_control.py clear
```

Open question, not yet measured: whether a *navigation* press at 120-300 ms really works or
whether those moves were also only visible because a sticky state was outstanding. Re-measure
before trusting the per-step timing above.

**Do not use the log's `[core]` SDL `OnControllerDeviceAdded` lines to judge whether our pad
reaches the guest.** Those are the HOST layer (real pads, e.g. an Xbox pad and a Valve
`0x28DE` device). Our pad is a rexglue `InputDriver` at the emulator's XInput layer
(`remote_gamepad_driver.h`), registered via `fable_2_app.h:133`, `info.synthetic = true`, and
it never appears in SDL's list — by design. Its absence there is not evidence of failure.

---

## 11. The state-detection probes do NOT work for this title — MEASURED 2026-11-04

This matters more than it looks: two purpose-built tools exist for reading the game's state,
both arm correctly, and **neither produces a usable answer on Fable II**. Anyone gating on
them is gating on a constant.

**How they arm.** They are **launch-time environment variables**, not cvars — setting one
through the control channel answers `{"ok":false,"error":"unknown cvar '<NAME>'"}`. They must
be present in the environment of the launched title, NOT the environment of a later command.

Prove they arrived by reading the game's own environment rather than assuming — find the wine
process holding the title and read its `/proc/<pid>/environ`. Both the `steam.exe` shim
process and the `Z:\...` title process carry them; the launcher script process does not.

**They write to the process CWD, which is NOT the exe dir.** Launching from a different working
directory puts the log in that directory (e.g. `~/fable2_state_probe.log`). Look there before
concluding a probe failed — the file existing elsewhere reads exactly like "no output".

**`FABLE2_STATE_PROBE` — inert.** Ran the whole session, one sample per second (197 samples),
and **every classifier field was constant at its default for the entire run**:

```
boot=196834ms  ?  (raw=?  pe=16 ui=993 ra=1 pa=0 menu=0 a_age=-1 a_btn=0 fe=v=DefaultScenario)
distinct values across 197 samples:  pa: pa=0   menu: menu=0   a_age: a_age=-1
                                     a_btn: a_btn=0   fe: fe=v=DefaultScenario
```

Only the counters `pe`/`ui`/`ra` move. The probe's own hunt line — `[fe-hunt] 0x40071545 holds
ptr to CAN_PRESS_A` — is still hunting: it has not located the flag it keys on. So the state
query returns `Unknown` **permanently, for this title**, while the game is demonstrably running
and rendering. Do not use it as a gate, a verification, or a synchronisation primitive.

**`FABLE2_UI_TEXT_DUMP` — never fires.** Armed and proven present in the title's environment,
and **no dump log was created anywhere** (checked the home dir, the exe dir, the launch dir,
and a filesystem search). Its hook does not trigger on this title. Do not count on it to read
the menus.

**What DOES work as an oracle.** The port log names real subsystems and real events — that is
how the state was actually established:

```
[texture-morph] building hero/dog textures in realtime (GPU) mode
[motion-blur]   game requested full-screen motion blur 0.300 (left on)
[ui-stretch]    2D display aspect (display path) = 1.777778, hook off
[ui-canvas]     guest display-area width = 1120 (call #1)
```

Together with `screenshot` + `avg_luma` (and a frame you actually look at), that is the working
way to know where the game is. `avg_luma` swinging hard between samples (32 → 132 → 2) is the
signature of an FMV cutting between shots.

**Tooling gotcha.** The lane guard string-matches terminal commands, so a command that merely
*mentions* a title launch (including one embedded in a heredoc while writing documentation) is
refused as an out-of-lane exec. Write docs with a file tool, not a shell heredoc.

---

## 12. The verified walk into gameplay — MEASURED 2026-11-04 22:2x

Repeatable, driven solo with nothing else touching the pad, no human input, no keyboard. Every
step is a **sticky hold** (`state`, wait, `clear`) — never a timed `press`:

| screen | action | result |
|---|---|---|
| title / press-Ⓐ | sticky `A` ~3 s | main menu |
| main menu (`New Game` has the Ⓐ prompt) | sticky `A` ~3 s | **character select** (two hero cards) |
| character select | **sticky `Right` ~1 s** | focus moves onto a card |
| character select | sticky `A` ~4 s | **in the game** |

**The step that is easy to miss, and cost hours: the character-select screen ignores a confirm
until focus has been moved onto a card.** Holding `A` there does nothing at all; `Right` first,
then `A`, goes straight through. Screenshotting between steps is what revealed it — the screen
looked "stuck" while actually waiting for a directional input.

**Proof it is live gameplay and not a still:** five frames captured 15 s apart have five
distinct MD5s (a still would be byte-identical) and `avg_luma` swung 66 → 166 → 122 → 88 → 75.

**One driver at a time.** Two processes issuing `state`/`clear` against the same channel fight
over the single sticky baseline and cancel each other — the symptom is input that "sometimes
works". Before concluding an input was ignored, confirm nothing else is driving the pad.

**Focus is NOT required.** Measured directly: with the window confirmed active
(`xdotool getactivewindow getwindowname` → the title), a sticky `A` still did not advance a
screen that needed a directional input first. The remote pad's focus-independence is real; a
genuine focus test is `xdotool`, not a supposition.

**Killing and finding the title — the pattern self-matches, and the "anchored" form matches
nothing that matters.** `pkill -f 'fable_2.exe'` matches the launcher shell itself, because the
pattern appears literally in the command line that invokes it: the script kills its own parent,
and a "still running" check then reports the launcher as if it were the game.

The usual repair — requiring a slash, `[/]fable_2\.exe` — is **worse than useless, and
backwards**: Wine's command line is a **Windows path with backslashes**
(`Z:\run\media\…\out\dbg-launch\fable_2.exe`), so a forward-slash-anchored pattern **misses the
real game entirely** while still matching every launcher shell, whose paths use forward slashes.
Measured: after a `pkill -f '[/]fable_2\.exe'` the launchers were gone and **the game was still
running** (`pid 2733740`, cmdline starting `Z:\…\fable_2.exe`).

`pgrep -f 'fable_2'` shows both, so the discriminator is the FIRST TOKEN, not the slash:

```bash
# the game only — its command line STARTS with the Windows path
pgrep -af 'fable_2' | awk '$2 ~ /^Z:/ || $2 ~ /fable_2\.exe$/'
```

A launcher's first token is `/usr/bin/bash` (or `bash`); the title's first token is
`Z:\…\fable_2.exe`. Two frames captured a few seconds apart with **different hashes** is the
cheap proof that a run is live and rendering; a single frame, or two identical hashes, proves
nothing.

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


---

# Appendices generated by tools/port-audit.py

The sections above were written by hand as discoveries happened, which is why each one cost
a relaunch. These appendices are **generated from the source** — every cvar the port and its
SDK register, every environment variable, and the enum values that matter. Re-run
`~/.hermes/cache/scratch/port-audit.py` after any SDK or port upgrade and commit the diff:
**the diff is the upgrade capability delta**, and reading it is cheaper than discovering
each knob by rebuilding.
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

---

## 13. Which knobs actually WORK, measured — the audit's real payload

An audit that only lists names is worth little; three of tonight's dead ends came from knobs
that *exist* and do nothing. This section marks the ones that were tested. **A name in the
source is not a working feature.**

### The perf CSV — 2 of 17 counters are real

`perf_log_csv` / `REX_PERF_LOG_CSV=<path>` **does** work: it wrote 5,721 rows of
`fable_2.log`-style per-frame CSV. But across the whole capture:

```
frame_time_us        0 → 42,312      POPULATED
fps                  0 → 30          POPULATED
draw_calls               0           flat zero
vertices_processed       0           flat zero
command_buffer_stalls    0           flat zero
xma_frames_decoded       0           flat zero
functions_dispatched     0           flat zero
texture_cache_hits/misses             flat zero
pipeline_cache_hits/misses            flat zero
active_threads                        flat zero
```

Why: `PROFILE_DRAW_CALL()` / `PROFILE_VERTICES()` have **2 call sites each, only in
`src/graphics/d3d12/command_processor.cpp`** — a path this port's Xenos GPU plugin does not
use. `fps`/`frame_time_us` are populated because they are set directly by `SetCounter` at
`src/graphics/command_processor.cpp:1055`.

**Consequence: the perf CSV canNOT distinguish an FMV from gameplay.** It was proposed for
exactly that and it does not do it. Wire the macros into the path actually used, or do not
rely on it.

### `gpu_debug_markers` — inert for this purpose

Set `true` live, waited, and the log gained **no per-draw names** (`Draw` / `Dispatch` /
`BeginEvent` all 0 hits). It does not give a per-operation trace here, so it cannot be used to
count geometry either.

### `present_effect` — real, but read at chain-build time

Accepted `fsr` and `cas` once the runtime was armed, but the paint chain is built **once**
(`guest output paint:` appears at startup and never again) and the runtime's own string says
`"Requires restart to take effect"`. **Setting it live changes nothing** — it must be set
before the chain builds. The effect must be chosen at launch, not toggled during a run.

### `resolution_scale` — name-confusion hazard

The port answers a cvar named `resolution_scale`, but the SDK's actual scaling knobs are
**`draw_resolution_scale_x` / `draw_resolution_scale_y`**. A null result measured on
`resolution_scale` is therefore **not** a statement about draw scaling. Identify the real knob
before concluding anything from a cvar that merely accepts a value.

### Which runtime is armed, and why it matters

`present_effect` accepts `cas`/`fsr*` **only when the runtime is FSR-armed**
(`REX_HAS_FIDELITYFX_SDK`, gated at `src/ui/presenter.cpp:131`). The armed pair is selected by
**which `rexruntime.dll` is deployed**, and the SDK keeps one directory per build profile:

| profile | size | armed | built |
|---|---|---|---|
| `backup-fsr1-off` | 9,564,160 | no | 12:42 |
| `fsr-clean` | 9,668,608 | **yes** | 13:26 — **pre-fix, crashes at 34 s** |
| `off-detect` | 9,597,440 | no | 16:30 |
| `win-amd64` | 9,672,192 | **yes** | **19:58 — post-fix, survives** |

**`drawer-detect2` has the same byte size as `win-amd64` with a different hash** — match on
hash, never size. And the crash fix landed at 18:06, so **mtime is the cheap discriminator**
between an armed runtime that works and one that dies.

Measured on this box, same session: armed **pre-fix** exited 5 after **34 s**; armed
**post-fix** ran **8 minutes** and was only stopped by a deliberate replacement; the unarmed
baseline ran 16m34s. That is the layout fix verified in the armed configuration with a live
control.

---

## 14. The working launch shape — and the CWD trap that produces a silent no-log death

**`cd`ing into the exe's directory before launching kills the run silently.** Measured 2026-11-04:
launching with `cd out/dbg-launch` as the working directory produced **no `fable_2_0NN.log` at
all**, no control channel, and no perf CSV — the process vanished without the emulator writing a
single line, which reads exactly like a lane, gate or VRAM fault. It was none of those: the lane
reported `launchable: true`, `lane_held: false`, `gpu: safe 8762 MB free`, marker valid.

Relaunched with the **identical env and identical command** from the repository root, it came up
in ~18 s, wrote `fable_2_009.log`, opened the perf CSV, and answered the control channel. The
working directory was the only difference.

**Launch from the repo root** (or wherever the lane's ledger expects). The motivation for `cd`ing
in — getting the runtime's own outputs into the dump directory — is not needed for the FSR work:
the perf CSV is placed by `REX_PERF_LOG_CSV=<absolute path>`, which works regardless of CWD.

### A launch that works has all four of these

Check them in this order; the first absence tells you where it died.

1. **A new `out/dbg-launch/logs/fable_2_0NN.log` exists.** No log = died before the emulator's
   logging came up. Not a lane problem — check the working directory first.
2. **`127.0.0.1:8791` answers** (`ping` → `{"ok": true}`), typically ~18–25 s after launch.
3. **The env vars reached the title** — verify on the process, not by assumption:
   `for p in $(pgrep -f 'fable_2'); do tr '\0' '\n' < /proc/$p/environ | grep '^REX_'; done`.
   The game-job launcher process carries them and so does the title process.
4. **The runtime reports the arm you asked for** — `guest output paint: … #0 <effect> -> WxH` in
   the log. This is the only trustworthy confirmation that a launch-time effect took; a live
   `cvar` read can agree while the chain is still the old one.

### Launch-time env, confirmed correct names

`REX_` + the uppercase cvar name (`src/core/cvar.cpp:106`): `present_effect` →
**`REX_PRESENT_EFFECT`**, `perf_log_csv` → **`REX_PERF_LOG_CSV`**. Both were verified present in
the running title's environment.

Read-only pre-flight that costs nothing and answers most of the above:
`~/.local/bin/game-job.sh --check` (display plan, `launchable`, `would_refuse`) and
`~/.local/bin/game-job.sh --status` (lane holder, GPU verdict, marker expiry).

---

## 15. FSR1 in gameplay — first real measurement (2026-11-04)

The spike document's own §13 said of the earlier FSR result that it was *"by six frames of a
boot video and **is not a claim about gameplay**."* That limitation is now removed.

### Method

Effect chosen **at launch** — `REX_PRESENT_EFFECT=<effect>` in the title's environment — because
`present_effect` is read when the paint chain is built and **cannot be toggled live** (§13).
Each arm was launched, driven into gameplay through the remote control channel with the
documented walk (§12), and captured there. Same box, same session, sequential arms.

### The clean evidence — the runtime's own paint chain

```
bilinear arm:  1 pass(es): #0 bilinear  -> 2560x1440
fsr arm:       2 pass(es): #0 fsr-easu  -> 2560x1440
                            #1 fsr-rcas  -> 2560x1440
```

**This is the proof FSR is running**, and it is not an inference from pixels: the runtime names
the two passes it built. It also confirms the accepted effect survived into the live chain
rather than merely being read back by the cvar.

### The numbers

| arm | laplacian sharpness (mean) | frame_time_us median | p99 |
|---|---|---|---|
| bilinear | 7.931 | 33,342 | 39,783 |
| **FSR (easu+rcas)** | **8.648** | 33,344 | 41,056 |
| delta | **+9.0%** | ~0% | +3.2% |

Both arms confirmed in gameplay by the game's own markers (`texture-morph`, `motion-blur`) and
by capturing 5–6 frames with **distinct** hashes (a still would repeat).

### What this does NOT establish

**The two arms are different runs, so the scene content is not identical.** Within-arm
frame-to-frame differences (mean |diff| ≈ 54) dwarf any cross-arm comparison, so the +9.0% is a
**strong signal and not a clean measurement** of the effect. To make it clean, hold the scene:
use a save/state both arms load into, or compare consecutive frames interleaved *within* one
run by restarting between effects. The **chain difference** in the log is clean; the percentage
is not, and should be quoted with that caveat or not at all.

### Cost

Frame time did not move (33,342 → 33,344 µs median): the two-pass FSR chain costs the same as
the single bilinear pass at this resolution on this box. p99 rose ~3%, consistent with two
passes instead of one.

---

## 16. Draw resolution scale — live null on the CORRECT knob (2026-11-04)

`t_c06e8813` asks whether everything scales with the draw resolution. §13 records that the
earlier attempt used `resolution_scale`, which is **not** the SDK's scaling knob. Re-measured on
the right one.

**Both correct cvars exist and accept live writes:** `draw_resolution_scale_x`,
`draw_resolution_scale_y` (default `1`).

**Method:** interleaved in one run — set 2, capture, set 1, capture, twice — so the scene-motion
floor is measured alongside the comparison.

| | sharpness | |
|---|---|---|
| 1x | 29.931 / 29.778 | |
| 2x | 29.855 / 29.644 | |
| within-setting floor | 1x 2.47, 2x 2.28 | scene motion |
| **cross-setting 1x vs 2x** | **2.61** | **at the floor** |

**Live-toggling `draw_resolution_scale_x/y` 1↔2 produces no change distinguishable from the
scene moving.** Sharpness is identical to two decimal places.

**The caveat is the same one `present_effect` carries, and it is not yet resolved here:** a live
write that changes nothing does **not** establish the setting is inert — it may be read at
startup or on scene reload, exactly as the presenter's effect is (§13). The presenter's paint
chain is *not* the right place to look for a draw-scale change either: it reports the presenter's
own output (`1280x720 -> 3440x1440`), which is downstream of the guest render targets the draw
scale affects.

**So the honest state of this card is: live = no effect (measured); at-launch = not yet tested.**
That is the remaining experiment, and it needs a launch-time env
(`REX_DRAW_RESOLUTION_SCALE_X` / `_Y`) plus something in the log that reports an internal render
target size to confirm the scale took — otherwise the comparison repeats the same scene-motion
problem.

**Do not repeat the mistake this section corrects:** `resolution_scale` accepting a value is not
evidence it is the knob that scales anything.

---

## 17. Draw resolution scale — ANSWERED: it takes, and this title does not use it

§16 recorded a live null and left the at-launch test open. It is now done, and the port answers
the question itself.

**Test:** launch with `REX_DRAW_RESOLUTION_SCALE_X=2` / `REX_DRAW_RESOLUTION_SCALE_Y=2`, then
diff the boot log against a 1x arm's, normalised for timestamps, thread ids and addresses.

**The line that matters — present in the 2x log and absent from the 1x log:**

```
[warning] [gpu] D3D12 draw resolution scaling is enabled, but the swap source is unscaled (NxX).
                This title may be presenting from an unscaled resolve path.
```

**Reading:**

1. **The scale took.** The port says draw resolution scaling *is enabled* — so the launch-time
   env landed and the setting is active. The live-write null in §16 was therefore not a
   "setting didn't apply" story.
2. **The title does not use it.** It presents from an **unscaled resolve path**, so a scaled draw
   target is never what reaches the swap chain. That is why the image does not change, live or at
   launch.
3. **This reconciles both nulls** — the earlier mis-knobbed `resolution_scale` result and the
   correct-knob `draw_resolution_scale_x/y` result — under one mechanism, and it is a statement
   about *this title's* resolve path, not about the knobs.

**Answer to the card's question** ("does everything scale with resolution_scale — post-FX,
shadows, particles, HUD"): **not for this title via this knob.** The scale is applied and the
presentation path bypasses it. A per-effect breakdown is therefore moot until the title is made
to resolve through the scaled path, which is a port/code change rather than a setting.

**Method note worth keeping:** a *log diff between two arms* found this in one launch, where two
rounds of frame comparison could not. When a visual setting appears inert, look for a line that
reports the setting's own state before concluding from pixels — the port said "enabled" while the
image said "nothing", and both were true.
