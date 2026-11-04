# Fable II recomp — upscaling spike: the FSR 1 present pass

Status: **spike complete, pass proven running, but the FidelityFX-enabled runtime
makes the guest session terminate itself.** Read "Launch outcomes" before using
anything here.

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
path itself**, independent of which effect is selected. The numbers point at a
frame-pacing stall rather than a crash: the GPU `WAIT_REG_MEM` long-wait rate
climbs 230 → 685 → 917/s in the last two seconds before the guest returns, where
the surviving control sits flat at ~333/s. Candidates inside the guard, none of
which were bisected yet: `kMaxGuestOutputPaintEffects` (1 → 4), the intermediate
texture / `guest_output_intermediate_texture_last_usage` machinery, and the
`SetGuestOutputPaintConfigFromUIThread` repaint path (the presenter now owns a
multi-pass chain the guest's swap wait may be starved by).

Bisecting those three is the next pass; it is a presenter-side problem, not a
shader or a Fable-side one.

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
- The FSR-enabled runtime is `rexruntime.dll` md5 `1362d1e6…`
  (build of the SDK + patch above).

Nothing here has been posted anywhere; this is local work.
