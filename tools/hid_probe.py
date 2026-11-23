"""Read-only HID probe for the Z2 vendor HID interface (MI_04).

  python hid_probe.py caps            -> report IDs, sizes, value/button caps (JSON)
  python hid_probe.py watch [sec]     -> print every input report that changes (move knobs/faders/buttons)
  python hid_probe.py record out.jsonl [sec] -> save raw input reports with timestamps

Only reads. Uses Windows hid.dll; shares the device with the NI driver.
"""
import ctypes, ctypes.wintypes as wt, sys, json, time, struct

hid = ctypes.WinDLL("hid"); setupapi = ctypes.WinDLL("setupapi", use_last_error=True); k32 = ctypes.WinDLL("kernel32", use_last_error=True)

class GUID(ctypes.Structure):
    _fields_ = [("d1", wt.DWORD), ("d2", wt.WORD), ("d3", wt.WORD), ("d4", ctypes.c_ubyte * 8)]
class SP_DID(ctypes.Structure):
    _fields_ = [("cbSize", wt.DWORD), ("g", GUID), ("Flags", wt.DWORD), ("r", ctypes.c_void_p)]
class ATTR(ctypes.Structure):
    _fields_ = [("Size", wt.ULONG), ("VendorID", wt.USHORT), ("ProductID", wt.USHORT), ("Version", wt.USHORT)]
class CAPS(ctypes.Structure):
    _fields_ = [("Usage", wt.USHORT), ("UsagePage", wt.USHORT), ("InLen", wt.USHORT), ("OutLen", wt.USHORT), ("FeatLen", wt.USHORT),
                ("Res", wt.USHORT * 17), ("nLinkColl", wt.USHORT), ("nInBtn", wt.USHORT), ("nInVal", wt.USHORT), ("nInData", wt.USHORT),
                ("nOutBtn", wt.USHORT), ("nOutVal", wt.USHORT), ("nOutData", wt.USHORT), ("nFeatBtn", wt.USHORT), ("nFeatVal", wt.USHORT), ("nFeatData", wt.USHORT)]
class RANGE(ctypes.Structure):
    _fields_ = [("UsageMin", wt.USHORT), ("UsageMax", wt.USHORT), ("StringMin", wt.USHORT), ("StringMax", wt.USHORT),
                ("DesigMin", wt.USHORT), ("DesigMax", wt.USHORT), ("DataIndexMin", wt.USHORT), ("DataIndexMax", wt.USHORT)]
class VCAPS(ctypes.Structure):
    _fields_ = [("UsagePage", wt.USHORT), ("ReportID", ctypes.c_ubyte), ("IsAlias", ctypes.c_ubyte), ("BitField", wt.USHORT), ("LinkCollection", wt.USHORT),
                ("LinkUsage", wt.USHORT), ("LinkUsagePage", wt.USHORT), ("IsRange", ctypes.c_ubyte), ("IsStringRange", ctypes.c_ubyte), ("IsDesignatorRange", ctypes.c_ubyte),
                ("IsAbsolute", ctypes.c_ubyte), ("HasNull", ctypes.c_ubyte), ("Reserved", ctypes.c_ubyte), ("BitSize", wt.USHORT), ("ReportCount", wt.USHORT),
                ("Reserved2", wt.USHORT * 5), ("UnitsExp", wt.ULONG), ("Units", wt.ULONG), ("LogicalMin", ctypes.c_long), ("LogicalMax", ctypes.c_long),
                ("PhysicalMin", ctypes.c_long), ("PhysicalMax", ctypes.c_long), ("u", RANGE)]
class BCAPS(ctypes.Structure):
    _fields_ = [("UsagePage", wt.USHORT), ("ReportID", ctypes.c_ubyte), ("IsAlias", ctypes.c_ubyte), ("BitField", wt.USHORT), ("LinkCollection", wt.USHORT),
                ("LinkUsage", wt.USHORT), ("LinkUsagePage", wt.USHORT), ("IsRange", ctypes.c_ubyte), ("IsStringRange", ctypes.c_ubyte), ("IsDesignatorRange", ctypes.c_ubyte),
                ("IsAbsolute", ctypes.c_ubyte), ("Reserved", wt.ULONG * 10), ("u", RANGE)]

setupapi.SetupDiGetClassDevsW.restype = ctypes.c_void_p
setupapi.SetupDiGetClassDevsW.argtypes = [ctypes.POINTER(GUID), wt.LPCWSTR, wt.HWND, wt.DWORD]
setupapi.SetupDiEnumDeviceInterfaces.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.POINTER(GUID), wt.DWORD, ctypes.POINTER(SP_DID)]
setupapi.SetupDiGetDeviceInterfaceDetailW.argtypes = [ctypes.c_void_p, ctypes.POINTER(SP_DID), ctypes.c_void_p, wt.DWORD, ctypes.POINTER(wt.DWORD), ctypes.c_void_p]
k32.CreateFileW.restype = wt.HANDLE
k32.ReadFile.argtypes = [wt.HANDLE, ctypes.c_void_p, wt.DWORD, ctypes.POINTER(wt.DWORD), ctypes.c_void_p]


def find():
    g = GUID(); hid.HidD_GetHidGuid(ctypes.byref(g))
    h = setupapi.SetupDiGetClassDevsW(ctypes.byref(g), None, None, 0x12)
    i = 0; res = []
    while True:
        d = SP_DID(); d.cbSize = ctypes.sizeof(d)
        if not setupapi.SetupDiEnumDeviceInterfaces(h, None, ctypes.byref(g), i, ctypes.byref(d)): break
        i += 1; need = wt.DWORD()
        setupapi.SetupDiGetDeviceInterfaceDetailW(h, ctypes.byref(d), None, 0, ctypes.byref(need), None)
        buf = ctypes.create_string_buffer(need.value); struct.pack_into("I", buf, 0, 8)
        if setupapi.SetupDiGetDeviceInterfaceDetailW(h, ctypes.byref(d), buf, need, None, None):
            p = ctypes.wstring_at(ctypes.addressof(buf) + 4)
            if "vid_17cc&pid_1130" in p.lower(): res.append(p)
    return res


def open_dev(p, access):
    hh = k32.CreateFileW(p, access, 3, None, 3, 0, None)
    if hh == wt.HANDLE(-1).value or hh is None: raise OSError("open failed %d" % ctypes.get_last_error())
    return hh


def caps(p):
    hh = open_dev(p, 0)
    a = ATTR(); a.Size = ctypes.sizeof(a); hid.HidD_GetAttributes(hh, ctypes.byref(a))
    pp = ctypes.c_void_p(); hid.HidD_GetPreparsedData(hh, ctypes.byref(pp))
    c = CAPS(); hid.HidP_GetCaps(pp, ctypes.byref(c))
    out = {"path": p, "vid": a.VendorID, "pid": a.ProductID, "ver": a.Version, "usagePage": hex(c.UsagePage), "usage": hex(c.Usage),
           "inLen": c.InLen, "outLen": c.OutLen, "featLen": c.FeatLen, "values": {}, "buttons": {}}
    for kind, n_val, n_btn in ((0, c.nInVal, c.nInBtn), (1, c.nOutVal, c.nOutBtn), (2, c.nFeatVal, c.nFeatBtn)):
        name = ["input", "output", "feature"][kind]
        if n_val:
            arr = (VCAPS * n_val)(); n = wt.USHORT(n_val); hid.HidP_GetValueCaps(kind, arr, ctypes.byref(n), pp)
            out["values"][name] = [{"rid": v.ReportID, "page": hex(v.UsagePage), "usage": (v.u.UsageMin, v.u.UsageMax) if v.IsRange else v.u.UsageMin,
                                    "bits": v.BitSize, "count": v.ReportCount, "min": v.LogicalMin, "max": v.LogicalMax,
                                    "dataIdx": (v.u.DataIndexMin, v.u.DataIndexMax), "link": v.LinkCollection} for v in arr[:n.value]]
        if n_btn:
            arr = (BCAPS * n_btn)(); n = wt.USHORT(n_btn); hid.HidP_GetButtonCaps(kind, arr, ctypes.byref(n), pp)
            out["buttons"][name] = [{"rid": b.ReportID, "page": hex(b.UsagePage), "usage": (b.u.UsageMin, b.u.UsageMax) if b.IsRange else b.u.UsageMin,
                                     "dataIdx": (b.u.DataIndexMin, b.u.DataIndexMax), "link": b.LinkCollection} for b in arr[:n.value]]
    hid.HidD_FreePreparsedData(pp); k32.CloseHandle(hh)
    return out


def watch(p, seconds, rec=None):
    c = caps(p); n = c["inLen"]
    hh = open_dev(p, 0x80000000)
    last = {}; t0 = time.time(); f = open(rec, "w") if rec else None
    buf = ctypes.create_string_buffer(n); got = wt.DWORD()
    print("reading %d-byte input reports for %ds - move controls now" % (n, seconds), flush=True)
    while time.time() - t0 < seconds:
        if not k32.ReadFile(hh, buf, n, ctypes.byref(got), None): break
        r = buf.raw[:got.value]; rid = r[0]
        if f: f.write(json.dumps({"t": round(time.time() - t0, 4), "r": r.hex()}) + "\n")
        prev = last.get(rid)
        if prev != r:
            if prev is None: print("rid %02x first: %s" % (rid, r.hex()), flush=True)
            else:
                diff = [(i, prev[i], r[i]) for i in range(len(r)) if prev[i] != r[i]]
                print("rid %02x  %s" % (rid, " ".join("[%d]%02x->%02x" % d for d in diff)), flush=True)
            last[rid] = r
    k32.CloseHandle(hh)


if __name__ == "__main__":
    paths = find()
    if not paths: sys.exit("Z2 HID not found")
    cmd = sys.argv[1] if len(sys.argv) > 1 else "caps"
    if cmd == "caps": print(json.dumps([caps(p) for p in paths], indent=1))
    elif cmd == "watch": watch(paths[0], int(sys.argv[2]) if len(sys.argv) > 2 else 20)
    elif cmd == "record": watch(paths[0], int(sys.argv[3]) if len(sys.argv) > 3 else 60, sys.argv[2])
