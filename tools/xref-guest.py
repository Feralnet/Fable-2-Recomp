#!/usr/bin/env python3
"""Find PPC code that references a 32-bit guest data address in the Fable II image.

The Xbox 360 PowerPC ABI materialises a data address as
    lis   rD, hi16(addr)            (or addis rD, 0, hi16)
    ...   lfs/lwz/addi/lfd rT, lo16(rD)
so we scan for addis-with-rA=0 of the target's high half and then look ahead
for an instruction whose rA is that register and whose 16-bit immediate is the
low half of the target.

Usage: xref-guest.py <image.bin> <image_base_hex> <addr_hex> [addr_hex ...]
"""
import sys

OP_ADDIS = 15
OP_ADDI = 14
OP_ADDIC = 12
OP_ORI = 24
OP_LWZ = 32
OP_LFS = 48
OP_LFD = 50
OP_STW = 36
OP_STFS = 52
OP_STFD = 54
OP_CMPWI = 11
OP_RLWINM = 21
OP_BC = 16
OP_B = 18

NAMES = {
    OP_ADDIS: "addis", OP_ADDI: "addi", OP_ADDIC: "addic", OP_ORI: "ori",
    OP_LWZ: "lwz", OP_LFS: "lfs", OP_LFD: "lfd", OP_STW: "stw",
    OP_STFS: "stfs", OP_STFD: "stfd", OP_CMPWI: "cmpwi", OP_RLWINM: "rlwinm",
    OP_BC: "bc", OP_B: "b",
}


def sx16(v):
    return v - 0x10000 if v & 0x8000 else v


def decode(w):
    op = w >> 26
    if op == OP_ADDIS:
        rd = (w >> 21) & 0x1F
        ra = (w >> 16) & 0x1F
        imm = w & 0xFFFF
        ra_s = "0" if ra == 0 else "r%d" % ra
        return "addis r%d, %s, 0x%04X (%d)" % (rd, ra_s, imm, sx16(imm)), rd, ra, imm
    if op == OP_ADDI:
        rd = (w >> 21) & 0x1F
        ra = (w >> 16) & 0x1F
        imm = w & 0xFFFF
        ra_s = "0" if ra == 0 else "r%d" % ra
        return "addi r%d, %s, 0x%04X (%d)" % (rd, ra_s, imm, sx16(imm)), rd, ra, imm
    if op == OP_ADDIC:
        rd = (w >> 21) & 0x1F
        ra = (w >> 16) & 0x1F
        imm = w & 0xFFFF
        return "addic r%d, r%d, 0x%04X" % (rd, ra, imm), rd, ra, imm
    if op == OP_ORI:
        rs = (w >> 21) & 0x1F
        ra = (w >> 16) & 0x1F
        imm = w & 0xFFFF
        return "ori r%d, r%d, 0x%04X" % (ra, rs, imm), ra, rs, imm
    if op in (OP_LWZ, OP_LFS, OP_LFD, OP_STW, OP_STFS, OP_STFD):
        rt = (w >> 21) & 0x1F
        ra = (w >> 16) & 0x1F
        imm = w & 0xFFFF
        return "%s r%d, 0x%04X (r%d)" % (NAMES[op], rt, imm, ra), rt, ra, imm
    if op == OP_RLWINM:
        rs = (w >> 21) & 0x1F
        ra = (w >> 16) & 0x1F
        return "rlwinm r%d, r%d, %d,%d,%d" % (
            ra, rs, (w >> 11) & 0x1F, (w >> 6) & 0x1F, (w >> 1) & 0x1F), ra, rs, w & 0xFFFF
    if op == OP_B:
        li = w & 0x03FFFFFC
        if li & 0x02000000:
            li -= 0x04000000
        if w & 1:
            return "bl 0x%X" % li, None, None, 0
        return "b 0x%X" % li, None, None, 0
    if op == OP_CMPWI:
        ra = (w >> 16) & 0x1F
        imm = w & 0xFFFF
        return "cmpwi r%d, 0x%04X (%d)" % (ra, imm, sx16(imm)), None, ra, imm
    return "op%d 0x%08X" % (op, w), None, None, w & 0xFFFF


def main():
    image_path, base_hex = sys.argv[1], sys.argv[2]
    targets = [int(a, 16) for a in sys.argv[3:]]
    with open(image_path, "rb") as f:
        img = f.read()
    base = int(base_hex, 16)
    nwords = len(img) // 4
    # index of "lis rX, hi16" instructions per high-half value
    lis_sites = {}  # hi16 -> list of (word_index, rt)
    for i in range(nwords):
        w = int.from_bytes(img[i * 4:i * 4 + 4], "big")
        if (w >> 26) == OP_ADDIS and ((w >> 16) & 0x1F) == 0:
            lis_sites.setdefault(w & 0xFFFF, []).append((i, (w >> 21) & 0x1F))

    for target in targets:
        # A data address is usually materialised as lis of the page above when
        # the low half is a negative signed offset: lis rX,0x820A then
        # lfs f1,-0x184(rX). Try both page bases.
        page = (target >> 16) & 0xFFFF
        lo = target & 0xFFFF
        cands = [(page, lo)]
        if lo >= 0x8000:
            cands.append(((page + 1) & 0xFFFF, lo))
        print("=== 0x%08X candidates %s" % (
            target, ", ".join("hi 0x%04X lo 0x%04X" % c for c in cands)))
        ptr = target.to_bytes(4, "big")
        print("  literal 4-byte occurrences as data: %d" % img.count(ptr))
        hits = 0
        for hi, lo in cands:
            for idx, rt in lis_sites.get(hi, []):
                for j in range(idx + 1, min(idx + 400, nwords)):
                    w = int.from_bytes(img[j * 4:j * 4 + 4], "big")
                    op = w >> 26
                    text, rd, ra, imm = decode(w)
                    if op in (OP_LWZ, OP_LFS, OP_LFD, OP_STW, OP_STFS, OP_STFD,
                              OP_ADDI, OP_ADDIC) and ra == rt and (w & 0xFFFF) == lo:
                        hits += 1
                        print("  xref at guest 0x%08X via lis@0x%08X (r%d)" % (
                            base + j * 4, base + idx * 4, rt))
                        for k in range(max(0, j - 5), min(nwords, j + 6)):
                            ww = int.from_bytes(img[k * 4:k * 4 + 4], "big")
                            mark = ">>" if k == j else "  "
                            print("     %s 0x%08X  %08X  %s" % (
                                mark, base + k * 4, ww, decode(ww)[0]))
                        break
        print("  total xrefs: %d" % hits)
        print()


if __name__ == "__main__":
    main()
