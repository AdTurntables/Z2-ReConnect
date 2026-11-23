"""USB stability test on the PC: running light over all LEDs (HID OUT 0x80/0x81 as fast as the
device takes them) while counting HID IN reports. Stops and reports if the Z2 drops off the bus.

  python usb_stress.py [seconds]
"""
import ctypes, ctypes.wintypes as wt, sys, time, threading
import hid_probe as hp
from led_step import k32, feature, out, dev

SECS = float(sys.argv[1]) if len(sys.argv) > 1 else 240
hw = dev(0x40000000); hr = dev(0x80000000)
n_in = [0, 0]; alive = [True]


def reader():
    buf = ctypes.create_string_buffer(53); n = wt.DWORD()
    while k32.ReadFile(hr, buf, 53, ctypes.byref(n), None):
        if n.value: n_in[0 if buf.raw[0] == 1 else 1] += 1
    alive[0] = False


threading.Thread(target=reader, daemon=True).start()
print("F1=FF 00:", feature(hw, 0xFF, 0), flush=True)
t0 = time.time(); n_out = 0; k = 0; ok = True; last = t0
while time.time() - t0 < SECS:
    k += 1
    if not (out(hw, 0x80, 1 + k % 0x5E, 40) and out(hw, 0x81, 1 + k % 0x28, 40)) or not alive[0]:
        ok = False; break
    n_out += 2
    if time.time() - last >= 30:
        last = time.time()
        print("%4ds  out %d  in: buttons %d analog %d" % (last - t0, n_out, n_in[0], n_in[1]), flush=True)
if ok:
    out(hw, 0x80); out(hw, 0x81); feature(hw, 0, 0)
print("%s after %.0fs: out %d, in buttons %d, analog %d" %
      ("PASSED" if ok else "DROPPED OFF THE BUS", time.time() - t0, n_out, n_in[0], n_in[1]), flush=True)
