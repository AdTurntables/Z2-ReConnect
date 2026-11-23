"""Step-by-step LED calibration driven from the chat.

  python led_step.py log            # background: logs every button press to build/presses.log
  python led_step.py start          # takes LED ownership (F1 = FF 00), lights candidate 1
  python led_step.py next [note]    # stores the presses seen for the lit LED, lights the next one
  python led_step.py back           # lights the previous candidate again (redo)
  python led_step.py done           # all LEDs off, ownership back (F1 = 00 00), writes the result

Each candidate is shown by itself. The user presses the lit button and sends Enter in the chat;
`next` then records every button pressed since that LED was lit. Results: build/led_calibration.json.
"""
import ctypes, ctypes.wintypes as wt, json, os, sys, time
import hid_probe as hp

k32 = ctypes.WinDLL("kernel32", use_last_error=True)
hid = ctypes.WinDLL("hid")
k32.WriteFile.argtypes = [wt.HANDLE, ctypes.c_void_p, wt.DWORD, ctypes.POINTER(wt.DWORD), ctypes.c_void_p]
k32.ReadFile.argtypes = [wt.HANDLE, ctypes.c_void_p, wt.DWORD, ctypes.POINTER(wt.DWORD), ctypes.c_void_p]

CANDS = [(0x80, i) for i in range(1, 0x1D)] + [(0x80, i) for i in range(0x1D, 0x35, 3)] + \
        [(0x81, i) for i in (0x01, 0x09, 0x11, 0x19)] + [(0x81, i) for i in range(0x21, 0x29)]
LOG = "build/presses.log"
STATE = "build/led_step_state.json"
OUT = "build/led_calibration.json"


def dev(access):
    return hp.open_dev(hp.find()[0], access)


def feature(h, b1, b2):
    buf = ctypes.create_string_buffer(bytes([0xF1, b1, b2]), 3)
    return bool(hid.HidD_SetFeature(h, buf, 3))


def out(h, rid, idx=0, val=127):
    size = 95 if rid == 0x80 else 41
    b = bytearray(size); b[0] = rid
    if idx: b[idx] = val
    n = wt.DWORD()
    return bool(k32.WriteFile(h, bytes(b), size, ctypes.byref(n), None))


def light(h, k):
    out(h, 0x80); out(h, 0x81)
    rid, idx = CANDS[k]
    out(h, rid, idx)


def load():
    if os.path.exists(STATE): return json.load(open(STATE))
    return {"k": 0, "t": 0.0, "result": {}}


def save(s):
    json.dump(s, open(STATE, "w"), indent=1)
    json.dump([s["result"].get(str(k), {"report": hex(r), "led": hex(i), "buttons": None})
               for k, (r, i) in enumerate(CANDS)], open(OUT, "w"), indent=1)


def presses_since(t):
    res = []
    if not os.path.exists(LOG): return res
    for line in open(LOG):
        ts, byte, mask = line.split()
        if float(ts) >= t:
            byte = int(byte); mask = int(mask, 16)
            note = 36 + (byte - 3) * 8 + mask.bit_length() - 1
            if note not in res: res.append(note)
    return res


def show(s):
    rid, idx = CANDS[s["k"]]
    print("Schritt %d/%d: LED %s/%s leuchtet" % (s["k"] + 1, len(CANDS), hex(rid), hex(idx)), flush=True)


cmd = sys.argv[1] if len(sys.argv) > 1 else ""
if cmd == "log":
    hr = dev(0x80000000)
    buf = ctypes.create_string_buffer(53); n = wt.DWORD(); last = None
    with open(LOG, "a") as f:
        while k32.ReadFile(hr, buf, 53, ctypes.byref(n), None):
            r = buf.raw[:n.value]
            if not r or r[0] != 0x01: continue
            if last is not None:
                for b in range(3, 9):
                    new = r[b] & ~last[b]
                    for bit in range(8):
                        if new & (1 << bit):
                            f.write("%.3f %d %02x\n" % (time.time(), b, 1 << bit)); f.flush()
            last = r
elif cmd == "start":
    h = dev(0x40000000)
    print("LED-Hoheit F1=FF 00:", feature(h, 0xFF, 0x00))
    s = load(); s["k"] = 0; s["t"] = time.time(); s["result"] = {}
    light(h, 0); save(s); show(s)
elif cmd in ("next", "back"):
    h = dev(0x40000000); s = load()
    feature(h, 0xFF, 0x00)               # again, in case the Z2 restarted in between
    if cmd == "next":
        rid, idx = CANDS[s["k"]]
        notes = presses_since(s["t"])
        entry = {"report": hex(rid), "led": hex(idx), "buttons": notes}
        if len(sys.argv) > 2: entry["comment"] = " ".join(sys.argv[2:])
        s["result"][str(s["k"])] = entry
        print("gespeichert: LED %s/%s -> Noten %s" % (hex(rid), hex(idx), notes))
        if s["k"] + 1 >= len(CANDS):
            out(h, 0x80); out(h, 0x81); save(s); print("FERTIG - alle LEDs getestet"); sys.exit()
        s["k"] += 1
    elif len(sys.argv) < 3 or sys.argv[2] != "again":
        s["k"] = max(0, s["k"] - 1)
    s["t"] = time.time(); light(h, s["k"]); save(s); show(s)
elif cmd == "done":
    h = dev(0x40000000)
    out(h, 0x80); out(h, 0x81)
    print("LED-Hoheit zurück F1=00 00:", feature(h, 0x00, 0x00))
    s = load(); save(s); print("gespeichert:", OUT, len(s["result"]), "LEDs")
else:
    print(__doc__)
