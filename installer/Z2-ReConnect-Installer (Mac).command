#!/bin/sh
# Z² Re:Connect – Installer fuer macOS (Doppelklick-Starter, ohne vorheriges Bauen).
# Sucht ein Python 3 mit tkinter, richtet beim ersten Start eine eigene Umgebung mit pyusb + libusb ein
# (unter ~/Library/Application Support/Z2-ReConnect) und startet den grafischen Installer.
cd "$(dirname "$0")" || exit 1

PY=""
for c in /Library/Frameworks/Python.framework/Versions/3.*/bin/python3 /opt/homebrew/bin/python3 /usr/local/bin/python3 python3; do
  if command -v "$c" >/dev/null 2>&1 && "$c" -c "import sys, tkinter; sys.exit(0 if sys.version_info >= (3, 8) else 1)" 2>/dev/null; then
    PY="$c"; break
  fi
done
if [ -z "$PY" ]; then
  echo ""
  echo "Python 3 (mit tkinter) wurde nicht gefunden."
  echo "Bitte Python von https://www.python.org/downloads/macos/ installieren und danach erneut starten."
  echo ""
  echo "Python 3 (with tkinter) was not found."
  echo "Please install Python from https://www.python.org/downloads/macos/ and start again."
  echo ""
  echo "Enter = Ende / quit"; read -r _; exit 1
fi

ENV="$HOME/Library/Application Support/Z2-ReConnect/venv"
if [ ! -x "$ENV/bin/python3" ]; then
  echo "Erster Start: richte Umgebung ein ... / First start: setting up ..."
  "$PY" -m venv "$ENV" || { echo "venv fehlgeschlagen / failed"; read -r _; exit 1; }
fi
if ! "$ENV/bin/python3" -c "import usb, libusb_package" 2>/dev/null; then
  echo "Lade USB-Pakete (pyusb, libusb) ... / Downloading USB packages ..."
  "$ENV/bin/python3" -m pip install --quiet --disable-pip-version-check pyusb libusb-package || {
    echo "Download fehlgeschlagen - Internetverbindung pruefen. / Download failed - check the internet connection."
    read -r _; exit 1; }
fi

"$ENV/bin/python3" z2_installer.py "$@"
