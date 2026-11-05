#!/usr/bin/env python3
"""Build the port capability inventory: every cvar, env var, effect and profile.

Why this exists: three separate discoveries tonight (`present_effect`, the FSR-armed
runtime profiles, the perf CSV) each cost a relaunch or a rebuild because the port's
surface was never enumerated. This script is the enumeration. Re-run it after any SDK
or port upgrade and commit the diff -- the diff IS the upgrade's capability delta.

Output: a markdown fragment on stdout.
"""
import re, subprocess, pathlib, os, sys

PORT = pathlib.Path("/run/media/feral/Games/Recomp/fable2")
SDK = pathlib.Path("/home/feral/toolchains/rexglue-sdk")

def read(p):
    try:
        return p.read_text(errors="replace")
    except Exception:
        return ""

def cvars(root):
    """REXCVAR_DEFINE_<TYPE>(name, default, "Category", "desc"  -> tuples."""
    out = []
    for ext in ("*.h", "*.cpp"):
        for f in root.rglob(ext):
            if "/thirdparty/" in str(f) or "/out/" in str(f):
                continue
            t = read(f)
            for m in re.finditer(
                r'REXCVAR_DEFINE_([A-Z0-9_]+)\(\s*([A-Za-z_0-9]+)\s*,\s*([^,]*?)\s*,\s*"([^"]*)"',
                t):
                typ, name, default, cat = m.groups()
                out.append((name, typ, default.strip(), cat, str(f.relative_to(root))))
    # dedupe by name keeping the first
    seen, uniq = set(), []
    for row in sorted(out):
        if row[0] in seen:
            continue
        seen.add(row[0]); uniq.append(row)
    return uniq

def envs(*roots):
    names = set()
    for root in roots:
        for ext in ("*.h", "*.cpp"):
            for f in root.rglob(ext):
                if "/thirdparty/" in str(f) or "/out/" in str(f):
                    continue
                for m in re.finditer(r'"((?:FABLE2|REX)_[A-Z0-9_]+)"', read(f)):
                    names.add(m.group(1))
    return sorted(names)

pc = cvars(PORT)
sc = cvars(SDK)
ev = envs(PORT, SDK)

print("## Appendix A.1 — the port's own cvars (live-settable through the remote channel)\n")
print(f"Count: **{len(pc)}**\n")
print("| cvar | type | default | category |")
print("|---|---|---|---|")
for n, t, d, c, _ in pc:
    print(f"| `{n}` | {t.replace('REXCVAR_DEFINE_','')} | `{d or '(none)'}` | {c} |")

print(f"\n## Appendix A.2 — SDK cvars inherited by every build\n")
print(f"Count: **{len(sc)}**. These are the emulator's own knobs and they are live-settable")
print("through the same `cvar` command. Grouped by category.\n")
cats = {}
for n, t, d, c, _ in sc:
    cats.setdefault(c, []).append((n, d))
for c in sorted(cats):
    print(f"\n### {c}\n")
    print("| cvar | default |")
    print("|---|---|")
    for n, d in sorted(cats[c]):
        print(f"| `{n}` | `{d or '(none)'}` |")

print(f"\n## Appendix A.3 — environment variables / debug probes\n")
print(f"Count: **{len(ev)}**. These are **launch-time only** — they are read at startup, not")
print("settable through the `cvar` command, and most must be present in the *title's*")
print("environment (verify with `/proc/<pid>/environ`, not by assuming).\n")
for e in ev:
    print(f"- `{e}`")

print(f"\n## Appendix A.4 — enum-valued cvars worth knowing\n")
print("Values pulled from the source where the default is a choice, not a number.\n")
print("| cvar | values |")
print("|---|---|")
for n, t, d, c, _ in sc + pc:
    if n in ("present_effect", "gpu_plugin", "draw_resolution_scale_x", "draw_resolution_scale_y"):
        print(f"| `{n}` | default `{d}` |")
print("| `present_effect` | `bilinear`, `cas`, `fsr`, `fsr2`, `fsr3` — **`cas`/`fsr*` are only accepted when the runtime is FSR-armed** |")
