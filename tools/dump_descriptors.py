"""Read-only USB descriptor dump for a device behind a Windows hub (no driver change needed).

Usage: python dump_descriptors.py <hub-instance-id> <port>
Uses IOCTL_USB_GET_DESCRIPTOR_FROM_NODE_CONNECTION on the parent hub. Sends only GET_DESCRIPTOR.
"""
import ctypes, ctypes.wintypes as wt, sys, struct, json

setupapi = ctypes.WinDLL("setupapi", use_last_error=True)
k32 = ctypes.WinDLL("kernel32", use_last_error=True)

class GUID(ctypes.Structure):
    _fields_ = [("d1", wt.DWORD), ("d2", wt.WORD), ("d3", wt.WORD), ("d4", ctypes.c_ubyte * 8)]

GUID_HUB = GUID(0xF18A0E88, 0xC30C, 0x11D0, (ctypes.c_ubyte * 8)(0x88, 0x15, 0x00, 0xA0, 0xC9, 0x06, 0xBE, 0xD8))

class SP_DEVINFO_DATA(ctypes.Structure):
    _fields_ = [("cbSize", wt.DWORD), ("ClassGuid", GUID), ("DevInst", wt.DWORD), ("Reserved", ctypes.c_void_p)]

class SP_DEVICE_INTERFACE_DATA(ctypes.Structure):
    _fields_ = [("cbSize", wt.DWORD), ("InterfaceClassGuid", GUID), ("Flags", wt.DWORD), ("Reserved", ctypes.c_void_p)]

setupapi.SetupDiGetClassDevsW.restype = ctypes.c_void_p
setupapi.SetupDiGetClassDevsW.argtypes = [ctypes.POINTER(GUID), wt.LPCWSTR, wt.HWND, wt.DWORD]
setupapi.SetupDiEnumDeviceInterfaces.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.POINTER(GUID), wt.DWORD, ctypes.POINTER(SP_DEVICE_INTERFACE_DATA)]
setupapi.SetupDiGetDeviceInterfaceDetailW.argtypes = [ctypes.c_void_p, ctypes.POINTER(SP_DEVICE_INTERFACE_DATA), ctypes.c_void_p, wt.DWORD, ctypes.POINTER(wt.DWORD), ctypes.POINTER(SP_DEVINFO_DATA)]
setupapi.SetupDiGetDeviceInstanceIdW.argtypes = [ctypes.c_void_p, ctypes.POINTER(SP_DEVINFO_DATA), wt.LPWSTR, wt.DWORD, ctypes.POINTER(wt.DWORD)]
k32.CreateFileW.restype = wt.HANDLE
k32.DeviceIoControl.argtypes = [wt.HANDLE, wt.DWORD, ctypes.c_void_p, wt.DWORD, ctypes.c_void_p, wt.DWORD, ctypes.POINTER(wt.DWORD), ctypes.c_void_p]


def hub_path(instance_id):
    h = setupapi.SetupDiGetClassDevsW(ctypes.byref(GUID_HUB), None, None, 0x12)  # PRESENT|DEVICEINTERFACE
    i = 0
    while True:
        ifd = SP_DEVICE_INTERFACE_DATA(); ifd.cbSize = ctypes.sizeof(ifd)
        if not setupapi.SetupDiEnumDeviceInterfaces(h, None, ctypes.byref(GUID_HUB), i, ctypes.byref(ifd)):
            return None
        i += 1
        need = wt.DWORD()
        setupapi.SetupDiGetDeviceInterfaceDetailW(h, ctypes.byref(ifd), None, 0, ctypes.byref(need), None)
        buf = ctypes.create_string_buffer(need.value)
        struct.pack_into("I", buf, 0, 8 if ctypes.sizeof(ctypes.c_void_p) == 8 else 6)
        dev = SP_DEVINFO_DATA(); dev.cbSize = ctypes.sizeof(dev)
        if not setupapi.SetupDiGetDeviceInterfaceDetailW(h, ctypes.byref(ifd), buf, need, None, ctypes.byref(dev)):
            continue
        path = ctypes.wstring_at(ctypes.addressof(buf) + 4)
        idb = ctypes.create_unicode_buffer(512)
        setupapi.SetupDiGetDeviceInstanceIdW(h, ctypes.byref(dev), idb, 512, None)
        if idb.value.upper() == instance_id.upper():
            return path


def get_desc(hh, port, dtype, index=0, lang=0, length=4096):
    # USB_DESCRIPTOR_REQUEST: ULONG port; SETUP (bmRequest,bRequest,wValue,wIndex,wLength); data
    req = struct.pack("<IBBHHH", port, 0x80, 6, (dtype << 8) | index, lang, length)
    buf = ctypes.create_string_buffer(req + b"\0" * length, len(req) + length)
    ret = wt.DWORD()
    ok = k32.DeviceIoControl(hh, 0x220410, buf, len(buf), buf, len(buf), ctypes.byref(ret), None)
    if not ok:
        return None
    return buf.raw[len(req):ret.value]


def main():
    hub, port = sys.argv[1], int(sys.argv[2])
    p = hub_path(hub)
    if not p:
        sys.exit("hub not found")
    hh = k32.CreateFileW(p, 0xC0000000, 3, None, 3, 0, None)
    if hh in (None, wt.HANDLE(-1).value):
        sys.exit("cannot open hub: %d" % ctypes.get_last_error())
    dev = get_desc(hh, port, 1, length=18)
    cfg_head = get_desc(hh, port, 2, length=9)
    total = struct.unpack_from("<H", cfg_head, 2)[0]
    cfg = get_desc(hh, port, 2, length=total)
    strings = {}
    langs = get_desc(hh, port, 3, 0, 0, 255)
    lang = struct.unpack_from("<H", langs, 2)[0] if langs and len(langs) >= 4 else 0x409
    idx = set([dev[14], dev[15], dev[16]])
    off = 0
    while off < len(cfg):
        l, t = cfg[off], cfg[off + 1]
        if t == 2: idx.add(cfg[off + 6])
        if t == 4: idx.add(cfg[off + 8])
        if l == 0: break
        off += l
    for i in sorted(x for x in idx if x):
        s = get_desc(hh, port, 3, i, lang, 255)
        if s: strings[i] = s[2:].decode("utf-16-le", "replace")
    for i in range(1, 32):
        if i in strings: continue
        s = get_desc(hh, port, 3, i, lang, 255)
        if s and len(s) > 2: strings[i] = s[2:].decode("utf-16-le", "replace")
    out = {"device": dev.hex(), "config": cfg.hex(), "strings": strings}
    print(json.dumps(out, indent=1))

main()
