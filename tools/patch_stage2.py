"""Stage-2 patch for Z2 firmware 42, core 1: panel -> USB-MIDI on EP 0x84.

On top of stage 1 (descriptors):
  * the xcc-built blob (firmware/stage2/blob.elf: midi_glue.c + z2midi + hooks) is relocated
    into the dormant CDC-ECM packet pool at BLOB_AT (pool 0x19f8c..0x1af6c, ECM never runs in
    normal mode); the tile image is extended up to the end of the blob, the gap from the old
    image end is zero-filled (it is .bss and was zeroed by the C runtime before)
  * the C runtime's .bss clear (0x18514) now starts behind the blob
  * three call sites in NI's HID thread are redirected to the hooks

  python patch_stage2.py build/ni_t1.bin ../firmware/stage2/blob.elf build/z2midi2_t1.bin
"""
import struct, sys
import capstone as cs
from patch_stage1 import patch as stage1

BASE = 0x10000
OLD_END = 0x19dc0             # end of NI's loaded image (bss starts here)
POOL = (0x19f8c, 0x1af6c)     # ECM packet pool, unused in normal mode
BLOB_AT = 0x19f90
BSS_CLEAR_LDAP = 0x18514      # ldap r11, <bss start> (4 bytes, prefixed)
SITES = {0x12d5e: ("z2_hook_init", 0x130cc), 0x12c6c: ("z2_hook_report", 0x13104),
         0x12e62: ("z2_hook_token", 0x13114)}
# NI's endpoint interrupt handlers (IN 0x14d94, OUT 0x14dd4) fetch the token chanend with
# "ldw r0, dp[0x2d2]" (0x19528). They run on the kernel stack whose top is 0x19524 (set up at
# 0x14d7e), after "kentsp 5", so the same word is sp[6]. Using sp makes the handlers independent
# of dp, and the blob (own dp/cp) can run with interrupts enabled.
ISR_SITES = (0x14dc2, 0x14e00)
ISR_OLD, ISR_NEW = bytes.fromhex("0bf01258"), bytes.fromhex("065c0090")   # ldw r0, sp[6]; nop


def elf_image(path):
    d = open(path, "rb").read()
    phoff, = struct.unpack_from("<I", d, 28); phsz, phn = struct.unpack_from("<HH", d, 42)
    shoff, = struct.unpack_from("<I", d, 32); shsz, shn, shstr = struct.unpack_from("<HHH", d, 46)
    mem = {}; end = 0
    for i in range(phn):
        t, off, va, pa, fsz, msz, fl, al = struct.unpack_from("<8I", d, phoff + i * phsz)
        if t != 1 or msz == 0: continue
        mem[va] = d[off:off + fsz] + bytes(msz - fsz); end = max(end, va + msz)
    img = bytearray(end - BASE)
    for va, b in mem.items(): img[va - BASE:va - BASE + len(b)] = b
    # symbols
    secs = [struct.unpack_from("<10I", d, shoff + i * shsz) for i in range(shn)]
    syms = {}
    for s in secs:
        if s[1] == 2:  # SYMTAB
            strtab = secs[s[6]]
            for j in range(s[5] // 16):
                nm, val, size, info, oth, shndx = struct.unpack_from("<IIIBBH", d, s[4] + j * 16)
                name = d[strtab[4] + nm:d.index(b"\0", strtab[4] + nm)].decode()
                if name: syms[name] = val
    return bytes(img), syms


def enc_ldap_fwd(pc, target):
    imm = (target - (pc + 4)) // 2; assert imm >= 0 and imm < (1 << 20)
    return struct.pack("<HH", 0xf000 | (imm >> 10), 0xd800 | (imm & 0x3ff))


def enc_bl_fwd(pc, target):
    imm = (target - (pc + 4)) // 2; assert imm >= 0 and imm < (1 << 20)
    return struct.pack("<HH", 0xf000 | (imm >> 10), 0xd000 | (imm & 0x3ff))


def dis(t, a, n=1):
    md = cs.Cs(cs.CS_ARCH_XCORE, cs.CS_MODE_BIG_ENDIAN)
    return ["%x: %s %s" % (i.address, i.mnemonic, i.op_str) for i in md.disasm(t[a - BASE:a - BASE + 8], a, count=n)]


def patch(t1, blob_path):
    t, _ = stage1(t1)
    t = bytearray(t)
    assert len(t) == OLD_END - BASE
    blob, syms = elf_image(blob_path)
    delta = BLOB_AT - BASE
    blob_end = BLOB_AT + len(blob)
    blob_end = (blob_end + 3) & ~3
    assert POOL[0] <= BLOB_AT and blob_end <= POOL[1], hex(blob_end)
    # extend image: zeros from old end to blob, then blob
    t += bytes(BLOB_AT - OLD_END)
    t += blob + bytes(blob_end - BLOB_AT - len(blob))
    # .bss clear now starts behind the blob
    assert t[BSS_CLEAR_LDAP - BASE:BSS_CLEAR_LDAP - BASE + 4] == bytes.fromhex("03f054d8")
    t[BSS_CLEAR_LDAP - BASE:BSS_CLEAR_LDAP - BASE + 4] = enc_ldap_fwd(BSS_CLEAR_LDAP, blob_end)
    # redirect call sites
    for site, (hook, orig) in SITES.items():
        old = t[site - BASE:site - BASE + 4]
        assert old == enc_bl_fwd(site, orig), (hex(site), old.hex())
        t[site - BASE:site - BASE + 4] = enc_bl_fwd(site, syms[hook] + delta)
    for site in ISR_SITES:
        assert t[site - BASE:site - BASE + 4] == ISR_OLD, hex(site)
        t[site - BASE:site - BASE + 4] = ISR_NEW
    report = {
        "blob": (hex(BLOB_AT), hex(blob_end), len(blob)),
        "hooks": {h: hex(syms[h] + delta) for h, _ in SITES.values()},
        "cp/dp": (hex(syms["_cp"] + delta), hex(syms["_dp"] + delta)),
        "bss_clear": dis(t, BSS_CLEAR_LDAP),
        "sites": [dis(t, s)[0] for s in SITES],
        "isr": [dis(t, s, 2) for s in ISR_SITES],
    }
    return bytes(t), report


if __name__ == "__main__":
    out, rep = patch(open(sys.argv[1], "rb").read(), sys.argv[2])
    open(sys.argv[3], "wb").write(out)
    for k, v in rep.items(): print(k, v)
