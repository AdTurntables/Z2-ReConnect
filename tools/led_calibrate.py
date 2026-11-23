"""Measure which LED belongs to which button on the user's Z2 (via the NI HID interface on the PC).

For every candidate LED index the tool lights only that LED (HID output report 0x80 or 0x81) and
waits up to WAIT seconds for a button press (HID input report 0x01). The user presses the button
that is lit, or nothing if the lit LED is not on a button. Results go to build/led_calibration.json.

LED ownership is taken with feature report 0xF1 = (0xFF, 0x00) during the run and given back with
(0x00, 0x00) afterwards (the value the device reports without NI software). Byte 2 = audio routing
flags stays 0 as on the device.

  python led_calibrate.py [wait_seconds]
"""
import ctypes, ctypes.wintypes as wt, json, sys, time, threading
import hid_probe as hp

WAIT = float(sys.argv[1]) if len(sys.argv) > 1 else 4.0
k32 = ctypes.WinDLL("kernel32", use_last_error=True)
hid = ctypes.WinDLL("hid")
k32.WriteFile.argtypes = [wt.HANDLE, ctypes.c_void_p, wt.DWORD, ctypes.POINTER(wt.DWORD), ctypes.c_void_p]
k32.ReadFile.argtypes = [wt.HANDLE, ctypes.c_void_p, wt.DWORD, ctypes.POINTER(wt.DWORD), ctypes.c_void_p]

# candidates: report 0x80 indices 1..0x34 (buttons, labels, pads: R of each RGB triple only),
# report 0x81 0x21..0x28 (MST label, MIC, CUE A/B, TRAKTOR A/B, USB, XF reverse) and the VU labels
CANDS = [(0x80, i) for i in range(1, 0x1D)] + [(0x80, i) for i in range(0x1D, 0x35, 3)] + \
        [(0x81, i) for i in (0x01, 0x09, 0x11, 0x19)] + [(0x81, i) for i in range(0x21, 0x29)]

path = hp.find()[0]
hw = hp.open_dev(path, 0x40000000)
hr = hp.open_dev(path, 0x80000000)
presses = []          # (time, byte, mask)
stop = False


def reader():
    last = None; buf = ctypes.create_string_buffer(53); n = wt.DWORD()
    while not stop:
        if not k32.ReadFile(hr, buf, 53, ctypes.byref(n), None): break
        r = buf.raw[:n.value]
        if not r or r[0] != 0x01: continue
        if last is not None:
            for b in range(3, 9):
                new = r[b] & ~last[b]
                for bit in range(8):
                    if new & (1 << bit): presses.append((time.time(), b, 1 << bit))
        last = r


def feature(b1, b2):
    buf = ctypes.create_string_buffer(bytes([0xF1, b1, b2]), 3)
    return hid.HidD_SetFeature(hw, buf, 3)


def out(rid, idx, val=127):
    size = 95 if rid == 0x80 else 41
    b = bytearray(size); b[0] = rid
    if idx: b[idx] = val
    n = wt.DWORD()
    return k32.WriteFile(hw, bytes(b), size, ctypes.byref(n), None)


threading.Thread(target=reader, daemon=True).start()
print("Ownership F1=FF 00:", feature(0xFF, 0x00), flush=True)
out(0x80, 0); out(0x81, 0)
result = []
try:
    for rid, idx in CANDS:
        out(0x80, 0); out(0x81, 0)
        out(rid, idx)
        t0 = time.time(); got = None
        while time.time() - t0 < WAIT:
            hit = [p for p in presses if p[0] >= t0]
            if hit: got = hit[0]; break
            time.sleep(0.02)
        entry = {"report": hex(rid), "led": hex(idx), "button": None}
        if got:
            entry["button"] = {"byte": got[1], "mask": hex(got[2]), "note": 36 + (got[1] - 3) * 8 + got[2].bit_length() - 1}
            time.sleep(0.6)                      # let the user release before the next LED
        result.append(entry)
        print("LED %s/%s -> %s" % (hex(rid), hex(idx), entry["button"]), flush=True)
finally:
    out(0x80, 0); out(0x81, 0)
    print("Ownership back to F1=00 00:", feature(0x00, 0x00), flush=True)
    stop = True
    json.dump(result, open("build/led_calibration.json", "w"), indent=1)
    print("saved build/led_calibration.json (%d LEDs tested)" % len(result))
