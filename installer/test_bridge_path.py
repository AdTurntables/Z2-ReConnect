"""Tests of the installer's bridge path (intermediate step, tester function) against a simulated Z2.
No hardware. Own code.

  python test_bridge_path.py <bridge.bin (sha256 = BRIDGE_SHA256)> <nifw42_dump> <expected beta2 image>

The simulated device ("World") models what was observed on the owner's Z2 on 25./26.11.2026:
  - factory firmware (bcdDevice 0x001E) with an empty slot: UPLOAD returns 0 bytes; DNLOAD from appIDLE
    goes to dfuERROR with status 0 and writes NOTHING (NI quirk), after CLRSTATUS it works;
  - the bridge (bcdDevice 0x0001): UPLOAD block 0xC7A0 = 16-byte trial report "Z2PB"; DNLOAD from appIDLE works;
    every start of an uncommitted bridge counts, the 4th deletes it (factory again) - the self-erase on the 4th
    start is proven in host tests and xsim, NOT yet observed on the device (ANNAHME);
  - an incomplete slot (power loss while writing) is not bootable: the factory firmware runs and its UPLOAD
    returns the incomplete bytes (derived from research/usb_dfu.md 6.3, ANNAHME);
  - NI Device Updater (simulated): installs firmware 42 over the bridge;
  - firmware 42 / Beta 2 (bcdDevice 0x002A): like the existing installer tests.
"""
import hashlib, os, struct, sys, tempfile
import z2_installer as zi

BRIDGE, NI42, BETA2 = (open(p, "rb").read() for p in sys.argv[1:4])
assert hashlib.sha256(BRIDGE).hexdigest() == zi.BRIDGE_SHA256, "wrong bridge file for this installer"
TMP = tempfile.mkdtemp()
BRIDGE_PATH = os.path.join(TMP, zi.BRIDGE_FILE)
open(BRIDGE_PATH, "wb").write(BRIDGE)
_orig_find = zi.find_file
USE_BRIDGE = {"on": True}
zi.find_file = lambda name: (BRIDGE_PATH if USE_BRIDGE["on"] else None) if name == zi.BRIDGE_FILE else _orig_find(name)
zi.time.sleep = lambda s: None


class Inst(zi.Installer):
    def __init__(self, b, d, ask): super().__init__(b, d, ask, sleep=lambda s: None)
zi.Installer = Inst


class World:
    def __init__(self, factory_bcd=0x001E, slot=None, quirk_twice=False, die_after_reset=False, trial_state=1,
                 junk=False, busy=False):
        self.factory_bcd, self.slot = factory_bcd, slot
        self.trial_state, self.junk, self.busy, self.clr_count = trial_state, junk, busy, 0
        self.quirk_twice, self.die = quirk_twice, die_after_reset
        self.starts, self.writes, self.present, self.pending, self.fresh = 0, 0, True, None, False
        self.boot()

    # what runs after a (re)start
    def running(self):
        if self.slot is None or self.junk: return "factory"
        if self.slot == BRIDGE: return "bridge"
        return "ni"

    def boot(self):
        if self.running() == "bridge":
            self.starts += 1
            if self.starts > 3: self.slot, self.starts = None, 0          # trial limit: bridge deletes itself
        self.state = 5 if getattr(self, "busy", False) else 0   # busy: another program is downloading
        self.fresh = False
        self.quirk_seen = 0

    def bcd(self):
        return {"factory": self.factory_bcd, "bridge": 0x0001, "ni": 0x002A}[self.running()]

    # backend API used by the installer
    def count(self): return 1 if self.present else 0
    def open(self):
        if not self.present: raise zi.Z2Error("nodev")
        return {"vid": 0x17CC, "pid": 0x1130, "bcd": self.bcd()}
    def close(self): pass
    def get_state(self): return self.state
    def get_status(self): return bytes([0, 1, 0, 0, self.state, 0])
    def clr_status(self):
        self.clr_count += 1
        if self.state == 10: self.state = 2
        elif self.running() != "bridge": self.state = 10                    # NI: CLRSTATUS elsewhere -> error
    def abort(self): self.state = 2 if self.state != 0 else 0
    def upload(self, block):
        if self.running() == "bridge" and block == zi.TRIAL_QUERY:
            return b"Z2PB" + bytes([self.trial_state, self.starts, 3, 0, 0x00, 0x01, 0x01]) + bytes(5)
        if self.running() != "bridge" and self.state == 0:
            self.state = 10; return b""                 # NI: UPLOAD from appIDLE -> 0 bytes + dfuERROR (observed)
        assert self.state in ((0, 2, 9) if self.running() == "bridge" else (2, 9)), "upload in state %d" % self.state
        if self.slot is None or self.fresh: return b""
        return self.slot[block * 64:(block + 1) * 64]
    def dnload(self, block, data):
        if self.running() != "bridge" and self.state == 0:
            self.state = 10; self.quirk_seen += 1; return                   # NI quirk, nothing written
        if self.running() != "bridge" and block == 0 and self.quirk_twice and self.quirk_seen < 2:
            self.quirk_seen += 1; self.state = 10; return                   # quirk again on the retry
        assert self.state in ((0, 2, 5) if self.running() == "bridge" else (2, 5)), "dnload in state %d" % self.state
        if block == 0: self.pending = bytearray(); self.writes += 1
        if not data:
            self.slot, self.pending, self.fresh, self.state = bytes(self.pending), None, True, 2
            self.junk = False
            if self.running() == "bridge": self.starts = 0
            return
        self.pending += data; self.state = 5
    def reset(self):
        if self.die: self.present = False; return
        self.boot()

    def ni_updater(self):
        """NI Device Updater 1.2.0 (simulated): bridge reports 1 < 42 -> installs firmware 42."""
        assert self.running() == "bridge"
        self.slot, self.starts = NI42, 0; self.boot()


res = []


def run(name, world, args, answers, expect_rc, check=lambda w, d: True):
    d = tempfile.mkdtemp()
    it = iter(answers)
    rc = zi.main(args + ["--lang", "de", "--backup-dir", d], backend=world, ask=lambda p: next(it, "nein"))
    ok = rc == expect_rc and check(world, d)
    print("=== %-62s %s (rc %d, writes %d, slot %s)\n" % (name, "PASS" if ok else "FAIL", rc, world.writes,
                                                         world.running() if world.slot is not None else "empty"))
    res.append(ok)
    return d


def no_backup(d): return not [f for f in os.listdir(d) if f.endswith(".z2backup")]
def log_ok(d):
    p = os.path.join(d, zi.BRIDGE_LOG)
    return os.path.isfile(p) and "Z2RCBR" not in open(p, encoding="utf-8").read()


# 1. without the bridge file: factory unit refused as before, nothing written
USE_BRIDGE["on"] = False
run("no bridge file: factory 30 empty -> refused", World(), ["install"], ["I UNDERSTAND", "JA"], 1,
    lambda w, d: w.writes == 0 and w.slot is None)
USE_BRIDGE["on"] = True

# 2. check only: factory_empty recognised, no backup, nothing written
run("check: factory 30 empty -> intermediate step offered", World(), ["check"], [], 0,
    lambda w, d: w.writes == 0 and no_backup(d))

# 3. full chain on factory 30: bridge -> hand-off -> NI updater -> Beta 2
w = World()
d = run("install: factory 30 -> bridge written (quirk once), verified", w, ["install"], ["I UNDERSTAND", "JA"], 0,
        lambda w, d: w.slot == BRIDGE and w.writes == 1 and w.running() == "bridge" and w.starts == 1 and log_ok(d))
run("install again while the bridge runs: hand-off only, nothing written", w, ["install"], [], 0,
    lambda w, d: w.writes == 1 and w.slot == BRIDGE)
w.ni_updater()
run("after NI updater: firmware 42 -> Beta 2 installed", w, ["install"], ["I UNDERSTAND", "JA"], 0,
    lambda w, d: w.slot == BETA2 and w.writes == 2)

# 4. user declines at each prompt
for ans, what in ((["no"], "disclaimer"), (["I UNDERSTAND", "nein"], "final JA")):
    run("install: declined at %s -> nothing written" % what, World(), ["install"], ans, 1,
        lambda w, d: w.writes == 0 and w.slot is None)

# 5. factory 51 (untested): needs the tester word
run("factory 51: without tester word -> cancelled", World(0x0033), ["install"], ["I UNDERSTAND", "JA", "JA"], 1,
    lambda w, d: w.writes == 0)
run("factory 51: with tester word -> bridge written", World(0x0033), ["install"], ["I UNDERSTAND", "TESTEN", "JA"], 0,
    lambda w, d: w.slot == BRIDGE and log_ok(d))

# 6. other factory version with an empty slot: refused, diagnosis file
run("factory 0x40 empty -> refused, nothing written", World(0x0040), ["install"], ["I UNDERSTAND", "TESTEN", "JA"], 1,
    lambda w, d: w.writes == 0 and os.path.isfile(os.path.join(d, "Z2-ReConnect-Diagnose.txt")))

# 7. quirk twice -> abort without a loop
run("quirk appears twice -> abort, nothing written", World(quirk_twice=True), ["install"], ["I UNDERSTAND", "JA"], 1,
    lambda w, d: w.writes == 0 and w.slot is None)

# 8. device gone after the restart -> fallback text, rc 1
run("device gone after restart -> fallback", World(die_after_reset=True), ["install"], ["I UNDERSTAND", "JA"], 1,
    lambda w, d: w.slot == BRIDGE and log_ok(d))

# 9. bridge with 2 of 3 starts used -> refresh offered; yes -> rewritten, counter reset
w = World(slot=BRIDGE); w.reset()                                       # second start
run("bridge 2/3: refresh offered and done", w, ["install"], ["JA"], 0,
    lambda w, d: w.writes == 1 and w.slot == BRIDGE and w.starts == 1)
w = World(slot=BRIDGE); w.reset()
run("bridge 2/3: refresh declined -> hand-off only", w, ["install"], ["nein"], 0, lambda w, d: w.writes == 0)

# 10. another bridge build running (header differs) -> never read further, advice, no write
other = bytes([BRIDGE[0] ^ 1]) + BRIDGE[1:]
class WorldOther(World):
    def running(self): return "bridge" if self.slot is not None else "factory"
w = WorldOther(slot=other)
d = run("other bridge build -> advice (power cycles), nothing written", w, ["install"], ["JA"], 1,
        lambda w, d: w.writes == 0)

# 11. manipulated bridge file -> path not offered at all
open(BRIDGE_PATH, "wb").write(BRIDGE[:-1] + bytes([BRIDGE[-1] ^ 1]))
w = World()
run("manipulated bridge file -> refused, nothing written", w, ["install"], ["I UNDERSTAND", "JA"], 1,
    lambda w, d: w.writes == 0)
open(BRIDGE_PATH, "wb").write(BRIDGE)


# 12. factory 30 that returns data in one pass only -> not "empty", error
class Flaky(World):
    def upload(self, block):
        self.calls = getattr(self, "calls", 0) + 1
        if self.calls == 1: return b"\x55" * 64 if block == 0 else b""
        return super().upload(block)
run("factory 30, inconsistent reads -> error, nothing written", Flaky(), ["install"], ["I UNDERSTAND", "JA"], 1,
    lambda w, d: w.writes == 0)

# 13. bridge running but this installer has no bridge file: recognised, hand-off, no write
USE_BRIDGE["on"] = False
w = World(slot=BRIDGE)
run("bridge running, no bridge file -> recognised, hand-off, nothing written", w, ["install"], [], 0,
    lambda w, d: w.writes == 0)
USE_BRIDGE["on"] = True

# 14. after writing the bridge the trial counter is not active -> failure path, fallback text
class WorldBadTrial(World):
    def upload(self, block):
        if self.running() == "bridge" and block == zi.TRIAL_QUERY:
            return b"Z2PB" + bytes([4, 0, 3, 0, 0, 1, 1]) + bytes(5)
        return super().upload(block)
run("bridge written but trial counter inactive -> failure reported", WorldBadTrial(), ["install"], ["I UNDERSTAND", "JA"], 1,
    lambda w, d: w.slot == BRIDGE and "FAILED" in open(os.path.join(d, zi.BRIDGE_LOG), encoding="utf-8").read())

# 15. another program is downloading (state 5) -> refused, nothing sent (no CLRSTATUS)
w = World(busy=True)
run("another program writing (state 5) -> refused, no CLRSTATUS", w, ["install"], ["I UNDERSTAND", "JA"], 1,
    lambda w, d: w.writes == 0 and w.clr_count == 0)

# 16. incomplete slot on a factory unit (power loss) -> backup, junk confirmation, bridge written
junk = NI42[:40000]
w = World(slot=junk, junk=True)
run("incomplete slot: without junk word -> cancelled", w, ["install"], ["I UNDERSTAND", "JA", "JA"], 1,
    lambda w, d: w.writes == 0 and [f for f in os.listdir(d) if f.endswith(".z2backup")])
w = World(slot=junk, junk=True)
run("incomplete slot: with junk word -> bridge written, slot backed up", w, ["install"], ["I UNDERSTAND", "TESTEN", "JA"], 0,
    lambda w, d: w.slot == BRIDGE and len([f for f in os.listdir(d) if f.endswith(".z2backup")]) == 1)

# 17. the device changed between check and install (GUI case): expected kind differs -> nothing written
w = World()
inst = zi.Installer(w, tempfile.mkdtemp(), lambda p: "I UNDERSTAND" if "UNDERSTAND" in p else "JA")
res.append(inst.install(expect_kind="source") is False and w.writes == 0)
print("=== device changed since the check -> refused:", res[-1], "\n")

# 18. English run of the whole first step
w = World()
d = tempfile.mkdtemp(); it = iter(["I UNDERSTAND", "YES"])
rc = zi.main(["install", "--lang", "en", "--backup-dir", d], backend=w, ask=lambda p: next(it, "no"))
res.append(rc == 0 and w.slot == BRIDGE); print("=== English run: bridge written:", res[-1], "\n")

# 19. GUI answers by key only (z2_gui.make_gui_ask), never by text; unknown key -> cancel
import z2_gui
class H: pass
h = H(); h.gui_answers = {"disclaimer": True, "confirm": True, "tester": False, "junk": True, "refresh": False}
ask = z2_gui.make_gui_ask(zi, h)
zi.LANG = 0
ok = (ask("x", "disclaimer") == zi.DISCLAIMER_WORD and ask("x", "confirm") == "JA" and ask("x", "tester") == "-"
      and ask("x", "junk") == zi.t("tester_word") and ask("x", "refresh") == "-" and ask("x", None) == "-"
      and ask(zi.t("bridge_untested", 51, zi.BRIDGE_LOG, zi.t("tester_word")), "confirm") == "JA"
      and getattr(ask, "keyed", False))
h.gui_answers = {}
ok = ok and all(ask("x", k) == "-" for k in ("disclaimer", "confirm", "tester", "junk", "refresh"))
res.append(ok); print("=== GUI ask routing by key:", ok, "\n")
# and the GUI ask drives a real install: tester word only if the user agreed in the dialog
w = World(0x0033); h.gui_answers = {"disclaimer": True, "confirm": True, "tester": False}
inst = zi.Installer(w, tempfile.mkdtemp(), z2_gui.make_gui_ask(zi, h))
res.append(inst.install(expect_kind="factory_empty") is False and w.writes == 0)
w = World(0x0033); h.gui_answers = {"disclaimer": True, "confirm": True, "tester": True}
inst = zi.Installer(w, tempfile.mkdtemp(), z2_gui.make_gui_ask(zi, h))
res.append(inst.install(expect_kind="factory_empty") is True and w.slot == BRIDGE and inst.bridge_result["state"] == 1)
print("=== GUI-driven install (51): refused without / done with the tester OK:", res[-2], res[-1], "\n")

# 20. English texts exist for every new key
missing = [k for k, v in zi.T.items() if not (isinstance(v, tuple) and len(v) == 2)]
res.append(not missing); print("=== all texts DE+EN:", not missing, missing)

print("\nALL PASS (%d)" % len(res) if all(res) else "FAILURES: %s" % res)
sys.exit(0 if all(res) else 1)
