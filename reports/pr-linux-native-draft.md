# DRAFT — NOT POSTED. Nothing here has been sent anywhere.

Status: **held for operator audit.** Do not open a PR, comment, or release from this file until
Marcus has read the exact text below and said go. Auditing the *audited region only* matters: the
title and body are the postable parts; everything outside the markers is scaffolding.

Target repo: `himdo/Fable-2-Recomp` · Source branch: `Feralnet/Fable-2-Recomp:linux-support`
Base: `upstream/master` `d0477e0` · Scope: 2 commits, 16 files, +570/−2

---

<!-- ===== POSTABLE REGION START ===== -->

**Title:** `Linux build support (Vulkan) — forward rebase of #80 with its SDK prerequisite merged`

**Body:**

Builds and runs the recomp on Linux x86-64 with the Vulkan renderer.

This is a **forward rebase of #80 by @hereandnowlive**, not a rival implementation. Credit for the
Linux port is theirs; this carries it onto current `master` and removes the part that the SDK has
since absorbed.

**What changed since #80 was opened (2026-10-13).** #80's own next step, stated by its author, was:
*"Once #12 is merged I'll push one more commit here that deletes the patch file, removes the apply
step from build.sh and bumps the submodule to the merged commit."* That prerequisite —
`himdo/rexglue-sdk#12` — merged on **2026-10-29**, along with the POSIX/Vulkan set on top of it
(#13–#17, #18, #19). This rebase performs exactly that step:

- `thirdparty/rexglue-sdk-linux.patch` is **removed** — its contents are upstream now.
- `build.sh` applies no SDK patch, so the submodule stays clean in `git status`.
- `thirdparty/rexglue-sdk` is **bumped to `aaad77f1`** (`himdo/rexglue-sdk` `main`,
  "Merge pull request #24 from Jack-Pettersson/fix-vblank-timer").
- `tools/prepare_runtime_sdk.py` is no longer run: it accepts only an SDK revision where our
  runtime-fixes patch applies or reverse-applies wholesale, and at this pin most of that patch is
  upstream, so its gate no longer describes the tree. Dependencies are initialised directly instead.

**What it contains.** `Linux.md` (build/run/tuning notes and known limitations), `build.sh`,
`run.sh`, the CMake Linux staging, the portable guards for the Windows-only diagnostics, and the
frame-limiter yield/config options for the Linux path. Same shape as #80, minus the SDK patch.

**Build.** Verified locally: full configure + codegen + link with the SDK built from the pinned
submodule produces an ELF x86-64 binary with `librexruntime.so` and `librexgpu-xenos.so` staged
beside it; the link resolves cleanly.

- **MEASURED:** a clean-tree build of **this branch** (base `d0477e0`, no other local changes) completes
  from scratch — **1277 targets, 0 errors** — producing a 213,138,424-byte ELF x86-64 binary with
  `librexruntime.so` and `librexgpu-xenos.so` staged beside it and every shared-library dependency
  resolving (`ldd` clean). The SDK is built from the pinned submodule in the same pass.
  Toolchain: **clang 23.1.4**, the `build.sh` fallback path, on CachyOS. **`clang-20` was not
  available in this environment**, so the exact compiler #80 names has **not** been exercised here —
  flagging that rather than implying it was.
- **UNVERIFIED:** this branch has not been play-tested beyond building. Treat the Linux path as alpha.

**Scope note.** This PR is Linux build support only. Our fork carries separate feature work
(draw-resolution scaling, ultrawide/Hor+) which is deliberately **not** included here.

<!-- ===== POSTABLE REGION END ===== -->

---

## Pre-flight checks before this is posted (do these, do not assume)

- [ ] `gh api repos/himdo/Fable-2-Recomp --jq '{has_issues}'` — the target repo accepts issues/PRs
      (`true` at time of writing).
- [ ] Re-read **#80's thread** for anything the author has posted since 2026-10-19. A correction the
      author already made is worse than no comment.
- [ ] Search upstream issues **and** PRs for Linux work landed independently since this draft
      (`#7`, `#12` "vulkan release?", `#80`, `Improve-volkan-rendering`, `Vulkan-Renderer-Testing`).
- [ ] Confirm our presenter layout-collision finding is **not** re-reported here — it is already
      filed as `rexglue/rexglue-sdk#564`.
- [ ] Reprint the exact postable region and hash it, so what gets posted is provably the bytes
      audited.
- [ ] Note: `himdo/rexglue-sdk` has **issues disabled** — a report against the SDK can only be a PR.

## Evidence to attach once a run exists

- the built binary's `sha256` and `file` output;
- the port's own log from a launch, showing the XEX verify and the Vulkan device;
- what the screen actually showed (a numeric screenshot read, not prose).
