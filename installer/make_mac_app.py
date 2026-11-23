"""Baut die eigenstaendige Mac-App (ohne Python- oder Internet-Voraussetzung) als ZIP – laeuft unter Windows.

Ergebnis: dist_mac/Z2-ReConnect-0.9.0-beta2-Mac.zip mit
  "Z2 ReConnect Installer.app"   – enthaelt Python 3.12 (Apple Silicon + Intel), tkinter, pyusb und libusb
  Anleitung Pad-Ebenen (DE/EN)   – Bilder; das djay-Mapping ist ein eigenes Paket (make_release.py)
  LIES MICH - READ ME (Mac).txt

Die Bausteine liegen in mac_vendor/ (werden bei Bedarf geladen und per SHA-256 geprueft):
  * python-build-standalone 20261110, CPython 3.12.16, install_only_stripped (github.com/astral-sh/python-build-standalone)
  * pyusb 1.3.1, libusb-package 1.0.30.1, importlib_resources 7.1.0 (libusb-package braucht es) (pypi.org)
Symlinks aus dem Python-Archiv werden weggelassen (die App ruft bin/python3.12 direkt auf).
"""
import hashlib, io, os, struct, tarfile, urllib.request, zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
os.chdir(HERE)
NAME = "Z2-ReConnect-0.9.0-beta2-Mac"
APP = NAME + "/Z2 ReConnect Installer.app/Contents"
DATE = (2026, 11, 22, 0, 0, 0)
PBS = "https://github.com/astral-sh/python-build-standalone/releases/download/20261110/"
PYPI = "https://files.pythonhosted.org/packages/py3/"
VENDOR = {
    "py-aarch64.tar.gz": (PBS + "cpython-3.12.16%2B20261110-aarch64-apple-darwin-install_only_stripped.tar.gz",
                          "2f11b8aa3726bdbd87dd9eb76568412faddf4f47e26913fa45d6a2e424972acd"),
    "py-x86_64.tar.gz": (PBS + "cpython-3.12.16%2B20261110-x86_64-apple-darwin-install_only_stripped.tar.gz",
                         "b78a4c479f1964ec484880bee567568266f68da102269fb93a05fe8716b45f91"),
    "pyusb-1.3.1-py3-none-any.whl": (PYPI + "p/pyusb/pyusb-1.3.1-py3-none-any.whl",
                                     "bf9b754557af4717fe80c2b07cc2b923a9151f5c08d17bdb5345dac09d6a0430"),
    "importlib_resources-7.1.0-py3-none-any.whl": (PYPI + "i/importlib_resources/importlib_resources-7.1.0-py3-none-any.whl",
                                                   "1bd7b48b4088eddb2cd16382150bb515af0bd2c70128194392725f82ad2c96a1"),
    "libusb_package-1.0.30.1-py3-none-macosx_11_0_arm64.whl": (PYPI + "l/libusb-package/libusb_package-1.0.30.1-py3-none-macosx_11_0_arm64.whl",
                                                              "46c7ca9931c46cd63ff89ce17c947653c3c5dec46a441c6bc103f1fda86d52df"),
    "libusb_package-1.0.30.1-py3-none-macosx_10_9_x86_64.whl": (PYPI + "l/libusb-package/libusb_package-1.0.30.1-py3-none-macosx_10_9_x86_64.whl",
                                                               "7ee86d9e1092f22239be28ae45e12cd47d65f4fa19f71e83f1f1036b97295cdc"),
}
ARCHS = {"arm64": ("py-aarch64.tar.gz", "libusb_package-1.0.30.1-py3-none-macosx_11_0_arm64.whl"),
         "x86_64": ("py-x86_64.tar.gz", "libusb_package-1.0.30.1-py3-none-macosx_10_9_x86_64.whl")}
GUIDES = [("../grafik/z2_ebenen.png", "Anleitung Pad-Ebenen.png"), ("../grafik/z2_ebenen_en.png", "Guide pad layers.png")]
APP_FILES = ["z2_installer.py", "z2_gui.py", "intro.frames"]

# Teile der Python-Distribution, die der Installer nicht braucht
DROP_PREFIX = ("python/include/", "python/share/", "python/lib/pkgconfig/", "python/lib/libpython3.12.dylib",
               "python/lib/python3.12/site-packages/", "python/lib/python3.12/config-3.12-darwin/")
DROP_STDLIB = {"ensurepip", "idlelib", "lib2to3", "pydoc_data", "test", "turtledemo", "venv", "tkinter/test"}

LAUNCHER = """#!/bin/sh
# Z2 Re:Connect – startet den Installer mit dem mitgelieferten Python (Apple Silicon oder Intel).
R="$(cd "$(dirname "$0")/../Resources" && pwd)"
if [ "$(uname -m)" = "arm64" ]; then P="$R/python-arm64"; else P="$R/python-x86_64"; fi
LOG="$HOME/Library/Logs/Z2-ReConnect-Installer.log"
mkdir -p "$HOME/Library/Logs" 2>/dev/null
exec "$P/bin/python3.12" -s -E -B "$R/z2_installer.py" 2>>"$LOG"
"""

PLIST = """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>CFBundleName</key><string>Z² Re:Connect</string>
  <key>CFBundleDisplayName</key><string>Z² Re:Connect Installer</string>
  <key>CFBundleIdentifier</key><string>org.z2reconnect.installer</string>
  <key>CFBundleExecutable</key><string>Z2ReConnect</string>
  <key>CFBundleIconFile</key><string>AppIcon</string>
  <key>CFBundlePackageType</key><string>APPL</string>
  <key>CFBundleShortVersionString</key><string>0.9.0</string>
  <key>CFBundleVersion</key><string>0.9.0b1</string>
  <key>LSMinimumSystemVersion</key><string>10.13</string>
  <key>NSHighResolutionCapable</key><true/>
  <key>NSDocumentsFolderUsageDescription</key><string>Das Backup der Original-Firmware wird im Ordner Dokumente gespeichert. / The backup of the original firmware is saved in your Documents folder.</string>
</dict>
</plist>
"""

README = """Z² Re:Connect 0.9.0 Beta 2 – macOS
=====================================

DEUTSCH
Alles ist enthalten – es muss nichts zusätzlich installiert oder heruntergeladen werden.
1. ZIP entpacken, Z2 mit Netzteil per USB anschließen.
2. "Z2 ReConnect Installer" doppelklicken (am besten vorher in den Ordner "Programme" ziehen).
3. Da die App nicht von Apple beglaubigt ist, blockiert macOS den ersten Start:
   - macOS 15 und neuer: Meldung schließen, dann Systemeinstellungen -> Datenschutz & Sicherheit ->
     ganz unten "Dennoch öffnen" klicken und bestätigen.
   - Ältere macOS-Versionen: Rechtsklick auf die App -> Öffnen -> Öffnen.
   Das ist nur beim ersten Start nötig.
4. Fragt macOS nach Zugriff auf den Ordner "Dokumente": erlauben (dort landet das Backup).
Das passende djay-Mapping (Version 8) gibt es als eigenes Paket "Z2-ReConnect-djay-Mapping".
Die macOS-Version ist experimentell und noch ungetestet. Wenn möglich, bitte unter Windows installieren.
Bei Problemen hilft die Protokolldatei: ~/Library/Logs/Z2-ReConnect-Installer.log

ENGLISH
Everything is included – nothing else needs to be installed or downloaded.
1. Unzip, connect the Z2 (with power supply) via USB.
2. Double-click "Z2 ReConnect Installer" (ideally move it to "Applications" first).
3. The app is not notarized by Apple, so macOS blocks the first start:
   - macOS 15 and newer: close the message, then System Settings -> Privacy & Security ->
     scroll down, click "Open Anyway" and confirm.
   - Older macOS: right-click the app -> Open -> Open.
   This is only needed the first time.
4. If macOS asks for access to your "Documents" folder: allow it (the backup is saved there).
The matching djay mapping (version 8) comes as a separate package, "Z2-ReConnect-djay-Mapping".
The macOS version is experimental and not tested yet. If possible, install on Windows.
If something goes wrong, see the log file: ~/Library/Logs/Z2-ReConnect-Installer.log

Private hobby project, not affiliated with Native Instruments, no warranty. Use at your own risk.
"""


def vendor(name):
    url, sha = VENDOR[name]
    path = os.path.join("mac_vendor", name)
    if not os.path.exists(path):
        os.makedirs("mac_vendor", exist_ok=True)
        print("lade", name)
        urllib.request.urlretrieve(url, path)
    data = open(path, "rb").read()
    if hashlib.sha256(data).hexdigest() != sha:
        raise SystemExit("Pruefsumme falsch: " + path)
    return data


def make_icns():
    """App-Symbol aus dem letzten Intro-Bild (Z² auf dunklem, abgerundetem Quadrat), als PNG-basiertes .icns."""
    from PIL import Image, ImageDraw
    raw = open("intro.frames", "rb").read()
    n = struct.unpack_from("<I", raw, 8)[0]; o = 16
    for _ in range(n):
        ln = struct.unpack_from("<I", raw, o)[0]; png = raw[o + 4:o + 4 + ln]; o += 4 + ln
    im = Image.open(io.BytesIO(png)).convert("RGB")
    box = im.convert("L").point(lambda v: 255 if v > 60 else 0).getbbox()
    logo = im.crop(box)
    S = 1024
    bg = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    mask = Image.new("L", (S, S), 0)
    ImageDraw.Draw(mask).rounded_rectangle((100, 100, S - 100, S - 100), radius=185, fill=255)
    bg.paste(Image.new("RGBA", (S, S), (14, 14, 18, 255)), (0, 0), mask)
    w = 560; h = int(logo.height * w / logo.width)
    logo = logo.resize((w, h), Image.LANCZOS)
    bg.paste(logo, ((S - w) // 2, (S - h) // 2), logo.convert("L"))
    out = b""
    for typ, size in ((b"ic10", 1024), (b"ic09", 512), (b"ic08", 256), (b"ic07", 128)):
        buf = io.BytesIO(); bg.resize((size, size), Image.LANCZOS).save(buf, "PNG")
        out += typ + struct.pack(">I", 8 + len(buf.getvalue())) + buf.getvalue()
    return b"icns" + struct.pack(">I", 8 + len(out)) + out


def keep(name):
    if name.startswith(DROP_PREFIX): return False
    if "/bin/" in name and not name.endswith("/bin/python3.12"): return False
    if "/__pycache__/" in name: return False
    if name.startswith("python/lib/python3.12/"):
        rest = name[len("python/lib/python3.12/"):]
        if any(rest == d or rest.startswith(d + "/") for d in DROP_STDLIB): return False
    return True


def add(z, path, data, mode=0o644):
    info = zipfile.ZipInfo(path, date_time=DATE)
    info.external_attr = (0o100000 | mode) << 16
    info.create_system = 3
    info.compress_type = zipfile.ZIP_DEFLATED
    z.writestr(info, data, compresslevel=9)


def main():
    os.makedirs("dist_mac", exist_ok=True)
    out = os.path.join("dist_mac", NAME + ".zip")
    common = [zipfile.ZipFile(io.BytesIO(vendor(w))) for w in ("pyusb-1.3.1-py3-none-any.whl", "importlib_resources-7.1.0-py3-none-any.whl")]
    count = 0
    with zipfile.ZipFile(out, "w") as z:
        add(z, APP + "/Info.plist", PLIST.encode("utf-8"))
        add(z, APP + "/PkgInfo", b"APPL????")
        add(z, APP + "/MacOS/Z2ReConnect", LAUNCHER.encode("utf-8"), 0o755)
        add(z, APP + "/Resources/AppIcon.icns", make_icns())
        for f in APP_FILES:
            add(z, APP + "/Resources/" + f, open(f, "rb").read())
        for f in sorted(os.listdir(".")):
            if f.endswith(".z2patch"):
                add(z, APP + "/Resources/" + f, open(f, "rb").read())
        count += 5 + len(APP_FILES)
        for arch, (tgz, lwhl) in ARCHS.items():
            base = APP + "/Resources/python-%s/" % arch
            t = tarfile.open(fileobj=io.BytesIO(vendor(tgz)))
            for m in t:
                if not m.isfile() or not keep(m.name): continue
                add(z, base + m.name[len("python/"):], t.extractfile(m).read(), 0o755 if m.mode & 0o111 else 0o644)
                count += 1
            site = base + "lib/python3.12/site-packages/"
            for whl in common + [zipfile.ZipFile(io.BytesIO(vendor(lwhl)))]:
                for n in whl.namelist():
                    if n.endswith("/") or ".dist-info/" in n or "__pyinstaller" in n or "/tests/" in n: continue
                    add(z, site + n, whl.read(n), 0o755 if n.endswith(".dylib") else 0o644)
                    count += 1
        for src, dst in GUIDES:
            add(z, NAME + "/" + dst, open(src, "rb").read()); count += 1
        add(z, NAME + "/LIES MICH - READ ME (Mac).txt", README.encode("utf-8")); count += 1
    print(out, os.path.getsize(out) // 1024, "KB,", count, "Dateien")


if __name__ == "__main__":
    main()
