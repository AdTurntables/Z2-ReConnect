# Z2-Re:Connect 0.9.0 Beta 2 – Installer

Z2-Re:Connect bringt den Native Instruments Traktor Kontrol Z2 ohne Treiber ans iPad und iPhone: Audio **und** USB-MIDI,
zum Beispiel mit djay Pro (4 Decks, DVS), dazu vier Pad-Ebenen pro Deck über DECK A/C bzw. B/D.
**0.9.0 Beta 2 ist der zweite öffentliche Testlauf** (neu: Cue-Farben, Pegelanzeigen A/B, LEDs nach USB-Neuverbinden). Rückmeldungen von Testern sind ausdrücklich erwünscht.
English: start the program with `--lang en`; all prompts are available in English.

**Privates Hobby-Projekt ohne kommerziellen Hintergrund, um alte, aber gute Technik weiter zu nutzen. Benutzung auf eigene Gefahr, ohne jede Gewähr. Kein Produkt von Native Instruments. Wer nicht weiß, wofür er diese Firmware braucht, sollte sie nicht installieren.**
Vor dem Flashen zeigt der Installer diesen Hinweis auf Englisch; weiter geht es nur nach Eingabe von `I UNDERSTAND`.

## Inhalt
| Datei | Zweck |
|---|---|
| `Z2-ReConnect-Installer.exe` (Windows) / `Z2-ReConnect-Installer` (macOS) | der Installer |
| `djay/Traktor Kontrol Z2.djayMidiMapping` | passendes djay-Mapping (am iPad in djay importieren) |
| `djay/z2_djay_mapping*.png` | Übersicht der Belegung (deutsch und englisch) |

## Stand
| Teil | Stand |
|---|---|
| Firmware Z2-Re:Connect 0.9.0 Beta 2 (Stand 5b) | auf dem Entwicklungsgerät geflasht und am iPad mit djay getestet |
| Ablauf (Prüfen, Backup, Schreiben, Kontrolle, Wiederherstellen, Update von 3b) | gegen ein simuliertes Gerät getestet (`test_installer.py`, 15 Prüfungen) |
| Grafische Oberfläche (Assistent) | alle Seiten in Deutsch und Englisch automatisch geprüft. Am echten Z2 **noch nicht** durchgespielt |
| Windows-Programm | gebaut (Fensterprogramm ohne Konsole) |
| macOS | Paket `dist_mac/Z2-ReConnect-0.9.0-beta2-Mac.zip`: eigenständige App `Z2 ReConnect Installer.app` mit eingebautem Python, tkinter und libusb (Apple Silicon + Intel), nichts nachzuladen. Oberfläche mit Mac-tauglichen Knöpfen, automatisch geprüft. Auf einem echten Mac **ungetestet** |
| Andere Z2 als das Entwicklungsgerät | **ungetestet** |

## Voraussetzungen
- Z2 mit **Firmware 42** (letzte Version von Native Instruments) oder einer älteren Z2-Re:Connect-Version.
- Z2 am Netzteil, per USB direkt am Rechner (kein Hub).
- Windows: der Z2-Treiber von Native Instruments muss installiert sein. Traktor muss geschlossen sein.
- macOS: kein Treiber nötig.

## Starten
- **Windows:** `Z2-ReConnect-Installer.exe` doppelklicken. Zuerst läuft das Intro (Klick oder Taste überspringt es), dann öffnet sich der Assistent.
- **macOS:** ZIP entpacken, `Z2 ReConnect Installer` doppelklicken – nichts muss zusätzlich installiert werden.
  Die App ist nicht von Apple beglaubigt: beim ersten Start Rechtsklick → Öffnen bzw. (macOS 15+)
  Systemeinstellungen → Datenschutz & Sicherheit → „Dennoch öffnen“. Protokoll: `~/Library/Logs/Z2-ReConnect-Installer.log`.
- Aus dem Quelltext: `python z2_installer.py` (macOS/Linux vorher `pip install pyusb libusb-package`). `--no-intro` lässt das Intro weg,
  `--cli` zeigt statt des Fensters das Textmenü; `check`, `backup`, `install`, `restore` gehen auch direkt als Befehl.

## Der Assistent
0. **Sprache** – Englisch oder Deutsch, gilt für den ganzen Assistenten.
1. **Willkommen** – was das Programm macht und was vorbereitet sein muss.
2. **Hinweis** – auf Englisch; weiter geht es nur mit dem Häkchen „I have read and understood this notice …“.
3. **Gerät prüfen** – liest die Firmware, speichert sie **immer automatisch als Backup** und prüft sie. Auf den Z2 wird nichts geschrieben.
4. **Installieren** – Backup, Rückfrage, Schreiben mit Fortschrittsbalken, Neustart, Kontrolle.
5. **Fertig** – Hinweis auf das djay-Mapping und den Speicherort des Backups.

Das Backup ist Pflicht und lässt sich nicht abschalten: Ohne gültiges Backup wird nichts geschrieben.
Unter **Erweitert …**: Backup zurückschreiben (erst nach bestätigtem Hinweis), Backup-Ordner öffnen.
Backups liegen in `Dokumente/Z2-Firmware-Backup`.

## Textmenü (`--cli`)
1. **Prüfen** – Sicherheitsmodus. Liest die Firmware aus dem Z2 und sagt, ob dieses Gerät geeignet ist. Es wird nichts geschrieben.
2. **Backup** – sichert die aktuelle Firmware nach `Dokumente/Z2-Firmware-Backup`.
3. **Installieren** – Prüfung, Hinweis (englisch, mit „I UNDERSTAND“ bestätigen), Backup, Rückfrage, Schreiben, Neustart, Kontrolle. Bei einer älteren Z2-Re:Connect-Version: Update.
4. **Backup zurückschreiben** – stellt eine gesicherte Firmware wieder her, zum Beispiel die Original-Firmware 42.

## Was die Sicherheitsprüfung tut
1. Das Gerät meldet sich als Traktor Kontrol Z2 (USB 17CC:1130).
2. Die Firmware wird zweimal ausgelesen; beide Durchgänge müssen identisch sein.
3. Der Aufbau des Abbilds wird geprüft.
4. Die Prüfsumme (SHA-256) muss **exakt** einer Firmware entsprechen, für die ein Patch gebaut wurde
   (NI-Firmware 42 oder Z2-Re:Connect 3b).
5. Die neue Firmware wird lokal gebaut; ihre Prüfsumme muss exakt der getesteten Version entsprechen.

Nur wenn alle Punkte stimmen, wird geschrieben. Damit landet auf jedem Gerät Byte für Byte dieselbe Firmware, die auf dem
Entwicklungsgerät läuft. Weicht die Firmware im Gerät ab (andere Version, andere Hardware-Revision, fremde Firmware), lehnt
das Programm ab.

Grenze der Prüfung: Sie vergleicht die Firmware, nicht die Elektronik. Sollte es Z2 mit gleicher Firmware 42, aber anderer
Hardware geben, erkennt die Prüfung das nicht.

## Wenn etwas schiefgeht
- Nach dem Schreiben liest das Programm zurück. Weicht das Ergebnis ab, schreibt es automatisch das Backup zurück.
- Bricht das Schreiben ab (Strom, Kabel), startet der Z2 mit seiner Werks-Firmware und bleibt per USB erreichbar.
  Der Werks-Bereich wird vom Programm nie beschrieben. Z2 aus- und einschalten, Programm starten, Menüpunkt 4.
- Backups werden nie überschrieben. Der Dateiname enthält den Anfang der Prüfsumme; beschädigte Dateien werden abgelehnt.

## Rechtliches
Das Programm enthält **keine** Firmware von Native Instruments. Die Patch-Dateien (`z2reconnect_0.9.0-beta2.z2patch` für NI-Firmware 42, `…_from_beta1`, `…_from_3b` und `…_from_dev5` für Updates,
je unter 3 KB; die Beta-1-Patches liegen in `alte_patches/`) enthalten nur Kopier-Anweisungen und die neu hinzugekommenen
Bytes; die Original-Firmware kommt immer aus dem eigenen Gerät.
Backups (`*.z2backup`) enthalten die Original-Firmware und dürfen **nicht** weitergegeben werden.

## Für Entwickler
- `make_patch.py` erzeugt eine Patch-Datei aus Ausgangs-Abbild und neuem Abbild. Alle Patch-Dateien im Ordner müssen dasselbe
  Ziel-Abbild bauen.
- `python test_installer.py <nifw42_dump> <neues_abbild> [<z2reconnect_3b>]` prüft den Ablauf ohne Gerät.
- `z2_gui.py` ist die Oberfläche (tkinter); die Arbeit macht weiter die Klasse `Installer` in `z2_installer.py`.
- `intro.frames` ist die Start-Animation: 160 PNG-Bilder (432 × 540, 20 Bilder/s) in einer Datei.
- `build_windows.ps1`, `build_mac.sh`, `.github/workflows/build.yml` bauen die Programme samt `djay`-Ordner.
- `make_mac_app.py` baut unter Windows das Mac-ZIP mit eigenständiger App (Python-Bausteine aus `mac_vendor/`, per SHA-256 geprüft).
- `make_mac_package.py` packt die schlanke Alternative `...-Mac-lite.zip` (Startdatei `.command`, braucht Python 3 auf dem Mac).

## Veröffentlichung (Beta 2)
`build_windows.ps1` → `dist_win/`, `python make_mac_app.py` → `dist_mac/`, dann `python make_release.py` → `release/`:
Windows-ZIP und Mac-ZIP (je Installer + Anleitung Pad-Ebenen, **ohne** djay-Mapping) und `Z2-ReConnect-djay-Mapping-v8.zip` (Mapping, Belegungsbild, Ebenen-Anleitung, DVS-Hinweis).
