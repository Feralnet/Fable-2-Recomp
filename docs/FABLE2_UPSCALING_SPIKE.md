# Fable II recomp — upscaling spike: the FSR 1 present pass

Status: **spike complete, pass proven running; the early guest self-exit is real
but INTERMITTENT (~90 % of launches, not every one) and the bisection in §7
cleared every named suspect — read §7 before §5's attribution.** §9 identified
the failure as a crash, not a guest exit, and §10 names the crashing function
from symbols, records a second armed-only binary difference (the `Presenter`
layout moves by `0x10` when `REX_HAS_FIDELITYFX_SDK` is on) and **stages the
detector + fix shape unmeasured** — the human gate lapsed before any launch, so
the invalidated-iterator hypothesis is still open; §10.7 is the batch that
settles it.
Read "Launch outcomes" before using anything here.

Branch: `feral/dlss`. SDK source: `/home/feral/toolchains/rexglue-sdk`
(HEAD `cc5f03dd0488720a0f277412d7c36b63964d5b18` + the pre-existing local
modifications + `thirdparty/rexglue-sdk-fsr1-raster.patch`).

## 1. What was already there (finding #1)

Fable's present path is **not** in this repo. The game is RexGlue: the final
composite happens in the SDK's `rex::ui::Presenter` /
`rex::ui::d3d12::D3D12Presenter` (`src/ui/presenter.cpp`,
`src/ui/d3d12/d3d12_presenter.cpp`), which ship as prebuilt
`rexruntime.dll` / `rexgpu-xenos.dll` from `/home/feral/toolchains/rexglue-sdk`.

That presenter already implements the whole KZ2-shaped design, upstream:

- `Presenter::GuestOutputPaintConfig` — one effect enum (`kBilinear`, `kCas`,
  `kFsr`, `kFsr2`, `kFsr3`), a quality mode, sharpness, upscaling-pass limit.
- `GetGuestOutputPaintFlow()` — decides the pass chain and its sizes:
  FSR = chained `kFsrEasu` passes (up to `present_fsr_max_upsampling_passes`,
  doubling per pass) ending in a 1:1 `kFsrRcas`; bilinear otherwise.
- The FSR 1 EASU / RCAS and CAS shaders are **vendored as precompiled DXIL
  bytecode** in `src/ui/shaders/bytecode/d3d12_5_1/guest_output_ffx_*` (built
  from the AMD FidelityFX headers; those headers themselves are *not* needed to
  compile the raster path).
- Everything is compiled out unless `REX_HAS_FIDELITYFX_SDK` is defined, which
  upstream only does when the whole FidelityFX SDK is fetched
  (`REXGLUE_ENABLE_FIDELITYFX` → FetchContent + Vulkan SDK). Default = off =
  plain bilinear, no extra pass, no extra context (the KZ2 NULL=off rule,
  already upstream).

So the spike did **not** need a new hook: the hook point exists, it is the guest
output paint/blit path, and it is reachable with a compile-time switch plus the
`present_effect` cvar. `src/` in this repo is the *game* (hooks, config,
diagnostics); it never owns the present.

## 2. What the patch does

`thirdparty/rexglue-sdk-fsr1-raster.patch` (283 insertions over 4 files):

1. `CMakeLists.txt` — new option
   `REXGLUE_ENABLE_FSR1_RASTER` (default OFF) that turns on the raster
   FidelityFX effects **without** the FidelityFX SDK fetch. The temporal path
   (`REX_HAS_FIDELITYFX_RUNTIME`, ffx_api headers, FSR2/FSR3) stays compiled
   out, which is what this spike promised.
2. `src/ui/CMakeLists.txt` — `REX_HAS_FIDELITYFX_SDK=1` when that option is on.
3. `src/ui/d3d12/d3d12_presenter.cpp/.h` — diagnostics only (no behaviour
   change when off):
   - an effect-chain log line, once per change:
     `guest output paint: 1280x720 -> 3440x1440, 2 pass(es): #0 fsr-easu -> 2560x1440 #1 fsr-rcas -> 2560x1440`
   - `present_dump_final` / `..._start` / `..._every` / `..._count` — writes the
     **finished back buffer** (post-effect, pre-Present) as binary PPM. This is
     the piece the existing `CaptureGuestOutput` cannot give: that one reads the
     *guest* texture before host-side scaling, so it can never show whether the
     upscaler ran.

Default is still off: with `present_effect` unset the chain is the same single
bilinear pass as before.

## 3. Build and run

```sh
# SDK runtime + plugin, Release, from the SDK source tree
cmake -S /home/feral/toolchains/rexglue-sdk -B /home/feral/toolchains/rexglue-sdk/build \
      -DCMAKE_TOOLCHAIN_FILE=/home/feral/toolchains/windows-x64/cmake/windows-msvc-x64.cmake \
      -DCMAKE_BUILD_TYPE=Release -DREXGLUE_USE_D3D12=ON -DREXGLUE_USE_VULKAN=OFF \
      -DREXGLUE_ENABLE_TRACY=OFF -DREXGLUE_ENABLE_PERF_COUNTERS=ON \
      -DREXGLUE_BUILD_TESTS=OFF -DREXGLUE_ENABLE_FSR1_RASTER=ON
cmake --build /home/feral/toolchains/rexglue-sdk/build --target rexgpu-xenos rexruntime -j16
# → out/win-amd64/rexruntime.dll + rexgpu-xenos.dll (copy both next to fable_2.exe)
```

The game itself needs no rebuild — the presenter lives in the runtime DLL.
`tools/setup_sdk_src.cmd` now applies `thirdparty/rexglue-sdk-fsr1-raster.patch`
after the existing local patch (skipped, with a note, if it does not apply to
the pinned SDK). `tools/build_runtime_sdk.cmd` hard-codes
`-DREXGLUE_ENABLE_FIDELITYFX=OFF`; add `-DREXGLUE_ENABLE_FSR1_RASTER=ON` to its
cmake line (or configure by hand as above) to get the upscaling runtime.

Run (the launch layout is `out/launchcheck/`, staged by the game's own build):

```sh
REX_PRESENT_EFFECT=fsr \
REX_PRESENT_DUMP_FINAL=Z:/run/media/feral/Games/Recomp/fable2/out/upscale-dumps/fsr \
REX_PRESENT_DUMP_FINAL_START=300 REX_PRESENT_DUMP_FINAL_EVERY=400 \
REX_PRESENT_DUMP_FINAL_COUNT=10 \
STEAM_COMPAT_CLIENT_INSTALL_PATH=$HOME/.local/share/Steam \
STEAM_COMPAT_DATA_PATH=/run/media/feral/Games/Recomp/fable2/out/launchcheck/pfx \
  "$HOME/.local/share/Steam/compatibilitytools.d/Proton-CachyOS Latest/proton" run \
  /run/media/feral/Games/Recomp/fable2/out/launchcheck/fable_2.exe
```

(launched inside `~/.local/bin/game-job.sh`, which is mandatory for agent runs;
the effect is picked with `present_effect=bilinear|cas|fsr`, and
`present_fsr_sharpness_reduction`, `present_fsr_max_upsampling_passes` come with
the same switch.)

## 4. Evidence the pass runs (finding #2: it does)

Same layout, same paint indices, `bilinear` vs `fsr`:

| run | chain logged |
|---|---|
| bilinear | `1 pass(es): #0 bilinear -> 2560x1440` |
| fsr | `2 pass(es): #0 fsr-easu -> 2560x1440 #1 fsr-rcas -> 2560x1440` |

Guest output is 1280x720, the swap chain 3440x1440, so EASU is the 2x upscale
that bilinear was doing, and RCAS the 1:1 sharpen on top of it.

Dumps (3440x1440 PPM, same scene, same paint index):

| pair | RMSE (bilinear vs fsr) | Laplacian std bilinear → fsr |
|---|---|---|
| paint 300 | 0.0022 | 0.0396 → 0.0410 (+3.5%) |
| paint 700 | 0.0024 | 0.0475 → 0.0488 (+2.7%) |
| paint 700, 900x240 text crop | 0.0046 | 0.0120 → **0.0278 (+132%)** |

Whole-frame numbers are small because the captured frames are the smooth
Microsoft/Lionhead boot-video frames; the crop is the logo's wordmark and that
is where EASU+RCAS pays off — same glyph shapes, clearly harder edges
(`out/upscale-dumps/text-compare.png`: bilinear on top, FSR below).

## 5. Launch outcomes — the honest part (finding #3: it resists here)

Every launch, in order (all through `game-job.sh`, all on the operator default
output DP-1, all timed out or self-exited):

| # | effect | dumps | outcome |
|---|---|---|---|
| A | bilinear | 150–152 | guest **exited itself** 29 s after launch (2 s after first paint) |
| B | fsr | 150–152 | guest **exited itself** 40 s after launch (14 s after first paint) |
| C | bilinear | 300, 700 | guest **exited itself** 32 s after launch |
| D | fsr | 300, 700, 1100, 1500 | guest **exited itself** 37 s after launch |
| control 1 | prebuilt 0.10.0 DLLs (untouched) | — | ran the full 90 s timeout, no self-exit |
| control 2 | source-built SDK, `REXGLUE_ENABLE_FSR1_RASTER=OFF` | — | ran the full 70 s timeout, no self-exit |
| control 3 | FSR build, **no dump cvars** | — | guest **exited itself** ~20 s after first paint |

`Execution complete` with no preceding `Window closing` / `Title terminated`
means the *guest main returned* — the game quit, the host did not close it.

Attribution, from the controls:

- **Not the launch layout, not the game, not the host**: control 1 (the same
  binary and data with the previously staged prebuilt DLLs) stays up.
- **Not the source-built runtime as such**: control 2 (same source build, the
  new option OFF) stays up.
- **Not the diagnostics**: control 3 (option ON, dump cvars unset) still exits.
- **Not the FSR shaders**: bilinear-only runs with the option ON exit too.

So it is something in the **`REX_HAS_FIDELITYFX_SDK`-gated presenter code
path itself**, independent of which effect is selected. Two more exclusions were
run before that conclusion was written down:

- **Not the effect array size**: rebuilding with `kMaxGuestOutputPaintEffects`
  forced back to 1 (`#if defined(REX_HAS_FIDELITYFX_SDK)` branch, i.e. the same
  value the non-FidelityFX build uses) and running bilinear still self-exits,
  4 s after first paint. That was a temporary local edit; the patch in this repo
  does not contain it.
- **Not the shaders**: no FSR pass is ever scheduled in the bilinear runs.

The numbers point at a frame-pacing stall rather than a crash: the GPU
`WAIT_REG_MEM` long-wait rate climbs 230 → 685 → 917/s in the last two seconds
before the guest returns, where the surviving control sits flat at ~333/s.
What is left inside the guard, none of it bisected yet: the extra
`present_*` cvars and the config plumbing they feed
(`BuildGuestOutputPaintConfigFromCVar` / `SetGuestOutputPaintConfigFromUIThread`,
which the FidelityFX build populates and the plain build does not), the
guest-output pipeline set created for the vendored `guest_output_ffx_*` shaders,
and the intermediate-texture bookkeeping. That is the next pass; it is a
presenter-side problem, not a shader or a Fable-side one.

Observed oddity worth knowing: the swap chain is 3440x1440 while the display the
window is placed on (DP-1) is 2560x1440 — the dumps are 3440x1440 with the
2560-wide picture inside them. That predates this patch (it is window placement
versus surface size) but it means "output size" in these logs is the swap chain,
not the monitor.

## 6. Where the artefacts are

- `out/upscale-dumps/bilinear/`, `out/upscale-dumps/fsr/` — PPM + PNG dumps
  (git-ignored, derived files).
- `out/upscale-dumps/text-compare.png` — the crop comparison above.
- `out/orig-dlls/` — the prebuilt runtime/plugin the tree shipped with
  (`rexruntime.dll` md5 `726c8f7e…`, `rexgpu-xenos.dll` md5 `3417f468…`), so the
  launch layout can always be put back.
- The FSR-enabled runtime is the build of the SDK + patch above; the binary that
  produced the evidence in §4 has md5 `1362d1e6…` (a rebuild from the same source
  hashes differently — the DLL embeds build metadata), staged as
  `out/upscale-build/rexruntime-fsr1.dll` + `rexgpu-xenos-fsr1.dll`. The §7 bisect
  left that directory holding a post-bisect rebuild of the same source, md5
  `13a5d065…` / `01a56d4e…`; `out/fsr-clean/` is the same pair under its bisect name.

Nothing here has been posted anywhere; this is local work.

## 7. Bisection pass (kanban `t_f73e8894`) — the three named suspects, cleared

Method: the same launch layout and lane (`game-job.sh`, operator default output
DP-1, window placed never activated, audio muted), **bilinear** as the probe, the
lane's own 70–75 s timer as the survival bar. Every arm below was a real launch in
this session; the prebuilt DLLs and/or the option-OFF source build are the control
in every batch. Individual runs are logged `out/launchcheck/logs/fable_2_0NN.log`
(NN as in the table), ledger `~/.hermes/logs/game-jobs.jsonl`.

**Finding 0, which changes how every number below must be read: the failure is
intermittent.** The *same binary* both self-exited and survived (arm D, md5
`915758d5…`: died at 16.2 s and 41 s, survived 74 s). Across all guard-ON builds
in this session it self-exits in **9 of 10** launches; across option-OFF and
prebuilt launches, **0 of 3 and 0 of 2**. So a single run per arm proves nothing —
the exclusions below are on *rates*, not on one surviving or one dying launch.

| arm | what was compiled out / changed | runs | self-exit | survived | time after 1st paint | last-second `WAIT_REG_MEM` |
|---|---|---|---|---|---|---|
| A0 | control: prebuilt 0.10.0 DLLs (before the arms, and again after the last one) | 2 | 0 | 2 | — (full 80 s timer ×2) | 306, 294/s |
| A1 | nothing (patch as committed), bilinear | 1 | 1 | 0 | 18.2 s | 675/s |
| B | nothing; bisect instrumentation added | 1 | 1 | 0 | 14.4 s | 215/s |
| C | suspect 2: ffx root signatures + `guest_output_ffx_*` PSOs | 1 | 1 | 0 | 4.3 s | 274/s |
| D | suspects 1+2: C, plus the six `present_*` cvars and the config population | 6 | 5 | 1 | 5.8 / 11.3 / 16.2 / 30.6 / ~45 s | 207–931/s |
| E | control: option **OFF** source build (fresh, Ninja) | 2 | 0 | 2 | — (full 80 s timer ×2) | 132, 297/s |
| F | patch as committed, bilinear, repeats | 4 | 3 | 1 | 6.5 / 25 / 39.3 s | 201–910/s |
| F' | patch as committed + an exit-reason probe in `rex_app.cpp` (never compiled — see below) | 2 | 2 | 0 | 12.0 / 64.6 s | 228, 289/s |
| G | `kMaxGuestOutputPaintEffects` forced back to 1 (the non-Fable2 value) | 4 | 4 | 0 | 5.0 / 5.2 / 10.6 / 13.2 s | 227–281/s |

Armed-build total this pass (A1, B, F, F', and the two §7.1 runs): **9 self-exits
in 10 launches**. Controls: A0 (prebuilt DLLs, run before the first arm and again
after the last one) and E (option OFF, two fresh builds) — **4 launches, 4
survivals**, no self-exit in any of them; §5's option-OFF control is a fifth.

### The three suspects, one at a time

1. **The extra `present_*` cvars and the config plumbing they feed — CLEARED.**
   Instrumentation first, because it makes the exclusion structural rather than
   statistical: `BuildGuestOutputPaintConfigFromCVar` runs **once** (from
   `InitializeCommonSurfaceIndependent`, logged `bisect: paint config from cvars:
   effect=0 cas=0.0000 fsr_sharp=0.2000 max_passes=4 quality=0 dither=false`), and
   `SetGuestOutputPaintConfigFromUIThread` is **never called at all** (the probe at
   its entry logged zero calls in the whole session) — nothing in the runtime or the
   game calls it, so its FidelityFX comparison blocks are dead code here. Compiling
   the six cvars and the config population out as well (arm D) left the rate
   unchanged at 5/6 self-exit.
2. **The `guest_output_ffx_*` pipeline set — CLEARED.** Arming the build with the
   root-signature block and every FidelityFX PSO case compiled out leaves exactly
   the plain build's set (`bisect: guest output PSOs after init: 0 intermediate, 2
   final (of 9 effects)` versus `4 intermediate, 8 final` with the code in). Still
   self-exits: arm C 1/1, arm D 5/6.
3. **The intermediate-texture bookkeeping — CLEARED, and vacuously so.** In a
   bilinear run the presenter never allocates an intermediate texture at all: the
   probe at the creation point logged **zero** allocations in every bilinear run
   (the loop requests `(0,0)` for all `i` when `effect_count == 1`). There is no
   multi-pass bookkeeping to bisect until an FSR pass is actually scheduled.

Also cleared, this pass, by rate rather than by one run:
`kMaxGuestOutputPaintEffects` back to 1 (arm G, 4/4 self-exit) — so the bigger flow
arrays / descriptor counts are not the cause either, which corroborates §5's
single-run array-size test with four more launches.

### What is left inside the guard

Every code path that *runs* in a bilinear launch has now been compiled out and the
behaviour did not change, so the remainder has to be something that does not need a
running code path:

- the seven vendored `guest_output_ffx_*` DXIL blobs compiled into the runtime
  image (the option adds ~73 KB to `rexruntime.dll`: 9 668 608 B armed versus
  9 595 392 B plain — arm C keeps the `#include`s, only the PSO cases go);
- FidelityFX-guarded code with no executed path in a bilinear run: the
  effect-name `switch`, `ParsePresentEffect`'s `cas`/`fsr*` branches, the
  `LogTemporalFsr*` helpers, the extra `switch` cases in the paint loop, and the
  larger per-paint `effect_constants` union on the stack;
- `GuestOutputPaintConfig`'s FidelityFX fields (layout only).

So the shape is now: **data/layout or a timing-sensitive race that the armed build
shifts, not a logic defect in the three places the previous pass named.**

### The `WAIT_REG_MEM` climb is a symptom, not the signature

The previous pass read the failure as a frame-pacing stall from the
`WAIT_REG_MEM` rate climbing 230 → 685 → 917/s. That does not hold across the runs
above: self-exits end at 201, 207, 215, 227, 229, 230, 234, 274, 289, 675, 909, 910
and 911/s, and surviving runs sit at 132–306/s. Arm D ended with a **flat 230/s**
and no stall at all. The high numbers appear when the guest stops submitting frames
(it is already on its way out); they are the consequence, not the cause. The guest
main thread simply returns — `Execution complete` — with no error, no
`Window closing`, and nothing from the runtime explaining why.

### Where to go next (the cheap tests, in order)

1. **Ask the guest why.** The runtime logs nothing at the exit point. `Execution
   complete` is emitted by `ReXApp::LaunchModule` in `src/ui/rex_app.cpp`, which is
   **not** part of the `rexui` target and not in the runtime DLL's build graph (it
   is compiled by the game exe), so a reason probe is a *game* rebuild, not an SDK
   one: log `X_KTHREAD::exit_status` / `last_error` right at `OnGuestThreadExit` in
   the module-thread lambda. That was attempted here inside the SDK and could not
   take effect — `git grep rex_app.cpp build/build.ninja` is empty.
2. **Data-presence test for the blobs**: replace the seven `guest_output_ffx_*_ps.h`
   includes with zero-length arrays (no PSO uses them) and re-run — a rate drop
   names the blobs, a flat rate excludes the image-size theory.
3. **Present-path timing**: same armed build with `present_dither=1` (one extra
   shader branch) and with a different swap-chain size — if the rate tracks
   *anything* that changes present timing, it is a race in the present handshake,
   not the upscaler.

### Artefacts from this pass

- `out/bisect-armCD/` — arm D runtime (`rexruntime-armCD.dll`, md5 `915758d5…`).
- `out/bisect-kmax1/` — arm G runtime (md5 `d2d4d26d…`).
- `out/fsr-clean/` — the patch as committed, rebuilt after the bisect (md5
  `13a5d065…`); this is the binary the FSR re-verification in §7.1 used.
- `out/off-build/` — the option-OFF control build (md5 `a27a9a5b…`).
- `out/upscale-dumps/verify-bilinear/`, `verify-fsr/` — the re-verification dumps.

### 7.1 FSR re-verified after the bisect

Armed build `13a5d065…`, same layout, dumps at paint 300 / 700 (every 400):

| run | chain logged |
|---|---|
| `verify-bilinear` | `1 pass(es): #0 bilinear -> 2560x1440` |
| `verify-fsr` | `2 pass(es): #0 fsr-easu -> 2560x1440 #1 fsr-rcas -> 2560x1440` |

Six dumps per run, all 3440x1440. Both runs then self-exited (16.7 s and 13.6 s
after first paint) — expected, arms A1/F do the same. Metric on the pair: the two
runs are **not** the same video frame this time (whole-frame RMSE 2.9/255 at paint
300, 16.2/255 at paint 700, versus 0.56 for the frame-matched pair in §4), so only
the crop is comparable: the busiest 900x240 text region gains Laplacian std
1.106 → 2.026 (**+83 %**) at paint 300 and 1.234 → 3.120 (**+153 %**) at paint 700.
The pass still runs; the frame-matched numbers stay §4's.

## 8. SDK reproducibility: what is captured, and the patch that closes the gap

The SDK tree at `/home/feral/toolchains/rexglue-sdk` (HEAD `cc5f03d`) carries
uncommitted modifications to **8** files (5 at the time the card was written; the
FSR-1 raster patch adds the other 3). Mapping each against the patches tracked in
`thirdparty/`:

| file | tracked patch | state |
|---|---|---|
| `CMakeLists.txt` | `rexglue-sdk-fsr1-raster.patch` | exact |
| `include/rex/ui/d3d12/d3d12_presenter.h` | `rexglue-sdk-fsr1-raster.patch` | exact |
| `src/ui/CMakeLists.txt` | `rexglue-sdk-fsr1-raster.patch` | exact |
| `src/ui/d3d12/d3d12_presenter.cpp` | `rexglue-sdk-fsr1-raster.patch` | exact |
| `include/rex/perf/counter.h` | `rexglue-sdk-local.patch` (partial) | **was not reproducible** |
| `src/core/perf/counter.cpp` | none | **was not reproducible** |
| `src/system/runtime.cpp` | none | **was not reproducible** |
| `src/graphics/d3d12/command_processor.cpp` | none | **was not reproducible** |

`rexglue-sdk-local.patch` does **not** apply to the pinned commit at all (it fails
on `src/graphics/command_processor.cpp` and `src/ui/vulkan/vulkan_presenter.cpp`),
so it cannot reproduce the tree — and `tools/setup_sdk_src.cmd` pins
`f5337cdc…` while the built tree is at `cc5f03d`, which is the root of that drift.

What the four uncovered files actually are (two features, not drift):

- **perf CSV recorder** — `counter.cpp` + `runtime.cpp` + `counter.h`: wires the
  already-exported `perf_log_csv` cvar / CSV writer, which nothing used to read
  (`REX_PERF_LOG_CSV=<path>` wrote no file). `StartCsvLogFromCvar()` is called from
  `Runtime::Setup`, `WriteCsvFrame()` from `ResetFrameCounters()`, `FlushCsv()`
  from `Runtime::Shutdown()`.
- **Fable 2 vertex-constant dump probe** — `d3d12/command_processor.cpp`: an
  env-gated, read-only probe (`FABLE2_VC_DUMP`, `_EVERY`, `_PER_FRAME`, `_LO/_HI`)
  that appends vertex-constant-block snapshots from both register-write paths.

Both are captured as **`thirdparty/rexglue-sdk-perf-csv-and-vc-dump.patch`**
(4 files, 165 insertions / 2 deletions), generated against the pinned commit.

**Verified reproduction**: on a clean worktree of `cc5f03d`, applying
`rexglue-sdk-fsr1-raster.patch` and then
`rexglue-sdk-perf-csv-and-vc-dump.patch` reproduces **all eight** modified files
byte-for-byte (`diff -q` identical for every one, no extra files). That pair, on
the pin, is the durable state; nothing was committed to the SDK tree itself.
`tools/setup_sdk_src.cmd` now applies the new patch after the FSR one, with the
same "only if it applies cleanly" guard.

§9 adds a **ninth** modified file (`src/ui/rex_app.cpp`, the exit-reason probe),
captured as `thirdparty/rexglue-sdk-guest-exit-status-probe.patch` — see §9.3.

## 9. Exit-status pass (kanban `t_42fc19a7`) — the guest does not quit; the host faults

### 9.1 What this pass changed about the question

The card's premise (and §7's) was that the guest main thread *returns* and nobody
knows why. **That is not what happens.** With the guest-exit probe in place and
`WINEDEBUG=+seh`, the failure is a hard **`EXCEPTION_ACCESS_VIOLATION`
(0xC0000005)** inside `rexruntime.dll`. The process does not shut down, does not
return an exit code from the guest, and never reaches `Execution complete` —
Wine kills it, and the lane records **exit code 5** (which is exactly what every
"self-exit" in §5/§7 was: a crash, not a quit).

So the earlier wording — "the guest exits itself for an unknown reason" — was
the wrong frame. There is no guest exit to explain; there is a crash to fix.

### 9.2 The crash, exactly

From `WINEDEBUG=+seh` on three separate armed launches (`fable_2_040/044/045`,
logs kept, raw trace beside them):

```
code=c0000005 (EXCEPTION_ACCESS_VIOLATION) flags=0
info[0]=0000000000000000        ; read (not write)
info[1]=FFFFFFFFFFFFFFFF        ; faulting address = -1, i.e. a NULL base + offset
rip=00006ffffc5bc690            ; rexruntime.dll + 0xEC690
rsp=000000000010f620 rbp=000000000010f6e0   ; identical in all three runs
```

The module base changes per run (ASLR), the **RVA does not**: `+0xEC690` in all
three traces, with an identical `rsp`/`rbp`, i.e. the same call path at the same
depth. This is a deterministic site, not a race window.

The faulting instruction (disassembled from the armed DLL) is

```
1800ec68c:  movq 0x10(%rcx), %r8
1800ec690:  cmpb $0x0, 0x19(%r8)      <-- fault
```

`0x19` is the MSVC `std::_Tree_node` **isnil** byte (colour at `+0x18`, nil at
`+0x19`); the code is walking a red-black tree (`std::map`/`multimap`) and
dereferences a node pointer taken from a node that is no longer a live tree
entry — the classic shape of an **iterator/nodes invalidated under the
iterator**, i.e. the walk is reading the nil flag through a null/garbage node.
Registers just before the fault (`rcx=0x2d8211`, `rdx=0x2d8211`, `r8` derived
from `rcx+0x10`) show the walk had already moved inside the tree.

Where: `.pdata` puts the containing function at `0xEC650..0xEC751` (257 B, fault
at `+0x40`). The DLL carries no COFF symbols and was built without `/DEBUG`, so
there is no PDB to name it exactly; the nearest **export** below it is
`rex::ui::Presenter::RefreshGuestOutput` (`0xEA160`), and the frame sits `0x4F0`
into that region — a nested/out-of-line helper of the presenter's refresh path.
The unwind chain (`+0xEC690` → `+0x119867` → `+0xE9D5B` → `+0xF5391` →
`+0xFF111` → `+0xFEE97` → two `fable_2.exe` frames) ends in
**`SDLWindowedAppContext::RunMainMessageLoop`** (`0xFEE50..0xFEF8B`,
`0xFEFC0..0xFF458`): the fault is on the **UI/present thread**, not on the guest
module thread.

The presenter stores the iterator state in the object at `this+0x1e8` with a flag
at `this+0x1f0` — the shape of a **saved iterator + has-value pair**. The only
`std::multimap` in `Presenter` is `ui_drawers_`, and it is driven exactly that
way: `AddUIDrawer`/`RemoveUIDrawers` (`src/ui/presenter.cpp:735-780`) keep
`ui_draw_next_iterator_` alive across a draw execution and `erase()` other nodes
while it is held. That is the strongest candidate for the node the walk reads,
and it is testable (erase-during-walk assertion / copy the iterator list at walk
start). It is a **candidate named by the machine code shape + the only matching
container**, not yet proven by a bisect of its own.

### 9.3 The exit-status probe itself (test 1), and why it returned nothing

The probe was implemented as the card asked — `guest_object<X_KTHREAD>()`'s
`exit_status` / `last_error` at `OnGuestThreadExit`, in the module-thread lambda
of `src/ui/rex_app.cpp` (compiled by the **game** exe; `win-amd64/share/rexglue/
rex_app.cpp` is the copy the game build actually compiles, so both were edited).
It is a **game** rebuild, as §7 predicted; the game exe is
`out/build/wincross-release-v2r/fable_2.exe` (md5 `4b6dfc55…`, plain pre-probe
exe kept at `out/exe-plain/fable_2.exe`, md5 `558e7a9a…`).

Three attempts were needed and each one taught something the doc should keep:

1. `guest_object<X_KTHREAD>()` **does not link** from a consumer exe — the
   `XObject::memory()` accessor it calls inline is not exported from
   `rexruntime.dll`. Read the struct through
   `runtime_->kernel_state()->memory()->TranslateVirtual<...>(...)` instead.
2. The probe wrote to the **log sink first**, and its lines vanished: in 2 of 12
   armed runs the log recorded the module thread's return (`guest module thread
   returned (exit probe reached)`, `fable_2_037/038`) and then the log simply
   **stops** — the process dies with the logger's buffer unflushed. So the probe
   was rebuilt to append to `probe-exit.txt` with `fopen`/`fprintf`/`fclose`
   (unbuffered per line) *and* to the log.
3. With that build, **`probe-exit.txt` is never created in any run**: the
   module-thread continuation does not run at all in the decisive cases, because
   the UI thread's access violation kills the process while the guest thread is
   still parked. This is the one-line answer to the card's test 1: **the exit
   status cannot be obtained, because there is no exit — the process is destroyed
   by a crash on another thread.** (In the two runs where the continuation *did*
   run, the crash still followed within the same second, before the file write;
   the file probe was not reached even then.)

The probe stays in the tree, captured as a new tracked patch, because it is the
only instrument that can tell "guest returned" from "process crashed" in future
runs — and it is inert: 38 inserted lines, all inside the module-thread lambda,
run once per launch at most.

### 9.4 This pass's launches (rates, not single runs)

Same layout and lane as §7 (`game-job.sh`, operator default DP-1, window placed
never activated, audio muted), bilinear probe, 75 s survival bar
(`/usr/bin/timeout -k 15 75`), `--gpu-wait 0` so the advisory gate cannot stall a
batch. Logs `out/launchcheck/logs/fable_2_0NN.log` (035–050), ledger
`~/.hermes/logs/game-jobs.jsonl`. Free VRAM was 3.8–4.6 GB throughout (the
resident `qwen3-tts` server holds ~4.9 GB); the same pressure sat on every arm
including the controls, and no other game or job held the lane at any point.

| # | arm | runs | outcome | time alive after 1st paint | last-second `WAIT_REG_MEM` |
|---|---|---|---|---|---|
| 035 | control: prebuilt 0.10.0 DLLs (before the batches) | 1 | survived 75.6 s | — | 319/s |
| 036 | armed + probe r1 | 1 | crash (rc 5) | 53.5 s | 911/s |
| 037 | armed + probe r2 | 1 | crash (rc 5), module thread returned first | 28.5 s | 910/s |
| 038 | armed + probe r3 | 1 | crash (rc 5), module thread returned first | 7.1 s | 189/s |
| 039 | armed + probe r4 | 1 | crash (rc 5) | 12.4 s | 199/s |
| 040 | armed + probe r5, `+seh` | 1 | crash (rc 5), **RIP +0xEC690** | 9.9 s | 201/s |
| 041 | armed + probe A1 | 1 | crash (rc 5) | 1.3 s | — |
| 042 | armed + probe A2 | 1 | **survived 75.8 s** | — | 290/s |
| 043 | armed + probe A3 | 1 | crash (rc 5) | 1.3 s | — |
| 044 | armed + probe, `+seh` (1) | 1 | crash (rc 5), **RIP +0xEC690** | 1.7 s | — |
| 045 | armed + probe, `+seh` (2) | 1 | crash (rc 5), **RIP +0xEC690** | 16.9 s | 187/s |
| 046 | **test 3a**: `present_dither=1` | 1 | crash (rc 5) | 8.7 s | 207/s |
| 047 | **test 3a**: `present_dither=1` | 1 | crash (rc 5) | 23.7 s | 903/s |
| 048 | FSR re-verify (`present_effect=fsr`, dumps) | 1 | **survived 76.8 s** | — | 269/s |
| 049 | control: prebuilt DLLs (closing bracket) | 1 | survived 75.6 s | — | 292/s |
| 050 | control: option-OFF source build (closing bracket) | 1 | survived 75.6 s | — | 640/s |

**Rates.** Armed bilinear (036–041, 043, 044–047): **11 crashes in 12 launches**;
one survivor (042). Controls in this session **3 launches, 3 survivals, 0
crashes** (035, 049 prebuilt; 050 option-OFF), and with §7's four and §5's one
the control tally is **8 survivals in 8 control launches**. This reproduces §7's
9/10 armed versus 0/8 control with the failure now *identified* rather than
merely counted.

Two details worth keeping:

- the crash time after first paint is far wider than §7 recorded — 1.3 s to
  53.5 s, with two launches dying **on the first presented frame** (041, 043) and
  two before a single `WAIT_REG_MEM` counter tick — so "~30-40 s" was a sampling
  artefact of short batches;
- the last-second `WAIT_REG_MEM` is confirmed *again* as uninformative: crashes
  ended at 187–911/s and a **surviving control ended at 640/s** (050), the
  highest rate of any run in this session that did not crash.

### 9.5 Test 3a (present timing) and tests 2/3b that were not reached

- **Test 3a, `present_dither=1` — rate flat.** 2 launches, 2 crashes, and the
  chain line changes as expected (`1 pass(es): #0 bilinear-dither -> 2560x1440`
  in both). An extra shader branch in the present path moves nothing. **Sample
  size 2 — this is direction, not a rate**; the baseline is 11/12, so 2/2 is what
  the baseline predicts and no more.
- **Test 2 (zero-length DXIL blobs) — NOT RUN.** It needs a fresh
  `rexruntime.dll` build (~4 min) plus ≥5 launches, and the human gate on this box
  expires 2026-11-04 15:35 (it is not renewable by an agent). Running three
  launches instead of five would have produced a number the card explicitly
  refuses to accept, so it was left to the next pass with the gate time intact.
- **Test 3b (different swap-chain size) — NOT RUN**, same reason.

Note that test 2's premise has also weakened: it was designed to test whether
*image size/layout* changes the rate of a **guest exit**. The exit is now known to
be a deterministic fault in presenter refresh code, so image size is a much less
promising lever than "does the crash survive at all without the FidelityFX-gated
presenter" — which §5's controls already answer (it does not).

### 9.6 FSR re-verified (no SDK rebuild this pass)

No SDK rebuild was needed for anything in §9 except the game exe, so the armed
runtime in use is **byte-identical** to §7.1's (`out/fsr-clean/rexruntime.dll`,
md5 `13a5d065…`). It was re-verified anyway, on the probe exe, launch 048:
chain logged `2 pass(es): #0 fsr-easu -> 2560x1440 #1 fsr-rcas -> 2560x1440`,
**10 dumps** written at 3440x1440 (`out/upscale-dumps/verify-fsr2/
present-final-0{3000,7000,…}.ppm`, paints 300–3900 every 400), and the run then
**survived the full 76.8 s bar**. Every bilinear arm in §9.4 logged
`1 pass(es): #0 bilinear -> 2560x1440` or `#0 bilinear-dither` in the same
breath, so the presenter chain is live in every arm that crashed as well.

### 9.7 Recommendation (one line, for Marcus)

**Do not ship the armed build as it stands:** it crashes 11 times in 12 launches
at a deterministic `rexruntime.dll+0xEC690` fault, so keep it on the branch but
revert it from anything the operator runs, until the `ui_drawers_`-shaped
iterator walk in the presenter refresh path is fixed or disproved.

### 9.8 Artefacts from this pass

- `thirdparty/rexglue-sdk-guest-exit-status-probe.patch` — the exit-reason
  probe (38 lines, `src/ui/rex_app.cpp`), the ninth modified SDK file; §8's pair
  still reproduces the other eight unchanged.
- `out/exe-plain/fable_2.exe` — the pre-probe game exe (md5 `558e7a9a…`), kept so
  the plain build can be staged again.
- `out/upscale-dumps/verify-fsr2/` — the §9.6 dump pair.
- `out/launchcheck/logs/fable_2_0{35..50}.log` and `out/launchcheck/last-run.out`
  (the `+seh` trace of the last instrumented run) — the per-run evidence.


## 10. Iterator-invalidation pass (kanban `t_683bb4e2`) — the function is named, the instrument is built, the measurement is blocked

**Bottom line: the site is now identified rather than inferred — `+0xEC690` is
`rex::ui::Presenter::ExecuteUIDrawersFromUIThread` — and the detector plus the
fix shape are built into a staged DLL. But `REX_HAS_FIDELITYFX_SDK` makes the
option-OFF and option-ON builds disagree about the **layout of `Presenter`
itself** (`ui_drawers_` at `0x1B8` vs `0x1C8`), which is an armed-only binary
difference nobody had recorded. No launches were possible this pass: the human
gate (`/run/user/1000/hermes-game.allow`) expired **2026-11-04 15:35:05**, so
the crash rate of neither the instrumented build nor the fix was measured. The
hypothesis is therefore **neither confirmed nor refuted by measurement** — read
§10.5 for what the code says, and §10.7 for the one-batch test that settles it.**

### 10.1 The function at `+0xEC690`, named from symbols (deliverable 1)

The DLL has no COFF symbols and no PDB, but it was built from this tree by this
toolchain, so the **compiler's own symbol table for the same compile** still
exists in the build directory:

```
build/src/ui/CMakeFiles/rexui.dir/presenter.cpp.obj
  .text+0x3ae0  ?ExecuteUIDrawersFromUIThread@Presenter@ui@rex@@IEAAXAEAVUIDrawContext@23@@Z
```

The DLL function at RVA `0xEC650` and that object symbol are **byte-for-byte
identical for all 257 bytes** — same instruction bytes, same displacements, even
the same internal branch offsets (`DLL 0xEC650+0xEC` == `obj 0x3ae0+0xEC`). So
the containing function is named from the compiler's own record, not inferred:

- `0xEC650..0xEC751` = **`rex::ui::Presenter::ExecuteUIDrawersFromUIThread(rex::ui::UIDrawContext&)`**
- the fault at `+0xEC690` is `+0x40` into it;
- it is a **separate out-of-line method, not a nested helper of
  `RefreshGuestOutput`** — §9.2's "0x4F0 into that region" is wrong by an order
  of magnitude (`0xEC650 - 0xEA160 = 0x24F0`); the nearest-export heuristic was
  the only thing available without symbols, and it pointed one function too far
  down.

Decoded from the machine code, this is the drawer walk and nothing else:

| `this` + | member |
|---|---|
| `0x1c8` | `ui_drawers_` (address of the `std::multimap`) |
| `0x1d8` | `ui_draw_current_` |
| `0x1e0` | `ui_draw_current_z_order_` |
| `0x1e8` | `ui_draw_next_iterator_` (`_Ptr` only — Release, no iterator debugging) |
| `0x1f0` | `is_executing_ui_drawers_` |

and node `+0x00 _Left`, `+0x08 _Parent`, `+0x10 _Right`, `+0x18` colour,
`+0x19` **isnil**, `+0x20` key (`z_order`), `+0x28` `drawer`, `+0x30`
`last_draw` — a plain MSVC `std::_Tree_node`, which is why `0x19(%r8)` is the
faulting operand. `+0xEC690` sits **inside the inlined
`std::_Tree_iterator::operator++`** that computes `it_current =
ui_draw_next_iterator_++`: it reads `rcx->_Right` for the node the iterator
currently names, called with `rcx` = the *current* node of the iteration.

### 10.2 What the code actually does (and what that means for the hypothesis)

`src/ui/presenter.cpp:1280` (`ExecuteUIDrawersFromUIThread`; line numbers in this
section are the pristine ones, +7 in the patched file) advances the
iterator **before** calling `Draw()` and keeps the advanced iterator in the
object (`ui_draw_next_iterator_++` is `mov %rdx,0x1e8(%rsi)` *before* the
virtual `Draw` call at `+0xEC70A`). The next iteration therefore dereferences
**the stored iterator**, not a freshly derived one — exactly the shape §9.2
described.

The mutation surface, exhaustively (grepped across `src/` and `include/`):

- the **only** mutators of `ui_drawers_` are `AddUIDrawerFromUIThread` and
  `RemoveUIDrawerFromUIThread` (`presenter.cpp:731-780`);
- there is **no** `clear()`, no direct `erase()` anywhere else, and no other
  container that the presenter iterates this way;
- **both** mutators already advance the iterator when the node being erased *is*
  the next one (`presenter.cpp:750`, `:775`), which is the complete guard for a
  `multimap::erase`: only the erased element's iterator is invalidated.

So **single-threaded, the invalidation this card hypothesises cannot happen** —
the guard covers it. The walk runs on the UI thread only: the sole call site is
`d3d12_presenter.cpp:1305`, inside `PaintAndPresentImpl`, reached from
`PaintAndPresent(draw_ui)` in `PaintFromUIThread` (`presenter.cpp:554`); the
guest-output thread calls `PaintAndPresent(false)` (`presenter.cpp:704`) and
never enters the walk.

Two things follow, and they are the useful result of this pass:

1. **§9.2's "not a race" does not hold.** An identical RVA, `rsp`/`rbp` and call
   depth are what you get for *any* crash at a fixed instruction in a fixed
   function; they say nothing about whether another thread mutated the container
   first. Determinism of the site is not determinism of the cause.
2. If the stored iterator is dangling, the mutation has to come from **outside**
   the guarded paths — either a thread other than the painting UI thread
   (`is_executing_ui_drawers_` is a plain `bool` and `ui_drawers_` has no mutex,
   so a cross-thread `Add`/`Remove`/`AddUIDrawerFromUIThread` is unsynchronised
   and the guard is then meaningless; note also that in Release every
   `assert_false(is_executing_ui_drawers_)` / `assert_true(is_in_ui_thread_paint_)`
   is compiled out, `CMakeLists.txt:146` `-DNDEBUG`), or the node is corrupted
   from elsewhere.

Two latent defects found while reading, both worth fixing regardless:

- `ui_draw_current_z_order_` (`presenter.h:1023`) has **no initialiser**. A
  drawer added from another thread before the first `Draw()` of a walk reads an
  indeterminate value in `AddUIDrawerFromUIThread:760`.
- `AddUIDrawerFromUIThread:761` **dereferences the held iterator**
  (`ui_draw_next_iterator_->first`) when it is not `end()`. If the iterator is
  already dangling, *this* is the first read of freed memory, and the crash at
  `+0xEC690` can be the second symptom rather than the first.

### 10.3 The instrument (deliverable 2) — built, staged, not yet run

`thirdparty/rexglue-sdk-ui-drawer-instrumentation.patch` (233 lines,
`src/ui/presenter.cpp` only, verified to reproduce the modified file
byte-for-byte from the pinned `cc5f03d`) adds, all env-gated and inert when the
variables are unset:

| env | effect |
|---|---|
| `REX_UI_DRAWERS_DETECT=<path>` | before every walk iteration, checks that the iterator names a node that is **live in `ui_drawers_`** by scanning the tree; on failure logs `DEAD ITERATOR walk N: next node <p> is not among the N live node(s)` with `ui_draw_current`, `ui_draw_current_z_order`, then **resyncs** to the first undrawn live node instead of walking the freed one. Also logs every `Add-erase` / `Remove-erase` with `during_walk=` and `erased_is_next=`, every `Add-insert-in-walk`, and per-walk `enter`/`draw`/`exit` lines (unbuffered `fopen`/`fprintf`/`fflush`, because §9.3 showed the log sink loses its buffer on this crash) |
| `REX_UI_DRAWERS_FIX=1` | the fix shape: **no iterator is held across `Draw()`**. Each step re-derives the next drawer from the live map (first entry not yet drawn this frame with `z_order >= ui_draw_current_z_order_`), so nothing the loop keeps can be erased under it. Semantics: same forward-only Z ordering, same "never draw twice per frame", and drawers added during the walk at the current-or-higher Z are still drawn in the same frame |

Built against the armed configuration (`REXGLUE_ENABLE_FSR1_RASTER=ON`) and
staged, ready to drop into `out/launchcheck/` in seconds:

```
out/drawer-detect/rexruntime.dll       f06ca75d4ec89c34bbf89898b2af04c5
out/drawer-detect/rexgpu-xenos.dll     6e405575fa8017779a8b104545c479fc
```

The walk is still identifiable in that DLL and still uses the armed offsets
(`0x1c8`/`0x1d8`/`0x1e8`/`0x1f0`), now at RVA `0xECC14` because the fix branch
precedes it. Nothing was staged into `out/launchcheck/` — that still holds the
option-OFF control pair (`rexruntime.dll a27a9a5b…`), so the operator's lane is
exactly as §9.4 left it.

### 10.4 Why the option changes the binary at all (deliverable 4, first half)

This is the finding §9 was missing, and it is a **binary** fact, not a theory:
`REX_HAS_FIDELITYFX_SDK` adds four data members to
`Presenter::GuestOutputPaintConfig` (`cas_additional_sharpness_`,
`fsr_max_upsampling_passes_`, `fsr_sharpness_reduction_`, `fsr_quality_mode_`,
`presenter.h:330-333`, setters at `:300-314`). `GuestOutputPaintConfig` is a `Presenter` member, so
**every member after it moves by `0x10`** — including the drawer state. Measured
in all three builds with the same byte motif:

| build | `ui_drawers_` | `ui_draw_next_iterator_` | `is_executing_ui_drawers_` |
|---|---|---|---|
| `out/fsr-clean` (armed, `REXGLUE_ENABLE_FSR1_RASTER=ON`) | `0x1C8` | `0x1E8` | `0x1F0` |
| `out/drawer-detect` (armed + instrumentation) | `0x1C8` | `0x1E8` | `0x1F0` |
| `out/off-build` (option OFF) | `0x1B8` | `0x1D8` | `0x1E0` |

The define is `PRIVATE` to the `rexui` target (`src/ui/CMakeLists.txt:124`,
`:135`), so **no consumer of the SDK inherits it** — the game exe and the
`rexgpu-xenos` plugin are compiled against the option-OFF layout while the
armed DLL runs the option-ON layout. Today's checks say that hazard is latent
rather than live:

- the game exe (`rex_app.cpp` in `share/rexglue/`) only passes `Presenter*`
  around (`SetPresenter`), never touching a member inline; the game build tree
  contains no `REX_HAS_FIDELITYFX_SDK` anywhere in its compile flags;
- no virtual function is gated, so the vtable is identical;
- the plugin (`src/graphics/`) references none of the gated structs
  (`GuestOutputPaintFlow` / `GuestOutputPaintConfig` / `GuestOutputPaintEffect`)
  and only uses `D3D12GuestOutputRefreshContext` accessors, whose layout does not
  depend on the define;
- `D3D12Presenter::Create` (`d3d12_presenter.h:72`) allocates the presenter
  **inside** `rexruntime.dll`, so no `sizeof` is taken by a mismatched TU.

So the layout delta is a **real armed-only trap with no known consumer** — it is
on the list, not at the top of it.

### 10.5 Why the option makes an *inert* path crash (deliverable 4, second half)

The decisive awkward fact from §9.4: every crashing armed launch was
**bilinear** (`1 pass(es): #0 bilinear`). With `present_effect=bilinear` none of
the FSR code runs, yet the armed build crashes 11/12 and the option-OFF build
0/8. So "the extra shader/pipeline plumbing perturbs the refresh timing" cannot
be the mechanism via the FSR passes themselves — the difference has to be
something the define changes *structurally*, present even when the chain is one
bilinear pass. Enumerated from the source, that is exactly:

1. the `Presenter` layout `+0x10` (§10.4) and, with it, every offset the walk
   uses;
2. `kMaxGuestOutputPaintEffects` `1` → `6` (`presenter.h:487-495`), i.e. the
   `GuestOutputPaintFlow` local in `GetGuestOutputPaintFlow` grows, and the
   flow's loop bounds change;
3. extra root signatures + the extra `present_*` cvars registered at startup
   (restart-gated, so they only matter as construction work);
4. everything else — code addresses, code size, allocation order.

None of those is a *semantic* change to the drawer walk, which is why the
hypothesis "the walk is invalidated" and the observation "only the armed build
crashes" are still compatible with **both** a cross-thread mutation (C1) and a
corruption of the node from elsewhere (C3). Ranked for the next pass:

- **C1 — cross-thread mutation of `ui_drawers_` while the UI thread walks it.**
  Test: `REX_UI_DRAWERS_DETECT` fires, and the log names the same node that an
  `Add-erase`/`Remove-erase` line just touched. Near-conclusive if it fires.
- **C2 — the `+0x10` layout delta reaching a mismatched TU.** Test: today's
  evidence says no consumer exists; it moves up only if a new caller appears.
- **C3 — memory corruption of the node from elsewhere in the armed build**
  (§9.5's "FidelityFX dead code" remainder). Test: the detector stays silent for
  a whole crashing launch — the walk then dies on a node that was never erased,
  which refutes the invalidation hypothesis and points at corruption.
- **C4 — presenter/paint teardown interleaving** (`SetPresenter(nullptr)` while a
  walk is live). Test: same detector, teardown logged via the erase lines while
  `is_executing_ui_drawers_` is set.

### 10.6 Fix shape (deliverable 3) — built, not measured

`REX_UI_DRAWERS_FIX=1` implements the card's option "otherwise stop holding an
iterator across an erase window" as a **re-derived walk** rather than a copied
snapshot, because a snapshot would drop drawers added mid-frame (the behaviour
the guards at `presenter.cpp:800`/`:837` exist to preserve). If it measures ~0
against a bracketing control, the invalidation hypothesis is confirmed and the
mechanism is whatever the detector says erased the node. If the rate is
unchanged, the hypothesis is **refuted** and the remainder is C3 (corruption) —
the fix removes the *only* way this loop can read freed memory, so a crash that
survives it is not this loop's bug.

**No arm was run. No rate exists. This is not a null result, it is an
unmeasured one**, and the card's own rule (5+ runs against a bracketing control,
interleaved A B C C B A) is the bar.

### 10.7 The exact next batch (blocked only on the human gate)

The gate expired at **2026-11-04 15:35:05** — `game-job.sh --status` reports
`launch_allowed: false`, `reason: "allow marker expired at …15:35:05"`,
`expires_in_s: -1906`. Per the card the marker is never renewed by an agent, so
this pass stops here rather than run a 2-launch sample it would have to
disqualify.

When a gate exists again, the batch is mechanical (each run is one 75 s lane):

1. stage `out/drawer-detect/*.dll` into `out/launchcheck/`;
2. **detector arm** — `REX_UI_DRAWERS_DETECT=Z:/…/out/drawer-detect/detect-armNN.txt`,
   `REX_PRESENT_EFFECT=bilinear`, 5 runs + one prebuilt control bracketing;
3. **fix arm** — same DLL with `REX_UI_DRAWERS_FIX=1`, 5 runs, control bracket;
4. interleave (`A B C C B A …`) so drift cannot correlate with arm; keep the
   resident `qwen3-tts` VRAM load equal (it was 4.0 GB free at the time of this
   pass — no arm ran, so nothing was confounded, but the next batch must hold it
   constant the way §9.4 did);
5. record per launch: outcome (rc 5 / survived), time alive after first paint,
   and whether `+0xEC690` recurs under `+seh`.

### 10.8 FSR re-verification (deliverable 6) — NOT DONE, and nothing was broken

An SDK rebuild **did** happen (the instrumented `rexruntime.dll` above), so the
card's re-verification rule was in scope — but re-verifying needs a launch, and
there was no gate. What protects the operator instead: **nothing was staged**;
`out/launchcheck/` still holds the option-OFF control pair from §9.4
(`rexruntime.dll a27a9a5b…`), and `out/fsr-clean/` (the armed reference,
`13a5d065…`) is untouched. The instrumented pair lives only in
`out/drawer-detect/`. The first launch of the next batch must still log the
chain (`2 pass(es): #0 fsr-easu … #1 fsr-rcas`) with `present_effect=fsr` plus
one dump pair before any rate is trusted.

### 10.9 Recommendation (deliverable 5, for Marcus)

**Keep the armed build off the operator's install, unchanged from §9.7.** This
pass did not weaken the case against it — it *strengthened* it, by removing the
guesswork about where it dies (a named presenter method, not an inferred helper)
and by finding a second armed-only difference in the same object (the `+0x10`
layout delta). But it did not produce the one thing that would let the build
come back: a measured crash rate for the fix. Until that exists, the armed build
is a known-11-in-12 crasher on a named instruction, and the branch keeps it
without the operator running it.

### 10.10 Artefacts from this pass

- `thirdparty/rexglue-sdk-ui-drawer-instrumentation.patch` — the detector + fix
  shape (233 lines, `src/ui/presenter.cpp`, reproduces byte-for-byte on the
  pinned `cc5f03d`); the tenth SDK change, and the first that is inert with no
  env var set.
- `out/drawer-detect/{rexruntime.dll,rexgpu-xenos.dll}` — armed build carrying
  it, `f06ca75d…` / `6e405575…`, staged but not installed anywhere.
- **Zero launches this pass.** Ledger `~/.hermes/logs/game-jobs.jsonl` has no
  entry from it; the only lane activity was `game-job.sh --status` (read-only,
  no allow needed).

**Superseded:** §10.3 (instrument unmeasured), §10.5 (the C1-C4 ranking),
§10.6 (fix shape unmeasured) and §10.7 (the blocked batch) are all answered by
**§11** — the measurements were run, and the cause turned out to be C2.

## 11. The same card, measured (kanban `t_683bb4e2`, second pass) — the erase hypothesis is refuted, the cause is named, and it is a cross-module layout collision

**Bottom line: `ui_draw_next_iterator_` is not invalidated by an erase — it is
overwritten, one byte per emulated vblank, by an inline method in the GPU plugin
that was compiled against the *option-OFF* layout of `Presenter`. The armed build
puts `ui_draw_next_iterator_` at `+0x1E8`; the plugin's `OnGuestVblank()` writes
`guest_vblank_count_` at `+0x1E8`. That is §10.4's "latent trap with no known
consumer" — it has a consumer, and it fires every vblank.**

24 launches through the lane, rates against a bracketing control: the armed build
crashed **6 of 6** times it ran without mitigation; every mitigated or option-OFF
arm survived **18 of 18** (§11.4).

### 11.1 What §10 could not see

§10 reasoned from the *container*: only `AddUIDrawerFromUIThread` and
`RemoveUIDrawerFromUIThread` can mutate `ui_drawers_`, both already advance the
iterator when they erase the node it names, therefore a single-threaded
invalidation "cannot happen" (§10.2) and the remainder had to be cross-thread
mutation (C1) or corruption (C3). It then ranked the `+0x10` layout delta (C2)
below both, on the grounds that "today's evidence says no consumer exists".

The measurement says otherwise, on both points:

- **No erase ever runs.** Across the seven instrumented armed launches
  (`detect-3/6/9/11/13/16/19`), **0** `Add-erase`, **0** `Remove-erase` and **0**
  `Add-insert-in-walk` events in **89,878 walks**. The erase guards §10.2 analysed
  are never even reached — the drawer list holds exactly one drawer from first
  frame to last and is never touched again after startup. So the guards are not
  the story, and neither is `RemoveUIDrawers`.
- **The corruption is structured, not random.** It lands on the same byte, in the
  same object, every time: `this+0x1E8`, +1 per hit. That is a layout collision,
  not a race on a container or an arbitrary overrun.

### 11.2 The cause, proven three ways

**(a) Source.** `include/rex/ui/presenter.h:195-201`:

```cpp
// called from the GPU VSync thread. Defined inline (not in presenter.cpp) so
// the GPU plugin - which holds the Presenter but does not link the rexui
// object library (symbols come via the curated rexruntime export table) - can
// call it without needing an exported symbol.
inline void OnGuestVblank() {
  guest_vblank_count_.fetch_add(1, std::memory_order_relaxed);
}
```

It is inline *by design*, precisely so a target outside `rexui` can call it. That
is the trap: an inline accessor bakes `offsetof(Presenter, guest_vblank_count_)`
into the **caller's** translation unit. The caller is
`src/graphics/graphics_system.cpp:339` (`presenter_->OnGuestVblank();`), which
belongs to target `rexgpu-xenos` (`src/graphics/CMakeLists.txt:19`), while
`REX_HAS_FIDELITYFX_SDK` is `target_compile_definitions(rexui PRIVATE ...)`
(`src/ui/CMakeLists.txt:124`, `:135`). So:

| member | `rexruntime` (armed, define ON) | `rexgpu-xenos` (define never applied) |
|---|---|---|
| `is_executing_ui_drawers_` (4 bools) | `0x1F0..0x1F3` | `0x1E0..0x1E3` |
| `guest_vblank_count_` (`atomic<uint64_t>`) | `0x1F8` | **`0x1E8`** |
| `ui_draw_next_iterator_` | **`0x1E8`** | `0x1D8` |

A `fetch_add(1)` compiled into the plugin therefore writes to `+0x1E8` — the low
byte of the armed DLL's saved drawer iterator.

**(b) Object code.** The plugin's own object file carries the write:

```
build/src/graphics/CMakeFiles/rexgpu-xenos.dir/graphics_system.cpp.obj
  incq 0x1e8(%rax)          # == OnGuestVblank(), option-OFF offsets
```

and the same instruction is in the shipped plugin
(`rexgpu-xenos.dll` +`0xD378`, +`0xE7DF`). In `rexruntime.dll` every access to
`+0x1E8` inside the presenter region is an 8-byte iterator move — the DLL never
writes a small value there. The two modules disagree about the same class.

**(c) Runtime.** A hexdump of 32 bytes at the *real* offset of the iterator
(computed as `&ui_draw_next_iterator_ - this`, so nothing is hardcoded), taken
immediately before and after `Draw()` (`REX_UI_DRAWERS_DETECT` on, launch 19):

```
walk 503 pre-draw  +488: 40 4d 2d 00 00 00 00 00 01 01 00 00 ...
walk 503 post-draw +488: 41 4d 2d 00 00 00 00 00 01 01 00 01 ...
DEAD ITERATOR walk 503: next node 00000000002D4D61 ... end=00000000002D4D60
```

`+488` is `0x1E8`. During one `Draw()`: byte 0 (`0x1E8`, the iterator's low byte)
goes `0x40 -> 0x41`, and byte 11 (`0x1F3`, `request_ui_paint_after_current_ui_
thread_paint_`) goes `0 -> 1`. The first is the plugin's vblank increment landing
on the iterator; the second is presenter.cpp's own honest write, at the *correct*
armed offset. Byte 24 (`0x200`, `guest_frame_count_` in the armed layout) is
untouched — and, as a consequence of the same collision, the armed build's
`guest_vblank_count_` at `0x1F8` is never incremented at all (not directly
observed: the pacer diagnostic that prints it does not fire under this config).

The fatal consequence, from the `+seh` launch 24 (armed baseline, no mitigation):

```
code=c0000005 (EXCEPTION_ACCESS_VIOLATION) addr=00006FFFFCAFC690
 info[0]=0000000000000000   info[1]=FFFFFFFFFFFFFFFF
 rip=00006ffffcafc690 rsp=... rbp=...
 r8=0100000000161df0
 rexruntime.dll + 0xEC690
```

`0x6FFFFCAFC690` is `+0xEC690` exactly as §9 recorded, `info[0]=0` (read) and
`info[1]=-1`. `r8 = 0x0100000000161df0`: the top byte of a node pointer has been
overwritten with `0x01` — the same one-byte corruption, on a different pointer
inside the same tree walk. `cmpb $0x0,0x19(%r8)` then reads unmapped memory.

### 11.3 The card's hypothesis: refuted

The card asks whether the walk "dereferences a node that `RemoveUIDrawers` erased
while `ui_draw_next_iterator_` was still holding it". **No.**

- `RemoveUIDrawerFromUIThread` and `AddUIDrawerFromUIThread` are never called:
  0 erases, 0 inserts, in 89,878 armed walks (§11.1).
- The iterator's *node* is never freed. What changes is its *low byte*, by an
  increment from another module, at a fixed offset.
- The erase guards at `presenter.cpp:750`/`:775` are correct for the case they
  cover, and §10.2's reading of them stands. They simply never run here.

What survives from the hypothesis is the weaker, structural half: **the walk is
the crash site because it dereferences a stored iterator that nothing revalidates
across `Draw()`.** Detection + resync and the fix shape both remove the crash
(§11.4/§11.6). But the thing that makes the iterator wrong is not an erase, and a
fix placed in the drawer list cannot remove it.

### 11.4 Rates (24 launches, this session, same lane)

Lane `game-job.sh` (operator default DP-1, window placed never activated, audio
muted), `--timeout 130 --gpu-wait 0`, inner bar `/usr/bin/timeout -k 15 75`,
`REX_PRESENT_EFFECT=bilinear`, interleaved so drift cannot track arm. Arms:
**B** = armed build as shipped (`out/fsr-clean`, `13a5d065…`); **D/Z** = armed +
detector; **F** = armed + fix shape; **C** = option-OFF build (`a27a9a5b…`);
**O** = option-OFF + detector; **V** = FSR re-verify.

| arm | launches | crashes (rc 5) | survived | detections |
|---|---|---|---|---|
| **B** armed baseline | 5 (20-24) | **5** | 0 | — |
| **V** armed, `present_effect=fsr` | 1 (1) | **1** | 0 | — |
| **D** armed + detector | 5 (3,6,9,11,13) | **0** | 5 | 10, 8, 10, 6, 14 |
| **Z** armed + detector + topology | 2 (16,19) | **0** | 2 | 15, 29 |
| **F** armed + fix shape | 5 (4,7,10,12,14) | **0** | 5 | — |
| **C** option-OFF control | 4 (2,5,8,15) | **0** | 4 | — |
| **O** option-OFF + detector | 2 (17,18) | **0** | 2 | **0** |

Totals: **6 crashes in 6 armed-unmitigated launches** (5 bilinear + 1 FSR);
**0 crashes in 18** mitigated or option-OFF launches. Detector runs caught
**92** dead-iterator events in 89,878 armed walks; the option-OFF build caught
**0** in 26,054 walks — the phenomenon is armed-only, which is the direct
answer to §11.5.

Time alive after first paint for the crashes: **14.1, 20.0, 37.3, 55.7, 64.9 s**
(bilinear) and 58.7 s (FSR) — reproducing §9.4's 1.3-53.5 s spread and its
conclusion that the crash is not tied to a fixed point in the run. Surviving arms
all reached the 72.2-75.1 s bar.

Free VRAM was ~9.0 GB throughout (the resident `qwen3-tts` server was **not**
loaded this pass, unlike §9's 3.8-4.6 GB). It was equal across every arm and
control, so it did not confound the comparison — but it means this batch ran
under lighter GPU pressure than §9's, which is worth knowing when comparing
absolute crash times. No other game or job held the lane at any point.

### 11.5 Why the option triggers it (deliverable 4, answered)

`REXGLUE_ENABLE_FSR1_RASTER=ON` → `REX_HAS_FIDELITYFX_SDK=1` is applied to
**`rexui` only** → `rexui`'s `Presenter` grows by `0x10` (four `GuestOutputPaint
Config` members) → in `rexruntime.dll`, `ui_draw_next_iterator_` sits at `0x1E8`
→ the GPU plugin, compiled without the define, still writes
`guest_vblank_count_` at `0x1E8` → every emulated vblank increments the low byte
of the armed iterator → when that byte is incremented while the iterator is held
at `end()` across a `Draw()`, the next loop test sees `end+1` instead of `end`,
enters the body, and `operator++` dereferences `end+1` as a tree node.

It is not the shader/pipeline plumbing, not the extra cvars, and not a timing
perturbation. It is a data-layout disagreement between two modules about one
class, made reachable by making the accessor inline.

This also explains §10.5's awkward fact — that the crash fires with
`present_effect=bilinear`, where no FSR code runs — and it explains why the
option-OFF build is stable: there, `0x1E8` *is* `guest_vblank_count_`, so the
write is correct. The two builds differ in whether the plugin's write is
harmless or destructive, which is exactly the correlation §9 could measure but
not explain.

### 11.6 The fix shape (deliverable 3) — measured

`REX_UI_DRAWERS_FIX=1` (no iterator held across `Draw()`; the next drawer is
re-derived from the live map each step): **5 launches, 5 survivals, 0 crashes**
against a bracketing control of 4 option-OFF survivals and 5 armed-baseline
crashes. By the card's rule that is rate → ~0, i.e. the arm that removes the held
iterator removes the crash.

What it does **not** do: it does not stop the corruption. The plugin still writes
to `+0x1E8` on every vblank; the fix merely guarantees this loop never reads that
field, so the scribble stops being fatal *here*. Treat it as a workaround with a
proven symptom-removal rate, not as the repair — other readers of the same
object are still exposed, and `guest_vblank_count_` is still not incremented in
the armed build.

### 11.7 The actual repair

The defect is the inline accessor, not the drawer list. In preference order:

1. **Move `OnGuestVblank()` out of line into `presenter.cpp`** and export it
   (the class's rationale for inlining it was avoiding an export; the curated
   export table can carry it). This removes all layout knowledge from the plugin
   and is a one-function change. It also fixes every sibling hazard at once,
   including the un-incremented `guest_vblank_count_`.
2. **Stop the layout from shifting**: give `Presenter` the FidelityFX members
   regardless of the define (unused when off), or put them behind a pointer, so
   option ON/OFF are layout-identical.
3. Making the define `PUBLIC`/`INTERFACE` on `rexui` would also align consumers,
   but it drags FidelityFX headers into every consumer — worse trade.

The blast radius is narrow by construction: `OnGuestVblank` is the only
member-touching method defined in-class that an external target calls (its own
comment says so), and it is reachable from one call site. Any future inline
accessor added to `Presenter` re-opens the same hole.

### 11.8 FSR re-verified (deliverable 6)

The instrumented `rexruntime.dll` is an SDK rebuild, so the rule applied. Launch
1, `present_effect=fsr`, armed instrumented build: chain logged
`2 pass(es): #0 fsr-easu -> 2560x1440 #1 fsr-rcas -> 2560x1440`, **10 dumps**
written at 3440x1440 in `out/upscale-dumps/verify-fsr3/`
(`present-final-0{0300,0700,…,3900}-3440x1440-fsr-easu+fsr-rcas.ppm`), and the
run then crashed at 58.7 s — the same armed-only fault, i.e. FSR is running and
the crash is not FSR-specific. Bilinear arms logged `1 pass(es): #0 bilinear ->
2560x1440` in the same breath, so the presenter chain is live in every arm.

### 11.9 Recommendation (deliverable 5, for Marcus)

**The armed build still should not go on the operator's install — but the reason
has changed, and it is now cheap to fix.** It is not an unexplained crash any
more: a GPU-plugin inline accessor writes `guest_vblank_count_` at the offset the
armed DLL uses for `ui_draw_next_iterator_`, and it does so on every emulated
vblank. Moving that one accessor out of line (or making the option not shift the
layout) removes the whole class of bug.

Basis for the decision:

- **keep on `feral/dlss`** — yes, as the test vehicle: it is the only build that
  exercises the FSR path, and it is now instrumented and understood;
- **keep off the install** — yes, until §11.7 lands. `ui_drawers_`-independent
  workarounds (the fix shape) remove the crash this pass measured, but they leave
  the corrupting write in place and leave `guest_vblank_count_` at 0, which means
  the pacer's vblank cadence is wrong in the armed build even when it survives;
- **do not revert the armed build to escape the crash** — the crash is a
  one-function repair away, and reverting loses the FSR work.

### 11.10 Artefacts from this pass

- `thirdparty/rexglue-sdk-ui-drawer-instrumentation.patch` — regenerated
  (278 lines) to include the topology + hexdump diagnostics used in §11.2(c);
  verified with `git apply --check -R` to reproduce the modified source exactly
  from pinned `cc5f03d`. The SDK tree itself is not committed.
- `out/drawer-detect/` — armed + instrumentation, `f06ca75d…` (detector + fix
  shape, used for arms D and F).
- `out/drawer-detect2/` — armed + diagnostics, `4e388882…` (arms Z).
- `out/off-detect/` — option-OFF + detector, `86cbcb6d…` (arms O).
- `out/drawer-detect/batch-results.csv` — one row per launch: arm, rc, wall,
  log, first-paint timestamp, alive-after-paint, chain, detection counts.
- `out/drawer-detect/detect-{3,6,9,11,13,16,17,18,19}.txt` — the detector logs,
  1.9-6.7 MB each (~25 MB total); `detect-19` carries the pre/post-draw hexdumps
  of §11.2(c), and `detect-17`/`-18` are the option-OFF runs with zero hits.
- `out/drawer-detect/stdout-24.txt` — the `+seh` trace naming `+0xEC690`.
- 24 launches, ledger `~/.hermes/logs/game-jobs.jsonl` (051-074).
- `out/launchcheck/` restored to the option-OFF control pair (`a27a9a5b…`)
  after the batch, as §9.4 left it.

## 12. The repair (kanban `t_ab11feef`) — the layout no longer depends on the PRIVATE define, and the plugin no longer bakes an offset

**Bottom line: fixed, and proved by rate and by instrument.** The armed build
survived **7 of 7** launches (6 bilinear + 1 FSR) where the pre-fix build crashed
**2 of 2** in the same session; the option-OFF build survived 3 of 3. The
`§11.2(c)` hexdump test is now clean in both builds: **0 byte-0 moves in 12,954
armed walks and 12,975 option-OFF walks**, against 10 in 12,703 before the fix.
The detector reported **0 dead-iterator events** in both. FSR still runs
(`fsr-easu -> fsr-rcas`, 6 dump pairs, measured below) on a build that does not
crash.

Two independent changes were made, and they were made *both*, not one of them:

1. **the layout of `Presenter` no longer depends on `REX_HAS_FIDELITYFX_SDK`** —
   so the option cannot shift a member offset for anyone; and
2. **`OnGuestVblank()` is out of line and exported** — so no caller bakes an
   offset at all, including for members that do not exist yet.

### 12.1 The choice, and what it costs

The card asked for both options to be evaluated. Both were implemented and
measured; here is why the pair, rather than either alone:

| option | what it fixes | what it leaves | verdict |
|---|---|---|---|
| **Minimal** — propagate `REX_HAS_FIDELITYFX_SDK` to `rexgpu-xenos` | today's offsets | the class stays layout-fragile: every future member addition moves `ui_draw_next_iterator_` again, and every future inline accessor re-opens the hole | **rejected** |
| **Layout invariance** (chosen, part 1) | the whole *class* of bug for this define, permanently | a caller still bakes an offset — correct today, fragile under a new define | kept |
| **Out-of-line + exported accessor** (chosen, part 2) | bakes nothing in any caller, ever | does not by itself protect *other* accessors | kept |

The minimal option was rejected on cost/benefit: propagating the define to the
plugin drags `REX_HAS_FIDELITYFX_SDK` into a target that must not have it. It
happens *today* not to include any FidelityFX header (`presenter.h`'s includes
are standard-only — checked), so it would "work"; but it would silently make the
plugin's behaviour depend on a build option that has nothing to do with GPU
plugin code, and it would still leave the layout conditional. The card's own
instruction — "if doing so drags FidelityFX code into the plugin, this is not
minimal and probably wrong" — points at the same conclusion from the other side:
it does not drag code today, and the fact that it *could* tomorrow is the reason
not to do it.

**Cost of what was chosen:**

- `sizeof(GuestOutputPaintConfig)` is **16 bytes larger in option-OFF builds**
  (12 → 28). No allocation changes: those members are a float, a uint32, a float
  and an enum, never read when the option is off. No VRAM, no per-frame work.
- **One new export** in the curated table (`rexruntime.def`), 118th entry,
  `?OnGuestVblank@Presenter@ui@rex@@QEAAXXZ`. Export-section growth is one entry;
  no existing import changes, so **no rebuild of `fable_2.exe` is required** — the
  game imports the runtime, the plugin is runtime-loaded.
- **ABI:** `Presenter` is now the *same* size in both configurations, which is a
  simplification, not a break — anything built before against the option-OFF
  layout is unaffected in its own layout, and the option-ON build now agrees with
  it.
- **Rebuild shape:** a header change, so `rexui` + the plugin's
  `graphics_system.cpp` recompile. Incremental build: ~5 s. Full DLL pair for
  both configurations: ~2 min each.
- **A trap found on the way** and closed in the same patch: for a D3D12-only
  build the export table is *filtered into*
  `${CMAKE_CURRENT_BINARY_DIR}/rexruntime-d3d12.def` at **configure** time, so a
  `.def` edit is silently ignored by a plain incremental build — the symptom is
  `undefined symbol: public: void __cdecl rex::ui::Presenter::OnGuestVblank(void)`
  at link. `src/system/CMakeLists.txt` now lists `rexruntime.def` in
  `CMAKE_CONFIGURE_DEPENDS`, so editing it re-runs CMake.

**Residual fragility, stated plainly:** the *class* is fixed for this define, but
the general trap remains for any future `PRIVATE` define that adds or removes a
public class member. Nothing in the build system stops that. The out-of-line
accessor removes the trap for *this* call path; a future inline accessor in a
public header would re-open it, which is why §12.7's sweep rule belongs in the
SDK's contribution guidance (see the held upstream report).

### 12.2 The layout is now invariant — three ways to see it

**(a) Compile-time, with and without the define.** A probe TU that includes
`include/rex/ui/presenter.h` with `#define private public` and prints the real
offsets (probe kept out of the tree, `cache/scratch/offsetprobe.cpp`):

| | before the fix, OFF | before, ON | **after, OFF** | **after, ON** |
|---|---|---|---|---|
| `sizeof(Presenter)` | 432 | 448 | **448** | **448** |
| `offsetof(ui_draw_next_iterator_)` | `0x160` | `0x170` | **`0x170`** | **`0x170`** |
| `offsetof(guest_vblank_count_)` | `0x170` | `0x180` | **`0x180`** | **`0x180`** |
| `sizeof(GuestOutputPaintConfig)` | 12 | 28 | **28** | **28** |

(Host/Linux `clang`, so the absolute numbers differ from the Windows ones below;
the *equality* is the property, and the pre-fix column proves the probe is
sensitive.) A `-Xclang -fdump-record-layouts` diff of the whole header is
identical between the two modes after the fix; before it, only
`GuestOutputPaintFlow` (the internal struct sized by
`kMaxGuestOutputPaintEffects`) differed.

**(b) In the shipped binaries.** Both configurations' `rexruntime.dll` now open
`OnGuestVblank` with the same instruction and the same offset:

```
armed     : 1800eaf60 <?OnGuestVblank…>: f0  lock | 48 ff 81 f8 01 00 00  incq 0x1f8(%rcx)
option-OFF: 1800ead40 <?OnGuestVblank…>: f0  lock | 48 ff 81 f8 01 00 00  incq 0x1f8(%rcx)
```

`0x1F8` is `guest_vblank_count_` in *both* — which is the invariant asserted as
a binary fact rather than a source reading. Neither `rexgpu-xenos.dll` contains
any `incq 0x1e8`.

**(c) At runtime.** The instrumented option-OFF build now reports the drawer
iterator at `+488` (`0x1E8`), the same offset the armed build reports; before
the fix the option-OFF layout put it at `0x1D8`. The detector computes its
offset as `&ui_draw_next_iterator_ - this` (`REX_UI_DRAWERS_DETECT`, §11.2(c)),
so that agreement is measured, not assumed.

### 12.3 The plugin no longer bakes an offset

`src/graphics/graphics_system.cpp` (`MarkVblank`) now *calls* the export:

```
1547: e8 00 00 00 00   callq  …
      IMAGE_REL_AMD64_REL32  ?OnGuestVblank@Presenter@ui@rex@@QEAAXXZ
```

Both call sites (the vblank path and the `SetupGuestGpu` lambda) are relocations
against the import table; there is no `+offset` instruction left in the plugin
for this accessor. The `incq 0x1e8(%rax)` that §11.2(b) recorded in
`graphics_system.cpp.obj` is gone from both configurations' objects.

### 12.4 Rates — 12 launches, this session, one batch, same lane

Arms: **B** = pre-fix armed build (`out/fsr-clean`, `13a5d065…`, the same binaries
§11 measured); **F** = armed + fix (`5185f715…` runtime / `9f254a46…` plugin);
**C** = option-OFF + fix (`0698cb62…` / `feacaefa…`); **V** = armed + fix, FSR.
Lane `game-job.sh` (DP-1 default, window placed never activated, audio muted),
`--timeout 130 --gpu-wait 0`, inner bar `/usr/bin/timeout -k 15 75`, interleaved
so drift cannot track the arm.

| # | log | arm | rc | alive after 1st paint | note |
|---|---|---|---|---|---|
| 01 | 075 | **B** | **5** | 22.5 s | pre-fix crash |
| 02 | 076 | F | 124 | 73.7 s | survived the bar |
| 03 | 077 | C | 124 | 74.2 s | control |
| 04 | 078 | F | 124 | 73.7 s | |
| 05 | 079 | **B** | **5** | 22.0 s | pre-fix crash |
| 06 | 080 | C | 124 | 74.8 s | control |
| 07 | 081 | F | 124 | 74.2 s | `REX_UI_DRAWERS_DETECT` |
| 08 | 082 | F | 124 | 73.2 s | present dumps (bilinear) |
| 09 | 083 | C | 124 | 74.2 s | control + detector |
| 10 | 084 | F | 124 | 74.2 s | |
| 11 | 085 | **V** | 124 | 73.8 s | FSR + present dumps |
| 12 | 086 | F | 124 | 74.8 s | |

**Pre-fix armed: 2 of 2 crashed. Armed + fix: 7 of 7 survived (6 bilinear, 1 FSR).
Option-OFF + fix: 3 of 3 survived.** Against §11's 6-of-6 / 18-of-18, the
pre-fix armed build is now **8 of 8 crashes across two sessions** and the fixed
armed build **7 of 7 survivals**, with controls bracketing at positions 3, 6 and
9. `rc 5` is the crash; `rc 124` is the lane's own 75 s timer, i.e. alive at the
bar.

Every chain line is the same shape as before the fix — `1280x720 -> 3440x1440,
1 pass(es): #0 bilinear -> 2560x1440` (or `2 pass(es): #0 fsr-easu … #1
fsr-rcas` on 085) — so the fix changed nothing about the present path itself.

**GPU pressure was equal across every arm:** free VRAM was 8.5–8.7 GB for all 12
launches (ledger `pre_free_vram_mb`: 8865, 8503, 8482, 8483, 8509, 8530, 8509,
8510, 8511, 8510, 8688, 8599). The resident `qwen3-tts` server held ~5 GB at the
start of this pass but had released its model (274 MiB resident) before the
batch, so it was **not** a confounder — and, unlike §11, the crash arm and the
surviving arms ran at the *same* pressure.

Noted for honesty: the lane marks 9 of the 12 rows `verdict: FAIL — free vram
… below baseline`, because a **surviving** run leaves ~800 MB of presenter and
allocator memory briefly unreleased; the two crashing runs `PASS` because the
process died. That is the lane's post-run accounting, not a launch outcome — the
outcome measure here is `rc` and time alive.

### 12.5 The direct test — the byte stops moving

`REX_UI_DRAWERS_DETECT` hexdumps 32 bytes at the *real* offset of
`ui_draw_next_iterator_` before and after every `Draw()` (§11.2(c)). Counting
across whole logs:

| log | build | walks (pre/post pairs) | byte 0 (`0x1E8`) moves | byte 11 (`0x1F3`) | dead iterator |
|---|---|---|---|---|---|
| `detect-19` (§11, **before**) | armed | 12,703 | **10** (`40 -> 41`) | 12,703 × `0 -> 1` | 58 |
| `fix-batch/detect-f7.txt` (**after**) | armed + fix | 12,954 | **0** | 12,954 × `0 -> 1` | **0** |
| `fix-batch/detect-c9.txt` (**after**) | option-OFF + fix | 12,975 | **0** | 12,975 × `0 -> 1` | **0** |

Byte 11 flipping on *every* walk in the fixed logs is the control that matters:
the hexdump is live and the harness still sees presenter writes — the zero in the
byte-0 column is a real silence, not a dead instrument. Sample from `f7`:

```
walk 0 pre-draw  +488: 50 83 2d 00 00 00 00 00 01 01 00 |00| …
walk 0 post-draw +488: 50 83 2d 00 00 00 00 00 01 01 00 |01| …
```

Byte 0 unchanged; only `request_ui_paint_after_current_ui_thread_paint_` flips,
which is `presenter.cpp`'s own write at the correct offset.

### 12.6 FSR re-verified after the fix — and the first honest look at it

Launch 11, `present_effect=fsr`, armed + fix, survived the bar:

- chain logged: `1280x720 -> 3440x1440, 2 pass(es): #0 fsr-easu -> 2560x1440 #1
  fsr-rcas -> 2560x1440`;
- **6 dump pairs**, identical paint indices 300/500/700/900/1100/1300 at
  3440x1440, in `out/fix-batch/dumps-fsr/` (bilinear companion run: launch 08,
  `dumps-bilinear/`).

Measured (`cache/scratch` script, Laplacian std, numpy; whole frame and a
900x240 crop grid — the "best-gain" column is the crop where FSR gains most
among crops with real edge content, so it is chosen by the data not by hand):

| paint | whole-frame std bilinear -> fsr | busiest crop | best-gain crop |
|---|---|---|---|
| 300 | 3.402 -> 3.662 (**+7.7 %**) | +1.4 % | +9.9 % |
| 500 | 3.396 -> 3.689 (**+8.6 %**) | +1.2 % | +7.4 % |
| 700 | 4.051 -> 4.322 (**+6.7 %**) | +1.2 % | +7.5 % |
| 900 | 4.550 -> 4.678 (**+2.8 %**) | +0.7 % | +6.2 % |
| 1100 | 5.260 -> 5.550 (**+5.5 %**) | +2.0 % | +5.6 % |
| 1300 | 6.706 -> 6.904 (**+2.9 %**) | -0.1 % | +2.5 % |

**What the upscaling actually looks like, on a build that does not crash:** the
EASU+RCAS chain is operating and measurably sharpening (whole-frame +2.8 to
+8.6 %, best local crop +2.5 to +9.9 %), and the rendered image is *stable* —
frame-to-frame whole-frame RMSE between the bilinear and FSR runs is 0.56–0.72
out of 255 for paints 300–1100, i.e. the two runs are the same scene rendered
with the same inputs. These are the **boot-video frames**, which are smooth: this
is a small effect on smooth content and would be larger on UI/text, exactly as
§4 found with a hand-picked wordmark crop (+132 %). Paint 1300 (RMSE 2.4) is a
scene transition and is not comparable.

No artefacts were seen in the dumps at these indices; that statement is bounded
by six frames of a boot video and is not a claim about gameplay.

### 12.7 The sweep — same class of bug elsewhere

**Method** (repeatable; scripts kept in `~/.hermes/kanban/workspaces/t_ab11feef/`):
1. enumerate every compile definition applied **PRIVATE** to an in-tree target
   (`grep -rn target_compile_definitions --include=CMakeLists.txt`);
2. for each, grep `include/rex/**/*.h` for conditional regions and classify them
   as **layout** (declares members / sizes a struct / initialises a member) or
   **behaviour** (enumerators beyond the first, switch arms, functions, static
   asserts);
3. enumerate every inline member function defined inside a class body in
   `include/rex/**/*.h` whose body touches a member (1,119 found; the SDK's
   `member_` convention makes this mechanical — `sweep-layout-collisions.py`);
4. cross-reference those that live in a layout-conditional header against call
   sites outside their own library (`rexgpu-xenos` = `src/graphics/**`,
   `rexruntime` = `src/system|core/**`, and the game tree) —
   `xref-inline.py`;
5. for each cross-module hit, check whether the *class* that owns the accessor
   has a define-dependent layout. That, and only that, is the defect.

**Result: one live hit — the one this pass fixed — and it is now safe.**
Everything else is either behaviour-only, PUBLIC (so every target agrees), or
internal to `rexui`. Full inventory:

| # | site | define scope | kind | class |
|---|---|---|---|---|
| 1 | `include/rex/ui/presenter.h:196,243,329` — `OnGuestVblank` inline + `GuestOutputPaintConfig` members | `PRIVATE rexui` | **layout + cross-module inline** | **LIVE — the defect; fixed here** |
| 2 | `presenter.h:233` `Effect` enumerators | `PRIVATE rexui` | behaviour (enum width unchanged) | safe |
| 3 | `presenter.h:297` config get/set accessors | `PRIVATE rexui` | behaviour (no layout) | safe |
| 4 | `presenter.h:454` `GuestOutputPaintEffect` enumerators | `PRIVATE rexui` | behaviour (enum width unchanged) | safe |
| 5 | `presenter.h:488` `kMaxGuestOutputPaintEffects` → sizes `GuestOutputPaintFlow` | `PRIVATE rexui` | layout of an **internal** struct, returned by value from a private method; no cross-module caller (checked) | latent (safe today) |
| 6 | `presenter.h:575-642` `CasSharpenConstants` etc. | `PRIVATE rexui` | internal helper structs, `rexui`-only | latent (safe today) |
| 7 | `d3d12_presenter.h:140` root-signature index enum | `PRIVATE rexui` | behaviour (enum values) | safe |
| 8 | `d3d12_presenter.h:156` switch over effects | `PRIVATE rexui` | behaviour | safe |
| 9 | `d3d12_presenter.h:250` `PaintContext::guest_output_intermediate_textures[kMaxGuestOutputPaintEffects-1]` | `PRIVATE rexui` | layout of `D3D12Presenter` (a **derived** class the plugin includes but never instantiates; it only casts to `D3D12GuestOutputRefreshContext`, whose layout is invariant — verified at the two call sites) | latent (safe today) |
| 10 | `vulkan/presenter.h:233,249` + `:393-396` arrays | `PRIVATE rexui` | same shape as 7-9 | latent (and Vulkan is off in this build) |
| 11 | `d3d12_presenter.h:270,320` / `vulkan/presenter.h:438,484` — `REX_HAS_FIDELITYFX_RUNTIME` adds `temporal_upscaler_*` members | `PRIVATE rexui` | layout of the derived presenters, after `paint_context_`; no inline accessor for them; **option OFF in this build** | latent |
| 12 | `include/rex/graphics/flags.h:82,98`, `include/rex/ui/flags.h:42,51` — `REX_HAS_D3D12` / `REX_HAS_VULKAN` | **PUBLIC** on `rexcore` + `rexruntime` (`src/core/CMakeLists.txt:120,123`, `src/system/CMakeLists.txt:141,149`) | enum values only | safe — every consumer sees it |
| 13 | `REX_PLATFORM_*`, `REX_ARCH_*`, `REX_COMPILER_*` (16+17+4 uses) | derived inside `rex/platform.h` from compiler built-ins | platform/arch | safe by construction — identical in every TU |
| 14 | `REXGLUE_BUILD_CONFIG` (string) | `PRIVATE` per title target (`cmake/rexglue_helpers.cmake:84`) | string literal, not used by any header | safe |
| 15 | `Window::presenter()` `window.h:571` — inline accessor **called from the game exe** (`src/diagnostics/fable2_screenshot.h:73`) | n/a | `window.h` contains **zero** `#if` | safe |
| 16 | `IGraphicsSystem::provider/presenter` (`system/interfaces/graphics.h:57-58`) | n/a | **virtual** → vtable dispatch, no offset baked | safe by construction |
| 17 | `Presenter::GuestOutputRefreshContext::SetIs8bpc` (plugin call sites `src/graphics/{d3d12,vulkan}/command_processor.cpp`) | n/a | caller class has no conditional members (`bool&`) | safe |
| 18 | `D3D12GuestOutputRefreshContext::resource_uav_capable`, `VulkanGuestOutputRefreshContext::{image,image_view,image_version,image_ever_written_previously}` | n/a | small context classes, invariant layout | safe |
| 19 | `GuestOutputPaintConfig` get/set accessors (`presenter.h:298-320`) | `PRIVATE rexui` | **no** cross-module caller — none in `src/graphics/**`, none in the game tree | safe |

Counts: **1,119** inline member functions in public headers touch a member; **46**
of them live in headers carrying a layout-conditional region; the cross-
referencer finds **10** of those with a call site outside `rexui`, and each was
checked by hand — **6 are genuine** cross-module calls (items 17-18, all on the
two small refresh-context classes) and **4 are name collisions** on unrelated
types (`->provider()` on `IGraphicsSystem`, `->memory()`, `->view()`,
`->vulkan_device()` on providers). Of the six genuine ones, **exactly one** — item
1, `OnGuestVblank` — belonged to a class whose layout depended on a `PRIVATE`
define. **One live defect, now fixed. Ten latent items, all listed above with the
reason they are safe today.**

(Note on the tooling: the cross-referencer attributes a nested class's method to
its enclosing class, which is why check-by-hand was part of the method rather
than an optional extra.)

The rule the sweep implies, and the one worth upstreaming: *a `PRIVATE` compile
definition must not change the layout of a type that appears in a public header.
If it does, the affected members go behind a pointer, become unconditional, or
the accessor that exposes them moves out of line and into the export table.*

### 12.8 Instrumentation disposition

- **Kept in the tree, as its own tracked patch**
  (`thirdparty/rexglue-sdk-ui-drawer-instrumentation.patch`): the
  `REX_UI_DRAWERS_DETECT` walk/hexdump diagnostics and the `REX_UI_DRAWERS_FIX`
  workaround arm. Both are env-gated and inert unless asked for; the detector is
  what makes §12.5 repeatable, and this pass used it unchanged.
- **Kept, permanent, and part of the new fix patch**: the layout change, the
  out-of-line exported accessor, and the `CMAKE_CONFIGURE_DEPENDS` guard.
- **Not shipped in any patch**: the two throwaway probes used for §12.2 —
  `offsetprobe.cpp` (`#define private public`, prints real offsets) and
  `layoutprobe.cpp` (`-fdump-record-layouts` driver). Both live only in
  `~/.hermes/profiles/rigsy/cache/scratch/`.
- **Removed this pass**: nothing was left behind in the SDK tree that is not
  either in the fix patch or in the instrumentation patch — verified by
  reproducing the tree byte-for-byte from the patch stack (§12.9).

### 12.9 Reproducibility

`thirdparty/rexglue-sdk-presenter-layout-invariant.patch` (4 files: the header,
`presenter.cpp`, `rexruntime.def`, `src/system/CMakeLists.txt`) applies **after**
the FSR, perf-CSV and instrumentation patches on the pinned `cc5f03d`.
verified: on a clean worktree of `cc5f03d`, applying
`rexglue-sdk-fsr1-raster` → `rexglue-sdk-perf-csv-and-vc-dump` →
`rexglue-sdk-guest-exit-status-probe` → `rexglue-sdk-ui-drawer-instrumentation` →
`rexglue-sdk-presenter-layout-invariant` reproduces the live SDK tree's
`git diff` **byte-for-byte** (`diff -q` identical; the tree's total diff is 950
lines before this pass's fix and 1,064 after). `tools/setup_sdk_src.cmd` now
applies the new patch as its fourth optional step, with the same "only if it
applies cleanly" guard. Nothing was committed to the SDK tree.

### 12.10 Recommendation

**The armed build is now fit to go on the operator's install, with one caveat
that is about policy rather than code:** the crash that kept it off is fixed at
its cause rather than worked around — the corrupting write no longer happens, the
offset it was writing to is now `guest_vblank_count_` in both builds, and that
counter is incremented by the runtime itself (`lock incq 0x1f8`, §12.2(b)) rather
than never being reached. *(That the counter now increments is a source-and-
disassembly statement: the pacer diagnostic that would print the rate still does
not fire under this config, so it was not observed at runtime.)* 7/7 survivals,
an instrumented build that shows the byte no longer moving, and an FSR chain that
still runs.

The caveat: the fix lives in an SDK **patch**, not upstream, and the SDK tree
stays at `cc5f03d` + patch stack — so any rebuild that forgets the patch
reintroduces the crash. `tools/setup_sdk_src.cmd` now applies it automatically,
which is the mitigation.

- **keep on `feral/dlss`** — yes; it is the only build that exercises FSR and it
  is now instrumented, understood and stable;
- **install** — the blocker is cleared; the remaining work is the ordinary
  packaging question (which DLL pair ships), not a defect;
- **do not revert the armed build to escape the crash** — no longer necessary.

### 12.11 Artefacts from this pass

- `thirdparty/rexglue-sdk-presenter-layout-invariant.patch` — the fix, 4 files,
  applies on the pinned `cc5f03d` after the four existing patches (verified,
  §12.9). The SDK tree itself is not committed.
- `out/fix-armed/` — armed + fix DLL pair, `rexruntime 5185f715…`,
  `rexgpu-xenos 9f254a46…` (arms F and V in §12.4).
- `out/fix-off/` — option-OFF + fix pair, `rexruntime 0698cb62…`,
  `rexgpu-xenos feacaefa…` (arms C).
- `out/fix-batch/batch-results.csv` — one row per launch (arm, rc, wall, md5,
  full env), 12 rows.
- `out/fix-batch/detect/detect-f7.txt` (6.8 MB), `detect-c9.txt` (6.8 MB) — the
  §12.5 hexdump logs; both zero-move.
- `out/fix-batch/dumps-bilinear/` and `dumps-fsr/` — 6 PPM pairs each,
  3440x1440, paint indices 300-1300.
- `out/fix-batch/sharpness.txt` — the §12.6 measurements.
- `out/fix-batch/disasm-evidence.txt` — the §12.3 disassembly.
- `out/fix-batch/stdout-NN.txt` — raw lane output per launch.
- `docs/UPSTREAM-REPORT-presenter-layout-collision.md` — **held, unposted**
  (§12.10 / the card's PUBLIC POST AUDIT requirement).
- Sweep tooling, kept for repetition:
  `~/.hermes/kanban/workspaces/t_ab11feef/{sweep-layout-collisions.py,
  xref-inline.py, hexdump-test.py, measure-sharpness.py, analyze-batch.py,
  run-batch.sh}`.
- 12 launches, logs `out/launchcheck/logs/fable_2_075..086.log`, ledger
  `~/.hermes/logs/game-jobs.jsonl` (the 12 most recent Fable II rows).
- `out/launchcheck/` restored to the option-OFF control pair after the batch.
