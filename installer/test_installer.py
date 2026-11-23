"""Tests des Installers gegen ein simuliertes Geraet (kein Z2 noetig).

  python test_installer.py <original_dump.bin> <erwartetes_neues_abbild.bin> [<aeltere_ios_firmware.bin>]
"""
import hashlib, os, shutil, sys, tempfile
import z2_installer as zi

SRC, DST = open(sys.argv[1], "rb").read(), open(sys.argv[2], "rb").read()
OLD = open(sys.argv[3], "rb").read() if len(sys.argv) > 3 else None


class Fake:
    """Simuliert die DFU-Schnittstelle des Z2 samt Eigenheiten (dfuERROR nach Start, 0 Bytes vor Neustart)."""
    def __init__(self, flash, corrupt_block=None, die_after_reset=False):
        self.flash, self.corrupt, self.die = flash, corrupt_block, die_after_reset
        self.state, self.pending, self.fresh, self.present, self.writes, self.opened = 10, None, False, True, 0, False
    def count(self): return 1 if self.present else 0
    def open(self):
        if not self.present: raise zi.Z2Error("nodev")
        self.opened = True
        return {"vid": 0x17CC, "pid": 0x1130, "bcd": 0x002A}
    def close(self): self.opened = False
    def get_state(self): return self.state
    def get_status(self): return bytes([0, 1, 0, 0, self.state, 0])
    def clr_status(self): self.state = 2
    def upload(self, block):
        assert self.state in (2, 9), "upload in state %d" % self.state
        if self.fresh: return b""
        return self.flash[block * 64:(block + 1) * 64]
    def dnload(self, block, data):
        assert self.state in (2, 5)
        if block == 0: self.pending = bytearray(); self.writes += 1
        if not data:
            self.flash, self.pending, self.fresh, self.state = bytes(self.pending), None, True, 2; return
        if self.corrupt == block and self.writes == 1: data = bytes([data[0] ^ 1]) + data[1:]
        self.pending += data; self.state = 5
    def reset(self):
        self.fresh, self.state = False, 10
        if self.die: self.present = False


def run(name, fake, args, answers, expect_rc, expect_flash, expect_writes):
    d = tempfile.mkdtemp()
    it = iter(answers)
    zi.time.sleep = lambda s: None
    rc = zi.main(args + ["--lang", "de", "--backup-dir", d], backend=fake, ask=lambda p: next(it))
    backups = [f for f in os.listdir(d) if f.endswith(".z2backup")]
    good = rc == expect_rc and fake.flash == expect_flash and fake.writes == expect_writes
    print("=== %-45s %s (rc %d, writes %d, backups %d)\n" % (name, "PASS" if good else "FAIL", rc, fake.writes, len(backups)))
    return good, d, backups


res = []
orig_sleep = zi.time.sleep
class Inst(zi.Installer):
    def __init__(self, b, d, ask): super().__init__(b, d, ask, sleep=lambda s: None)
zi.Installer = Inst

g0, d0, b0 = run("check: original firmware", Fake(SRC), ["check"], [], 0, SRC, 0)
res.append(g0 and len(b0) == 1 and open(os.path.join(d0, b0[0]), "rb").read() == SRC)   # Backup ist Pflicht
res.append(run("check: already installed", Fake(DST), ["check"], [], 0, DST, 0)[0])
other = SRC[:5000] + bytes([SRC[5000] ^ 0x10]) + SRC[5001:]
res.append(run("check: unknown firmware -> refused", Fake(other), ["check"], [], 1, other, 0)[0])
res.append(run("install: unknown firmware -> nothing written", Fake(other), ["install"], ["I UNDERSTAND", "JA"], 1, other, 0)[0])
g, d, b = run("install: good path", Fake(SRC), ["install"], ["I understand", "JA"], 0, DST, 1); res.append(g and len(b) == 1)
res.append(open(os.path.join(d, b[0]), "rb").read() == SRC)
res.append(run("install: user says no", Fake(SRC), ["install"], ["I UNDERSTAND", "nein"], 1, SRC, 0)[0])
g3, d3, b3 = run("install: disclaimer not accepted", Fake(SRC), ["install"], ["yes"], 1, SRC, 0)
res.append(g3 and len(b3) == 1)                 # auch ohne Installation liegt das Backup vor
res.append(run("install: write corrupted -> auto restore", Fake(SRC, corrupt_block=700), ["install"], ["I UNDERSTAND", "JA"], 1, SRC, 2)[0])
res.append(run("install: device gone after reset", Fake(SRC, die_after_reset=True), ["install"], ["I UNDERSTAND", "JA"], 1, DST, 1)[0])
if OLD:
    res.append(run("check: older iOS firmware -> update offered", Fake(OLD), ["check"], [], 0, OLD, 0)[0])
    g2, d2, b2 = run("install: update from older iOS firmware", Fake(OLD), ["install"], ["I UNDERSTAND", "JA"], 0, DST, 1)
    res.append(g2 and len(b2) == 1 and open(os.path.join(d2, b2[0]), "rb").read() == OLD)
# restore: backup from the good run back onto a device running the new firmware
f = Fake(DST); it = iter(["1", "JA"])
rc = zi.main(["restore", "--lang", "de", "--backup-dir", d], backend=f, ask=lambda p: next(it))
res.append(rc == 0 and f.flash == SRC); print("=== restore from list:", res[-1], "\n")
# restore: damaged backup file is refused
bad = os.path.join(d, b[0]); raw = bytearray(open(bad, "rb").read()); raw[30000] ^= 1; open(bad, "wb").write(raw)
f = Fake(DST)
rc = zi.main(["restore", bad, "--lang", "en", "--backup-dir", d], backend=f, ask=lambda p: "YES")
res.append(rc == 1 and f.flash == DST and f.writes == 0); print("=== damaged backup refused:", res[-1], "\n")
print("ALL PASS" if all(res) else "FAILURES: %s" % res)
sys.exit(0 if all(res) else 1)
