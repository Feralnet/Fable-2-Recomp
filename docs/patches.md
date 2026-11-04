# Guest-image patch system (Xenia patch format)

Runtime patching of the loaded `default.xex` guest image, using the op shape
of Xenia's game-patches (`patch.toml`) format.

## How it works

- `src/core/fable2_patches.h` / `src/core/fable2_patches.cpp` — the patch table +
  applier. Each op is `{be8|be16|be32|be64, address, value}`, exactly the
  `[[patch.be32]] address/value` shape from Xenia's patch files.
- **No patch file.** The table is built in code; each patch's `enabled` comes
  from a `[patches]` key in `fable2_config.toml` (loaded in
  `OnPostInitLogging`, before the patches are applied). The old
  `fable2_patches.toml` is no longer read and can be deleted.
- `Fable2App::OnPostLoadXexImage()` (src/core/fable_2_app.h) calls
  `fable2::patches::ApplyAll(runtime()->memory(), PPCImageConfig)` — the SDK
  hook that runs after `default.xex` is decrypted/expanded into the guest
  arena and before the guest module launches (the SDK documents this hook as
  the place for data patches).
- The SDK marks XEX code/rodata pages **read-only** after load
  (`XexModule::LoadContinue` page-descriptor pass), so `PageWriteGuard`
  flips the touched guest pages to R/W via `heap->Protect()` and restores the
  original protection after the write. Safe at this point: no guest thread
  exists yet.
- Every op is logged: `[patches] <patch> be8 0xADDR: 0xOLD -> 0xNEW
  (data: takes effect at runtime)`, plus a summary line.

## Current patches (both default to **disabled**)

| Config key | Xenia patch | Data op (this table) | Code op (mid-asm hook) |
|---|---|---|---|
| `high_tick_rate` | High Tick Rate (Guy) | be8 0x83319511 = 0x3E (LF tick double 0x83319510: 15.0 → 30.0) | NOP of the store at 0x8233AEB4 → `fable2_hook_high_tick_rate_skip_store` |
| `higher_hf_tick_rate` | Higher HF Tick Rate (Ultra) | be8 0x83319519 = 0x4E (HF tick double 0x83319518: 30.0 → 60.0) | NOP of the store at 0x8233AE98 → `fable2_hook_high_hf_tick_rate_skip_store` |

Both stores are in `sub_8233AE50` (game init) and are the only writers of
those doubles; without the hooks the game overwrote the patched values and
the data ops had no effect. The game runs HF at twice LF (30:15). With only
`high_tick_rate` the ratio becomes 1:1 (30:30) and cloth physics misbehaves,
so turn on `higher_hf_tick_rate` with it (60:30).

This is the fundamental recomp vs. emulator split: **data patches work, code
patches don't** (a code patch here would mean editing the recompiled C++ at
build time, which codegen would clobber on the next run), so every code op is
a mid-asm hook.

## Validation (2026-09-15)

- Built (`build.cmd fable_2`, debug), launched the game (all ops applied,
  ~7 min run, clean shutdown; the 60 FPS entry later moved to a mid-asm
  hook and is no longer a guest-image patch):
  ```
  [patches] applying 'High Tick Rate' by Guy (2 ops) - Doubles tickrate to 30hz. ...
  [patches]   High Tick Rate be32 0x8233AEB4: 0xd8089510 -> 0x60000000 (code region: ...)
  [patches]   High Tick Rate be8 0x83319511: 0x2e -> 0x3e (data: takes effect at runtime)
  [patches] done: 2 op(s) applied, 0 skipped
  ```
- Game ran ~7 minutes with patches applied, clean user-initiated shutdown,
  no access violations or protection errors (first run, before the
  read-only-page handling existed, did fault on the code op — fixed by
  `PageWriteGuard`).

## Recomp-level patches (making code patches work)

Since guest .text is never executed, code-region Xenia patches must be
applied to the **recompiled code**. Two mechanisms, in order of preference:

### 1. Mid-asm hooks (preferred) — SDK-native, declarative

The SDK's `[[entrypoint.midasm_hook]]` config (manifest) injects a call to a
C++ function at a specific guest instruction address during codegen
(docs: https://rexglue-rexglue-sdk.mintlify.app/config/hooks). Registers
named in the hook are passed **by reference** (`PPCRegister&`), so the hook
function can rewrite them — "value injection".

Wiring (all three pieces):
1. `fable_2_manifest.toml` → `[[entrypoint.midasm_hook]]` with `address`,
   `name`, `registers`, and `after_instruction = true` so the call lands
   right after the patched instruction executes.
2. `src/core/fable2_hooks.cpp` → the hook function, plain C++ linkage matching
   the prototype codegen auto-emits into the generated code
   (`extern void fable2_hook_website_g1(PPCRegister& r9);`).
3. Nothing else — codegen handles the rest, and it survives codegen re-runs
   by construction (the manifest is a codegen input).

**Runtime toggle (done):** the hook body is C++ in the game process and
consults `fable2::config::Get()` on every call — a `[patches]` key in
`fable2_config.toml` enables/disables the patch with no rebuild.
(New hooks should follow the same pattern: read their toggle from
`fable2::config::Get()`.)

### 2. Post-codegen text patches (fallback)

`tools/apply_recomp_patches.py` mirrors a patch into codegen's emitted C++
by anchored text replacement; wired into CMakeLists.txt as a step **between
codegen and compiling fable_2_recomp** (keyed on
generated/default/codegen.build.stamp). Idempotent via a unique
`// [recomp-patch: <name>]` marker; missing anchor = build failure.
`FABLE2_RECOMP_PATCHES=0` skips all (A/B runs). Use only for patches that
can't be expressed as hooks (e.g. constants baked into memory operands).
Currently **empty**.

### Current recomp-level patches

| Patch | Mechanism | Change | Measured effect |
|---|---|---|---|
| Unlock Website Items (Guy) | mid-asm hook `fable2_hook_unlock_website` @ 0x8256E384 (after `rlwinm r9,r10,0,25,25`); toggle: `[patches] unlock_website` | Forces `r9 = 0x40` (bit 6) in `sub_8256E368`, so the website/Guild-chest item lookup reads as unlocked and runs the real lookup. Re-derives the Xenia "Unlock Website Items" intent for THIS build (the stock ops target a different revision's bytes). | Hook confirmed in generated code + clean startup; in-game chest unlock pending manual test |
| Unlock CE Content (Guy) | mid-asm hook `fable2_hook_unlock_ce` @ 0x824B3540 (after `rlwinm r10,r11,0,25,25`); toggle: `[patches] unlock_ce` | Forces `r10 = 0x40` (bit 6) in `sub_824B3528`, so the Collectors-Edition chest item lookup reads as unlocked and runs the real lookup. Same re-derivation approach. | Hook confirmed in generated code + clean startup; in-game chest unlock pending manual test |

To add a new code patch: a `[[entrypoint.midasm_hook]]` entry + hook
function gated on a `[patches]` config key (preferred), or an
`apply_recomp_patches.py` PATCHES entry (fallback). If it also needs a data
write, add it to the table in `src/core/fable2_patches.cpp`, gated on the
same key.

## Widescreen 21:9 (Hor+) — guest aspect data patch

`[patches] widescreen_21_9` in `fable2_config.toml` widens the drawn field of
view to an ultrawide aspect. It is a pure **data** patch: two float constants
in the guest image are rewritten at boot by `src/core/fable2_patches.cpp`
(`ApplyAll`, i.e. `Fable2App::OnPostLoadXexImage`), so no mid-asm hook and no
rebuild of the recompiled code is involved — only the host exe that carries the
op table.

| Guest address | Section | Stock | Patched (defaults) |
|---|---|---|---|
| `0x8209FE7C` | `.rdata` constant pool | `0x3FE38E39` = 16/9 | `widescreen_aspect` = 3440/1440 = `0x4018E38E` |
| `0x8209FDF4` | `.rdata` constant pool | `0x3FAAAAAB` = 4/3 | `widescreen_reference_aspect` = 16/9 = `0x3FE38E39` |

Authority: the pair, and the 4/3 → 16/9 second write, come from Xenia's
`4D5307F1 - Fable II (GOTY_Platinum Edition).patch.toml` 21:9 preset (module
hash `4145F96D2DEE2AB5`, media `716F0A0D` — this dump). Its 32:9 preset writes
`0x8209FE7C`, which is what identifies that word as the display aspect; its
21:9 value is `2560/1080 = 2.370370`, which leaves ~13 px bars at 3440x1440, so
the default here is the exact `3440/1440` instead. Do **not** port
`4D5307F1 - Fable II (1).patch.toml`: its `0x8209C9AC/B0` are mask tables in
this image.

Why not the presenter: `present_letterbox = 0` (the earlier stopgap) stretches
the 16:9 frame by 3440/2560 = 1.3438 — distortion, not ultrawide. Widening has
to happen in the guest's aspect constant, after which the presenter scales
nothing at all because the guest aspect and the window aspect are equal.

Revert: `widescreen_21_9 = false` (or `FABLE2_ULTRAWIDE=0`, which `launch.sh`
exports as the same key) — stock 16:9, no rebuild.

Open question this patch exists to answer by measurement: whether the guest
rewrites `0x8209FE7C` during init (in which case the boot-time write is
overwritten and a mid-asm hook is needed). The log line
`[patches]   Widescreen 21:9 (Hor+) be32 0x8209FE7C: 0x3FE38E39 -> 0x4018E38E
(data: takes effect at runtime)` proves the write happened, **not** that it
survived; `scripts/probe-aspect.py` reads the live guest arena twice a few
seconds apart to settle it.

## Front-end canvas fill — mid-asm hook (guest 2D display area)

> **Measured inert for the front-end plate (2026-11-03).** This patch moves the
> display-area descriptor's width (1120 → 1280, confirmed in a run's log) and
> leaves the picture unchanged: with it on, the menu's guest frame is identical
> within noise (symmetric seam pair 323/2238 px, corr(L,flipR) +0.50, side/centre
> sharpness 0.697 both ways). The descriptor is **not** the plate's source. It is
> kept as a documented negative result and because it is harmless; the patch that
> actually removes the plate is `ui_frontend_stretch`, below.

`[patches] ui_canvas_fill` (default **false**; `FABLE2_UIFILL=1` to enable per
run) makes the guest's 2D display area the full width of its own canvas.

**Mechanism.** `sub_8238DE58` builds a display-area descriptor
`{+0x94 width, +0x98 height = 720, +0x9C mode = 2}` and writes the width from a
guest global:

| Guest address | Instruction | Path | Stock value |
|---|---|---|---|
| `0x8238DF58` | `li r11,1120` | executes on **both** paths, before the branch at `0x8238DF5C` | 1120 (widescreen) |
| `0x8238DF60` | `li r11,960` | 4:3 fallback path only (branch not taken) | 960 |
| `0x8238DF64` | `stw r11,148(r31)` | stores the width into the descriptor | — |

The gate is the guest global at **`0x83360168`** (`lis 0x8336; addi r10,r11,344;
lwz r11,16(r10)` — *not* `0x83320168`, an easy transcription slip: `lis
-31946` folds to `0x83360000`, not `0x83320000`). The 4:3 fallback is the one
the front end actually takes at the main menu, which is why the measured plate
is 960 guest px wide.

Two `[[entrypoint.midasm_hook]]` entries are required — one after each `li` —
because the fallback path overwrites the value the first hook set. Both call
`ApplyUiCanvasWidth()`, which writes
`clamp(round(720 * widescreen_aspect), 960, 1280)` into `r11`. A third hook
(`0x8238DF68`, after the mode store, while `r11` still holds the width) logs
the value the guest actually kept — one line per distinct width, so a run's log
answers "did the hook apply, and did the game rebuild the descriptor later?".

**Why 1280 and not a per-ratio number.** The descriptor lives inside the guest's
hard-coded 1280x720 render mode (`.rdata 0x820FA460`), so 1280 is the widest
area it can express; the rest of an ultrawide aspect comes from the guest's own
anamorphic squeeze (the display-aspect constant) plus the presenter's uniform
scale. Deriving the width from `widescreen_aspect` keeps one code path for 21:9
and 32:9, and a 4:3 window still gets the game's own 960 layout.

**Not a data patch.** `be16 0x8238DF5A = 0x0500` (the unported Xenia
"1280x720" op) edits the immediate of `li r11,1120`; guest `.text` is never
executed in a recomp, so as a data write it is inert. It is also the wrong
branch: that op widens the widescreen value (1120 → 1280), while the front end
uses the 960 fallback.

## Front-end stretch — mid-asm hook (the 2D layer's aspect)

`[patches] ui_frontend_stretch` (default **false**; `FABLE2_UISTRETCH=1` per run)
makes the front end compose the **16:9 presentation edge-to-edge** at any aspect
wider than 16:9, instead of fitting it into the display aspect and padding the
leftover strips with a mirrored wrap of the plate's own edge. At 21:9 and 32:9
the menu then looks like it does at 16:9 — filled, no seam, no mirrored bands —
while the 3D world keeps the wider field of view that `widescreen_21_9` gives it.

**Mechanism.** The 2D layer takes its aspect from one function,
`sub_821A5D80`, called straight from the display-area constructor
`sub_8238DE58`. It loads one of the two guest aspect constants and stores it on
the 2D display-area object:

| Guest address | Instruction | Meaning | Object field |
|---|---|---|---|
| `0x821A5E00` | `lfs f30,27080(r30)` | display aspect `0x8209FE7C` | → `+0xE4` |
| `0x821A5E08` | `lfs f30,26944(r30)` | reference aspect `0x8209FDF4` | → `+0xE4` |
| `0x821A5E0C` | `fmuls f1,f0,f30` → `bl 0x8227EE80` | derived scale | → `+0xD8` |
| `0x821A5E2C` | `stfs f30,224(r31)` | stores the aspect | `+0xE4` |

The gate on which constant is used is the guest global `0x83360164`
(`lwz r11,12(r10)` with `r10 = 0x83360158`); at ultrawide the **display** path
is the one taken, confirmed in a run's log:

```
[ui-stretch] 2D display aspect (display path) = 2.388889, hook on
```

Two `[[entrypoint.midasm_hook]]` entries are required — one after each `lfs` —
because the value is loaded on two paths 8 bytes apart, the same shape as the
960/1120 width pair above. Both clamp `f30` to `16/9` when the value is wider:

```c
if (guest > 16.0 / 9.0) f30.f64 = 16.0 / 9.0;
```

**Why the cap is 16/9 and not a per-ratio number.** The 16:9 presentation is what
the front end is authored for; anything wider is the *presenter's* job. The
presenter already maps a 16:9 guest frame onto the window by stretching it —
measured with the aspect patch off: the presented frame's edge bands match a
×1.34375 stretch of the 16:9 reference to 0.3 grey levels. So the guest composes
16:9 and the presenter supplies the difference: one code path for 21:9, 32:9 and
anything else, and at 16:9 or narrower the clamp is a no-op because the value is
already ≤ 16/9.

**Why not a UV-span edit.** The plate is not a scaled quad with UVs outside
[0,1] — it is the 2D layer being told a display aspect and composing a 16:9
presentation inside it. Clamping the aspect makes it compose edge-to-edge, and
needs no vertex/shader work in the Xenos plugin (whose mirrored-wrap conversion
is closed to per-draw rewrites anyway).

**Measured** (`reports/frontend-stretch.md`): guest frame at 21:9 loses the
symmetric 323/2238 seam pair and the mirror signature (corr +0.50 → +0.17,
side/centre sharpness 0.697 → 0.817, against the 16:9 reference's 0.838); the
presented 3440×1440 frame's edge bands match the 16:9 reference stretched
×1.34375 at corr +1.000 / mad 0.31 (left) and +0.999 / mad 0.30 (right), and are
identical to the stock patch-off presentation (mad 0.00). The 32:9 run does not
re-flow: same edge numbers, sharpness ratio 0.82.

## Screenshot hotkey — guest-frame capture in a Release build

`--screenshot_key F9` (cvar `screenshot_key`, `--screenshot_dir` for the output
directory, default `screenshots/`) writes one PNG of the **guest output** — the
guest's own frame before the presenter scales or letterboxes it — on each
keypress. It is off by default (empty key name) and needs no Debug build and no
socket: `Presenter::CaptureGuestOutput` (`SDK/src/ui/d3d12_presenter.cpp`)
takes the guest-output mailbox lock and does a fence-waited copy, and
`framecapture::CaptureGuestOutputToPng` (`src/diagnostics/fable2_frame_capture.h`)
turns it into a PNG with a self-contained writer. Implementation:
`src/diagnostics/fable2_screenshot.h`, polled from the host input driver
(edge detect) and the main loop (capture on a short-lived thread).

This is the instrument that separates guest-side from presenter-side artefacts:
pair one `guest-*.png` with one window shot of the same moment.



### FPS meter

`src/diagnostics/fps_meter.h` (included from main.cpp): strong override of the weak
recompiled `MainRenderLoop_82B9CD68` (0x82B9CD68, main loop, one call per frame; renamed from `sub_82B9CD68`) that counts
invocations in 5 s windows and appends `mainloop rate=NN.N/s` to
`fps_meter.log` next to the exe. Forward-only (counts, then calls the
original `__imp__` entry). Enabled with `FABLE2_FPS_METER=1`.

## Follow-ups

1. ~~Tie to config~~ **done**: every patch, data or code, is toggled by a
   `[patches]` key in `fable2_config.toml` (the separate
   `fable2_patches.toml` was removed).
2. **Other Xenia patches** for this title (from
   `4D5307F1 - Fable II (GOTY).patch.toml`). Done as mid-asm hooks:
   **Unlock Website Items**, **Unlock CE Content** (all re-derived for THIS
   build — see the recomp-level patches table above). Remaining (still to port,
   each needs the same build-mismatch investigation — the stock ops target a
   different revision): 1280x720 (be16 0x8238DF5A=0x0500), Disable MSAA
   (be8 0x8238DF3F=0x01), Disable Texture Morphing (be16 0x8220EF10=0x4280),
   21:9 / 32:9 widescreen — all .text/data-in-.text, so expect the same "applied
   but inert" behavior for their code ops if applied to the guest image.
3. **Oddity worth investigating (separate issue):** the recompiled C++ for
   `sub_8233AE50` (generated/default/fable_2_recomp.65.cpp:3211) was compiled
   from a word at 0x8233AEB4 of `0xD9009510` (stfd f0,0x9510(r8)), but the
   current `default.xex` image contains `0xD8089510` (stfd f8,0x1510(r0))
   there — verified two independent ways: an independent AES-CBC +
   basic-compression-block expansion of default.xex, and a live read of the
   running process's guest arena (see scratch/fable2_image_decrypted_expanded.bin
   for the fully expanded image). Neighboring words 0x8233AE54 and
   0x8233AE98 differ too. Same file (SHA-verified, unchanged since
   2026-08-26) and the v0.10.0 XEX loader source is byte-identical to the
   nightly's — so the prebuilt codegen tool's image and the runtime image
   differ by a handful of bytes (register fields transposed / stray bits).
   Possibly a `be<enum>` struct-layout difference in
   `xex2_opt_file_format_info` between the prebuilt 0.10.0 tool and the
   source-built nightly runtime (block table at +8 vs +12). If any recompiled
   function's data operands come from those bytes, the recompiled code is
   subtly out of sync with what the runtime loads. Low priority (the game
   plays fine), but worth a dedicated look if anything mysterious happens.

## XEX2 decoding notes (for future reference)

`default.xex` (GOTY, media 716F0A0D): XEX2, header 0x4000, base 0x82000000,
image_size 0x1620000, session key = AES-CBC(retail_key, secinfo+0x150),
encryption=NORMAL (AES-CBC, zero IV), compression=BASIC = a block table of
`{data_size, zero_size}` pairs: the file stream is the concatenation of the
block data only; each block expands to `data_size` decrypted bytes followed by
`zero_size` zero bytes. Block table (this file):
`(0x168000, 0x8000), (0x1158000, 0x8000), (0x58000, 0x1D0000), (0x120000, 0)`.
