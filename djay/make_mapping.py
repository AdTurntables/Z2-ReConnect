"""Erzeugt das djay-Mapping fuer den Z2 mit iOS-Firmware.
Belegung gemessen und abgestimmt in djay/Belegung_pruefen.md (djay mischt, 4 Decks, ohne Bedingungen).
Pad-Ebenen 1-4 brauchen Firmware Stand 4 (z2midi_stage4_dfu.bin), Cue-Farben Stand 5 (z2midi_stage5_dfu.bin).
FX-Umschaltung und Loop-Anzeige kommen spaeter.

  python make_mapping.py              -> Traktor Kontrol Z2.djayMidiMapping
  python make_mapping.py --cuepoint   -> farbtest/Traktor Kontrol Z2 (CuePoint).djayMidiMapping: gleiche Belegung,
                                         Cue-Pads aber mit den keyPaths cueOrJumpIfAlreadySetCuePointN (so heissen sie
                                         im Launchpad-Mapping mit Cue-Farben). Nur fuer den Farbtest."""
import plistlib, os, sys
CUEPOINT = "--cuepoint" in sys.argv
C = []
def note(kp, n, shift=False, led=True, out=None, midiChannel=0, **kw):
    d = dict(keyPath=kp, midiChannel=midiChannel, midiData=n, midiMessageType=1, **kw)
    if out is not None: d["output"] = out
    elif led: d["output"] = {}
    if shift: d["modifier"] = True
    C.append(d)
def cc(kp, n, shift=False, **kw):
    d = dict(keyPath=kp, midiChannel=0, midiData=n, midiMessageType=3, **kw)
    if shift: d["modifier"] = True
    C.append(d)
def led(idx, lo=0, hi=127):
    """LED idx des Berichts 0x80 roh ansteuern: MIDI-Kanal 2, CC idx (siehe firmware/README.md)."""
    return dict(midiChannel=1, midiMessageType=3, midiData=idx, midiMinValue=lo, midiMaxValue=hi)

# Allgemein und Bibliothek
note("application.modifier", 68)                                        # SHIFT
cc("musicLibrary.libraryRotary", 16, controlType="rotary")              # BROWSE drehen
cc("musicLibrary.sourceRotary", 16, True, controlType="rotary")
note("musicLibrary.toggleLibrarySource", 43, led=False)                 # BROWSE druecken
note("musicLibrary.libraryBack", 43, True, led=False)
note("musicLibrary.toggleLibraryVisible", 38)                           # SNAP
note("application.viewModeNext", 39, led=False)                         # SETTINGS
note("application.quantizeToggle", 40)                                  # QUANT

# Mixer (djay mischt)
cc("mixer.crossfade", 114)
cc("mixer.crossfadeStyle", 115)                                         # XF-Kurve
note("mixer.midiHamsterSwitchToggle", 83, led=False)                    # XF-Reverse (LED kommt mit FW)
cc("mixer.monitorLevel", 22)                                            # Kopfhoerer
cc("mixer.monitorMix", 23)                                              # Cue Mix
cc("mixer.masterLevel", 24)
cc("mixer.boothLevel", 25)
cc("microphone.level", 20)                                              # Mic/Aux Vol
cc("microphone.echoDuration", 21)                                       # Mic/Aux Tone
note("microphone.active", 52)                                           # MIC
cc("mixer.lineVolume3", 110)                                            # Deck C Vol
cc("mixer.lineVolume4", 111)                                            # Deck D Vol

for t, gain, hi, mid, low, flt, fader, cue, load, rel, sync, flux, loopb, loope, echo, fxa, fxb, dw, par, pad0 in (
        (1, 28, 29, 30, 31, 102, 112, 46, 44, 48, 50, 66, 58, 17, 53, 54, 55, 26, 27, 62),
        (2, 105, 106, 107, 108, 109, 113, 47, 45, 49, 51, 75, 81, 18, 76, 77, 78, 103, 104, 71)):
    T = "turntable%d." % t
    cc(T + "gain", gain); cc(T + "highEQ", hi); cc(T + "midEQ", mid); cc(T + "lowEQ", low)
    cc(T + "filter", flt)
    cc("mixer.lineVolume%d" % t, fader)
    note("mixer.monitorActive%d" % t, cue); note("mixer.monitorActive%d" % (t + 2), cue, True)
    note("musicLibrary.load%d" % t, load, led=False); note("musicLibrary.load%d" % (t + 2), load, True, led=False)
    note(T + "toggleControlMode", rel)                                  # REL/INTL = DVS an/aus
    note(T + "bpmSync", sync); note(T + "turntableIsSyncMaster", sync, True)
    note(T + "deckSlipToggle", flux)                                    # FLUX
    note(T + "autoLoopOnOff", loopb); note(T + "reloop", loopb, True, led=False)
    cc(T + "autoLoopDurationRotary", loope, controlType="rotary")
    cc(T + "autoLoopMoveRotary", loope, True, controlType="rotary")
    note(T + "echoTransitionEffect", echo)                              # FX1 ON / FX2 ON = Echo Out
    note(T + "fx1Enabled", fxa); note(T + "fx2Enabled", fxb)            # A-FX1/2, B-FX1/2
    cc(T + "fx1WetDryValue", dw); cc(T + "fx1ParameterValue", par)
    # Pads: die Firmware (Stand 4) schaltet die Ebenen mit DECK A/C bzw. B/D selbst und schickt die
    # Pads je Ebene auf eigenem MIDI-Kanal: Ebene 1 Kanal 1, Ebene 2 Kanal 4, Ebene 3 Kanal 5, Ebene 4 Kanal 6.
    # Die LED-Rueckmeldung kommt als gleiche Note auf gleichem Kanal zurueck (output {}); die Firmware
    # merkt sie sich je Ebene und zeigt sie in der Ebenenfarbe (1 blau, 2 lila, 3 gelb, 4 weiss).
    # Cue 1-8 = cueOrJumpIfAlreadySet1..8 ("Start CUE" ist ein eigener Punkt und wird nicht benutzt).
    for i in range(4):
        CUE = T + ("cueOrJumpIfAlreadySetCuePoint%d" if CUEPOINT else "cueOrJumpIfAlreadySet%d")
        note(CUE % (1 + i), pad0 + i)                                             # Ebene 1: Cue 1-4
        note(T + "clearCuePoint%d" % (1 + i), pad0 + i, True, led=False)
        note(CUE % (5 + i), pad0 + i, midiChannel=3)                              # Ebene 2: Cue 5-8
        note(T + "clearCuePoint%d" % (5 + i), pad0 + i, True, led=False, midiChannel=3)
        # Ebene 3: Neural Mix, Pad 1 Vocals, 2 Melodie (Harmonic), 3 Bass, 4 Drums
        note(T + "unmixerFourTrackChannel%dActive" % (4 - i), pad0 + i, midiChannel=4)
        # Ebene 4 (Kanal 6): frei

# Cue-Farben (Firmware Stand 5): djay schickt fuer einen gesetzten Cue den Wert padColorsActive[Farbe],
# sonst padColorOff. Die Firmware liest Velocity 1-16 als Palettenfarbe (voll), 17-32 als dieselbe Farbe gedimmt:
#   1 rot, 2 rotorange, 3 orange, 4 bernstein, 5 gelb, 6 limette, 7 gruen, 8 fruehlingsgruen,
#   9 cyan, 10 himmelblau, 11 blau, 12 indigo, 13 violett, 14 magenta, 15 pink, 16 weiss.
# Welche djay-Farbe an welcher Stelle steht, ist nicht dokumentiert. Die Reihenfolge folgt dem Launchpad-Mapping
# (rot, orange, blau, gelb, gruen, pink, tuerkis, lila, ...); Stellen 9-16 sind geschaetzt und werden am iPad abgeglichen.
# Jede Stelle hat einen eigenen Wert, damit sich falsche Zuordnungen beim Test eindeutig erkennen lassen.
PAL = [1, 3, 11, 5, 7, 15, 9, 13, 10, 12, 6, 8, 4, 2, 14, 16]
USER_INFO = dict(padColorOff=0, padColorWhiteActive=16, padColorWhiteDimmed=32,
                 padColorsActive=PAL, padColorsDimmed=[v + 16 for v in PAL])

# Pegelanzeigen A/B (Firmware Stand 5): djay schickt den Pegel von Deck 1/2 als CC 65/66 auf Kanal 3,
# skaliert auf 0..7 = Anzahl leuchtender LEDs. Die mittleren Anzeigen (C/D bzw. Master) bleiben bei der Hardware.
OUTPUTS = [dict(controlType="control", keyPath="turntable%d.monoMeter" % (1 + i), midiChannel=2,
                midiData=65 + i, midiMessageType=3, midiMinValue=0.0, midiMaxValue=7.0) for i in range(2)]

m = dict(USBID=(0x17CC << 16) | 0x1130, endpointName="Traktor Kontrol Z2",
         uuid="7A2C0D5E-5B1F-4E0A-9C1D-2F6B8E3A41A3" if CUEPOINT else "7A2C0D5E-5B1F-4E0A-9C1D-2F6B8E3A41A2",
         schemeVersion=1, version=8,
         audioConfiguration=dict(mixerMode=1, externalModeTurntableOutputChannels=[0, 2],
                                 inputTurntableChannelOffsets=[0, 2]),
         controls=C, outputs=OUTPUTS, userInfo=USER_INFO)
HERE = os.path.dirname(os.path.abspath(__file__))
if CUEPOINT:
    os.makedirs(os.path.join(HERE, "farbtest"), exist_ok=True)
    name = os.path.join(HERE, "farbtest", "Traktor Kontrol Z2 (CuePoint).djayMidiMapping")
else:
    name = os.path.join(HERE, "Traktor Kontrol Z2.djayMidiMapping")
plistlib.dump(m, open(name, "wb"), sort_keys=False)
print(os.path.basename(name), len(C), "Zuweisungen")
