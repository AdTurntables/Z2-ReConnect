"""MIDI-Monitor ohne Zusatzpakete (Windows winmm). Schreibt jede Nachricht des Z2 in midi_log.txt."""
import ctypes, ctypes.wintypes as W, sys, time, os
winmm = ctypes.WinDLL("winmm")
class CAPS(ctypes.Structure):
    _fields_ = [("wMid", W.WORD), ("wPid", W.WORD), ("ver", W.UINT), ("name", W.WCHAR * 32), ("sup", W.DWORD)]
n = winmm.midiInGetNumDevs()
names = []
for i in range(n):
    c = CAPS(); winmm.midiInGetDevCapsW(i, ctypes.byref(c), ctypes.sizeof(c)); names.append(c.name)
print("MIDI-Eingaenge:", names, flush=True)
log = open(os.path.join(os.path.dirname(__file__), "midi_log.txt"), "a", buffering=1, encoding="utf-8")
CB = ctypes.WINFUNCTYPE(None, W.HANDLE, W.UINT, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p)
def cb(h, msg, inst, p1, p2):
    if msg != 0x3C3: return                     # MIM_DATA
    d = p1 or 0; st, a, b = d & 0xFF, (d >> 8) & 0xFF, (d >> 16) & 0xFF
    typ = {0x80: "NoteOff", 0x90: "NoteOn", 0xB0: "CC"}.get(st & 0xF0, hex(st))
    log.write("%s %s ch%d %d %d\n" % (time.strftime("%H:%M:%S"), typ, (st & 15) + 1, a, b))
cbf = CB(cb); hs = []
for i, nm in enumerate(names):
    if "Z2" in nm or "Traktor" in nm or len(sys.argv) > 1:
        h = W.HANDLE()
        r = winmm.midiInOpen(ctypes.byref(h), i, cbf, None, 0x30000)
        print("oeffne", i, nm, "->", r, flush=True)
        if r == 0: winmm.midiInStart(h); hs.append(h)
if not hs: print("Kein Z2-MIDI-Eingang geoeffnet", flush=True); sys.exit(1)
while True: time.sleep(1)
