#!/bin/bash
# Build a Z2 DFU upgrade image from two raw tile memory images (loaded at 0x10000).
# Verified 2026-11-20: with NI's unmodified tiles this reproduces the read-back
# firmware 42 byte for byte (tools/backup/z2_upload_idle.bin).
#
# Usage (in WSL):  ./build_image.sh tile0.bin tile1.bin out.bin [upgrade-version]
# tileN.bin = memory image WITHOUT the trailing check word (xflash appends it).
set -eo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
TOOLS="${XMOS_TOOLS:-$HOME/xmos/XMOS/xTIMEcomposer/Community_14.4.1}"
T0="$1"; T1="$2"; OUT="$3"; VER="${4:-2}"
cd "$TOOLS" && source SetEnv >/dev/null && cd - >/dev/null
export LD_LIBRARY_PATH="$HOME/xmos/compat:$LD_LIBRARY_PATH"   # libtinfo.so.5 -> .so.6 shim
W="$(mktemp -d)"
python3 "$HERE/../../tools/mkelf.py" "$T0" "$W/t0.elf"
python3 "$HERE/../../tools/mkelf.py" "$T1" "$W/t1.elf"
xcc -O2 "$HERE/z2.xn" "$HERE/stub.xc" -o "$W/base.xe"
xobjdump --replace "0,0,$W/t0.elf" "$W/base.xe" >/dev/null
xobjdump --replace "1,0,$W/t1.elf" "$W/base.xe" >/dev/null
xflash --noinq --factory-version 12 --no-compression --upgrade "$VER" "$W/base.xe" -o "$OUT"
xflash_image_check -f "$OUT" -v tools_12 -t SPI
rm -rf "$W"
