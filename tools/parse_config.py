"""Pretty-print a USB configuration descriptor (UAC2 / DFU / HID aware) from dump_descriptors.py JSON."""
import json, sys, struct

d = json.load(open(sys.argv[1]))
cfg = bytes.fromhex(d["config"]); S = {int(k): v for k, v in d["strings"].items()}
dev = bytes.fromhex(d["device"])
print("DEVICE bcdUSB=%04x class=%02x/%02x/%02x ep0=%d VID=%04x PID=%04x bcdDevice=%04x iMan=%d iProd=%d iSer=%d nCfg=%d" %
      ((struct.unpack_from("<H", dev, 2)[0],) + tuple(dev[4:8]) + struct.unpack_from("<HHH", dev, 8) + tuple(dev[14:18])))
s = lambda i: "%d(%s)" % (i, S.get(i, "")) if i else "0"
AC = {1: "HEADER", 2: "INPUT_TERMINAL", 3: "OUTPUT_TERMINAL", 4: "MIXER_UNIT", 5: "SELECTOR_UNIT", 6: "FEATURE_UNIT",
      7: "EFFECT_UNIT", 8: "PROCESSING_UNIT", 9: "EXTENSION_UNIT", 10: "CLOCK_SOURCE", 11: "CLOCK_SELECTOR", 12: "CLOCK_MULTIPLIER"}
cur_cls = None; cur_sub = None
off = 0
while off < len(cfg):
    l, t = cfg[off], cfg[off + 1]; b = cfg[off:off + l]
    if t == 2:
        print("CONFIG total=%d nIf=%d val=%d attr=%02x maxPower=%dmA" % (struct.unpack_from("<H", b, 2)[0], b[4], b[5], b[7], b[8] * 2))
    elif t == 0x0B:
        print(" IAD first=%d count=%d class=%02x/%02x/%02x iFunc=%s" % (b[2], b[3], b[4], b[5], b[6], s(b[7])))
    elif t == 4:
        cur_cls, cur_sub = b[5], b[6]
        print(" IF %d alt %d nEP=%d class=%02x/%02x/%02x %s" % (b[2], b[3], b[4], b[5], b[6], b[7], s(b[8])))
    elif t == 5:
        ep = b[2]; at = b[3]; mps = struct.unpack_from("<H", b, 4)[0]
        print("   EP %02x %s attr=%02x (sync=%d usage=%d) mps=%d (x%d) bInterval=%d" % (ep, "IN" if ep & 0x80 else "OUT", at, (at >> 2) & 3, (at >> 4) & 3, mps & 0x7FF, ((mps >> 11) & 3) + 1, b[6]))
    elif t == 0x24 and cur_cls == 1 and cur_sub == 1:
        st = b[2]; n = AC.get(st, "?%d" % st)
        if st == 1: print("   AC HEADER bcdADC=%04x category=%02x total=%d ctrls=%02x" % (struct.unpack_from("<H", b, 3)[0], b[5], struct.unpack_from("<H", b, 6)[0], b[8]))
        elif st == 10: print("   AC CLOCK_SOURCE id=%d attr=%02x ctrls=%02x assocTerm=%d %s" % (b[3], b[4], b[5], b[6], s(b[7])))
        elif st == 11: print("   AC CLOCK_SELECTOR id=%d nIn=%d in=%s ctrls=%02x %s" % (b[3], b[4], list(b[5:5 + b[4]]), b[5 + b[4]], s(b[6 + b[4]])))
        elif st == 2: print("   AC INPUT_TERMINAL id=%d type=%04x assoc=%d clk=%d nCh=%d chCfg=%08x iChName=%s ctrls=%04x %s" % (b[3], struct.unpack_from("<H", b, 4)[0], b[6], b[7], b[8], struct.unpack_from("<I", b, 9)[0], s(b[13]), struct.unpack_from("<H", b, 14)[0], s(b[16])))
        elif st == 3: print("   AC OUTPUT_TERMINAL id=%d type=%04x assoc=%d src=%d clk=%d ctrls=%04x %s" % (b[3], struct.unpack_from("<H", b, 4)[0], b[6], b[7], b[8], struct.unpack_from("<H", b, 9)[0], s(b[11])))
        elif st == 6:
            n_ch = (l - 6) // 4 - 1
            print("   AC FEATURE_UNIT id=%d src=%d ctrls=%s %s" % (b[3], b[4], [hex(struct.unpack_from('<I', b, 5 + 4 * i)[0]) for i in range(n_ch + 1)], s(b[l - 1])))
        else: print("   AC %s %s" % (n, b.hex()))
    elif t == 0x24 and cur_cls == 1 and cur_sub == 2:
        st = b[2]
        if st == 1: print("   AS GENERAL term=%d ctrls=%02x fmtType=%d fmts=%08x nCh=%d chCfg=%08x iChName=%s" % (b[3], b[4], b[5], struct.unpack_from("<I", b, 6)[0], b[10], struct.unpack_from("<I", b, 11)[0], s(b[15])))
        elif st == 2: print("   AS FORMAT_TYPE type=%d subslot=%d bits=%d" % (b[3], b[4], b[5]))
        else: print("   AS ? %s" % b.hex())
    elif t == 0x25:
        print("   CS_EP attr=%02x ctrls=%02x lockUnits=%d lockDelay=%d" % (b[3], b[4], b[5], struct.unpack_from('<H', b, 6)[0]))
    elif t == 0x21 and cur_cls == 0xFE:
        print("   DFU FUNC attr=%02x detachTO=%d xfer=%d %s" % (b[2], struct.unpack_from("<H", b, 3)[0], struct.unpack_from("<H", b, 5)[0], b[7:].hex()))
    elif t == 0x21 and cur_cls == 3:
        print("   HID bcd=%04x country=%d n=%d type=%02x len=%d" % (struct.unpack_from('<H', b, 2)[0], b[4], b[5], b[6], struct.unpack_from('<H', b, 7)[0]))
    else:
        print("   ?? type %02x %s" % (t, b.hex()))
    if l == 0: break
    off += l
