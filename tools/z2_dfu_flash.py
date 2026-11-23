"""Write a DFU upgrade image to the Z2 through the installed NI driver, then verify by read-back.

  python z2_dfu_flash.py check  image.bin        -> offline checks only, nothing is sent
  python z2_dfu_flash.py write  image.bin --yes  -> DNLOAD + read-back compare (no reset)
  python z2_dfu_flash.py reboot --yes            -> XMOS 0xF0: restart into the new image

Device side (XMOS module_dfu): first DNLOAD block erases the upgrade image(s), blocks of 64 bytes
fill 256-byte flash pages, a zero-length DNLOAD ends the write. The factory image is never touched;
if the transfer breaks off, the Z2 boots its factory image, which also has DFU.
Restore NI firmware 42: write tools/backup/z2_upload_idle.bin the same way.
Revert-to-factory (0xF1) is still not reachable from here on purpose.
"""
import struct, sys, time, hashlib
import z2_dfu_readback as rb

DNLOAD = 0x80862408
RESET_F0 = 0x80862424
rb.ALLOWED |= {DNLOAD, RESET_F0}
STATES = rb.STATES


def offline_check(img):
    rev = bytes(int(f"{b:08b}"[::-1], 2) for b in range(256))
    p = bytes(rev[b] for b in img)
    tag, size = struct.unpack_from("<I", p, 0)[0], struct.unpack_from("<I", p, 12)[0]
    problems = []
    if tag != 0x1a551e5: problems.append("image tag %08x != 0x1a551e5" % tag)
    if not (0 < size <= len(img)): problems.append("size field %d vs file %d" % (size, len(img)))
    if len(img) % 64: problems.append("file length not a multiple of 64")
    for o in range(0, len(img), 256):
        page = img[o:o + 256]
        if len(page) == 256 and page == b"\xff" * 256: problems.append("all-0xFF page at %#x" % o)
    print("file %d bytes, sha256 %s, tag ok=%s, size field %d" % (len(img), hashlib.sha256(img).hexdigest(), tag == 0x1a551e5, size))
    return problems


def wait_status(d, want, timeout=20.0):
    t0 = time.time()
    while True:
        st = d.status()
        if st["bStatus"] != 0: raise RuntimeError("DFU error status %s" % st)
        if st["state"] in want: return st
        if time.time() - t0 > timeout: raise RuntimeError("timeout waiting for %s, last %s" % (want, st))
        time.sleep(max(st["pollMs"], 1) / 1000.0)


def write(img):
    d, info = rb.pick()
    print("using", d.path[:90], info)
    st = d.state()
    if st == 10:
        d.ioctl(rb.IOCTL["CLRSTATUS"]); st = d.state()
    if st not in (0, 2):
        raise RuntimeError("device not idle: %s" % STATES.get(st, st))
    xfer = info["xfer"] or 64
    n = len(img) // xfer
    t0 = time.time()
    for blk in range(n):
        chunk = img[blk * xfer:(blk + 1) * xfer]
        buf = struct.pack("<HH", blk, len(chunk)) + chunk + bytes(512 - len(chunk))
        d.ioctl(DNLOAD, buf)
        wait_status(d, (5,))                      # dfuDNLOAD-IDLE
        if blk % 128 == 0: print("  block %d/%d" % (blk, n), flush=True)
    d.ioctl(DNLOAD, struct.pack("<HH", n, 0) + bytes(512))
    st = wait_status(d, (2, 7, 8), timeout=60)    # idle / manifest / wait-reset
    print("download done in %.1fs, state %s" % (time.time() - t0, STATES.get(st["state"])))
    if st["state"] != 2:
        try: d.ioctl(rb.IOCTL["CLRSTATUS"])
        except OSError: pass
    d.close()
    # module_dfu only re-locates the new upgrade image after a restart, so UPLOAD returns 0 bytes
    # until then. Verify after `reboot`: readback.py clear, then readback.py upload, then cmp.
    print("written. verify after reboot: z2_dfu_readback.py clear && z2_dfu_readback.py upload x.bin")
    return True


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd in ("check", "write"):
        img = open(sys.argv[2], "rb").read()
        probs = offline_check(img)
        if probs: sys.exit("NOT OK: " + "; ".join(probs))
        print("offline checks passed")
        if cmd == "write":
            if "--yes" not in sys.argv: sys.exit("refusing to write without --yes")
            sys.exit(0 if write(img) else 1)
    elif cmd == "reboot":
        if "--yes" not in sys.argv: sys.exit("refusing without --yes")
        d, _ = rb.pick()
        try: d.ioctl(RESET_F0)
        except OSError as e: print("reset ->", e)
        print("reset sent")
    else:
        sys.exit(__doc__)
