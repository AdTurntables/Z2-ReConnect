"""Wrap a raw XS1 tile memory image (loaded at 0x10000) into a minimal xcore ELF32 file,
so xobjdump --replace / xflash can package it.

  python mkelf.py tile.bin out.elf [load_addr]
"""
import struct, sys

EM_XCORE = 0xCB


def mkelf(img, load=0x10000):
    shstr = b"\0.text\0.shstrtab\0"
    ehsize, phsize, shsize = 52, 32, 40
    ph_off = ehsize
    data_off = (ph_off + phsize + 3) & ~3
    shstr_off = data_off + len(img)
    sh_off = (shstr_off + len(shstr) + 3) & ~3
    eh = b"\x7fELF" + bytes([1, 1, 1, 0]) + bytes(8)
    eh += struct.pack("<HHIIIIIHHHHHH", 2, EM_XCORE, 1, load, ph_off, sh_off, 0, ehsize, phsize, 1, shsize, 3, 2)
    ph = struct.pack("<8I", 1, data_off, load, load, len(img), len(img), 7, 4)
    sh = bytes(shsize)
    sh += struct.pack("<10I", 1, 1, 7, load, data_off, len(img), 0, 0, 4, 0)          # .text PROGBITS AWX
    sh += struct.pack("<10I", 7, 3, 0, 0, shstr_off, len(shstr), 0, 0, 1, 0)          # .shstrtab
    out = bytearray(eh + ph)
    out += bytes(data_off - len(out)) + img + shstr
    out += bytes(sh_off - len(out)) + sh
    return bytes(out)


if __name__ == "__main__":
    img = open(sys.argv[1], "rb").read()
    load = int(sys.argv[3], 0) if len(sys.argv) > 3 else 0x10000
    open(sys.argv[2], "wb").write(mkelf(img, load))
