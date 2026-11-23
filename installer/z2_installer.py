"""Z² Re:Connect – Installer (Windows, macOS, Linux).

Bringt die Firmware Z² Re:Connect (Audio + USB-MIDI am iPad/iPhone) auf einen Native Instruments Traktor Kontrol Z2:
  1. liest die Firmware aus dem angeschlossenen Z2 (Backup),
  2. prueft, ob es genau eine Firmware ist, fuer die ein Patch gebaut und getestet wurde
     (Original-Firmware 42 von Native Instruments oder eine aeltere Z² Re:Connect-Version),
  3. baut daraus lokal die neue Firmware und prueft deren Pruefsumme,
  4. schreibt sie, startet den Z2 neu und liest zur Kontrolle zurueck.
Die Original-Firmware ist nicht Teil dieses Programms; sie kommt immer aus dem eigenen Geraet.

  z2_installer            Menue
  z2_installer check      nur pruefen, es wird nichts geschrieben
  z2_installer backup     Backup der aktuellen Firmware
  z2_installer install    Z² Re:Connect installieren
  z2_installer restore    ein Backup zurueckschreiben
Ohne Befehl startet die grafische Oberflaeche; --cli zeigt stattdessen das Textmenue.
Optionen: --lang de|en, --backup-dir <Ordner>, --no-intro, --cli
"""
import glob, hashlib, json, locale, os, struct, sys, time, zlib

VERSION = "0.9.0 Beta 2"               # zweiter oeffentlicher Testlauf
PRODUCT = "Z² Re:Connect"
FW_VERSION = "0.9.0 Beta 2"            # = interner Entwicklungsstand 5b (Neuverbinden, Cue-Farben, Pegel)
FW_NAME = PRODUCT + " " + FW_VERSION   # Name der Firmware, die dieser Installer bringt
NI42_SHA256 = "208c0767c06baa0b99bd0600ced536dbef336b0218af885cd58f71e228198b16"   # NI-Firmware 42 (Pruefsumme, keine Daten)
VID, PID_RUN, PID_DFU = 0x17CC, 0x1130, 0x1132
XFER = 64
MAX_IMAGE = 2 * 1024 * 1024
STATE_IDLE, STATE_DNLOAD_IDLE, STATE_ERROR = 2, 5, 10

# ----------------------------------------------------------------------------- Texte
T = {
    "title": (PRODUCT + " – Installer %s", PRODUCT + " – installer %s"),
    "menu": ("\n  1  Prüfen (es wird nichts auf den Z2 geschrieben, Backup automatisch)\n  2  Backup der aktuellen Firmware\n  3  " + PRODUCT + " installieren\n"
             "  4  Backup zurückschreiben (Original wiederherstellen)\n  5  Beenden\n",
             "\n  1  Check (nothing is written)\n  2  Back up the current firmware\n  3  Install " + PRODUCT + "\n"
             "  4  Write a backup back (restore the original)\n  5  Quit\n"),
    "choice": ("Auswahl: ", "Choice: "),
    "nodev": ("Kein Z2 gefunden. Bitte Netzteil und USB-Kabel anschließen und einschalten.",
              "No Z2 found. Connect the power supply and the USB cable and switch it on."),
    "nodev_win": ("Unter Windows muss der Z2-Treiber von Native Instruments installiert sein.",
                  "On Windows the Native Instruments Z2 driver must be installed."),
    "multi": ("Es sind mehrere Z2 angeschlossen. Bitte nur ein Gerät anschließen.",
              "More than one Z2 is connected. Connect only one device."),
    "found": ("Z2 gefunden: USB %04x:%04x, Geräteversion %d", "Z2 found: USB %04x:%04x, device version %d"),
    "reading": ("Lese Firmware aus dem Z2 (Durchgang %d von 2) ...", "Reading firmware from the Z2 (pass %d of 2) ..."),
    "read_fail": ("Die Firmware ließ sich nicht auslesen (%s).", "The firmware could not be read (%s)."),
    "read_empty": ("Der Z2 liefert keine Firmware. Vermutlich läuft er noch mit der Werks-Firmware ohne Update. "
                   "Bitte zuerst mit dem Programm von Native Instruments auf Firmware 42 aktualisieren.",
                   "The Z2 returns no firmware. It probably still runs the factory firmware without an update. "
                   "Update it to firmware 42 with the Native Instruments tool first."),
    "read_diff": ("Zwei Lesedurchgänge ergaben unterschiedliche Daten. Abbruch – bitte USB-Kabel und Anschluss prüfen.",
                  "Two read passes returned different data. Stopping – check the USB cable and port."),
    "fw_is": ("Firmware im Gerät: %s\n  %d Bytes, SHA-256 %s", "Firmware in the device: %s\n  %d bytes, SHA-256 %s"),
    "fw_source": ("Original-Firmware 42 von Native Instruments", "Native Instruments original firmware 42"),
    "fw_target": ("%s (bereits installiert)" % FW_NAME, "%s (already installed)" % FW_NAME),
    "fw_older": ("ältere Version von %s (Update auf %s möglich)" % (PRODUCT, FW_NAME), "older version of %s (update to %s available)" % (PRODUCT, FW_NAME)),
    "fw_unknown": ("unbekannt", "unknown"),
    "c_dev": ("Gerät ist ein Traktor Kontrol Z2", "Device is a Traktor Kontrol Z2"),
    "c_read": ("Firmware zweimal identisch ausgelesen", "Firmware read twice with identical result"),
    "c_struct": ("Aufbau des Firmware-Abbilds ist gültig", "Firmware image structure is valid"),
    "c_backup": ("Backup der Firmware im Gerät automatisch gespeichert", "Backup of the firmware in the device saved automatically"),
    "c_known": ("Firmware ist genau eine getestete Ausgangsversion", "Firmware is exactly one of the tested base versions"),
    "c_build": ("Neue Firmware lokal gebaut, Prüfsumme stimmt mit der getesteten Version überein",
                "New firmware built locally, checksum matches the tested version"),
    "ok": ("  [ OK ]  ", "  [ OK ]  "), "bad": ("  [NEIN]  ", "  [ NO ]  "),
    "verdict_ok": ("\nErgebnis: Dieser Z2 ist für %s geeignet." % FW_NAME,
                   "\nResult: this Z2 is suitable for %s." % FW_NAME),
    "verdict_update": ("\nErgebnis: Auf diesem Z2 läuft eine ältere Version. Das Update auf %s ist möglich (Menüpunkt 3)." % FW_NAME,
                       "\nResult: this Z2 runs an older version. The update to %s is available (menu item 3)." % FW_NAME),
    "verdict_done": ("\nErgebnis: Auf diesem Z2 läuft %s bereits. Es ist nichts zu tun." % FW_NAME,
                     "\nResult: this Z2 already runs %s. Nothing to do." % FW_NAME),
    "verdict_no": ("\nErgebnis: Dieser Z2 wird NICHT unterstützt. Es wird nichts geschrieben.\n"
                   "Die Firmware im Gerät weicht von der getesteten Version ab. Mögliche Gründe: andere "
                   "Firmware-Version (nicht 42), andere Hardware-Revision oder eine fremde Firmware.",
                   "\nResult: this Z2 is NOT supported. Nothing will be written.\n"
                   "The firmware in the device differs from the tested version. Possible reasons: another "
                   "firmware version (not 42), another hardware revision, or third-party firmware."),
    "backup_saved": ("Backup gespeichert: %s", "Backup saved: %s"),
    "backup_same": ("Dieses Backup gibt es schon: %s", "This backup already exists: %s"),
    "warn": ("\nACHTUNG\n  - Der Z2 muss am Netzteil hängen.\n  - USB-Kabel und Strom während des Schreibens nicht trennen.\n"
             "  - Traktor und andere Audio-Programme vorher schließen.\n  - Benutzung auf eigene Gefahr, ohne Gewähr.\n",
             "\nWARNING\n  - The Z2 must be on its power supply.\n  - Do not unplug USB or power while writing.\n"
             "  - Close Traktor and other audio software first.\n  - Use at your own risk, without warranty.\n"),
    "confirm": ("Zum Schreiben bitte %s eintippen (alles andere bricht ab): ",
                "Type %s to write (anything else cancels): "),
    "yes_word": ("JA", "YES"),
    "cancel": ("Abgebrochen. Es wurde nichts geschrieben.", "Cancelled. Nothing was written."),
    "writing": ("Schreibe %d Bytes ...", "Writing %d bytes ..."),
    "progress": ("\r  %3d %%", "\r  %3d %%"),
    "restart": ("Starte den Z2 neu ...", "Restarting the Z2 ..."),
    "wait": ("Warte auf den Z2 ...", "Waiting for the Z2 ..."),
    "no_return": ("Der Z2 hat sich nach dem Neustart nicht wieder gemeldet. Bitte aus- und einschalten und das "
                  "Programm neu starten. Mit Menüpunkt 4 lässt sich das Backup zurückschreiben.",
                  "The Z2 did not come back after the restart. Switch it off and on and start this program again. "
                  "Menu item 4 writes the backup back."),
    "verify": ("Lese zur Kontrolle zurück ...", "Reading back for verification ..."),
    "verify_ok": ("Kontrolle bestanden: Die Firmware im Gerät ist Byte für Byte die erwartete.",
                  "Verification passed: the firmware in the device matches byte for byte."),
    "verify_bad": ("Kontrolle FEHLGESCHLAGEN: Die Firmware im Gerät weicht ab.",
                   "Verification FAILED: the firmware in the device differs."),
    "auto_restore": ("Schreibe jetzt automatisch das Backup zurück ...", "Writing the backup back automatically ..."),
    "restore_ok": ("Das Backup ist wieder im Gerät.", "The backup is back in the device."),
    "restore_bad": ("Auch das Zurückschreiben schlug fehl. Der Z2 startet in diesem Fall mit seiner Werks-Firmware "
                    "und bleibt per USB erreichbar. Bitte aus- und einschalten und Menüpunkt 4 wiederholen.\nBackup: %s",
                    "Writing the backup back failed as well. In that case the Z2 boots its factory firmware and "
                    "stays reachable over USB. Switch it off and on and repeat menu item 4.\nBackup: %s"),
    "done": ("\nFertig. Der Z2 läuft jetzt mit %s. Am iPad erscheint er als Audio- und MIDI-Gerät.\n"
             "Das passende djay-Mapping (Version 8) gibt es als eigenes Paket 'Z2-ReConnect-djay-Mapping'." % FW_NAME,
             "\nDone. The Z2 now runs %s. On an iPad it shows up as an audio and MIDI device.\n"
             "The matching djay mapping (version 8) comes as a separate package, 'Z2-ReConnect-djay-Mapping'." % FW_NAME),
    "restored": ("\nFertig. Das Backup ist zurückgeschrieben und geprüft.", "\nDone. The backup is written back and verified."),
    "no_backups": ("Keine Backups in %s gefunden.", "No backups found in %s."),
    "pick_backup": ("Welches Backup zurückschreiben? Nummer (Enter = Abbruch): ", "Which backup to write back? Number (Enter = cancel): "),
    "backup_corrupt": ("Diese Backup-Datei ist beschädigt oder kein Z2-Abbild (%s). Sie wird nicht geschrieben.",
                       "This backup file is damaged or not a Z2 image (%s). It will not be written."),
    "same_already": ("Diese Firmware ist bereits im Gerät. Es ist nichts zu tun.", "This firmware is already in the device. Nothing to do."),
    "err": ("FEHLER: %s", "ERROR: %s"),
    "enter": ("\nEnter zum Beenden ...", "\nPress Enter to quit ..."),
    "need_usb": ("Für macOS/Linux fehlt das Python-Paket 'pyusb' bzw. 'libusb-package' (pip install pyusb libusb-package).",
                 "On macOS/Linux the Python packages 'pyusb' and 'libusb-package' are required (pip install pyusb libusb-package)."),
}
LANG = 0

# Shown in English before every installation, whatever language is set. Only "I UNDERSTAND" continues.
DISCLAIMER = """
==============================================================================
  PLEASE READ BEFORE FLASHING
==============================================================================
  Z² Re:Connect is a private, non-commercial hobby project. Its only purpose
  is to keep old but good hardware - the Traktor Kontrol Z2 - in use with
  today's devices such as the iPad.

  - It is not affiliated with, endorsed or supported by Native Instruments.
  - There is no commercial background. Nothing is sold, nothing is offered
    as a product or service.
  - There is NO WARRANTY of any kind. You use this software and firmware
    entirely at your own risk. Nobody accepts any liability for damage to
    your device, loss of data or any other consequence.
  - Flashing a modified firmware can, in rare cases, leave a device unusable.

  If you do not know what you need this firmware for, do NOT install it.
==============================================================================
"""
DISCLAIMER_WORD = "I UNDERSTAND"


def t(key, *a):
    s = T[key][LANG]
    return s % a if a else s


def say(key, *a):
    print(t(key, *a), flush=True)


class Z2Error(Exception):
    pass


# ----------------------------------------------------------------------------- Patch
def load_patch(path):
    raw = open(path, "rb").read()
    if raw[:8] != b"Z2PATCH1": raise Z2Error("bad patch file")
    n = struct.unpack_from("<I", raw, 8)[0]
    return json.loads(raw[12:12 + n].decode()), zlib.decompress(raw[12 + n:])


def apply_patch(head, body, src):
    """Baut das Ziel-Abbild. Gibt None zurueck, wenn Quelle oder Ergebnis nicht exakt passen."""
    if len(src) != head["source_size"] or hashlib.sha256(src).hexdigest() != head["source_sha256"]: return None
    out, i = bytearray(), 0
    while i < len(body):
        if body[i] == 0:
            off, n = struct.unpack_from("<II", body, i + 1); i += 9
            if off + n > len(src): return None
            out += src[off:off + n]
        elif body[i] == 1:
            n = struct.unpack_from("<I", body, i + 1)[0]; i += 5
            out += body[i:i + n]; i += n
        else:
            return None
    out = bytes(out)
    if len(out) != head["target_size"] or hashlib.sha256(out).hexdigest() != head["target_sha256"]: return None
    return out


def _here():
    return [getattr(sys, "_MEIPASS", ""), os.path.dirname(os.path.abspath(sys.argv[0])), os.path.dirname(os.path.abspath(__file__))]


def find_patches():
    """Alle Patch-Dateien des ersten Ordners, der welche hat. Alle muessen dasselbe Ziel-Abbild bauen."""
    for d in _here():
        ps = sorted(glob.glob(os.path.join(d, "*.z2patch")))
        if ps:
            pats = [load_patch(p) for p in ps]
            if len({h["target_sha256"] for h, _ in pats}) != 1: raise Z2Error("patch files build different targets")
            return pats
    raise Z2Error("patch file (*.z2patch) not found next to the program")


def find_file(name):
    for d in _here():
        p = os.path.join(d, name)
        if d and os.path.isfile(p): return p
    return None


def load_intro_frames():
    """intro.frames: b"Z2FRAMES", Anzahl, Bilddauer in ms, dann je Bild Laenge + PNG. Rueckgabe (pngs, ms) oder None."""
    p = find_file("intro.frames")
    if not p: return None
    raw = open(p, "rb").read()
    if raw[:8] != b"Z2FRAMES": return None
    n, ms = struct.unpack_from("<II", raw, 8)
    o, out = 16, []
    for _ in range(n):
        ln = struct.unpack_from("<I", raw, o)[0]; o += 4
        out.append(raw[o:o + ln]); o += ln
    return out, ms


_REV = bytes(int("{:08b}".format(b)[::-1], 2) for b in range(256))


def image_problems(img):
    """Pruefungen am Abbild selbst (XMOS-Upgrade-Abbild, jedes Byte bit-gespiegelt)."""
    if len(img) < 64 or len(img) > MAX_IMAGE: return "size %d" % len(img)
    if len(img) % XFER: return "length not a multiple of %d" % XFER
    plain = bytes(_REV[b] for b in img[:16])
    tag, size = struct.unpack_from("<I", plain, 0)[0], struct.unpack_from("<I", plain, 12)[0]
    if tag != 0x1A551E5: return "tag %08x" % tag
    if not 0 < size <= len(img): return "size field %d" % size
    for o in range(0, len(img) - 255, 256):
        if img[o:o + 256] == b"\xff" * 256: return "empty page at %#x" % o
    return None


# ----------------------------------------------------------------------------- Geraete-Zugriff
class WinBackend:
    """Windows: ueber den installierten NI-Treiber (Geraete-IOCTLs)."""
    I_INFO, I_DNLOAD, I_UPLOAD, I_GETSTATUS, I_CLRSTATUS, I_GETSTATE, I_RESET, I_GETDESC = \
        0x80862400, 0x80862408, 0x8086240C, 0x80862410, 0x80862414, 0x80862418, 0x80862424, 0x80892004

    def __init__(self):
        import ctypes, ctypes.wintypes as wt
        self.ct, self.wt = ctypes, wt
        self.k32 = ctypes.WinDLL("kernel32", use_last_error=True)
        self.sa = ctypes.WinDLL("setupapi", use_last_error=True)
        class GUID(ctypes.Structure):
            _fields_ = [("d1", wt.DWORD), ("d2", wt.WORD), ("d3", wt.WORD), ("d4", ctypes.c_ubyte * 8)]
        class SPDID(ctypes.Structure):
            _fields_ = [("cbSize", wt.DWORD), ("g", GUID), ("Flags", wt.DWORD), ("r", ctypes.c_void_p)]
        self.GUID, self.SPDID = GUID, SPDID
        self.guid = GUID(0x938FA945, 0xD818, 0x48A1, (ctypes.c_ubyte * 8)(0xBE, 0x66, 0x69, 0x21, 0xB0, 0xD6, 0x49, 0xCF))
        self.sa.SetupDiGetClassDevsW.restype = ctypes.c_void_p
        self.sa.SetupDiGetClassDevsW.argtypes = [ctypes.POINTER(GUID), wt.LPCWSTR, wt.HWND, wt.DWORD]
        self.sa.SetupDiEnumDeviceInterfaces.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.POINTER(GUID), wt.DWORD, ctypes.POINTER(SPDID)]
        self.sa.SetupDiGetDeviceInterfaceDetailW.argtypes = [ctypes.c_void_p, ctypes.POINTER(SPDID), ctypes.c_void_p, wt.DWORD, ctypes.POINTER(wt.DWORD), ctypes.c_void_p]
        self.sa.SetupDiDestroyDeviceInfoList.argtypes = [ctypes.c_void_p]
        self.k32.CreateFileW.restype = wt.HANDLE
        self.k32.CreateFileW.argtypes = [wt.LPCWSTR, wt.DWORD, wt.DWORD, ctypes.c_void_p, wt.DWORD, wt.DWORD, wt.HANDLE]
        self.k32.DeviceIoControl.argtypes = [wt.HANDLE, wt.DWORD, ctypes.c_void_p, wt.DWORD, ctypes.c_void_p, wt.DWORD, ctypes.POINTER(wt.DWORD), ctypes.c_void_p]
        self.k32.CloseHandle.argtypes = [wt.HANDLE]
        self.h = None

    def _paths(self):
        ct, wt = self.ct, self.wt
        hs = self.sa.SetupDiGetClassDevsW(ct.byref(self.guid), None, None, 0x12)
        out, i = [], 0
        while True:
            d = self.SPDID(); d.cbSize = ct.sizeof(d)
            if not self.sa.SetupDiEnumDeviceInterfaces(hs, None, ct.byref(self.guid), i, ct.byref(d)): break
            i += 1; need = wt.DWORD()
            self.sa.SetupDiGetDeviceInterfaceDetailW(hs, ct.byref(d), None, 0, ct.byref(need), None)
            buf = ct.create_string_buffer(need.value); struct.pack_into("I", buf, 0, 8)
            if self.sa.SetupDiGetDeviceInterfaceDetailW(hs, ct.byref(d), buf, need, None, None):
                out.append(ct.wstring_at(ct.addressof(buf) + 4))
        self.sa.SetupDiDestroyDeviceInfoList(hs)
        low = [p.lower() for p in out]
        return [p for p, l in zip(out, low) if "vid_17cc" in l and (("pid_1130" in l and "mi_03" in l) or "pid_1132" in l)]

    def count(self):
        return len(self._paths())

    def open(self):
        self.close()
        ps = self._paths()
        if len(ps) != 1: raise Z2Error("nodev" if not ps else "multi")
        h = self.k32.CreateFileW(ps[0], 0xC0000000, 3, None, 3, 0, None)
        if h in (None, self.wt.HANDLE(-1).value): raise Z2Error("open failed (%d)" % self.ct.get_last_error())
        self.h = h
        dd = self._io(self.I_GETDESC, struct.pack("<IBBH", 0, 1, 0, 0), 18)
        vid, pid, bcd = struct.unpack_from("<HHH", dd, 8)
        return {"vid": vid, "pid": pid, "bcd": bcd}

    def close(self):
        if self.h: self.k32.CloseHandle(self.h); self.h = None

    def _io(self, code, inb=b"", outlen=0):
        ct = self.ct
        ib = ct.create_string_buffer(inb, len(inb)) if inb else None
        ob = ct.create_string_buffer(outlen) if outlen else None
        got = self.wt.DWORD()
        if not self.k32.DeviceIoControl(self.h, code, ib, len(inb), ob, outlen, ct.byref(got), None):
            raise OSError("device request %08x failed (%d)" % (code, ct.get_last_error()))
        return ob.raw[:got.value] if ob else b""

    def get_state(self): return self._io(self.I_GETSTATE, outlen=1)[0]
    def get_status(self): return self._io(self.I_GETSTATUS, outlen=6)
    def clr_status(self): self._io(self.I_CLRSTATUS)
    def upload(self, block): return self._io(self.I_UPLOAD, struct.pack("<H", block), XFER)
    def dnload(self, block, data): self._io(self.I_DNLOAD, struct.pack("<HH", block, len(data)) + data + bytes(512 - len(data)))
    def reset(self):
        try: self._io(self.I_RESET)
        except OSError: pass                      # the device drops off the bus while answering


class UsbBackend:
    """macOS / Linux: USB-DFU-Anfragen direkt ueber libusb (pyusb)."""
    def __init__(self):
        try:
            import usb.core, usb.util
        except ImportError:
            raise Z2Error(t("need_usb"))
        self.usb = usb
        try:
            import libusb_package
            self._find = libusb_package.find
        except ImportError:
            self._find = usb.core.find
        self.dev, self.intf = None, None

    def _devs(self):
        return [d for d in self._find(find_all=True, idVendor=VID) if d.idProduct in (PID_RUN, PID_DFU)]

    def count(self):
        return len(self._devs())

    def open(self):
        self.close()
        ds = self._devs()
        if len(ds) != 1: raise Z2Error("nodev" if not ds else "multi")
        self.dev = ds[0]
        self.intf = None
        for cfg in self.dev:
            for i in cfg:
                if i.bInterfaceClass == 0xFE and i.bInterfaceSubClass == 1: self.intf = i.bInterfaceNumber
        if self.intf is None: raise Z2Error("no DFU interface")
        try:
            if self.dev.is_kernel_driver_active(self.intf): self.dev.detach_kernel_driver(self.intf)
        except (NotImplementedError, self.usb.core.USBError):
            pass
        try: self.usb.util.claim_interface(self.dev, self.intf)
        except self.usb.core.USBError: pass
        return {"vid": self.dev.idVendor, "pid": self.dev.idProduct, "bcd": self.dev.bcdDevice}

    def close(self):
        if self.dev is not None:
            try: self.usb.util.dispose_resources(self.dev)
            except Exception: pass
        self.dev = None

    def _out(self, req, value, data=b""):
        try: self.dev.ctrl_transfer(0x21, req, value, self.intf, data, 5000)
        except self.usb.core.USBError as e: raise OSError(str(e))

    def _in(self, req, value, n):
        try: return bytes(self.dev.ctrl_transfer(0xA1, req, value, self.intf, n, 5000))
        except self.usb.core.USBError as e: raise OSError(str(e))

    def get_state(self): return self._in(5, 0, 1)[0]
    def get_status(self): return self._in(3, 0, 6)
    def clr_status(self): self._out(4, 0)
    def upload(self, block): return self._in(2, block, XFER)
    def dnload(self, block, data): self._out(1, block, data)
    def reset(self):
        try: self._out(0xF0, 0)                   # XMOS: restart
        except OSError: pass


def make_backend():
    return WinBackend() if sys.platform == "win32" else UsbBackend()


# ----------------------------------------------------------------------------- Ablauf
class Installer:
    def __init__(self, backend, backup_dir, ask=input, sleep=time.sleep):
        self.b, self.backup_dir, self.ask, self.sleep = backend, backup_dir, ask, sleep
        self.on_progress = None                   # GUI: Fortschritt 0..100 beim Schreiben
        self.last_backup = None
        self.patches = find_patches()
        self.target_sha = self.patches[0][0]["target_sha256"]

    # --- Geraet
    def connect(self):
        try:
            info = self.b.open()
        except Z2Error as e:
            if str(e) == "nodev":
                raise Z2Error(t("nodev") + ("\n" + t("nodev_win") if sys.platform == "win32" else ""))
            if str(e) == "multi": raise Z2Error(t("multi"))
            raise
        if info["vid"] != VID or info["pid"] not in (PID_RUN, PID_DFU): raise Z2Error(t("nodev"))
        say("found", info["vid"], info["pid"], info["bcd"])
        return info

    def _idle(self):
        """Bringt die DFU-Schnittstelle in den Ruhezustand (nach dem Start steht sie oft auf dfuERROR)."""
        for _ in range(5):
            try: st = self.b.get_state()
            except OSError: st = STATE_ERROR
            if st in (0, STATE_IDLE): return
            try: self.b.clr_status()
            except OSError: pass
            self.sleep(0.5)

    def _read_once(self):
        self._idle()
        data, block = bytearray(), 0
        while True:
            chunk = self.b.upload(block)
            data += chunk; block += 1
            if len(chunk) < XFER: break
            if len(data) > MAX_IMAGE: raise Z2Error("image too large")
        self._idle()
        return bytes(data)

    def read_firmware(self, passes=2):
        """Liest die Firmware; direkt nach dem Start liefert der Z2 manchmal 0 Bytes, dann nochmal versuchen."""
        got = []
        for n in range(passes):
            say("reading", n + 1)
            data = b""
            for attempt in range(4):
                try:
                    data = self._read_once()
                except OSError as e:
                    if attempt == 3: raise Z2Error(t("read_fail", e))
                    data = b""
                if data: break
                self.sleep(3)
            if not data: raise Z2Error(t("read_empty"))
            got.append(data)
        if any(g != got[0] for g in got): raise Z2Error(t("read_diff"))
        return got[0]

    def classify(self, img):
        """target: neue Firmware schon drin · source: NI-Firmware 42 · older: aeltere Z² Re:Connect-Version · unknown"""
        sha = hashlib.sha256(img).hexdigest()
        if sha == self.target_sha: return "target"
        for h, _ in self.patches:
            if sha == h["source_sha256"]: return "source" if sha == NI42_SHA256 else "older"
        return "unknown"

    def build(self, img):
        sha = hashlib.sha256(img).hexdigest()
        for h, body in self.patches:
            if sha == h["source_sha256"]: return apply_patch(h, body, img)
        return None

    # --- Pruefung
    def check(self, quiet_backup=False):
        """Sicherheitspruefung. Schreibt nichts auf den Z2. Rueckgabe: (art, abbild, neues_abbild).
        Die gelesene Firmware wird IMMER sofort als Backup gespeichert (Pflicht, nicht abschaltbar).
        Klappt das nicht, bricht die Pruefung mit Fehler ab, und es kann nichts installiert werden."""
        self.connect()
        img = self.read_firmware()
        self.save_backup(img)
        kind = self.classify(img)
        new = self.build(img) if kind in ("source", "older") else None
        say("fw_is", t(KIND_TEXT[kind]),
            len(img), hashlib.sha256(img).hexdigest())
        results = [("c_dev", True), ("c_read", True), ("c_backup", True), ("c_struct", image_problems(img) is None)]
        if kind != "target":
            results += [("c_known", kind in ("source", "older")),
                        ("c_build", new is not None and image_problems(new) is None)]
        for key, good in results: print(t("ok" if good else "bad") + t(key))
        if kind == "target": say("verdict_done")
        elif all(g for _, g in results): say("verdict_update" if kind == "older" else "verdict_ok")
        else:
            say("verdict_no"); new = None
            kind = "unknown"
        return kind, img, new

    # --- Backup
    def save_backup(self, img):
        os.makedirs(self.backup_dir, exist_ok=True)
        sha = hashlib.sha256(img).hexdigest()
        for p in glob.glob(os.path.join(self.backup_dir, "*_%s.z2backup" % sha[:12])):
            if open(p, "rb").read() == img:
                say("backup_same", p); self.last_backup = p; return p
        path = os.path.join(self.backup_dir, "Z2_%s_%s.z2backup" % (time.strftime("%Y-%m-%d_%H%M%S"), sha[:12]))
        with open(path, "wb") as f: f.write(img)
        if open(path, "rb").read() != img: raise Z2Error("backup file could not be written correctly")
        with open(path + ".txt", "w", encoding="utf-8") as f:
            f.write("Traktor Kontrol Z2 firmware backup\nsha256 %s\nbytes %d\nfirmware %s\n" %
                    (sha, len(img), self.classify(img)))
        say("backup_saved", path)
        self.last_backup = path
        return path

    def backup(self):
        self.connect()
        return self.save_backup(self.read_firmware())

    # --- Schreiben
    def _wait(self, want, timeout):
        t0 = time.time()
        while True:
            st = self.b.get_status()
            if st[0] != 0: raise Z2Error("DFU status %d, state %d" % (st[0], st[4]))
            if st[4] in want: return st[4]
            if time.time() - t0 > timeout: raise Z2Error("timeout, state %d" % st[4])
            self.sleep(max(st[1] | st[2] << 8 | st[3] << 16, 1) / 1000.0)

    def write(self, img):
        """Schreibt ein Abbild. Der Werks-Bereich des Z2 wird dabei nie beruehrt."""
        if image_problems(img): raise Z2Error("image check failed: %s" % image_problems(img))
        self._idle()
        say("writing", len(img))
        n = len(img) // XFER
        for blk in range(n):
            self.b.dnload(blk, img[blk * XFER:(blk + 1) * XFER])
            self._wait((STATE_DNLOAD_IDLE,), 20)
            if blk % 16 == 0 or blk == n - 1:
                if self.on_progress: self.on_progress((blk + 1) * 100 // n)
                else: sys.stdout.write(t("progress", (blk + 1) * 100 // n)); sys.stdout.flush()
        if not self.on_progress: print()
        self.b.dnload(n, b"")
        st = self._wait((STATE_IDLE, 7, 8), 60)
        if st != STATE_IDLE:
            try: self.b.clr_status()
            except OSError: pass

    def restart(self):
        say("restart")
        self.b.reset(); self.b.close()
        self.sleep(4)
        say("wait")
        for _ in range(30):
            try:
                if self.b.count() == 1:
                    self.sleep(2); self.b.open(); return True
            except (OSError, Z2Error):
                pass
            self.sleep(1)
        return False

    def write_and_verify(self, img):
        self.write(img)
        if not self.restart(): raise Z2Error(t("no_return"))
        say("verify")
        back = self.read_firmware(passes=1)
        return back == img

    def accept_disclaimer(self):
        print(DISCLAIMER)
        a = self.ask("Type %s to continue (anything else cancels): " % DISCLAIMER_WORD)
        return " ".join(a.strip().upper().split()) == DISCLAIMER_WORD

    def confirm(self):
        print(t("warn"))
        return self.ask(t("confirm", t("yes_word"))).strip().upper() == t("yes_word")

    def install(self):
        kind, img, new = self.check()
        if kind == "target": return True
        if new is None: return False
        backup_path = self.last_backup                  # von check() gespeichert
        if not backup_path or not os.path.isfile(backup_path) or open(backup_path, "rb").read() != img:
            raise Z2Error("no valid backup - nothing written")
        if not self.accept_disclaimer():
            say("cancel"); return False
        if not self.confirm():
            say("cancel"); return False
        try:
            good = self.write_and_verify(new)
        except (OSError, Z2Error) as e:
            say("err", e); good = False
            reachable = False
            try: reachable = self.b.count() == 1
            except OSError: pass
            if not reachable:                      # nichts erreichbar: kein automatischer Versuch
                say("backup_saved", backup_path); return False
        if good:
            say("verify_ok"); say("done"); return True
        say("verify_bad"); say("auto_restore")
        try:
            self.connect()
            if self.write_and_verify(img):
                say("restore_ok"); return False
        except (OSError, Z2Error) as e:
            say("err", e)
        say("restore_bad", backup_path)
        return False

    def restore(self, path=None):
        if path is None:
            files = sorted(glob.glob(os.path.join(self.backup_dir, "*.z2backup")))
            if not files:
                say("no_backups", self.backup_dir); return False
            for i, p in enumerate(files):
                img = open(p, "rb").read()
                kind = t(KIND_TEXT[self.classify(img)])
                print("  %d  %s  (%s)" % (i + 1, os.path.basename(p), kind))
            a = self.ask(t("pick_backup")).strip()
            if not a.isdigit() or not 1 <= int(a) <= len(files):
                say("cancel"); return False
            path = files[int(a) - 1]
        img = open(path, "rb").read()
        prob = image_problems(img)
        name = os.path.basename(path)
        if prob is None and name.endswith(".z2backup") and "_" in name:      # Dateiname traegt die Pruefsumme
            if name[:-9].rsplit("_", 1)[1] != hashlib.sha256(img).hexdigest()[:12]: prob = "checksum"
        if prob:
            say("backup_corrupt", prob); return False
        self.connect()
        current = self.read_firmware()
        if current == img:
            say("same_already"); return True
        self.save_backup(current)                  # auch der Stand vor dem Zurueckschreiben wird gesichert
        if not self.confirm():
            say("cancel"); return False
        if self.write_and_verify(img):
            say("verify_ok"); say("restored"); return True
        say("verify_bad")
        return False


KIND_TEXT = {"source": "fw_source", "target": "fw_target", "older": "fw_older", "unknown": "fw_unknown"}


def default_backup_dir():
    return os.path.join(os.path.expanduser("~"), "Documents", "Z2-Firmware-Backup")


def main(argv=None, backend=None, ask=input):
    global LANG
    argv = list(sys.argv[1:] if argv is None else argv)
    lang = (locale.getlocale()[0] or os.environ.get("LANG") or "en").lower()
    backup_dir, interactive = default_backup_dir(), False
    intro = backend is None and "--no-intro" not in argv
    if "--no-intro" in argv: argv.remove("--no-intro")
    cli = "--cli" in argv or backend is not None
    if "--cli" in argv: argv.remove("--cli")
    if "--lang" in argv:
        i = argv.index("--lang"); lang = argv[i + 1]; del argv[i:i + 2]
    if "--backup-dir" in argv:
        i = argv.index("--backup-dir"); backup_dir = argv[i + 1]; del argv[i:i + 2]
    LANG = 0 if lang.startswith(("de", "german")) else 1
    if not argv and not cli:
        try:
            import z2_gui
        except Exception:
            z2_gui = None
        if z2_gui is not None and z2_gui.available():
            return z2_gui.run(sys.modules[__name__], backup_dir, intro)
    say("title", VERSION)
    ok = False
    try:
        inst = Installer(backend or make_backend(), backup_dir, ask)
        cmd = argv[0] if argv else None
        if cmd is None:
            interactive = True
            while True:
                print(t("menu"))
                c = ask(t("choice")).strip()
                try:
                    if c == "1": inst.check()
                    elif c == "2": inst.backup()
                    elif c == "3": inst.install()
                    elif c == "4": inst.restore()
                    elif c == "5": ok = True; break
                except (Z2Error, OSError) as e:
                    say("err", e)
                finally:
                    inst.b.close()
        elif cmd == "check": ok = inst.check()[0] in ("source", "older", "target")
        elif cmd == "backup": ok = bool(inst.backup())
        elif cmd == "install": ok = inst.install()
        elif cmd == "restore": ok = inst.restore(argv[1] if len(argv) > 1 else None)
        else: print(__doc__)
    except (Z2Error, OSError) as e:
        say("err", e)
    except (KeyboardInterrupt, EOFError):
        print()
    if interactive or getattr(sys, "frozen", False) and not argv:
        try: ask(t("enter"))
        except (KeyboardInterrupt, EOFError): pass
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
