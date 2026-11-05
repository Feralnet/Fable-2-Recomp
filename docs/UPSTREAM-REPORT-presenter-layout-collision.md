# Upstream report — POSTED as rexglue/rexglue-sdk#564

**Status: POSTED 2026-11-05T00:21:30Z as `rexglue/rexglue-sdk#564` — https://github.com/rexglue/rexglue-sdk/issues/564**

Posted bytes verified identical to the audited ones on read-back (body sha256 `79f3b2db2aadfe03c4580b72ab96b7faeb9a6d68432dd69bc30b1fcb7e71901d`, 6658 B, author `Feralnet`, issue open).
Target: the canonical ReXGlue SDK repository `rexglue/rexglue-sdk` — as an **issue** (its issue tracker is enabled).

**Target correction, found at post time (2026-11-04).** This draft previously named `himdo/rexglue-sdk`. That is a **fork** of the canonical project — it is the repo our game tree's submodule points at, and it has **issues disabled**, so it cannot receive a report. The canonical repo `rexglue/rexglue-sdk` has issues enabled. The Fable II runtime tree is pinned to commit `cc5f03d` from the fork; the defect is in the shared SDK code and is not fork-specific.
Author of the draft: Rigsy (agent), for Marcus.
Evidence: `/run/media/feral/Games/Recomp/fable2/docs/FABLE2_UPSCALING_SPIKE.md` §10–§12.

---

## Title

`PRIVATE` compile definition changes a public class layout — cross-module
memory corruption when the FidelityFX option is on

## Summary

`rex::ui::Presenter::OnGuestVblank()` is defined inline in
`include/rex/ui/presenter.h` **specifically so that the GPU plugin
(`rexgpu-xenos`), which does not link the `rexui` object library, can call it
without an exported symbol**. That reasoning is sound for linkage and wrong for
layout: an inline accessor bakes `offsetof(Presenter, guest_vblank_count_)` into
the *caller's* translation unit, and the caller does not see `rexui`'s private
compile definitions.

`REX_HAS_FIDELITYFX_SDK` is applied with `target_compile_definitions(rexui
PRIVATE …)` (`src/ui/CMakeLists.txt`), yet it adds four members to
`Presenter::GuestOutputPaintConfig` — and `GuestOutputPaintConfig` is a member
of `Presenter`. Turning the option on therefore changes `Presenter`'s layout in
`rexruntime.dll` only. The plugin is compiled against the option-OFF layout.

Consequence, measured on the Fable II recomp against the pinned SDK commit
`cc5f03d` with `REXGLUE_ENABLE_FSR1_RASTER=ON`:

| member | `rexruntime` (define ON) | `rexgpu-xenos` (define not visible) |
|---|---|---|
| `is_executing_ui_drawers_` | `0x1F0..0x1F3` | `0x1E0..0x1E3` |
| `guest_vblank_count_` (`std::atomic<uint64_t>`) | `0x1F8` | **`0x1E8`** |
| `ui_draw_next_iterator_` | **`0x1E8`** | `0x1D8` |

The plugin's copy of `OnGuestVblank()` executes `incq 0x1e8(%rax)` — the low
byte of the runtime's stored UI-drawer iterator — once per emulated vblank.
The result is not a random overrun but a single byte incremented in a fixed
place: the drawer walk then dereferences `end()+1` and the process dies with an
`EXCEPTION_ACCESS_VIOLATION` at a fixed instruction inside `rexruntime.dll`.

Two things make this hard to find from the outside:

1. **It only fires with the option ON**, but the executor of the corruption is
   the *plugin*, which contains no FidelityFX code at all. The failing module
   and the module that enabled the option are different.
2. **It is a rate, not a certainty.** With `present_effect=bilinear` (no FSR
   code in the chain) the armed build still crashed 6 of 6 runs, at 14–65 s
   after first paint; the option-OFF build survived 18 of 18. A single run
   proves nothing, which is why it reads as a flaky timing bug.

## Reproduction, minimally

1. Build the SDK with `-DREXGLUE_ENABLE_FSR1_RASTER=ON` (or any way of getting
   `REX_HAS_FIDELITYFX_SDK` defined for `rexui` only).
2. Build `rexgpu-xenos` in the same tree — note it never sees the define:
   `grep -c REX_HAS_FIDELITYFX_SDK build/src/graphics/.../graphics_system.cpp.obj`
   is 0, and the object carries `incq 0x1e8(%rax)` for the `OnGuestVblank()`
   call at `src/graphics/graphics_system.cpp` (`presenter_->OnGuestVblank();`).
3. Disassemble `rexruntime.dll` around the same class and see every `+0x1E8`
   access be an 8-byte iterator move, and the write of `guest_vblank_count_` at
   `+0x1F8` instead.
4. Run any title that draws a UI drawer and presents. It dies within a minute or
   so, at a fixed address, only in the armed build.

A one-line check that does not need a game: compare
`offsetof(Presenter, guest_vblank_count_)` as computed in a TU compiled with and
without `REX_HAS_FIDELITYFX_SDK`. Before the fix they differ by 16 bytes; after
it they are identical.

## The fix that is proposed here (two parts, applied and measured together)

1. **Make the layout define-independent.** `GuestOutputPaintConfig`'s FSR
   members (`cas_additional_sharpness_`, `fsr_max_upsampling_passes_`,
   `fsr_sharpness_reduction_`, `fsr_quality_mode_`), plus the `FsrQualityMode`
   enum and the constants that initialise them, are now present
   unconditionally; when the option is off they are simply never read. Cost:
   `sizeof(GuestOutputPaintConfig)` is 16 bytes larger in option-OFF builds, and
   `sizeof(Presenter)` therefore matches the option-ON build. No VRAM, no
   allocation change.
2. **Remove the layout knowledge from the caller entirely.** `OnGuestVblank()`
   is now declared in the header and defined in `src/ui/presenter.cpp`, and its
   mangled name is added to the curated export table
   (`src/system/rexruntime.def`). The plugin's call becomes an import, so no
   offset is baked into it at all — including any future member added to
   `Presenter`. Note for anyone applying this in a D3D12-only build: the
   `.def` is filtered into `${CMAKE_CURRENT_BINARY_DIR}/rexruntime-d3d12.def` at
   **configure** time, so a `.def` change needs a re-run of CMake, not just a
   build.

Both are applied in the Fable II tree as a patch against `cc5f03d`. Measured
result on the armed build: **7 of 7 launches survived** (6 bilinear + 1 FSR) in
one interleaved 12-launch batch where the pre-fix build **crashed 2 of 2** and
the option-OFF build survived 3 of 3; the detector reported **0** dead-iterator
events in 12,954 armed walks, and the byte at the iterator's offset moved **0**
times across a `Draw()` (it moved 10 times in 12,703 walks before the fix).

**Both parts were applied and measured together.** The reasoning above for why
each would independently close *this* crash is that (1) makes the two modules
agree on the layout and (2) removes the baked offset altogether — but the parts
were **not** measured separately, so that is an argument from the mechanism, not
a measured result.

## Why it is worth fixing upstream rather than patching per title

The trap is generic: **any** `inline` member function in a public header, called
from a target that does not share a layout-affecting `PRIVATE` definition, has
this failure shape — silent, option-gated, cross-module, and a rate rather than
a deterministic crash. Anyone enabling the FidelityFX option on any title hits
it; anyone debugging it will look at the presenter, the drawer list, and the
threading, all of which are correct.

A short rule for the SDK's own contribution guidance would prevent the class of
bug: *a `PRIVATE` compile definition must never change the layout of a type
that appears in a public header; if it does, the affected members go behind a
pointer, become unconditional, or the accessor that exposes them moves out of
line and into the export table.*

## What is deliberately not claimed here

- This is not a claim that the FSR implementation is wrong. The upscaling path
  itself was verified working (chain logged `fsr-easu -> fsr-rcas`, dumps
  produced) before and after the fix.
- The other `REX_HAS_FIDELITYFX_SDK`/`_RUNTIME` conditional regions that remain
  in `d3d12_presenter.h` and `vulkan/presenter.h` are **not** cross-module —
  they affect presenters that only `rexui` constructs — and were left alone;
  they are listed in the Fable II sweep so the judgement is auditable.
