#!/usr/bin/env python3
"""Dump guest image bytes/floats around addresses, and count 32-bit patterns.

Usage: dump-guest.py <image.bin> <base_hex> dump <addr_hex> [bytes]
       dump-guest.py <image.bin> <base_hex> find <value_hex> [value_hex ...]
"""
import struct
import sys


def main():
    path, base_hex, mode = sys.argv[1], sys.argv[2], sys.argv[3]
    base = int(base_hex, 16)
    with open(path, "rb") as f:
        img = f.read()

    if mode == "dump":
        addr = int(sys.argv[4], 16)
        span = int(sys.argv[5]) if len(sys.argv) > 5 else 64
        off = addr - base - span
        for i in range(0, span * 2, 4):
            a = off + i
            if a < 0 or a + 4 > len(img):
                continue
            w = int.from_bytes(img[a:a + 4], "big")
            fv = struct.unpack(">f", img[a:a + 4])[0]
            mark = "<--" if base + a == addr else ""
            print("0x%08X  %08X  %14.6f  %s" % (base + a, w, fv, mark))
    elif mode == "find":
        for v in sys.argv[4:]:
            pat = int(v, 16).to_bytes(4, "big")
            hits = []
            start = 0
            while True:
                i = img.find(pat, start)
                if i < 0:
                    break
                hits.append(base + i)
                start = i + 1
            print("%s -> %d hit(s): %s" % (
                v, len(hits), " ".join("0x%08X" % h for h in hits[:20])))


if __name__ == "__main__":
    main()
