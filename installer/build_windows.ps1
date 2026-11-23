# Baut dist_win\Z2-ReConnect-Installer.exe (Python 3.9+ noetig). Patches und Intro werden ins Programm gepackt.
# Das djay-Mapping ist ein eigenes Paket (make_release.py).
python -m pip install --quiet pyinstaller
$data = @()
foreach ($f in (Get-ChildItem *.z2patch) + (Get-Item intro.frames)) { $data += "--add-data"; $data += "$($f.FullName);." }
python -m PyInstaller --onefile --windowed --name Z2-ReConnect-Installer @data --distpath dist_win --workpath "$env:TEMP\z2build" --specpath "$env:TEMP\z2build" z2_installer.py
