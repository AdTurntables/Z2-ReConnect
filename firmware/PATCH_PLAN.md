# Bauplan: Z2-Firmware 42 + USB-MIDI (Stand 20.11.2026)

Grundlage: Rücklesen vom eigenen Gerät (`tools/backup/`), Analyse mit `tools/xdis.py`
(Listings in `tools/analysis/tile0.lst`, `tile1.lst`). Adressen = Kern-1-RAM (Basis 0x10000).

## Aufbau des Abbilds (beobachtet)
| Offset | Inhalt |
|---|---|
| 0x00 | XMOS-Image-Tag 0x1a551e5, dann 2 Prüfwörter (0x5a569146, 0x0b4e0078), Größe 0x176f4, Version-/Flagwörter |
| 0x20 | Segmenttabelle: 0x80000002, Kern-0-Länge 0x363f Wörter, Offset Kern 1 = 0xd930, 2, Kern-1-Länge 0x2771 Wörter |
| 0x34 | Kern 0 (55 KB): Mixer-DSP (EQ, Filter, Crossfader, Limiter, Meter), Panel |
| 0xd930 | Kern 1 (40 KB): USB (XUD), Endpoint 0, Audio-Puffer, HID, Netzwerk-Funktion (ECM) |
Gespeichert ist das Abbild bitweise gespiegelt (jedes Byte), nicht verschlüsselt.

## Schlüsselstellen auf Kern 1
- `fn_14e10`: `par` mit 5 Threads + `XUD_Manager` (`fn_105b8` → 0x150dc).
- Endpoint-Typtabellen: OUT @0x18a68 = {CTL, ISO, BUL(EP2 HID), **BUL(EP3)**},
  IN @0x18a78 = {CTL, ISO(0x81), ISO(0x82), INT(0x83 HID), **BUL(0x84)**}.
  → EP 0x03 OUT und EP 0x84 IN (Bulk, 512 B) werden vom USB-Kern schon bedient.
- Konfigurations-Descriptor-Vorlage @0x18dd4 (389 Bytes, 7 Interfaces):
  IF0–2 Audio, IF3 DFU, IF4 HID, **IF5/IF6 CDC-ECM** (55 Bytes, „ni-mx2“).
- `fn_11f5c` (Endpoint 0): Ist Bit 1 des Modus-Arguments 0, wird die Länge um 0x37 gekürzt
  und bNumInterfaces = 5 gesetzt (0x11f6c–0x11f70, 0x120ce–0x120ec).
  Den Modus setzt `fn_10518` aus einem Startbefehl von Kern 0 (Befehl 3 → Modus 2 = ECM sichtbar).
- Thread `fn_1047c` → `fn_12cac`: HID- und ECM-Verarbeitung (packetManager.xc, q.xc).

## Patch (Strategie A: NI-Firmware behalten, MIDI ergänzen)
1. **Descriptor**: Die 55 Bytes ECM durch USB-MIDI 1.0 ersetzen
   (AC-Interface 5 + MIDIStreaming-Interface 6, Embedded- und External-Jacks, Bulk EP 0x03/0x84, 512 B).
   USB-MIDI braucht ~92 Bytes. Dafür wird die Descriptor-Vorlage in freies RAM verlegt,
   und die 3 Verweise `ldaw rX, dp[0xfd]` (0x11d10, 0x120da, + Sende-Pfad) werden umgebogen.
   HID bleibt erhalten, Traktor am PC funktioniert also weiter.
2. **Sichtbar machen**: Den Sprung bei 0x11f70 so ändern, dass die MIDI-Interfaces immer gemeldet werden.
   Längenkorrektur (0x37) und bNumInterfaces an die neue Größe anpassen.
3. **Datenpfad**: Die ECM-Behandlung in `fn_12cac` durch `z2midi` ersetzen
   (`firmware/z2midi`, getestet). Der Panel-Zustand kommt aus denselben Puffern, aus denen
   die HID-Reports 0x01/0x02 entstehen. MIDI-Eingang schreibt in die LED-Puffer 0x80/0x81.
   Übersetzt wird mit LLVM 21 (`llc`/`llvm-mc -triple=xcore`, in WSL vorhanden).
4. **Abbild bauen**: Kern 1 neu zusammensetzen, Längen in der Segmenttabelle anpassen, Prüfwörter
   berechnen, bitweise spiegeln.

## Bau-Pipeline (gelöst 20.11.2026)
`firmware/build/build_image.sh tile0.bin tile1.bin out.bin 2` (WSL, xTIMEcomposer 14.4.1 unter
`~/xmos`). Die Kern-Abbilder werden mit `tools/mkelf.py` zu ELF verpackt, mit `xobjdump --replace` in
ein Programm für `z2.xn` (2 Knoten, Routing-IDs 0x8000/0x0000) gesetzt, und
`xflash --factory-version 12 --no-compression --upgrade 2` baut daraus das Abbild.
**Mit den unveränderten NI-Kernen ist das Ergebnis byte-identisch zur zurückgelesenen Firmware 42.**
Die Prüfwörter muss also niemand mehr selbst berechnen.

## Test 1 – nur Descriptor (geflasht 20.11.2026)
Abbild `firmware/z2midi_stage1_dfu.bin` (sha256 a2ce44a8…), gebaut mit `tools/patch_stage1.py`.
Ergebnis am PC:
- Der Z2 startet, und die live gelesene Konfiguration ist identisch zur gebauten (366 Bytes, 7 Interfaces, EF/02/01).
- Neue Funktion MI_05 mit Microsoft-Treiber `usbaudio`, ohne Fehlercode, mit KS-Interfaces Render/Capture/Audio.
- NI-Audio (alle WDM-Endpunkte) und HID sind weiter OK.
- Der Flash-Inhalt ist nach dem Neustart byte-identisch zurückgelesen.
- Noch offen: Der WinMM-Port fehlt, vermutlich weil der MIDI-Dienst die Funktion erst nach dem Neu-Einstecken übernimmt. Auch der iPad-Test steht noch aus.
- Hinweis: Direkt nach dem Schreiben liefert UPLOAD 0 Bytes. Erst nach Neustart + CLRSTATUS kann man wieder lesen.

## Test 2 – Panel → MIDI (gebaut 20.11.2026, noch nicht geflasht)
Abbild `firmware/z2midi_stage2_dfu.bin` (99 584 Bytes, sha256 253f1ed5…).
Gebaut aus `tools/patch_stage2.py` und `firmware/stage2/` (midi_glue.c, gen_hooks.py → hooks.S, blob.elf).
- Das Modul (2988 Bytes, xcc -Os) liegt im unbenutzten ECM-Paketpuffer bei 0x19f90–0x1ab3c.
  Das Löschen beim Start (0x18514) beginnt erst dahinter.
- Haken in NIs HID-Thread:
  - 0x12d5e → `z2_hook_init`: MIDI-IN-Endpunkt auf Kanal a22 mit NIs `0x130cc` einrichten.
  - 0x12c6c → `z2_hook_report`: HID-Bericht → z2midi → EP 0x84.
  - 0x12e62 → `z2_hook_token`: Fertig-Meldungen von EP 0x84 abfangen.
- Der USB-Kern verteilt die Endpunkt-Kennungen beim Start nicht blockierend (0x15350), deshalb hängt `in` auf a22 nicht.
- Im XMOS-Simulator (`sim_test.c`) besteht der Kern alle Tests.
- Noch nicht drin: LEDs per MIDI (EP 0x03 → Berichte 0x80/0x81), kommt als Schritt 3.

Ergebnis Test 2: Flash und Start ok, MIDI von den Bedienelementen kommt am iPad an (bestätigt 20.11.2026).

## Test 3 – MIDI → LEDs (geflasht 20.11.2026 mit Freigabe)
Abbild `firmware/z2midi_stage3_dfu.bin` (100 608 Bytes, sha256 31645682…).
- **MIDI OUT:** EP 0x03 auf Kanal a24 (`fn_12cac` sp[0x85]) über NIs `0x12fe8`/`0x13020`/`0x13034`, Empfangspuffer 512 B bei 0x1ad48.
- **LEDs/LED-Hoheit:** `mg_midi` (z2midi) erzeugt die Berichte 0x80/0x81 und das Feature 0xF1. Gesendet werden sie wie NIs HID OUT über `0x12c74(a20, buf, len, 0xc8)` (Befehl 0x18).
  Die Maske ist 0xB3, Byte 2 bleibt 0 (Gerätewert ohne NI-Software).
- **Review** (3 unabhängige Prüfer, 20.11.2026):
  - Korrigiert: Nach einem Null-Längen-Paket wurde EP 0x03 nicht neu scharf gemacht.
  - Gehärtet: Im NI-Netzwerkmodus (sp[0x86] ≠ 0) bleibt der MIDI-Code außen vor.
  - Ohne Befund geprüft: Register, Stack, Rückgabewerte, Interrupt- und dp/cp-Umschaltung, Speicherlayout und Token-Kollisionen.
  - Bekannter Punkt: `mg_midi` läuft bei sehr großen MIDI-Paketen bis ~0,1 ms mit gesperrten Interrupts. Harmlos, weil der USB-Kern selbst NAKt.
- **Platz:** Die Button-Tabelle ist kompakt (1 Byte/Taste), der Ring hat 32 Pakete. Das Modul belegt 0x19f90–0x1af4c (Puffer-Ende 0x1af6c).
- **Am PC geprüft:**
  - Start ok, alle USB-Funktionen ok, Live-Descriptor wie erwartet.
  - Der Flash-Inhalt ist byte-identisch zurückgelesen.
  - Der HID-Thread ist aktiv: 3 HID-OUT-Berichte wurden angenommen.
  - Der LED-Test am iPad steht noch aus.

## Test 3b – USB-Abbrüche behoben (geflasht 20.11.2026 mit Freigabe)
Abbild `firmware/z2midi_stage3b_dfu.bin` (100 608 Bytes, sha256 85665b97…).
- **Befund:** Mit Test 3 fiel der Z2 am PC mehrfach vom USB-Bus (nur der Hub blieb sichtbar, LEDs blieben an).
  Mit NI-Firmware 42 lief dasselbe Gerät stabil. Stack (645 Wörter frei) und Speicherbereich sind unauffällig.
- **Wahrscheinliche Ursache:** NIs USB-Kern überträgt Endpunkt-Daten in Echtzeit über die Interrupt-Routinen
  des HID-Threads (IN `0x14d94`, OUT `0x14dd4`, eingerichtet mit `setc 0xa` in `0x14d6c/0x14d70`).
  Die Haken sperrten während der z2midi-Aufrufe die Interrupts (`clrsr 2`), weil dp/cp umgeschaltet sind
  und die Routinen `dp[0x2d2]` lesen. Fiel ein USB-Paket in so ein Fenster (einige µs), antwortete der Z2 zu spät.
- **Korrektur:**
  - Die Interrupt-Routinen lesen den Token-Kanal jetzt über `sp[6]` statt `dp[0x2d2]`
    (0x14dc2, 0x14e00: `ldw r0, sp[6]; nop`). Der Kernel-Stack liegt bei 0x19524, nach `kentsp 5` ist das dasselbe Wort.
  - Die Haken sperren keine Interrupts mehr (`gen_hooks.py`, `call_blob`).
- **Geprüft:** `stage2/isr_test` (xsim: `sp[6]` stimmt, auch mit fremdem dp), `sim_test.c` besteht,
  Unterschiede zum Test-3-Kern nur an den erwarteten Stellen.
- **Am Gerät:** Start ok, Flash identisch zurückgelesen. Dauertest `tools/usb_stress.py` 240 s bestanden:
  39 972 HID-OUT-Berichte, 1 350 Tasten- und 11 330 Regler-Berichte, kein Abbruch (Test 3: 5 Abbrüche bei wenigen hundert Berichten).
- **Offen:** Test am iPad.

## Offene Punkte
| Punkt | Weg |
|---|---|
| Freies RAM auf Kern 1 (Stack-Bedarf der Threads) | Speicherkarte aus den `extsp`-Werten und dp/bss-Grenzen erstellen |
| Wo genau die Panel-Daten in Kern 1 ankommen | Datenfluss in `fn_12cac` weiter verfolgen (Kanal von Kern 0) |
| Akzeptiert iOS das erweiterte Gerät? | Erstes Test-Abbild am iPad prüfen |

## Sicherheit
- Geschrieben wird nur das Upgrade-Abbild. Das Werks-Abbild bleibt unangetastet.
- Ein Abbild mit falscher Prüfsumme bootet nicht. Der Bootloader startet dann das Werks-Abbild.
- Wenn ein Abbild bootet, aber USB/DFU defekt ist, rettet nur ein SPI-Programmer. Deshalb kommt vor
  dem ersten Flashen eine Test-Reihenfolge: Erst eine Version, die nur den Descriptor ändert.
- Nichts wird ohne ausdrückliches OK geflasht.
