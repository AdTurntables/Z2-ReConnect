"""Packs the TESTER package of the installer with the bridge (intermediate step) into release/:

  Z2-ReConnect-0.9.0-beta2-Tester-Windows.zip
      Z2-ReConnect-Installer.exe      (dist_win, built by build_windows.ps1 from the current sources)
      z2rc_bridge.z2bridge            (the bridge firmware, sha256 must equal z2_installer.BRIDGE_SHA256)
      LIESMICH-TESTER.txt             (DE/EN: what it does, risks, way back, what to send)
      THIRD_PARTY_NOTICES.txt         (XMOS sc_flash + sc_xud licences, used inside the bridge)

Only these files, explicitly listed (no glob): never firmware dumps, backups, NI firmware or diagnosis files.
Windows only (the bridge path is not tested with libusb on macOS/Linux yet).
"""
import hashlib, os, sys, zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import z2_installer as zi

BR = os.path.join(HERE, "..", "firmware", "newfw", "bridge")       # development tree
if not os.path.isdir(BR):
    BR = os.path.join(HERE, "..", "firmware", "bridge")           # public repository layout
SRC_BRIDGE = os.path.join(BR, "image", "z2rc_bridge_dfu.bin")
EXE = os.path.join(HERE, "dist_win", "Z2-ReConnect-Installer.exe")
OUT = os.path.join(HERE, "release", "Z2-ReConnect-0.9.0-beta2-Tester-Windows.zip")
DATE = (2026, 11, 26, 0, 0, 0)

README = """Z² Re:Connect 0.9.0 Beta 2 – TESTER-Version mit Zwischenschritt (Windows)
==========================================================================

DEUTSCH
Für wen: Z2, bei denen der normale Installer meldet, dass keine Firmware 42 im Speicher ist
(NIs Device Updater sagt dann "aktuell" und bietet nichts an).

Vorher: die ZIP-Datei in einen Ordner ENTPACKEN. "Z2-ReConnect-Installer.exe" und "z2rc_bridge.z2bridge"
müssen nebeneinander liegen (direkt aus der ZIP gestartet findet der Installer die Bridge nicht).
NIs Device Updater während des Installers geschlossen lassen.

Was passiert:
1. Der Installer prüft den Z2 (nur lesend). Erkennt er die Werks-Firmware mit LEEREM Update-Platz,
   bietet er den Zwischenschritt an.
2. Er schreibt eine kleine Bridge-Firmware (eigener Code, ohne Audio/MIDI) in den leeren Update-Platz.
   Die Werks-Firmware wird dabei nie beschrieben.
3. Danach den Z2 NICHT aus- und einschalten, sondern NIs Device Updater starten (getestet: 1.2.0).
   Er zeigt "Installed 1 / Newest 42" und spielt Firmware 42 auf. Wirkt er danach still: einfach schließen.
4. Den Installer erneut starten: Er erkennt jetzt die Firmware 42 und installiert Z² Re:Connect.

Stand der Tests:
- Werks-Firmware 30: der ganze Weg ist an einem Gerät erprobt.
- Werks-Firmware 51: NOCH NICHT erprobt. Der Installer verlangt dafür ein eigenes Bestätigungswort.
- Andere Versionen: werden abgelehnt.

Rückweg, falls etwas nicht klappt:
- den Z2 bis zu viermal aus- und einschalten, bis der Installer wieder die Werks-Firmware meldet: die Bridge
  löscht sich selbst, die Werks-Firmware startet wieder; oder
- SHIFT + SETTINGS beim Einschalten 5 Sekunden halten (alle anderen Tasten loslassen).
- Findet die Bridge sich auf einem anders aufgebauten Gerät nicht wieder, macht sie sich selbst ungültig,
  und die Werks-Firmware startet wieder (Sicherheitsnetz).

Restrisiko: Hat dein Z2 einen Flash-Chip, den die Bridge nicht kennt, kann er auf der Bridge hängen bleiben.
Dann hilft nur ein SPI-Programmer (Klemme auf den Speicherchip). Teste nur, wenn du das in Kauf nimmst.

Bitte schicke nach jedem Test (auch wenn es klappt) die Dateien "Z2-ReConnect-Bridge-Protokoll.txt" und
"Z2-ReConnect-Diagnose.txt" aus Dokumente\\Z2-Firmware-Backup sowie die Zahl, die NIs Device Updater
unter "Installed Firmware" angezeigt hat, und wenn möglich ein Foto vom Speicherchip auf der Platine.
Die Dateien enthalten keine Seriennummer und keine Firmware.

ENGLISH
Who it is for: Z2 units where the normal installer reports that no firmware 42 is in memory
(NI's Device Updater then says "up to date" and offers nothing).

First: EXTRACT the ZIP file into a folder. "Z2-ReConnect-Installer.exe" and "z2rc_bridge.z2bridge" must be
side by side (started directly from the ZIP the installer cannot find the bridge).
Keep NI's Device Updater closed while the installer runs.

What happens:
1. The installer checks the Z2 (read only). If it detects the factory firmware with an EMPTY update slot,
   it offers the intermediate step.
2. It writes a small bridge firmware (own code, no audio/MIDI) into the empty update slot.
   The factory firmware is never written.
3. Afterwards do NOT switch the Z2 off and on; start NI's Device Updater instead (tested: 1.2.0).
   It shows "Installed 1 / Newest 42" and installs firmware 42. If it looks idle afterwards: just close it.
4. Start the installer again: it now detects firmware 42 and installs Z² Re:Connect.

Test status:
- Factory firmware 30: the whole path is proven on one unit.
- Factory firmware 51: NOT tested yet. The installer asks for a separate confirmation word.
- Other versions: refused.

Way back if something fails:
- switch the Z2 off and on up to four times until the installer reports the factory firmware again: the bridge
  deletes itself, the factory firmware starts again; or
- hold SHIFT + SETTINGS for 5 seconds while switching on (release all other buttons).
- If the bridge cannot find itself on a differently built unit, it invalidates itself and the factory
  firmware starts again (safety net).

Remaining risk: if your Z2 has a flash chip the bridge does not know, it can hang on the bridge.
Then only an SPI programmer (clip on the memory chip) helps. Only test if you accept that.

After every test (also when it works) please send the files "Z2-ReConnect-Bridge-Protokoll.txt" and
"Z2-ReConnect-Diagnose.txt" from Documents\\Z2-Firmware-Backup, the number NI's Device Updater showed under
"Installed Firmware" and, if possible, a photo of the memory chip on the board.
The files contain no serial number and no firmware.

Private hobby project, not affiliated with Native Instruments or XMOS, no warranty. Use at your own risk.
"""

NOTICES_HEAD = """THIRD PARTY NOTICES – Z² Re:Connect Bridge firmware (z2rc_bridge.z2bridge)
==========================================================================

The bridge firmware is own code (firmware/newfw/bridge). It contains, compiled in, these XMOS libraries:
  - sc_flash, module_flash (commit c39116c), licence below
  - sc_xud 2.4.1 (commit 81cf9ac), module_xud, licence below
and the small C run-time start-up code and C library routines of the XMOS xTIMEcomposer 14.4.1 tools.
No Native Instruments code or data is contained.

"""


def main():
    problems = []
    bridge = open(SRC_BRIDGE, "rb").read()
    if hashlib.sha256(bridge).hexdigest() != zi.BRIDGE_SHA256:
        problems.append("bridge image sha256 != BRIDGE_SHA256 (%s)" % hashlib.sha256(bridge).hexdigest())
    if not os.path.isfile(EXE):
        problems.append("missing %s - run build_windows.ps1 first" % EXE)
    elif os.path.getmtime(EXE) < os.path.getmtime(os.path.join(HERE, "z2_installer.py")):
        problems.append("dist_win exe is older than z2_installer.py - rebuild with build_windows.ps1")
    lic_flash = open(os.path.join(BR, "third_party", "sc_flash", "LICENSE.txt"), encoding="utf-8").read()
    lic_xud = open(os.path.join(BR, "third_party", "sc_xud_LICENSE.txt"), encoding="utf-8").read()
    if problems:
        for p in problems: print("PROBLEM:", p)
        sys.exit(1)
    notices = (NOTICES_HEAD + "---------------- sc_flash ----------------\n" + lic_flash +
               "\n---------------- sc_xud ----------------\n" + lic_xud)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    entries = [("Z2-ReConnect-Installer.exe", open(EXE, "rb").read()),
               (zi.BRIDGE_FILE, bridge),
               ("LIESMICH-TESTER.txt", README.replace("\n", "\r\n").encode("utf-8")),
               ("THIRD_PARTY_NOTICES.txt", notices.replace("\r\n", "\n").replace("\n", "\r\n").encode("utf-8"))]
    with zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED) as z:
        for name, data in entries:
            zi_ = zipfile.ZipInfo(name, DATE); zi_.compress_type = zipfile.ZIP_DEFLATED
            z.writestr(zi_, data)
    with zipfile.ZipFile(OUT) as z:
        names = z.namelist()
    print("written %s\n  %s\n  sha256 %s" % (OUT, ", ".join(names), hashlib.sha256(open(OUT, "rb").read()).hexdigest()))
    assert names == [e[0] for e in entries]


if __name__ == "__main__":
    main()
