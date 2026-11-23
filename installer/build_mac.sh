#!/bin/sh
# Baut dist/Z2-iOS-Installer fuer macOS (auf einem Mac ausfuehren, Python 3.9+ noetig).
set -e
cd "$(dirname "$0")"
python3 -m pip install --quiet pyinstaller pyusb libusb-package
DATA=""
for f in *.z2patch intro.frames; do DATA="$DATA --add-data $PWD/$f:."; done
python3 -m PyInstaller --windowed --name Z2-ReConnect-Installer $DATA --collect-all libusb_package \
  --distpath dist --workpath /tmp/z2build --specpath /tmp/z2build z2_installer.py
mkdir -p dist/djay && cp djay/* dist/djay/
echo "Fertig: dist/Z2-ReConnect-Installer.app"
