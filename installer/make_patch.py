"""Erzeugt die Patch-Datei fuer den Installer (nur fuer den Entwickler).

  python make_patch.py <original_dump.bin> <neues_abbild.bin> <ausgabe.z2patch> "<Name>"

Die Patch-Datei enthaelt nur die Unterschiede: Kopier-Anweisungen (Offset, Laenge) auf den Dump, den
jeder Nutzer aus seinem eigenen Z2 liest, und die neu hinzugekommenen Bytes. Die Original-Firmware
selbst ist nicht enthalten.
"""
import hashlib, json, struct, sys, zlib

K = 16


def make_ops(src, dst):
    index = {}
    for i in range(0, len(src) - K + 1):
        index.setdefault(src[i:i + K], i)
    ops, lit, i = [], bytearray(), 0
    while i < len(dst):
        j = index.get(dst[i:i + K]) if i + K <= len(dst) else None
        if j is None:
            lit.append(dst[i]); i += 1; continue
        n = K
        while i + n < len(dst) and j + n < len(src) and dst[i + n] == src[j + n]: n += 1
        if lit: ops.append(("ins", bytes(lit))); lit = bytearray()
        ops.append(("copy", j, n)); i += n
    if lit: ops.append(("ins", bytes(lit)))
    return ops


def main():
    src, dst = open(sys.argv[1], "rb").read(), open(sys.argv[2], "rb").read()
    ops = make_ops(src, dst)
    body = bytearray()
    for op in ops:
        if op[0] == "copy": body += struct.pack("<BII", 0, op[1], op[2])
        else: body += struct.pack("<BI", 1, len(op[1])) + op[1]
    head = json.dumps({"name": sys.argv[4], "source_sha256": hashlib.sha256(src).hexdigest(), "source_size": len(src),
                       "target_sha256": hashlib.sha256(dst).hexdigest(), "target_size": len(dst)}).encode()
    out = b"Z2PATCH1" + struct.pack("<I", len(head)) + head + zlib.compress(bytes(body), 9)
    open(sys.argv[3], "wb").write(out)
    new = sum(len(o[1]) for o in ops if o[0] == "ins")
    print("%d Anweisungen, %d neue Bytes, %d kopierte Bytes, Patch %d Bytes" % (len(ops), new, len(dst) - new, len(out)))
    print(head.decode())


if __name__ == "__main__":
    main()
