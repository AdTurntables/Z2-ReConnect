#!/bin/bash
# Build the firmware blob (midi_glue + z2midi + hooks) and run the XS1 simulator test. Run in WSL.
# Output: blob.elf, blob.dis here. Then: cd ../../tools && python patch_stage2.py build/ni_t1.bin ../firmware/stage2/blob.elf <out_t1.bin>
set -eo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
TOOLS="${XMOS_TOOLS:-$HOME/xmos/XMOS/xTIMEcomposer/Community_14.4.1}"
cd "$TOOLS" && source SetEnv >/dev/null && cd "$HERE"
export LD_LIBRARY_PATH="$HOME/xmos/compat:$LD_LIBRARY_PATH"
python3 gen_hooks.py hooks.S
W="$(mktemp -d)"
xcc -Os -target=XK-1A -DZ2M_NO_NAMES -Wall -nostartfiles midi_glue.c hooks.S ../z2midi/z2midi.c -o "$W/blob.xe"
(cd "$W" && xobjdump --split blob.xe >/dev/null)
cp "$W/image_n0c0_2.elf" blob.elf
xobjdump -d blob.elf > blob.dis
xcc -Os -target=XK-1A -DZ2M_NO_NAMES sim_test.c ../z2midi/z2midi.c -o "$W/sim.xe" 2>&1 | grep -v -i hook || true
timeout 120 xsim "$W/sim.xe"
rm -rf "$W"
