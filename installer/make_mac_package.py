"""Packt das Mac-Paket dist_mac/Z2-ReConnect-0.9.0-beta1-Mac.zip (laeuft ohne Bauen, braucht Python 3 auf dem Mac).

Inhalt: Startdatei (.command, ausfuehrbar), Quelltext des Installers, Patches, Intro, djay-Ordner, Kurzanleitung.
Die Ausfuehrungsrechte der .command-Datei werden im ZIP gesetzt (macOS' Archivprogramm uebernimmt sie).
"""
import glob, os, zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
os.chdir(HERE)
NAME = "Z2-ReConnect-0.9.0-beta1-Mac-lite"   # Alternative ohne eingebautes Python (Hauptpaket: make_mac_app.py)
FILES = ["Z2-ReConnect-Installer (Mac).command", "z2_installer.py", "z2_gui.py", "intro.frames", "LIESMICH.md"] + \
        sorted(glob.glob("*.z2patch")) + sorted(os.path.join("djay", f) for f in os.listdir("djay"))
README = """Z² Re:Connect 0.9.0 Beta 1 – macOS
=====================================

DEUTSCH
1. Python 3 installieren (einmalig): https://www.python.org/downloads/macos/
2. Diesen Ordner entpacken, Z2 mit Netzteil per USB anschließen.
3. "Z2-ReConnect-Installer (Mac).command" doppelklicken.
   Meldet macOS "nicht verifizierter Entwickler": Rechtsklick -> Öffnen -> Öffnen.
   Neuere macOS-Versionen: Systemeinstellungen -> Datenschutz & Sicherheit -> "Dennoch öffnen".
4. Beim ersten Start werden die USB-Pakete aus dem Internet geladen (einmalig, etwa 1 MB).
5. Fragt das Terminal nach Zugriff auf den Ordner "Dokumente": erlauben (dort landet das Backup).
Die macOS-Version ist experimentell und noch ungetestet. Wenn möglich, bitte unter Windows installieren.

ENGLISH
1. Install Python 3 (once): https://www.python.org/downloads/macos/
2. Unzip this folder, connect the Z2 (with power supply) via USB.
3. Double-click "Z2-ReConnect-Installer (Mac).command".
   If macOS says "unidentified developer": right-click -> Open -> Open.
   Newer macOS: System Settings -> Privacy & Security -> "Open Anyway".
4. On first start the USB packages are downloaded (once, about 1 MB).
5. If Terminal asks for access to your "Documents" folder: allow it (the backup is saved there).
The macOS version is experimental and not tested yet. If possible, install on Windows.

Private hobby project, not affiliated with Native Instruments, no warranty. Use at your own risk.
"""

os.makedirs("dist_mac", exist_ok=True)
out = os.path.join("dist_mac", NAME + ".zip")
with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
    for f in FILES:
        info = zipfile.ZipInfo(NAME + "/" + f.replace(os.sep, "/"), date_time=(2026, 11, 22, 0, 0, 0))
        mode = 0o755 if f.endswith(".command") else 0o644
        info.external_attr = (0o100000 | mode) << 16
        info.create_system = 3                        # Unix, damit die Rechte gelesen werden
        info.compress_type = zipfile.ZIP_DEFLATED
        data = open(f, "rb").read()
        if f.endswith(".command"): data = data.replace(b"\r\n", b"\n")
        z.writestr(info, data)
    info = zipfile.ZipInfo(NAME + "/LIES MICH - READ ME (Mac).txt", date_time=(2026, 11, 22, 0, 0, 0))
    info.external_attr = (0o100644) << 16; info.create_system = 3; info.compress_type = zipfile.ZIP_DEFLATED
    z.writestr(info, README.encode("utf-8"))
print(out, os.path.getsize(out), "Bytes,", len(FILES) + 1, "Dateien")
