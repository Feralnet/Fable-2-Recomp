
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
