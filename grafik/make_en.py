"""Builds the English versions of both graphics from the German HTML files (the firmware one without the LED card)."""
import re, os
os.chdir(os.path.dirname(os.path.abspath(__file__)))

def conv(src, dst, R, pre=None):
    s = open(src, encoding="utf-8").read()
    if pre: s = pre(s)
    for a, b in R:
        assert a in s, a
        s = s.replace(a, b)
    open(dst, "w", encoding="utf-8").write(s)

EN_EXTRA = [('Z² RE:CONNECT · FIRMWARE FÜR TRAKTOR KONTROL Z2', 'Z² RE:CONNECT · FIRMWARE FOR TRAKTOR KONTROL Z2')]
drop_led = lambda s: re.sub(r'\n <div class="card"><h3><span class="ico c">◉</span>LEDs per MIDI</h3>.*?</div>', '', s, flags=re.S)

LAYERS = [("EBENE 1", "LAYER 1"), ("EBENE 2", "LAYER 2"), ("EBENE 3", "LAYER 3"), ("EBENE 4", "LAYER 4")]

conv("z2_firmware.html", "z2_firmware_en.html", [
    ('<html lang="de">', '<html lang="en">'),
    ('<div class="card"><h3><span class="ico">♪</span>USB-MIDI eingebaut</h3>', '<div class="card wide"><h3><span class="ico">♪</span>Built-in USB MIDI</h3>'),
    ('<p><b>48 Tasten, 26 Regler und Fader, 3 Encoder</b> senden MIDI. Beim Verbinden werden alle Reglerstellungen einmal übertragen.</p>',
     '<p><b>All 48 buttons, 26 knobs and faders and 3 encoders</b> send MIDI. On connect, every knob and fader position is sent once, so the app starts in sync.</p>'),
    *EN_EXTRA,
    ('Der Z2 am <span>iPad</span>.<br>Ohne Treiber.', 'Your Z2 on the <span>iPad</span>.<br>No drivers.'),
    ('Z² Re:Connect macht den Z2 <b>class-compliant</b>: Audio <b>und</b> MIDI direkt am iPad und iPhone, z.&nbsp;B. mit djay Pro, 4 Decks und DVS.',
     'Z² Re:Connect makes the Z2 <b>class compliant</b>: audio <b>and</b> MIDI work straight on iPad and iPhone, e.g. with djay Pro, 4 decks and DVS.'),
    ('4 Pad-Ebenen pro Deck', '4 pad layers per deck'),
    ('Mit <b>DECK A / C</b> (rechts <b>B / D</b>) schaltest du um. Jede Ebene sendet auf einem eigenen MIDI-Kanal und hat ihre eigene Farbe. Die Firmware merkt sich jede Ebene, die Pads zeigen nach dem Umschalten also sofort den richtigen Stand.',
     'Switch with <b>DECK A / C</b> (right side <b>B / D</b>). Each layer sends on its own MIDI channel and has its own colour. The firmware remembers every layer, so the pads show the right state the moment you switch.'),
    *LAYERS,
    ('<div class="t">Cue 1–4</div>', '<div class="t">Cues 1–4</div>'), ('<div class="t">Cue 5–8</div>', '<div class="t">Cues 5–8</div>'),
    ('<div class="t">frei belegbar</div>', '<div class="t">free to map</div>'),
    ('Alles bleibt</h3>', 'Nothing lost</h3>'),
    ('Audio, eingebauter Mixer, <b>Timecode über die TRAKTOR-Tasten</b> und Traktor am Computer funktionieren wie vorher.',
     'Audio, the built-in mixer, <b>timecode via the TRAKTOR buttons</b> and Traktor on your computer work just like before.'),
    ('Stabil und umkehrbar</h3>', 'Stable and reversible</h3>'),
    ('Im Dauertest ohne USB-Abbruch. <b>Das Werks-Abbild bleibt unangetastet</b>, die Original-Firmware 42 jederzeit zurückspielbar.',
     'No USB dropouts in long-run tests. <b>The factory image is never touched</b>, and the original firmware 42 can be restored at any time.'),
    ('Bald</h3>', 'Coming</h3>'),
    ('<span>FX 1 → 2 → 3 umschalten</span><span>Loop-Größe auf dem 7&#8209;Segment-Display</span><span>XF-Reverse-LED</span>',
     '<span>Cycle FX 1 → 2 → 3</span><span>Loop size on the 7&#8209;segment display</span><span>XF reverse LED</span>'),
    ('<b>Inoffizielles Community-Projekt</b>, nicht von Native Instruments.<br>Version 0.9.0 Beta 1 · Basis: NI-Firmware 42 · Benutzung auf eigene Gefahr.',
     '<b>Unofficial community project</b>, not affiliated with Native Instruments.<br>Version 0.9.0 Beta 1 · based on NI firmware 42 · use at your own risk.'),
], pre=drop_led)

conv("z2_djay_mapping.html", "z2_djay_mapping_en.html", [
    ('<html lang="de">', '<html lang="en">'),
    ('Was macht <span>welcher Knopf?</span>', 'What does <span>each control do?</span>'),
    ('<span><b>4 Decks</b> am iPad</span><span><b>djay mischt</b> intern</span><span><b>DVS</b> per REL/INTL</span><span>4 Pad-Ebenen</span><span><b>Cue-Farben</b> + Pegel</span>',
     '<span><b>4 decks</b> on iPad</span><span><b>djay mixes</b> internally</span><span><b>DVS</b> via REL/INTL</span><span>4 pad layers</span><span><b>Cue colours</b> + meters</span>'),
    ('<h3>EFFEKTE</h3>', '<h3>EFFECTS</h3>'), ('<h3>BIBLIOTHEK</h3>', '<h3>LIBRARY</h3>'),
    ('Gain + EQ Deck 1 / 2', 'Gain + EQ deck 1 / 2'), ('Filter Deck 1 / 2', 'Filter deck 1 / 2'),
    ('Lautstärke Deck 1 / 2', 'Volume deck 1 / 2'), ('Lautstärke Deck 3 / 4', 'Volume deck 3 / 4'),
    ('Vorhören Deck 1 / 2<span class="s">Deck 3 / 4</span>', 'Headphone cue deck 1 / 2<span class="s">deck 3 / 4</span>'),
    ('Crossfader + Kurve', 'Crossfader + curve'), ('Hamster-Modus an/aus', 'Hamster mode on/off'),
    ('Kopfhörer · Cue/Mix', 'Headphones · cue/mix'), ('Main und Booth', 'Main and booth'),
    ('Mikro an/aus · Pegel · Echo', 'Mic on/off · level · echo'),
    ('FX 1 / FX 2 an Deck 1 / 2', 'FX 1 / FX 2 on deck 1 / 2'),
    ('<b style="color:var(--text)">Echo Out</b> Deck 1 / 2', '<b style="color:var(--text)">Echo out</b> deck 1 / 2'),
    ('<span class="k">XF · XF-KURVE</span>', '<span class="k">XF · XF CURVE</span>'),
    ('<span class="k">FX-REGLER</span>', '<span class="k">FX KNOB</span>'),
    ('BROWSE drehen', 'BROWSE turn'), ('BROWSE drücken', 'BROWSE push'), ('LOOP drehen', 'LOOP turn'), ('LOOP drücken', 'LOOP push'),
    ('Titel blättern<span class="s">Quellen blättern</span>', 'Scroll tracks<span class="s">scroll sources</span>'),
    ('Quellen ↔ Titel<span class="s">zurück</span>', 'Sources ↔ tracks<span class="s">back</span>'),
    ('Laden in Deck 1 / 2<span class="s">in Deck 3 / 4</span>', 'Load to deck 1 / 2<span class="s">to deck 3 / 4</span>'),
    ('Bibliothek ein/aus', 'Show/hide library'), ('Ansicht wechseln', 'Switch view'), ('Quantize an/aus', 'Quantize on/off'),
    ('DVS an/aus (Timecode)', 'DVS on/off (timecode)'), ('Sync<span class="s">Sync-Master</span>', 'Sync<span class="s">sync master</span>'),
    ('Slip-Modus', 'Slip mode'), ('Loop-Länge<span class="s">Loop verschieben</span>', 'Loop length<span class="s">move loop</span>'),
    ('Auto-Loop an/aus<span class="s">Reloop</span>', 'Auto loop on/off<span class="s">reloop</span>'),
    ('Eingang (Hardware)', 'Input select (hardware)'),
    ('PADS · EBENEN MIT DECK A + C (RECHTS B + D)', 'PADS · LAYERS VIA DECK A + C (RIGHT: B + D)'),
    *LAYERS,
    ('<div class="t">Cue 1–4</div><div class="d">in Cue-Farbe · SHIFT löscht</div>', '<div class="t">Cues 1–4</div><div class="d">in cue colour · SHIFT deletes</div>'),
    ('<div class="t">Cue 5–8</div><div class="d">in Cue-Farbe · SHIFT löscht</div>', '<div class="t">Cues 5–8</div><div class="d">in cue colour · SHIFT deletes</div>'),
    ('<p>Für Timecode in den djay-Audioeinstellungen die Eingänge wählen: <b style="white-space:nowrap">Deck A = Kanal 3/4</b>, <b style="white-space:nowrap">Deck B = Kanal 5/6</b>. Danach mit <b>REL / INTL</b> einschalten.</p>',
     '<p>For timecode, set the inputs in djay’s audio settings: <b style="white-space:nowrap">deck A = channels 3/4</b>, <b style="white-space:nowrap">deck B = channels 5/6</b>. Then switch it on with <b>REL / INTL</b>.</p>'),
    ('Vocals · Melodie · Bass · Drums', 'Vocals · melody · bass · drums'),
    ('<div class="t">frei</div><div class="d">für eigene Belegung</div>', '<div class="t">free</div><div class="d">map it your way</div>'),
    ('<b>Braucht die Firmware Z² Re:Connect 0.9.0 Beta 2 · Mapping Version 8.</b><br>Inoffizielles Community-Projekt, nicht von Native Instruments oder Algoriddim.',
     '<b>Requires the Z² Re:Connect 0.9.0 Beta 2 firmware · mapping version 8.</b><br>Unofficial community project, not affiliated with Native Instruments or Algoriddim.'),
])
print("ok")
