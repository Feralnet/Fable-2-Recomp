# Upstream merge 2026-11-06 — grafted history onto `d0477e0`

ROUTE: native x86-64 PC port of an Xbox 360 title by static recompilation
(ReXGlue / ReX SDK runtime + a Xenos GPU plugin). Not an emulator, not a
decompilation, not a mod.

This page records how the local branch `feral/dlss` was brought onto current
upstream without losing our work, and what had to be checked afterwards. Read
this before any further rebase/merge of this tree, because the mechanism is
**invisible to a plain `git log`** and nothing else in the repo states it.

## The problem

Our history was a local snapshot with **no ancestry** to upstream: root commit
`7227b49` ("baseline: our source build of upstream master `4d86f4a` + 3 local
patches") and 40 commits on top of it. `git merge-base HEAD upstream/master`
printed nothing, so `git merge upstream/master` was a full-tree conflict.

## The graft (still live — do not delete the replace ref)

```bash
git replace --graft 7227b49 4d86f4a
```

`7227b49` is content-wise upstream `4d86f4a` + 3 patches, so re-parenting it
onto `4d86f4a` makes the histories share a real ancestor. Checked **before**
merging:

```
git merge-base HEAD upstream/master   -> 4d86f4a10d61f9f0e105b836a1e6587520e8c191
git log --oneline | tail              -> walks into upstream history
```

(After the merge the answer is `d0477e0` instead — upstream/master is now an
ancestor — so `4d86f4a` is the expected answer only on a tree that has not
merged yet. On one that has, the proof is `git rev-list --left-right --count
upstream/master...HEAD` reading `0 <n>`.)

The graft lives in `.git/refs/replace/`, is **not** part of any commit, and is
**not pushed**. A fresh clone does not have it. If the replace ref is lost, the
merge commit still exists but `git log` stops being able to attribute ancestry
across `7227b49`. Keep it, or run the command above again.

## The merge

`git merge --no-ff upstream/master` (upstream `d0477e0`, 254 commits) produced
three conflicts, all of the same shape — **both sides added lines at the same
spot**. Resolved by keeping both:

| File | Resolution |
|---|---|
| `src/core/fable2_config.cpp` | keep our `<string_view>` **and** upstream's `<type_traits>` |
| `src/diagnostics/fps_meter.h` | keep our `fable2::screenshot::poll_capture()` **and** upstream's `fable2::console::poll(ctx, base)` |
| `src/input/keyboard_gamepad.h` | keep upstream's `fable2::f5lua::poll_f5(focused)` signature **and** our `fable2::screenshot::poll_hotkey()` |

Two deliberate non-merge decisions:

- **`thirdparty/rexglue-sdk` stays deleted.** Upstream never moved the gitlink
  (`cc5f03dd`, identical to the merge base), so our deletion merged cleanly and
  no submodule content is lost. SDK sources come from the
  `~/toolchains/rexglue-sdk` checkout plus the `thirdparty/rexglue-sdk-*.patch`
  files. Note: `.gitmodules` still carries the entry, so it is vestigial.
- **`generated/rexglue.cmake` stays deleted.** Untouched upstream; `generated/`
  is gitignored, and the file exists on disk (generated state, not tracked).

All 31 files of our post-commit delta (`git diff --name-status 4d86f4a
pre-modernise-2026-11-06` → 16 added, 13 modified, 2 deleted) were verified
present after the merge: the 16 files we added are byte-identical, the 2
deletions are still deletions, and every line we added to the 13 modified
files is still in the merged file.

## Patch inventory against the pinned SDK (`cc5f03dd`)

Upstream's 254 commits touched **nothing** under `thirdparty/`, and the SDK pin
is unchanged, so no patch became redundant *because of this merge*. What the
re-check did find is a pre-existing drift between three patches and the pinned
SDK commit. Checked with `git apply --check` against a pristine `cc5f03dd` tree:

| Patch | Status at `cc5f03dd` |
|---|---|
| `rexglue-sdk-fsr1-raster.patch` | applies |
| `rexglue-sdk-gapfill-bctr.patch` | applies |
| `rexglue-sdk-guest-exit-status-probe.patch` | applies |
| `rexglue-sdk-perf-csv-and-vc-dump.patch` | applies |
| `rexglue-sdk-presenter-layout-invariant.patch` | applies |
| `rexglue-sdk-ui-drawer-instrumentation.patch` | applies |
| `rexglue-sdk-vblank-timer.patch` | applies (the live SDK tree has two `.rej` from applying it *after* other patches — order-dependent) |
| `sdk_allocfixed_patch.patch` | applies alone |
| `sdk_mainmenu_crash_fix.patch` | applies alone, but the two xmemory patches overlap each other — only one can be applied |
| `rexglue-sdk-debug-exports.patch` | **redundant** — every hunk reverse-applies; all five exports and the `LIBRARY`-line removal are already in `cc5f03dd` |
| `rexglue-sdk-runtime-fixes.patch` | **redundant** — all 13 files reverse-apply (audio sink, frame limiter, guest frame meter are upstream now) |
| `rexglue-sdk-local.patch` | **conflicts at `cc5f03dd`**; applies cleanly to `f5337cdc`, the pin the README and `tools/setup_sdk_src.cmd` still name |

That last row is a **pin mismatch older than this merge**: README documents
`f5337cdc`, the gitlink (and the built SDK) are `cc5f03dd`. None of the three
stale patches are in the built SDK, which is why the runtime still builds and
runs; they need regenerating (or retiring) before anyone rebuilds the SDK from
the repo's own patches. Nothing was deleted — the files are the record.

## The rebuild that verified it (Windows target)

Fresh build directory (a reused one keeps the old absolute path in the cache and
lies about the toolchain — see `docs/PORT-CAPABILITY-INVENTORY.md` §21):

```bash
cmake -S . -B out/build/wincross-postmerge -G Ninja \
  -DCMAKE_TOOLCHAIN_FILE=out/toolchain-wincross.cmake \
  -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_C_FLAGS=-march=x86-64-v2 -DCMAKE_CXX_FLAGS=-march=x86-64-v2 \
  -DFABLE2_BUILD_PROFILE=goty-compatible -DFABLE2_PROFILER_FRIENDLY=OFF \
  -Drexglue_DIR=$HOME/toolchains/rexglue-sdk/win-amd64/lib/cmake/rexglue \
  -DREXGLUE_SDK_ROOT=$HOME/toolchains/rexglue-sdk/win-amd64 \
  -DFABLE2_CODEGEN_TOOL=$HOME/toolchains/rexglue-sdk/out/linux-amd64/rexglue \
  -DFABLE2_NO_PE_CLEAN=ON -DREXGLUE_RECOMP_DEBUG_INFO=none
cmake --build out/build/wincross-postmerge --target fable_2 --parallel 8
```

Result: 381/381 steps, 0 errors; codegen re-ran (`11 written, 586 unchanged`)
because `fable_2_manifest.toml` changed upstream.

| | |
|---|---|
| artefact | `out/build/wincross-postmerge/fable_2.exe` |
| bytes | 110,349,312 (pre-merge Release build was 109,936,128) |
| sha256 | `a2a205f2b556b8a1a1f1cb2f329233e0020afe16664c79a89659760ab9989d98` |
| format | PE32+ for MS Windows, x86-64 |
| our markers | `Widescreen 21:9` ×2, `FABLE2_ULTRAWIDE` ×4, `screenshot_key` ×2 |
| upstream markers | `console-v11`, `autoexec.txt`, `fable2_console` (the new developer console is in the binary) |
| negative controls | `XENIA`, `xenia`, `RPCS3` all 0 hits — still a recomp, not an emulator |

No game launch was performed for this verification (a launch needs the
operator's allow marker; the card did not ask for one).
