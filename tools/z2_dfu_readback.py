"""Read back the Z2's firmware (DFU upgrade image) through the installed NI driver (nikz2usb.sys).

READ-ONLY BY CONSTRUCTION: only the IOCTLs in ALLOWED can be sent. DFU_DNLOAD (0x80862408),
XMOS reset (0x80862424) and XMOS revert-to-factory (0x80862428, would erase the upgrade image)
are not reachable from this script.

  python z2_dfu_readback.py info            -> GET_DFU_INFO + GETSTATE on every Z2 node
  python z2_dfu_readback.py upload out.bin  -> upload in the current mode (no mode change)
  python z2_dfu_readback.py enter           -> XMOS 0xF2: reboot into DFU mode (PID 0x1132)
  python z2_dfu_readback.py leave           -> XMOS 0xF3: reboot back to normal mode
"""
import ctypes, ctypes.wintypes as wt, struct, sys, time, hashlib

IOCTL = {
    "INFO": 0x80862400, "ENTER_DFU_F2": 0x80862404, "UPLOAD": 0x8086240C, "GETSTATUS": 0x80862410,
    "GETSTATE": 0x80862418, "CLRSTATUS": 0x80862414, "ABORT": 0x8086241C, "LEAVE_DFU_F3": 0x80862420, "GETDESC": 0x80892004,
}
ALLOWED = set(IOCTL.values())
STATES = {0: "appIDLE", 1: "appDETACH", 2: "dfuIDLE", 3: "dfuDNLOAD-SYNC", 4: "dfuDNBUSY", 5: "dfuDNLOAD-IDLE",
          6: "dfuMANIFEST-SYNC", 7: "dfuMANIFEST", 8: "dfuMANIFEST-WAIT-RESET", 9: "dfuUPLOAD-IDLE", 10: "dfuERROR"}

setupapi = ctypes.WinDLL("setupapi", use_last_error=True); k32 = ctypes.WinDLL("kernel32", use_last_error=True)
class GUID(ctypes.Structure):
    _fields_ = [("d1", wt.DWORD), ("d2", wt.WORD), ("d3", wt.WORD), ("d4", ctypes.c_ubyte * 8)]
class SP_DID(ctypes.Structure):
    _fields_ = [("cbSize", wt.DWORD), ("g", GUID), ("Flags", wt.DWORD), ("r", ctypes.c_void_p)]
NI_GUID = GUID(0x938FA945, 0xD818, 0x48A1, (ctypes.c_ubyte * 8)(0xBE, 0x66, 0x69, 0x21, 0xB0, 0xD6, 0x49, 0xCF))
setupapi.SetupDiGetClassDevsW.restype = ctypes.c_void_p
setupapi.SetupDiGetClassDevsW.argtypes = [ctypes.POINTER(GUID), wt.LPCWSTR, wt.HWND, wt.DWORD]
setupapi.SetupDiEnumDeviceInterfaces.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.POINTER(GUID), wt.DWORD, ctypes.POINTER(SP_DID)]
setupapi.SetupDiGetDeviceInterfaceDetailW.argtypes = [ctypes.c_void_p, ctypes.POINTER(SP_DID), ctypes.c_void_p, wt.DWORD, ctypes.POINTER(wt.DWORD), ctypes.c_void_p]
setupapi.SetupDiDestroyDeviceInfoList.argtypes = [ctypes.c_void_p]
k32.CreateFileW.restype = wt.HANDLE
k32.DeviceIoControl.argtypes = [wt.HANDLE, wt.DWORD, ctypes.c_void_p, wt.DWORD, ctypes.c_void_p, wt.DWORD, ctypes.POINTER(wt.DWORD), ctypes.c_void_p]
k32.CloseHandle.argtypes = [wt.HANDLE]


def paths():
    h = setupapi.SetupDiGetClassDevsW(ctypes.byref(NI_GUID), None, None, 0x12)
    out, i = [], 0
    while True:
        d = SP_DID(); d.cbSize = ctypes.sizeof(d)
        if not setupapi.SetupDiEnumDeviceInterfaces(h, None, ctypes.byref(NI_GUID), i, ctypes.byref(d)): break
        i += 1; need = wt.DWORD()
        setupapi.SetupDiGetDeviceInterfaceDetailW(h, ctypes.byref(d), None, 0, ctypes.byref(need), None)
        buf = ctypes.create_string_buffer(need.value); struct.pack_into("I", buf, 0, 8)
        if setupapi.SetupDiGetDeviceInterfaceDetailW(h, ctypes.byref(d), buf, need, None, None):
            out.append(ctypes.wstring_at(ctypes.addressof(buf) + 4))
    setupapi.SetupDiDestroyDeviceInfoList(h)
    return out


class Dev:
    def __init__(self, path):
        self.path = path
        self.h = k32.CreateFileW(path, 0xC0000000, 3, None, 3, 0, None)
        if self.h in (None, wt.HANDLE(-1).value): raise OSError("open failed %d: %s" % (ctypes.get_last_error(), path))
    def ioctl(self, code, inb=b"", outlen=0):
        if code not in ALLOWED: raise PermissionError("IOCTL %08x is blocked (read-only tool)" % code)
        ib = ctypes.create_string_buffer(inb, len(inb)) if inb else None
        ob = ctypes.create_string_buffer(outlen) if outlen else None
        got = wt.DWORD()
        ok = k32.DeviceIoControl(self.h, code, ib, len(inb), ob, outlen, ctypes.byref(got), None)
        if not ok: raise OSError("IOCTL %08x failed, error %d" % (code, ctypes.get_last_error()))
        return ob.raw[:got.value] if ob else b""
    def close(self): k32.CloseHandle(self.h)
    def info(self):
        r = self.ioctl(IOCTL["INFO"], outlen=7)
        mode, attr, detach, xfer = struct.unpack_from("<BBHH", r)
        return {"mode": mode, "raw_mode": r[6] if len(r) > 6 else None, "attr": attr, "detach_ms": detach, "xfer": xfer}
    def state(self): return self.ioctl(IOCTL["GETSTATE"], outlen=1)[0]
    def status(self):
        r = self.ioctl(IOCTL["GETSTATUS"], outlen=6)
        return {"bStatus": r[0], "pollMs": r[1] | r[2] << 8 | r[3] << 16, "state": r[4]}
    def devdesc(self): return self.ioctl(IOCTL["GETDESC"], struct.pack("<IBBH", 0, 1, 0, 0), 18)


def dfu_nodes():
    res = []
    for p in paths():
        try:
            d = Dev(p); i = d.info(); res.append((d, i))
        except OSError as e:
            print("  skip", p[:70], e)
    return res


def cmd_info():
    for d, i in dfu_nodes():
        dd = d.devdesc()
        vid, pid, bcd = struct.unpack_from("<HHH", dd, 8)
        try: st = STATES.get(d.state(), "?")
        except OSError as e: st = str(e)
        print(d.path[:90]); print("   VID %04x PID %04x bcd %04x  info %s  state %s" % (vid, pid, bcd, i, st))
        d.close()


def pick():
    nodes = dfu_nodes()
    for d, i in nodes:
        if "mi_03" in d.path.lower() or "pid_1132" in d.path.lower():
            for o, _ in nodes:
                if o is not d: o.close()
            return d, i
    if nodes: return nodes[0]
    sys.exit("no Z2 DFU node found")


def cmd_upload(out):
    d, i = pick(); print("using", d.path[:90], i)
    xfer = i["xfer"] or 64
    data = bytearray(); block = 0; t0 = time.time()
    while True:
        try:
            chunk = d.ioctl(IOCTL["UPLOAD"], struct.pack("<H", block), xfer)
        except OSError as e:
            print("upload stopped at block %d: %s" % (block, e)); break
        data += chunk; block += 1
        if block % 256 == 0: print("  %d KB" % (len(data) // 1024), flush=True)
        if len(chunk) < xfer: break
        if len(data) > 8 * 1024 * 1024: print("safety stop at 8 MB"); break
    try: print("status after upload:", d.status())
    except OSError as e: print("status:", e)
    d.close()
    open(out, "wb").write(data)
    print("saved %d bytes to %s in %.1fs  sha256 %s" % (len(data), out, time.time() - t0, hashlib.sha256(data).hexdigest()))


def cmd_simple(name):
    d, i = pick(); print("using", d.path[:90], i)
    try: d.ioctl(IOCTL[name]); print(name, "sent")
    except OSError as e: print(name, "->", e)
    d.close()


if __name__ == "__main__":
    c = sys.argv[1] if len(sys.argv) > 1 else "info"
    if c == "info": cmd_info()
    elif c == "upload": cmd_upload(sys.argv[2])
    elif c == "enter": cmd_simple("ENTER_DFU_F2")
    elif c == "leave": cmd_simple("LEAVE_DFU_F3")
    elif c == "clear": cmd_simple("CLRSTATUS")
    else: sys.exit(__doc__)
