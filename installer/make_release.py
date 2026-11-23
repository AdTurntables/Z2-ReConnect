"""Packt die Veroeffentlichung 0.9.0 Beta 2 nach release/ (vorher build_windows.ps1 und make_mac_app.py ausfuehren):

  Z2-ReConnect-0.9.0-beta2-Windows.zip   Installer-EXE, Anleitung Pad-Ebenen (DE/EN), Kurzanleitung
  Z2-ReConnect-0.9.0-beta2-Mac.zip       Kopie aus dist_mac/ (App, Anleitung Pad-Ebenen, Kurzanleitung)
  Z2-ReConnect-djay-Mapping-v8.zip       djay-Mapping, Belegungsbild (DE/EN), Anleitung Pad-Ebenen (DE/EN), Kurzanleitung
"""
import os, shutil, zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
os.chdir(HERE)
G = "../grafik/"
DATE = (2026, 11, 23, 0, 0, 0)
OUT = "release"

WIN_README = """Z² Re:Connect 0.9.0 Beta 2 – Windows
======================================

DEUTSCH
1. Z2 mit Netzteil per USB anschließen und einschalten. Der NI-Treiber für den Z2 muss installiert sein.
2. "Z2-ReConnect-Installer.exe" starten und den Schritten folgen. Vor dem Schreiben wird automatisch ein Backup
   der aktuellen Firmware im Ordner Dokumente\\Z2-Firmware-Backup gespeichert.
3. Das passende djay-Mapping (Version 8) gibt es als eigenes Paket "Z2-ReConnect-djay-Mapping".
4. Wie die Pad-Ebenen funktionieren, zeigt "Anleitung Pad-Ebenen.png".
Neu in Beta 2: Cue-Farben aus djay auf den Pads, Pegelanzeigen A/B, LEDs funktionieren nach dem USB-Neuverbinden.

ENGLISH
1. Connect the Z2 (with power supply) via USB and switch it on. The NI driver for the Z2 must be installed.
2. Start "Z2-ReConnect-Installer.exe" and follow the steps. Before anything is written, a backup of the current
   firmware is saved automatically in Documents\\Z2-Firmware-Backup.
3. The matching djay mapping (version 8) comes as a separate package, "Z2-ReConnect-djay-Mapping".
4. "Guide pad layers.png" shows how the pad layers work.
New in Beta 2: cue colours from djay on the pads, level meters A/B, LEDs work again after re-plugging USB.

Private hobby project, not affiliated with Native Instruments or Algoriddim, no warranty. Use at your own risk.
"""

DJAY_README = """Z² Re:Connect – djay Pro Mapping Version 8
===========================================

DEUTSCH
Braucht einen Z2 mit der Firmware Z² Re:Connect 0.9.0 Beta 2.
1. "Traktor Kontrol Z2.djayMidiMapping" aufs iPad kopieren (z. B. über die Dateien-App) und in djay öffnen bzw.
   unter Einstellungen -> MIDI importieren. Ein älteres Z2-Mapping vorher entfernen.
2. DVS (Timecode): in den djay-Audioeinstellungen als Eingang wählen: Deck A = Kanal 3/4, Deck B = Kanal 5/6.
   Danach mit REL / INTL einschalten.
3. Belegung: "Belegung djay.png". Pad-Ebenen: "Anleitung Pad-Ebenen.png".
Neu in Version 8: Cue-Farben auf den Pads, Pegelanzeigen A/B für Deck 1/2.

ENGLISH
Needs a Z2 running the Z² Re:Connect 0.9.0 Beta 2 firmware.
1. Copy "Traktor Kontrol Z2.djayMidiMapping" to the iPad (e.g. with the Files app) and open it in djay or
   import it under Settings -> MIDI. Remove an older Z2 mapping first.
2. DVS (timecode): in djay's audio settings set the inputs: deck A = channels 3/4, deck B = channels 5/6.
   Then switch it on with REL / INTL.
3. Controls: "Controls djay.png". Pad layers: "Guide pad layers.png".
New in version 8: cue colours on the pads, level meters A/B for deck 1/2.

Unofficial community project, not affiliated with Native Instruments or Algoriddim, no warranty.
"""


def add(z, path, data):
    info = zipfile.ZipInfo(path, date_time=DATE)
    info.external_attr = 0o100644 << 16
    info.create_system = 3
    info.compress_type = zipfile.ZIP_DEFLATED
    z.writestr(info, data, compresslevel=9)


def pack(name, items):
    out = os.path.join(OUT, name + ".zip")
    with zipfile.ZipFile(out, "w") as z:
        for src, dst in items:
            add(z, name + "/" + dst, src if isinstance(src, bytes) else open(src, "rb").read())
    print(out, os.path.getsize(out) // 1024, "KB,", len(items), "Dateien")


os.makedirs(OUT, exist_ok=True)
GUIDES = [(G + "z2_ebenen.png", "Anleitung Pad-Ebenen.png"), (G + "z2_ebenen_en.png", "Guide pad layers.png")]
pack("Z2-ReConnect-0.9.0-beta2-Windows",
     [("dist_win/Z2-ReConnect-Installer.exe", "Z2-ReConnect-Installer.exe")] + GUIDES +
     [(WIN_README.replace("\n", "\r\n").encode("utf-8-sig"), "LIES MICH - READ ME.txt")])
shutil.copyfile("dist_mac/Z2-ReConnect-0.9.0-beta2-Mac.zip", os.path.join(OUT, "Z2-ReConnect-0.9.0-beta2-Mac.zip"))
print(os.path.join(OUT, "Z2-ReConnect-0.9.0-beta2-Mac.zip"), "kopiert")
pack("Z2-ReConnect-djay-Mapping-v8",
     [("../djay/Traktor Kontrol Z2.djayMidiMapping", "Traktor Kontrol Z2.djayMidiMapping"),
      (G + "z2_djay_mapping.png", "Belegung djay.png"), (G + "z2_djay_mapping_en.png", "Controls djay.png")] + GUIDES +
     [(DJAY_README.replace("\n", "\r\n").encode("utf-8-sig"), "LIES MICH - READ ME.txt")])
