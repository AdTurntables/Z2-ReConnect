"""Liest den Z2 per HID (nur lesen) und schreibt die MIDI-Nachrichten, die die iOS-Firmware daraus macht,
nach z2_live_log.txt. Uebersetzung wie firmware/z2midi/z2midi.c (Noten 36+i, CC-Tabelle, Encoder relativ)."""
import ctypes, ctypes.wintypes as wt, time, os, sys
sys.path.insert(0, os.path.dirname(__file__))
import hid_probe as hp

BTN = ["TRAKTOR A", "TRAKTOR B", "SNAP", "SETTINGS", "QUANT", "?3.20", "?3.40", "BROWSE druecken",
       "LOAD A", "LOAD B", "CUE A", "CUE B", "REL/INTL A", "REL/INTL B", "SYNC A", "SYNC B",
       "MIC", "FX1 ON", "A-FX1", "A-FX2", "?5.10", "?5.20", "LOOP A druecken", "?5.80",
       "DECK C", "DECK A", "PAD A1", "PAD A2", "PAD A3", "PAD A4", "FLUX A", "?6.80",
       "SHIFT", "DECK B", "DECK D", "PAD B1", "PAD B2", "PAD B3", "PAD B4", "FLUX B",
       "FX2 ON", "B-FX1", "B-FX2", "?8.08", "?8.10", "LOOP B druecken", "?8.40", "XF-REVERSE"]
ANA = [(20, "MIC/AUX VOL"), (21, "MIC/AUX TONE"), (22, "KOPFHOERER"), (23, "CUE MIX"), (24, "MASTER"), (25, "BOOTH/XF-KURVE"),
       (26, "FX1 DRY/WET"), (27, "FX1 FX"), (28, "GAIN A"), (29, "HI A"), (30, "MID A"), (31, "LOW A"), (102, "FILTER A"),
       (103, "FX2 DRY/WET"), (104, "FX2 FX"), (105, "GAIN B"), (106, "HI B"), (107, "MID B"), (108, "LOW B"), (109, "FILTER B"),
       (110, "DECK C VOL"), (111, "DECK D VOL"), (112, "FADER A"), (113, "FADER B"), (114, "CROSSFADER"), (115, "XF-KURVE/BOOTH")]
ENC = [(1, 0, 16, "BROWSE drehen"), (1, 4, 17, "LOOP A drehen"), (2, 0, 18, "LOOP B drehen")]

log = open(os.path.join(os.path.dirname(__file__), "z2_live_log.txt"), "a", buffering=1, encoding="utf-8")
def out(s): log.write(time.strftime("%H:%M:%S ") + s + "\n")

p = hp.find()[0]; n = hp.caps(p)["inLen"]
hh = hp.open_dev(p, 0x80000000); buf = ctypes.create_string_buffer(n); got = wt.DWORD()
btn = None; ana_cc = {}; last_ana_log = {}
out("--- Monitor gestartet ---")
while True:
    if not hp.k32.ReadFile(hh, buf, n, ctypes.byref(got), None): out("Lesefehler"); break
    r = buf.raw[:got.value]
    if r[0] == 1:
        if btn is not None:
            for b, sh, cc, name in ENC:
                d = (((r[b] >> sh) & 15) - ((btn[b] >> sh) & 15)) & 15
                if d >= 8: d -= 16
                if d: out("CC %d Wert %d  (%s %s)" % (cc, d if d > 0 else 128 + d, name, "rechts" if d > 0 else "links"))
            for i in range(48):
                by, m = 3 + i // 8, 1 << (i % 8)
                now, was = r[by] & m, btn[by] & m
                if now != was: out("Note %d %s  (%s)" % (36 + i, "On" if now else "Off", BTN[i]))
        btn = r
    elif r[0] == 2:
        for i, (cc, name) in enumerate(ANA):
            v = min(4095, r[1 + 2 * i] | (r[2 + 2 * i] << 8)) >> 5
            if i in ana_cc and abs(v - ana_cc[i]) >= 2 or (i in ana_cc and v in (0, 127) and v != ana_cc[i]):
                ana_cc[i] = v
                t = time.time()
                if t - last_ana_log.get(i, 0) > 0.25 or v in (0, 127):
                    out("CC %d Wert %d  (%s)" % (cc, v, name)); last_ana_log[i] = t
            elif i not in ana_cc: ana_cc[i] = v
