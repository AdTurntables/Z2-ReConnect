"""Annotated XCore (XS1) listing of one tile image of the Z2 firmware.

  python xdis.py analysis/tile1.bin analysis/tile1.lst
Resolves relative branches/ldap to absolute addresses, dp/cp-relative ldw/ldaw to absolute
data addresses (dp/cp taken from the startup code), marks function starts (entsp/dualentsp)
and annotates references to known strings/descriptor addresses.
"""
import sys, re, struct, capstone as cs

BASE = 0x10000
REL = {"bl", "bu", "bt", "bf", "ldap", "brft", "brbt", "brff", "brbf", "blrf", "blrb", "brfu", "brbu"}


def main(src, dst):
    t = open(src, "rb").read()
    md = cs.Cs(cs.CS_ARCH_XCORE, cs.CS_MODE_BIG_ENDIAN)
    ins = []
    pos = 0
    while pos < len(t):
        got = list(md.disasm(t[pos:pos + 4], BASE + pos, count=1))
        if got:
            ins.append(got[0]); pos += got[0].size
        else:
            ins.append(None); pos += 2
    # dp / cp from startup: ldap r11,X ; set cp,r11 ; ldap r11,Y ; set dp,r11
    dp = cp = None
    seq = [i for i in ins[:40] if i]
    for a, b in zip(seq, seq[1:]):
        if a.mnemonic == "ldap" and b.mnemonic == "set":
            tgt = a.address + a.size + 2 * int(a.op_str.split(",")[1], 0)
            if "cp" in b.op_str: cp = tgt
            if "dp" in b.op_str: dp = tgt
    strings = {}
    for m in re.finditer(rb"[\x20-\x7e]{4,}\x00", t):
        strings[BASE + m.start()] = m.group()[:-1].decode()
    out = open(dst, "w", encoding="utf-8")
    out.write("; dp=%s cp=%s\n" % (hex(dp or 0), hex(cp or 0)))
    pos = 0
    for i in ins:
        if i is None:
            pos += 2; continue
        ops = i.op_str; note = ""
        if i.mnemonic in REL and ops:
            parts = [p.strip() for p in ops.split(",")]
            try:
                off = int(parts[-1], 0)
                tgt = i.address + i.size + 2 * off
                note = "-> %s" % hex(tgt)
                if tgt in strings: note += '  "%s"' % strings[tgt]
            except ValueError:
                pass
        mm = re.search(r"(dp|cp)\[(0x[0-9a-f]+|\d+)\]", ops)
        if mm and dp:
            base = dp if mm.group(1) == "dp" else cp
            a = base + 4 * int(mm.group(2), 0)
            note = "@%s" % hex(a)
            if a in strings: note += '  "%s"' % strings[a]
        if i.mnemonic in ("entsp", "dualentsp"):
            out.write("\nfn_%x:\n" % i.address)
        out.write("%05x  %-9s %-8s %-28s %s\n" % (i.address, i.bytes.hex(), i.mnemonic, ops, note))
    out.close()
    print("dp", hex(dp or 0), "cp", hex(cp or 0), "instructions", sum(1 for i in ins if i))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
