# Z2 iOS-Firmware (Traktor Kontrol Z2, Basis NI-Firmware 42)

Ziel: Der Z2 läuft am iPad/iPhone ohne Treiber, mit Audio **und** MIDI.

## Stand 20.11.2026
| Test | Abbild | Ergebnis |
|---|---|---|
| 1 – USB-MIDI-Schnittstelle | `z2midi_stage1_dfu.bin` | iPad erkennt MIDI-Gerät, Audio geht ✔ |
| 2 – Bedienelemente → MIDI | `z2midi_stage2_dfu.bin` | MIDI kommt am iPad an ✔ |
| 3 – MIDI → LEDs | `z2midi_stage3_dfu.bin` (sha256 31645682…) | LEDs reagieren am iPad auf MIDI-Noten ✔ (20.11.2026). LED-Zuordnung am Gerät gemessen und richtig. Aber: Der Z2 fällt mit diesem Abbild gelegentlich vom USB-Bus |
| 3b – USB-Abbrüche behoben | `z2midi_stage3b_dfu.bin` (sha256 85665b97…) | geflasht 20.11.2026. 4-Minuten-Dauertest am PC ohne Abbruch ✔. iPad-Test steht aus |

| 4 – Pad-Ebenen | `z2midi_stage4_dfu.bin` (sha256 aa18f62c…) | geflasht 21.11.2026, am iPad mit djay getestet ✔. **Öffentlicher Name: Z2-Re:Connect 0.9.0 Beta 1** (erster Testlauf für andere Nutzer) |

| 5 – Neuverbinden + Cue-Farben | `z2midi_stage5_dfu.bin` (sha256 8b9cb47a…) | gebaut 23.11.2026, Host- und XS1-Simulatortests ✔, **noch nicht geflasht**. (1) Nach dem Ab- und Anstecken des USB-Kabels (Netzteil bleibt dran) wird die LED-Hoheit (0xF1) neu angefordert: bei der nächsten LED-Änderung, wenn das letzte 0xF1 über 1 s zurückliegt, dann gehen auch beide LED-Berichte komplett raus. (2) Pad-Velocity 1–16 = Palettenfarbe, 17–32 = gedimmt (Cue-Farben aus djay) |
| 5b – + Pegelanzeigen A/B | `z2midi_stage5b_dfu.bin` (sha256 1910b4a0…) | gebaut 23.11.2026, Tests ✔, noch nicht geflasht. Kanal 3, CC 65–68 = Pegelanzeige A–D als Balken (Wert = Anzahl LEDs 0–7); djay-Mapping v8 schickt `turntable1/2.monoMeter`. Baustein belegt den ECM-Puffer jetzt vollständig (4060/4060 Bytes); Ebenenfarben dafür mit Stufe 2 (Helligkeit gerade gerundet). Stand 5 (Neuverbinden) am iPad bestätigt ✔ |

Audio, der eingebaute Mixer und HID für Traktor am Computer bleiben unverändert.

## MIDI-Belegung (MIDI-Kanal 1)
**Vom Z2 zur App**
- **48 Tasten** → Note On (Velocity 127) / Note Off, Noten 36–83. Taste i = Bit (i % 8) von Byte 3 + i/8 des Panel-Berichts.
  - 36 TRAKTOR A · 37 TRAKTOR B · 38 SNAP · 39 SETTINGS · 40 QUANT · 43 BROWSE drücken
  - 44 LOAD A · 45 LOAD B · 46 CUE A · 47 CUE B · 48 REL/INTL A · 49 REL/INTL B · 50 SYNC A · 51 SYNC B
  - 52 MIC · 53 FX1 ON · 54 A-FX1 · 55 A-FX2 · 58 LOOP A drücken
  - 60 DECK C · 61 DECK A · 62–65 Pads A1–A4 · 66 FLUX A
  - 68 SHIFT · 69 DECK B · 70 DECK D · 71–74 Pads B1–B4 · 75 FLUX B
  - 76 FX2 ON · 77 B-FX1 · 78 B-FX2 · 81 LOOP B drücken · 83 Crossfader-Reverse-Schalter
  - Die übrigen Noten (41, 42, 56, 57, 59, 67, 79, 80, 82) liegen auf Bits, deren Bedeutung noch unbekannt ist.
- **26 Regler/Fader** → CC (0–127, mit Hysterese):
  - 20 Mic/Aux Vol · 21 Mic/Aux Tone · 22 Kopfhörer · 23 Cue Mix · 24 Master · 25 Booth bzw. XF-Kurve
  - 26 FX1 Dry/Wet · 27 FX1 FX
  - 28 Gain A · 29 Hi A · 30 Mid A · 31 Low A · 102 Filter A
  - 103 FX2 Dry/Wet · 104 FX2 FX
  - 105 Gain B · 106 Hi B · 107 Mid B · 108 Low B · 109 Filter B
  - 110 Deck C Vol · 111 Deck D Vol · 112 Fader A · 113 Fader B · 114 Crossfader · 115 XF-Kurve bzw. Booth
- **3 Encoder** → relative CC: 16 Browse · 17 Loop A · 18 Loop B. Wert 1…7 = rechts, 127…121 = links.
- Beim Verbinden werden einmal alle Regler-Positionen gesendet.
- **Pad-Ebenen (ab Stand 4):** DECK A / DECK C (rechts DECK B / DECK D) schalten je Seite um, die Firmware lässt die DECK-LEDs selbst leuchten.
  Ebene 1 = beide aus, 2 = A/B an, 3 = C/D an, 4 = beide an. Die Pads senden ihre Noten (62–65, 71–74) auf **Kanal 1, 4, 5, 6** für Ebene 1–4.
  Note Off geht auf den Kanal, auf dem die Taste gedrückt wurde. Die DECK-Tasten senden ihre Noten weiter auf Kanal 1.

**Von der App zum Z2 (LEDs)**
- Note mit gleicher Nummer wie die Taste (Kanal 1) → LED dieser Taste. Die Velocity 0–127 bestimmt die Helligkeit, Note Off = aus.
- **Pads (ab Stand 4):** Pad-Note auf Kanal 1, 4, 5 oder 6 → Helligkeit des Pads in Ebene 1–4. Die Firmware merkt sich jede Ebene und zeigt die aktive in ihrer Farbe: 1 blau, 2 lila, 3 gelb, 4 weiß. LED-Noten für DECK A–D von der App werden ignoriert.
- **Cue-Farben (ab Stand 5):** Velocity 1–16 = Farbe voll, 17–32 = dieselbe Farbe gedimmt, in jeder Ebene: 1 rot, 2 rotorange, 3 orange, 4 bernstein, 5 gelb, 6 limette, 7 grün, 8 frühlingsgrün, 9 cyan, 10 himmelblau, 11 blau, 12 indigo, 13 violett, 14 magenta, 15 pink, 16 weiß. Andere Werte wie bisher (Helligkeit in der Ebenenfarbe). Das djay-Mapping ab Version 8 schickt diese Werte über `userInfo` (`padColorsActive`/`padColorsDimmed`).
- Am Gerät gemessen (20.11.2026): Jede Tasten-Note trifft ihre eigene LED. Rel/Intl A/B haben zwei Farben (0x12/0x13 bzw. 0x1A/0x1B); die Note schaltet die grüne (0x13/0x1B). Deck C/D haben eine zweite LED (0x0B/0x0C).
- Weitere LEDs ohne Taste: 0x80/0x01 kleines Dreieck oben, 0x80/0x02 Schallplattensymbol (orange), 0x81/0x01, 0x09, 0x11, 0x19 = Buchstaben A, B, C, D der Pegelanzeige, 0x81/0x21 MST, 0x81/0x27 USB-Symbol.
- **Kanal 2, CC n (1–94)** → LED n des Berichts 0x80, roh. Dazu gehören die Pad-RGB-Kanäle 0x1D–0x34 und die 7-Segment-Anzeigen 0x35–0x5E (Reihenfolge der Segmente g, c, b, a, f, e, d).
- **Kanal 3, CC 65–68 (ab Stand 5b)** → Pegelanzeige A, B, C, D als Balken: Wert 0–7 = Anzahl leuchtender LEDs (C/D zeigen bei Master-Hoheit der Hardware weiter den Master).
- **Kanal 3, CC n (1–40)** → LED n des Berichts 0x81, roh: VU-Meter A 0x02–0x08, B 0x0A–0x10, C/Master-L 0x12–0x18, D/Master-R 0x1A–0x20, MST 0x21, MIC 0x22, Cue A/B 0x23/0x24, TRAKTOR A/B 0x25/0x26, USB 0x27, XF-Reverse 0x28.
- **LED-Hoheit:** Mit dem ersten LED-Befehl übernimmt die App die LED-Gruppen Deck A, Deck B, 7-Segment, USB-Symbol und Browse (Maske 0xB3). Master- und Mic-VU bleiben bei der Hardware.
  Ändern lässt sich die Maske über **Kanal 16**: CC 126 setzt die Bits 0–6 (01 Deck A, 02 Deck B, 04 Master-VU, 08 Mic, 10 7-Segment, 20 USB, 40 unbekannt), CC 127 ≥ 64 setzt Bit 7 (Browse).
  Die Audio-Bits von 0xF1 bleiben 0, wie ohne NI-Software.

## Bauen und Flashen
- Kern-Code: `z2midi/` (C99). Host-Tests: `gcc -std=c99 -Wall -Wextra -Werror z2midi.c test_z2midi.c`.
- Baustein bauen + XS1-Simulator-Test: `stage2/build_blob.sh` (WSL). Ab Stand 4 ohne C-Startcode (`-nostartfiles`, Einstieg `_start` in hooks.S), sonst passt er nicht in den ECM-Puffer (Stand 5b: 4060 von 4060 Bytes belegt – für Neues muss erst Platz geschaffen werden). Stand-3b-Baustein: `stage2/blob_stage3b.elf`.
- Firmware-Modul: `stage2/` (`midi_glue.c`, `gen_hooks.py` → `hooks.S`). XS1-Simulator-Test: `stage2/sim_test.c`.
- Patch, Abbild bauen und Flashen: Die Entwickler-Werkzeuge dafür (`tools/`) sind bewusst **nicht** Teil dieses Repos,
  weil sie ohne die Sicherheitsprüfungen des Installers auf den Z2 schreiben.
- **Installieren und zurück zur Original-Firmware 42:** nur mit dem Installer (`installer/`), der immer ein Backup anlegt.

Details zu Adressen, Analyse und Sicherheit stehen in `PATCH_PLAN.md`.
