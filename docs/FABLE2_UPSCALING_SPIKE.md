# Fable II recomp — upscaling spike: the FSR 1 present pass

Status: **spike complete, pass proven running; the early guest self-exit is real
but INTERMITTENT (~90 % of launches, not every one) and the bisection in §7
cleared every named suspect — read §7 before §5's attribution.**
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


