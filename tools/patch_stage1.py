"""Stage-1 patch for Z2 firmware 42, core 1: expose a USB-MIDI 1.0 function.

Descriptor-only change, no new code:
  * config template @0x18dd4 (389 bytes): the two control-less UAC2 feature units (ids 10, 11)
    are removed (output terminals wired straight to the input terminals), and the hidden CDC-ECM
    function (IF5/IF6, 55 bytes) is replaced by IAD + USB-MIDI AudioControl (IF5) +
    MIDIStreaming (IF6) on the bulk endpoints that XUD already serves (EP 0x03 OUT, EP 0x84 IN).
  * wTotalLength variable @0x1934c: 389 -> new length.
  * endpoint0 @0x11f70: the branch that either strips the ECM part (mode 0) or switches the
    device class to CDC (ECM mode) is replaced by a jump straight to the common code @0x11f8e,
    so the device keeps class EF/02/01 and reports all 7 interfaces.

  python patch_stage1.py build/ni_t1.bin build/z2midi1_t1.bin
"""
import struct, sys

BASE = 0x10000
CFG = 0x18dd4
CFG_LEN = 389
TOTLEN_VAR = 0x1934c
BRANCH = 0x11f70
COMMON = 0x11f8e

MIDI = bytes.fromhex(
    "080b050201010000"          # IAD: first IF 5, 2 interfaces, audio class
    "090405000001010000"        # IF5 AudioControl, 0 EPs
    "092401000109000106"        # AC header 1.0, total 9, 1 streaming IF = 6
    "090406000201030000"        # IF6 MIDIStreaming, 2 EPs
    "07240100014100"            # MS header 1.0, wTotalLength 0x41 (65)
    "062402010100"              # MIDI IN jack, embedded, id 1
    "062402020200"              # MIDI IN jack, external, id 2
    "092403010301020100"        # MIDI OUT jack, embedded, id 3, source = jack 2
    "092403020401010100"        # MIDI OUT jack, external, id 4, source = jack 1
    "090503020002000000"        # EP 0x03 OUT bulk 512
    "0525010101"                # CS EP: 1 embedded IN jack (id 1)
    "090584020002000000"        # EP 0x84 IN bulk 512
    "0525010103"                # CS EP: 1 embedded OUT jack (id 3)
)


def walk(d):
    o = 0; out = []
    while o < len(d) and d[o]:
        out.append((o, d[o], d[o + 1], d[o:o + d[o]])); o += d[o]
    return out


def patch(t1):
    t = bytearray(t1)
    cfg = bytes(t[CFG - BASE:CFG - BASE + CFG_LEN])
    assert cfg[:2] == b"\x09\x02" and cfg[4] == 7, "unexpected config template"
    assert struct.unpack_from("<I", t, TOTLEN_VAR - BASE)[0] == CFG_LEN
    descs = walk(cfg)
    new = bytearray(); cur_if = None; removed_fu = 0; ac_hdr_at = None
    for o, l, ty, b in descs:
        if ty == 4: cur_if = b[2]
        if cur_if is not None and cur_if >= 5:
            continue                                   # drop CDC-ECM IF5/IF6 and their descriptors
        b = bytearray(b)
        if cur_if == 0 and ty == 0x24:
            st = b[2]
            if st == 1: ac_hdr_at = len(new)
            if st == 6:                                # feature unit: all controls must be zero
                assert all(x == 0 for x in b[5:l - 1]), "feature unit has controls"
                removed_fu += l; continue
            if st == 3:                                # output terminal: bypass the feature unit
                b[7] = {10: 2, 11: 1}[b[7]]
        new += b
    assert removed_fu == 68, removed_fu
    ac_tot = struct.unpack_from("<H", new, ac_hdr_at + 6)[0]
    struct.pack_into("<H", new, ac_hdr_at + 6, ac_tot - removed_fu)
    new += MIDI
    assert len(new) <= CFG_LEN, len(new)
    t[CFG - BASE:CFG - BASE + CFG_LEN] = bytes(new) + bytes(CFG_LEN - len(new))
    struct.pack_into("<I", t, TOTLEN_VAR - BASE, len(new))
    # bu u6 (BRFU_u6): target = pc + 2 + 2*u6 ; encoding 0x7300 | u6
    u6 = (COMMON - (BRANCH + 2)) // 2
    assert 0 <= u6 < 64
    assert t[BRANCH - BASE:BRANCH - BASE + 4] == bytes.fromhex("02f02d78")
    struct.pack_into("<H", t, BRANCH - BASE, 0x7300 | u6)
    return bytes(t), len(new)


if __name__ == "__main__":
    src, dst = sys.argv[1], sys.argv[2]
    out, n = patch(open(src, "rb").read())
    open(dst, "wb").write(out)
    print("config length", n, "->", dst)
