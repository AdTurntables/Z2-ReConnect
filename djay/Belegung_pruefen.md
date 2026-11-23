# Z2-Belegung in djay (iPad, 4 Decks, djay mischt)

Gemessen am 21.11.2026 Element für Element mit dem HID-Monitor (`tools/z2_live.py`).
Alle Nummern stimmen mit der Firmware-Tabelle überein. MIDI-Kanal 1, wenn nicht anders angegeben.
**FW** = braucht das nächste Firmware-Update (nur mit deinem Ja).

## Mixer
| Bedienelement | sendet | djay-Funktion | mit SHIFT |
|---|---|---|---|
| Gain A / B | CC 28 / 105 | Deck 1 / 2: Gain | |
| Hi A / B | CC 29 / 106 | Deck 1 / 2: High EQ | |
| Mid A / B | CC 30 / 107 | Deck 1 / 2: Mid EQ | |
| Low A / B | CC 31 / 108 | Deck 1 / 2: Low EQ | |
| Filter A / B | CC 102 / 109 | Deck 1 / 2: Filter | |
| Linefader A / B | CC 112 / 113 | Deck 1 / 2: Lautstärke | |
| Deck C Vol / Deck D Vol | CC 110 / 111 | Deck 3 / 4: Lautstärke | |
| Crossfader | CC 114 | Crossfader | |
| XF-Kurve | CC 115 | Crossfader-Kurve | |
| XF-Reverse | Note 83 | Hamster-Schalter umschalten (LED: FW) | |
| CUE A / B | Note 46 / 47 | Deck 1 / 2: Vorhören | Deck 3 / 4: Vorhören |
| Kopfhörer | CC 22 | Monitor-Lautstärke | |
| Cue Mix | CC 23 | Monitor Cue/Mix | |
| Master | CC 24 | Main Volume | |
| Booth | CC 25 | Booth Volume | |
| Mic/Aux Vol | CC 20 | Mikrofon: Lautstärke | |
| Mic/Aux Tone | CC 21 | Mikrofon: Echo-Dauer | |
| MIC | Note 52 | Mikrofon an/aus | |
| TRAKTOR A / B | Note 36 / 37 | nicht belegt (Hardware-Eingangswahl) | |

## Bibliothek und Allgemein
| Bedienelement | sendet | djay-Funktion | mit SHIFT |
|---|---|---|---|
| SHIFT | Note 68 | Modifier | |
| BROWSE drehen | CC 16 (rel.) | Titelliste blättern (ohne Richtungsumkehr) | Quellenliste blättern |
| BROWSE drücken | Note 43 | Quellen ↔ Titel wechseln | zurück |
| LOAD A / B | Note 44 / 45 | Titel in Deck 1 / 2 laden | in Deck 3 / 4 laden |
| SNAP | Note 38 | Bibliothek ein/aus | |
| SETTINGS | Note 39 | Ansicht wechseln | |
| QUANT | Note 40 | Quantize an/aus | |

## Deck-Steuerung
| Bedienelement | sendet | djay-Funktion | mit SHIFT |
|---|---|---|---|
| REL/INTL A / B | Note 48 / 49 | Deck 1 / 2: DVS an/aus (Steuermodus) | |
| SYNC A / B | Note 50 / 51 | Deck 1 / 2: Sync | Sync-Master |
| FLUX A / B | Note 66 / 75 | Deck 1 / 2: Slip-Modus | |
| LOOP A / B drehen | CC 17 / 18 (rel.) | Deck 1 / 2: Loop-Länge | Loop verschieben |
| LOOP A / B drücken | Note 58 / 81 | Deck 1 / 2: Auto-Loop an/aus | Reloop |
| Loop-Anzeige (7-Segment) | – | Loop-Größe anzeigen (FW) | |

## Effekte
| Bedienelement | sendet | djay-Funktion | mit SHIFT |
|---|---|---|---|
| A-FX1 / A-FX2 | Note 54 / 55 | Deck 1: FX 1 / FX 2 an/aus | |
| B-FX1 / B-FX2 | Note 77 / 78 | Deck 2: FX 1 / FX 2 an/aus | |
| FX Dry/Wet links / rechts | CC 26 / 103 | Deck 1 / 2: FX 1 Wet/Dry | |
| FX Parameter links / rechts | CC 27 / 104 | Deck 1 / 2: FX 1 Parameter | |
| FX1 ON / FX2 ON | Note 53 / 76 | Deck 1 / 2: Echo Out | |
| später (FW) | | FX 1 → 2 → 3 umschalten, Regler folgen | |

## Pads und Ebenen
| Bedienelement | sendet | Funktion |
|---|---|---|
| DECK A / DECK B | Note 61 / 69 | Ebenen-Taste 1 (schaltet die Firmware) |
| DECK C / DECK D | Note 60 / 70 | Ebenen-Taste 2 (schaltet die Firmware) |
| Pads links | Note 62–65 | |
| Pads rechts | Note 71–74 | |

| Ebene | DECK A/B | DECK C/D | Pads 1–4 | mit SHIFT |
|---|---|---|---|---|
| 1 | aus | aus | Cue-Punkte 1–4 (Kanal 1) | Cue löschen |
| 2 | an | aus | Cue-Punkte 5–8 (Kanal 4) | Cue löschen |
| 3 | aus | an | Neural Mix: Vocals, Melodie, Bass, Drums (Kanal 5) | |
| 4 | an | an | frei (Kanal 6) | |

Die Ebenen schaltet die Firmware ab Stand 4 (`z2midi_stage4_dfu.bin`, öffentlich Z² Re:Connect 0.9.0 Beta 1). Pad-Farbe je Ebene: 1 blau, 2 lila, 3 gelb, 4 weiß. Mit Firmware 3b gibt es nur Ebene 1.
