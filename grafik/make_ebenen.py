"""Erzeugt die Anleitungsgrafik zu den Pad-Ebenen (z2_ebenen.html / z2_ebenen_en.html, 1080x1350).
Rendern: powershell -File render.ps1 z2_ebenen  bzw.  z2_ebenen_en"""
import os
os.chdir(os.path.dirname(os.path.abspath(__file__)))

CUE = ["#ff3b3b", "#ff8a1f", "#3a7bff", "#ffd23a"]          # Beispiel-Cue-Farben aus djay
T = {
 "de": dict(
  lang="de", kicker="Z² RE:CONNECT 0.9.0 BETA 2 · ANLEITUNG",
  h1='Vier Ebenen <span>pro Pad-Reihe</span>',
  lead="Mit <b>DECK A</b> und <b>DECK C</b> schaltest du die linken Pads um, mit <b>DECK B</b> und <b>DECK D</b> die rechten. "
       "Jede Taste schaltet ihr Licht an oder aus. Welche Ebene aktiv ist, zeigen die beiden DECK-LEDs.",
  layers=[("EBENE 1", "Cue 1–4", "Pads leuchten in der Cue-Farbe aus djay"),
          ("EBENE 2", "Cue 5–8", "Pads leuchten in der Cue-Farbe aus djay"),
          ("EBENE 3", "Neural Mix", "Vocals · Melodie · Bass · Drums"),
          ("EBENE 4", "frei", "für eigene Belegung")],
  how="So geht’s", steps=[
   "<b>Keine</b> DECK-LED an → Ebene 1",
   "Nur <b>DECK A</b> an → Ebene 2",
   "Nur <b>DECK C</b> an → Ebene 3",
   "<b>A und C</b> an → Ebene 4",
   "<b>SHIFT + Pad</b> löscht den Cue",
   "Rechts genauso mit <b>DECK B / D</b>"],
  new="Neu in Beta 2", news=[
   "<b>Cue-Farben</b>: die Pads zeigen die Farbe, die der Cue in djay hat",
   "<b>Pegelanzeigen A / B</b> laufen mit dem Pegel von Deck 1 / 2",
   "<b>USB ab- und wieder anstecken</b>: die LEDs gehen sofort wieder"],
  tech="Technik: Jede Ebene sendet auf eigenem MIDI-Kanal (1, 4, 5, 6). Die Firmware merkt sich die LEDs jeder Ebene, "
       "nach dem Umschalten stimmen die Pads sofort.",
  foot="<b>Braucht Z² Re:Connect 0.9.0 Beta 2 und das djay-Mapping Version 8.</b><br>Inoffizielles Community-Projekt, nicht von Native Instruments oder Algoriddim.",
  left="LINKS", right="RECHTS"),
 "en": dict(
  lang="en", kicker="Z² RE:CONNECT 0.9.0 BETA 2 · GUIDE",
  h1='Four layers <span>per pad row</span>',
  lead="<b>DECK A</b> and <b>DECK C</b> switch the left pads, <b>DECK B</b> and <b>DECK D</b> the right ones. "
       "Each button turns its light on or off. The two DECK LEDs show which layer is active.",
  layers=[("LAYER 1", "Cues 1–4", "Pads light up in the cue colour from djay"),
          ("LAYER 2", "Cues 5–8", "Pads light up in the cue colour from djay"),
          ("LAYER 3", "Neural Mix", "Vocals · Melody · Bass · Drums"),
          ("LAYER 4", "free", "for your own mapping")],
  how="How it works", steps=[
   "<b>No</b> DECK LED lit → layer 1",
   "Only <b>DECK A</b> lit → layer 2",
   "Only <b>DECK C</b> lit → layer 3",
   "<b>A and C</b> lit → layer 4",
   "<b>SHIFT + pad</b> deletes the cue",
   "Same on the right with <b>DECK B / D</b>"],
  new="New in Beta 2", news=[
   "<b>Cue colours</b>: the pads show the colour the cue has in djay",
   "<b>Level meters A / B</b> follow the level of deck 1 / 2",
   "<b>Unplug and replug USB</b>: the LEDs come straight back"],
  tech="Under the hood: each layer sends on its own MIDI channel (1, 4, 5, 6). The firmware remembers the LEDs of every layer, "
       "so the pads are right the moment you switch.",
  foot="<b>Needs Z² Re:Connect 0.9.0 Beta 2 and djay mapping version 8.</b><br>Unofficial community project, not by Native Instruments or Algoriddim.",
  left="LEFT", right="RIGHT"),
}
LED = [(0, 0), (1, 0), (0, 1), (1, 1)]                         # (A an, C an)
PADS = [CUE, CUE[::-1], ["#ffd23a"] * 4, ["#f4f4f4"] * 4]
ACC = ["#3a7bff", "#b04dff", "#ffd23a", "#f4f4f4"]

CSS = """
:root{--bg:#0c0e12;--panel:#151922;--line:#262c38;--text:#eef1f6;--mute:#9aa3b2;--acc:#ff7a1a;--cyan:#35c8ff}
*{box-sizing:border-box;margin:0;padding:0}
body{width:1080px;height:1350px;background:var(--bg);color:var(--text);font-family:"Segoe UI",system-ui,sans-serif;overflow:hidden;position:relative}
body:before{content:"";position:absolute;inset:0;background:radial-gradient(900px 600px at 90% -10%,rgba(53,200,255,.16),transparent 60%),radial-gradient(800px 600px at -10% 110%,rgba(255,122,26,.14),transparent 60%)}
.wrap{position:relative;padding:52px 56px 0}
.kicker{font-family:Bahnschrift,"Segoe UI";letter-spacing:.3em;font-size:20px;color:var(--cyan);font-weight:600}
h1{font-family:Bahnschrift,"Segoe UI";font-weight:700;font-size:62px;line-height:1.02;margin-top:10px}
h1 span{color:var(--cyan)}
.lead{font-size:21px;line-height:1.45;color:#c9d0db;margin-top:16px;max-width:950px}
.lead b{color:var(--text)}
.grid{display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-top:28px}
.lay{background:var(--panel);border:1px solid var(--line);border-radius:18px;padding:20px 20px 22px 24px;position:relative;overflow:hidden}
.lay:before{content:"";position:absolute;left:0;top:0;bottom:0;width:6px;background:var(--c)}
.top{display:flex;justify-content:space-between;align-items:flex-start}
.n{font-family:Bahnschrift;font-size:16px;color:var(--mute);letter-spacing:.14em}
.t{font-family:Bahnschrift;font-size:32px;font-weight:600;margin-top:2px}
.d{font-size:17px;color:var(--mute);margin-top:3px}
.dk{display:flex;gap:8px}
.dk u{text-decoration:none;font-family:Bahnschrift;font-weight:700;font-size:16px;width:46px;height:30px;border-radius:7px;display:flex;align-items:center;justify-content:center;border:1px solid #3a4150;color:#5d6574;background:#0f1218}
.dk u.on{color:#111;background:#ffb15e;border-color:#ffb15e;box-shadow:0 0 14px rgba(255,177,94,.55)}
.pads{display:flex;gap:12px;margin-top:20px}
.pads i{flex:1;height:92px;border-radius:10px;background:var(--p);box-shadow:0 0 18px color-mix(in srgb,var(--p) 55%,transparent),inset 0 0 0 1px rgba(255,255,255,.18)}
.row{display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-top:16px}
.card{background:var(--panel);border:1px solid var(--line);border-radius:18px;padding:16px 22px}
.card h3{font-family:Bahnschrift,"Segoe UI";font-size:21px;letter-spacing:.14em;font-weight:600;color:var(--acc);margin-bottom:8px;text-transform:uppercase}
.card.c h3{color:var(--cyan)}
.card li{list-style:none;font-size:19.5px;line-height:1.35;color:#c9d0db;padding:6px 0;border-top:1px solid #1e2430}
.card li:first-child{border-top:0}
.card li b{color:var(--text)}
.tech{margin-top:18px;font-size:17.5px;line-height:1.45;color:var(--mute)}
.foot{position:absolute;left:56px;right:56px;bottom:30px;display:flex;justify-content:space-between;align-items:flex-end;color:#6b7383;font-size:16px;line-height:1.4}
.foot b{color:var(--mute)}
.tag{font-family:Bahnschrift;color:var(--cyan);font-size:19px;letter-spacing:.2em}
"""

for code, L in T.items():
    cards = []
    for k, (n, t, d) in enumerate(L["layers"]):
        a, c = LED[k]
        pads = "".join('<i style="--p:%s"></i>' % p for p in PADS[k])
        cards.append('<div class="lay" style="--c:%s"><div class="top"><div><div class="n">%s</div><div class="t">%s</div>'
                     '<div class="d">%s</div></div><div class="dk"><u%s>A</u><u%s>C</u></div></div><div class="pads">%s</div></div>'
                     % (ACC[k], n, t, d, ' class="on"' if a else "", ' class="on"' if c else "", pads))
    steps = "".join("<li>%s</li>" % s for s in L["steps"])
    news = "".join("<li>%s</li>" % s for s in L["news"])
    html = ('<!doctype html>\n<html lang="%s"><head><meta charset="utf-8"><title>Z2 Pad-Ebenen</title><style>%s</style></head><body><div class="wrap">'
            '<div class="kicker">%s</div><h1>%s</h1><div class="lead">%s</div><div class="grid">%s</div>'
            '<div class="row"><div class="card"><h3>%s</h3><ul>%s</ul></div><div class="card c"><h3>%s</h3><ul>%s</ul></div></div>'
            '<div class="tech">%s</div></div><div class="foot"><div>%s</div><div class="tag">Z² Re:Connect</div></div></body></html>'
            % (L["lang"], CSS, L["kicker"], L["h1"], L["lead"], "".join(cards), L["how"], steps, L["new"], news, L["tech"], L["foot"]))
    open("z2_ebenen%s.html" % ("" if code == "de" else "_en"), "w", encoding="utf-8").write(html)
print("ok")
