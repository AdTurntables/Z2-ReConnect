"""Grafische Oberflaeche des Z² Re:Connect-Installers (tkinter, Windows/macOS/Linux).

Ein Assistent mit Schritten: Sprache -> Willkommen -> Hinweis (englisch, muss bestaetigt werden) -> Geraet pruefen -> Installieren -> Fertig.
Die eigentliche Arbeit macht die getestete Klasse Installer aus z2_installer.py; sie laeuft in einem eigenen Thread,
Ausgaben und Fortschritt kommen ueber eine Warteschlange zurueck in die Oberflaeche.
"""
import os, queue, sys, threading

try:
    import tkinter as tk
    from tkinter import ttk, filedialog
except Exception:                                # kein tkinter: Aufrufer faellt auf das Textmenue zurueck
    tk = None

BG, PANEL, LINE, TEXT, MUTE, ACC, OK, BAD = "#0c0e12", "#151922", "#262c38", "#eef1f6", "#9aa3b2", "#ff7a1a", "#3ccf7a", "#ff5a5a"

G = {
    "steps": (["Sprache", "Willkommen", "Hinweis", "Gerät prüfen", "Installieren", "Fertig"],
              ["Language", "Welcome", "Notice", "Check device", "Install", "Done"]),
    "lang_title": "Language  ·  Sprache",
    "lang_sub": "Choose the language for the installer.\nWähle die Sprache für den Installer.",
    "yes": ("Ja", "Yes"), "no": ("Nein", "No"), "ok": ("OK", "OK"),
    "adv_auto": ("Ein Backup der Firmware im Z2 wird bei jeder Prüfung automatisch gespeichert.",
                 "A backup of the firmware in the Z2 is saved automatically on every check."),
    "back": ("< Zurück", "< Back"), "next": ("Weiter >", "Next >"), "cancel": ("Abbrechen", "Cancel"),
    "close": ("Schließen", "Close"), "advanced": ("Erweitert …", "Advanced …"),
    "welcome_sub": ("Der Traktor Kontrol Z2 an iPad, iPhone und anderen Geräten – ohne Treiber.",
                    "The Traktor Kontrol Z2 on iPad, iPhone and other devices – no drivers."),
    "welcome_body": ("Dieser Assistent bringt die Firmware %s auf deinen Z2: Audio und USB-MIDI direkt am iPad "
                     "(Standard-USB, sollte auch an Android, Mac und Linux gehen, dort ungetestet), "
                     "zum Beispiel mit djay Pro (4 Decks, DVS, vier Pad-Ebenen).\n\n"
                     "Vorher wird geprüft, ob dein Gerät passt, und die aktuelle Firmware wird gesichert. "
                     "Die Original-Firmware lässt sich jederzeit zurückspielen.",
                     "This wizard puts the %s firmware on your Z2: audio and USB MIDI straight on the iPad "
                     "(standard USB, should also work with Android, Mac and Linux, untested there), "
                     "for example with djay Pro (4 decks, DVS, four pad layers).\n\n"
                     "It first checks that your device is suitable and backs up the current firmware. "
                     "The original firmware can be restored at any time."),
    "needs": ("Bitte vorbereiten", "Before you start"),
    "needs_list": (["Z2 mit Firmware 42 von Native Instruments (oder ältere Z² Re:Connect-Version)",
                    "Netzteil am Z2 angeschlossen und eingeschaltet",
                    "USB-Kabel direkt am Computer, kein Hub",
                    "Traktor und andere Audio-Programme geschlossen"],
                   ["Z2 with Native Instruments firmware 42 (or an older Z² Re:Connect version)",
                    "Power supply connected to the Z2 and switched on",
                    "USB cable directly to the computer, no hub",
                    "Traktor and other audio software closed"]),
    "needs_win": ("Windows: Der Z2-Treiber von Native Instruments muss installiert sein.",
                  "Windows: the Native Instruments Z2 driver must be installed."),
    "notice_title": ("Bitte lesen", "Please read"),
    "agree": ("Ich habe diesen Hinweis gelesen und verstanden. Ich benutze Z² Re:Connect vollständig auf eigene Gefahr.",
              "I have read and understood this notice. I use Z² Re:Connect entirely at my own risk."),
    "check_title": ("Gerät prüfen", "Check device"),
    "check_sub": ("Die Firmware wird zweimal aus dem Z2 gelesen, automatisch als Backup gespeichert und geprüft. "
                  "Auf den Z2 wird nichts geschrieben.",
                  "The firmware is read from the Z2 twice, saved automatically as a backup and checked. "
                  "Nothing is written to the Z2."),
    "check_again": ("Erneut prüfen", "Check again"),
    "running": ("Bitte warten …", "Please wait …"),
    "res_ok": ("Dein Z2 ist geeignet.", "Your Z2 is suitable."),
    "res_update": ("Auf deinem Z2 läuft eine ältere Version. Das Update ist möglich.",
                   "Your Z2 runs an older version. The update is available."),
    "res_done": ("Auf deinem Z2 läuft %s bereits.", "Your Z2 already runs %s."),
    "res_no": ("Dieser Z2 wird nicht unterstützt. Es wird nichts geschrieben.",
               "This Z2 is not supported. Nothing will be written."),
    "res_err": ("Prüfung nicht möglich. Details siehe unten.", "Check not possible. See details below."),
    "inst_title": ("Installieren", "Install"),
    "inst_warn": ("Während des Schreibens (etwa 10 Sekunden) USB-Kabel und Strom nicht trennen. "
                  "Das Backup deiner bisherigen Firmware ist bereits gespeichert.",
                  "Do not unplug USB or power while writing (about 10 seconds). "
                  "The backup of your current firmware has already been saved."),
    "inst_btn": ("Jetzt installieren", "Install now"),
    "inst_ask": ("%s jetzt auf den Z2 schreiben?\n\nUSB-Kabel und Strom bis zum Ende nicht trennen.",
                 "Write %s to the Z2 now?\n\nDo not unplug USB or power until it has finished."),
    "inst_fail": ("Die Installation wurde nicht abgeschlossen. Details siehe unten.",
                  "The installation did not complete. See details below."),
    "done_title": ("Fertig", "Done"),
    "done_body": ("Der Z2 läuft jetzt mit %s.\n\nSchließe ihn ans iPad an (oder an ein anderes Gerät mit USB-Audio/MIDI): Er erscheint als Audio- und MIDI-Gerät. "
                  "Das passende djay-Mapping (Version 8) gibt es als eigenes Paket „Z2-ReConnect-djay-Mapping“. Wie die Pad-Ebenen funktionieren, zeigt das Bild „Anleitung Pad-Ebenen“ neben diesem Programm.",
                  "The Z2 now runs %s.\n\nConnect it to your iPad (or another device with USB audio/MIDI): it shows up as an audio and MIDI device. "
                  "The matching djay mapping (version 8) comes as a separate package, 'Z2-ReConnect-djay-Mapping'. The picture 'Guide pad layers' next to this program shows how the pad layers work."),
    "done_backup": ("Backup der vorherigen Firmware:", "Backup of the previous firmware:"),
    "adv_title": ("Erweitert", "Advanced"),
    "adv_backup": ("Backup der aktuellen Firmware speichern", "Save a backup of the current firmware"),
    "adv_restore": ("Backup zurückschreiben (z. B. Original-Firmware) …", "Write a backup back (e.g. original firmware) …"),
    "adv_folder": ("Backup-Ordner öffnen", "Open backup folder"),
    "adv_need": ("Zum Zurückschreiben bitte zuerst den Hinweis lesen und bestätigen.",
                 "To write a backup back, read and accept the notice first."),
    "restore_ask": ("Dieses Backup auf den Z2 schreiben?\n\n%s\n\nUSB-Kabel und Strom bis zum Ende nicht trennen.",
                    "Write this backup to the Z2?\n\n%s\n\nDo not unplug USB or power until it has finished."),
    "busy": ("Bitte warten, bis der laufende Vorgang fertig ist.", "Please wait until the current task has finished."),
    "quit_busy": ("Gerade wird auf den Z2 geschrieben. Bitte warten.", "Writing to the Z2 right now. Please wait."),
    "footer": ("Privates Hobby-Projekt · keine Verbindung zu Native Instruments · ohne Gewähr",
               "Private hobby project · not affiliated with Native Instruments · no warranty"),
}


# macOS (Aqua) zeichnet tk.Button und tk.Checkbutton nativ und ignoriert dabei die Farben: helle Schrift auf
# weissem Knopf waere unlesbar. Dort werden Knoepfe und das Haekchen deshalb aus Labels gebaut.
# Z2_FLAT=1 erzwingt das auch auf anderen Systemen (zum Testen).
FLAT = sys.platform == "darwin" or os.environ.get("Z2_FLAT") == "1"

if tk is not None:
    class FlatButton(tk.Label):
        """Label, das sich wie ein Knopf verhaelt: command, state normal/disabled, Hover-Farbe."""
        def __init__(self, master, command=None, activebackground=None, activeforeground=None, **kw):
            kw.pop("relief", None); kw.pop("bd", None)
            super().__init__(master, relief="flat", bd=0, **kw)
            self._cmd, self._bg, self._abg = command, kw.get("bg"), activebackground or kw.get("bg")
            self.bind("<Button-1>", self._click)
            self.bind("<Enter>", lambda e: self._hover(True))
            self.bind("<Leave>", lambda e: self._hover(False))

        def _click(self, _):
            if str(self["state"]) != "disabled" and self._cmd: self._cmd()

        def _hover(self, on):
            if str(self["state"]) != "disabled": tk.Label.configure(self, bg=self._abg if on else self._bg)

        def configure(self, cnf=None, **kw):
            if "command" in kw: self._cmd = kw.pop("command")
            if "bg" in kw: self._bg = kw["bg"]
            return tk.Label.configure(self, cnf, **kw) if (cnf or kw) else tk.Label.configure(self)
        config = configure


def make_gui_ask(zi, holder):
    """The installer's ask() for the GUI. Every decision is taken in the main thread with a dialog and stored in
    holder.gui_answers; the worker thread only gets answers by KEY (never by prompt text). Unknown key -> "-"."""
    def ask(prompt, key=None):
        a = getattr(holder, "gui_answers", {})
        if key == "disclaimer": return zi.DISCLAIMER_WORD if a.get("disclaimer") else "-"
        if key == "confirm": return zi.t("yes_word") if a.get("confirm") else "-"
        if key in ("tester", "junk"): return zi.t("tester_word") if a.get(key) else "-"
        if key == "refresh": return zi.t("yes_word") if a.get("refresh") else "-"
        return "-"
    ask.keyed = True
    return ask


def available():
    if tk is None: return False
    try:
        r = tk.Tk(); r.withdraw(); r.destroy(); return True
    except Exception:
        return False


class _QueueWriter:
    """Ersetzt sys.stdout: alles, was der Installer ausgibt, landet im Protokollfeld."""
    def __init__(self, q): self.q = q
    def write(self, s):
        if s: self.q.put(("log", s))
    def flush(self): pass


class App:
    def __init__(self, zi, backup_dir, intro):
        self.zi, self.backup_dir = zi, backup_dir
        self.L = zi.LANG
        self.q = queue.Queue()
        self.busy = False
        self.writing = False
        self.accepted = False
        self.kind = None
        self.page = 0
        self.root = tk.Tk()
        self.root.withdraw()
        self.root.title("%s – Installer %s" % (zi.PRODUCT, zi.VERSION))
        self.root.configure(bg=BG)
        self.root.geometry("820x580")
        self.root.minsize(760, 540)
        self.root.protocol("WM_DELETE_WINDOW", self.quit)
        self.font = self._font()
        self._style()
        self._build()
        sys.stdout = _QueueWriter(self.q)
        self._after = self.root.after(60, self._pump)
        if intro: self._intro()
        else: self._show_main()

    # ------------------------------------------------------------------ Grundgeruest
    def g(self, key):
        v = G[key]
        return v[self.L] if isinstance(v, tuple) else v

    def _font(self):
        fams = set(tk.font.families()) if hasattr(tk, "font") else set()
        try:
            import tkinter.font as tkf
            fams = set(tkf.families())
        except Exception:
            pass
        for f in ("Segoe UI", "SF Pro Text", "Helvetica Neue", "Helvetica", "Arial"):
            if f in fams: return f
        return "TkDefaultFont"

    def F(self, size, weight="normal"):
        return (self.font, size, weight)

    def _style(self):
        st = ttk.Style(self.root)
        try: st.theme_use("clam")
        except tk.TclError: pass
        st.configure("Z.Horizontal.TProgressbar", troughcolor=PANEL, background=ACC, bordercolor=LINE,
                     lightcolor=ACC, darkcolor=ACC, thickness=14)

    def _button(self, parent, text, cmd, primary=False, **extra):
        kw = dict(text=text, command=cmd, font=self.F(10, "bold" if primary else "normal"),
                  bg=ACC if primary else PANEL, fg="#111111" if primary else TEXT,
                  activebackground="#ff9442" if primary else LINE, activeforeground="#111111" if primary else TEXT,
                  disabledforeground="#5b6271", relief="flat", bd=0, padx=16, pady=7, cursor="hand2",
                  highlightthickness=1, highlightbackground=LINE)
        kw.update(extra)
        return FlatButton(parent, **kw) if FLAT else tk.Button(parent, **kw)

    def _build(self):
        r = self.root
        side = tk.Frame(r, bg=PANEL, width=210)
        side.pack(side="left", fill="y")
        side.pack_propagate(False)
        tk.Label(side, text="Z²", font=self.F(40, "bold"), bg=PANEL, fg=TEXT).pack(anchor="w", padx=24, pady=(26, 0))
        tk.Label(side, text="Re:Connect", font=self.F(16, "bold"), bg=PANEL, fg=ACC).pack(anchor="w", padx=26)
        tk.Label(side, text="Installer %s" % self.zi.VERSION, font=self.F(9), bg=PANEL, fg=MUTE).pack(anchor="w", padx=26, pady=(2, 26))
        self.step_labels = []
        for i, name in enumerate(self.g("steps")):
            lab = tk.Label(side, text="", font=self.F(11), bg=PANEL, fg=MUTE, anchor="w")
            lab.pack(fill="x", padx=14, pady=3, ipady=5)
            self.step_labels.append(lab)
        self.footer = tk.Label(side, text="", font=self.F(8), bg=PANEL, fg="#6b7383", wraplength=180, justify="left")
        self.footer.pack(side="bottom", anchor="w", padx=20, pady=18)

        main = tk.Frame(r, bg=BG)
        main.pack(side="left", fill="both", expand=True)
        self.body = tk.Frame(main, bg=BG)
        self.body.pack(fill="both", expand=True, padx=34, pady=(28, 10))
        bar = tk.Frame(main, bg=BG)
        bar.pack(fill="x", padx=34, pady=(0, 22))
        self.b_adv = self._button(bar, self.g("advanced"), self.advanced)
        self.b_adv.pack(side="left")
        self.b_cancel = self._button(bar, self.g("cancel"), self.quit)
        self.b_cancel.pack(side="right")
        self.b_next = self._button(bar, self.g("next"), self.next, primary=True)
        self.b_next.pack(side="right", padx=(0, 10))
        self.b_back = self._button(bar, self.g("back"), self.back)
        self.b_back.pack(side="right", padx=(0, 10))
        self._relabel()

    def _relabel(self):
        """Alle festen Beschriftungen in der gewaehlten Sprache."""
        for i, name in enumerate(self.g("steps")):
            self.step_labels[i].configure(text="  %d   %s" % (i + 1, name))
        self.footer.configure(text=self.g("footer"))
        self.b_adv.configure(text=self.g("advanced"))
        self.b_back.configure(text=self.g("back"))

    def set_lang(self, L):
        self.L = L
        self.zi.LANG = L                            # auch die Meldungen des Installers im Protokoll
        self._relabel()
        self.show(1)

    def dialog(self, text, question=True):
        """Eigene Ja/Nein- bzw. OK-Abfrage in der gewaehlten Sprache (die System-Dialoge waeren in der Systemsprache)."""
        top = tk.Toplevel(self.root, bg=BG)
        top.title(self.zi.PRODUCT)
        top.transient(self.root)
        top.resizable(False, False)
        tk.Label(top, text=text, font=self.F(11), bg=BG, fg=TEXT, wraplength=420, justify="left").pack(
            anchor="w", padx=26, pady=(24, 18))
        res = {"v": False}
        bar = tk.Frame(top, bg=BG)
        bar.pack(fill="x", padx=26, pady=(0, 22))

        def done(v):
            res["v"] = v
            top.grab_release(); top.destroy()
        if question:
            self._button(bar, self.g("no"), lambda: done(False)).pack(side="right")
            self._button(bar, self.g("yes"), lambda: done(True), primary=True).pack(side="right", padx=(0, 10))
        else:
            self._button(bar, self.g("ok"), lambda: done(True), primary=True).pack(side="right")
        top.protocol("WM_DELETE_WINDOW", lambda: done(False))
        top.update_idletasks()
        x = self.root.winfo_rootx() + (self.root.winfo_width() - top.winfo_width()) // 2
        y = self.root.winfo_rooty() + (self.root.winfo_height() - top.winfo_height()) // 3
        top.geometry("+%d+%d" % (max(x, 0), max(y, 0)))
        top.grab_set()
        top.focus_force()
        self.root.wait_window(top)
        return res["v"]

    # ------------------------------------------------------------------ Intro
    def _intro(self):
        data = self.zi.load_intro_frames()
        if not data:
            self._show_main(); return
        pngs, ms = data
        top = tk.Toplevel(self.root, bg="black")
        top.overrideredirect(True)
        try: top.attributes("-topmost", True)
        except tk.TclError: pass
        try:
            first = tk.PhotoImage(data=pngs[0])
        except tk.TclError:
            top.destroy(); self._show_main(); return
        w, h = first.width(), first.height()
        top.geometry("%dx%d+%d+%d" % (w, h, (top.winfo_screenwidth() - w) // 2, (top.winfo_screenheight() - h) // 2))
        lab = tk.Label(top, image=first, bg="black", bd=0, cursor="hand2")
        lab.pack()
        state = {"done": False, "img": first}

        def finish(_=None):
            if state["done"]: return
            state["done"] = True
            top.destroy()
            self._show_main()

        def step(i):
            if state["done"]: return
            if i >= len(pngs):
                self.root.after(350, finish); return
            try: state["img"] = tk.PhotoImage(data=pngs[i])
            except tk.TclError: finish(); return
            lab.configure(image=state["img"])
            self.root.after(ms, step, i + 1)

        for wdg in (top, lab):
            wdg.bind("<Button-1>", finish)
        top.bind("<Key>", finish)
        top.focus_force()
        self.root.after(15000, finish)
        step(1)

    def _show_main(self):
        self.root.deiconify()
        self.root.lift()
        try: self.root.focus_force()
        except tk.TclError: pass
        self.show(0)

    # ------------------------------------------------------------------ Seiten
    def clear(self):
        for w in self.body.winfo_children(): w.destroy()

    def h1(self, text):
        tk.Label(self.body, text=text, font=self.F(22, "bold"), bg=BG, fg=TEXT, anchor="w").pack(fill="x")

    def p(self, text, color=MUTE, size=11, pady=(8, 0)):
        lab = tk.Label(self.body, text=text, font=self.F(size), bg=BG, fg=color, anchor="w", justify="left", wraplength=540)
        lab.pack(fill="x", pady=pady)
        return lab

    def log_box(self, height=9):
        fr = tk.Frame(self.body, bg=LINE, bd=0)
        fr.pack(fill="both", expand=True, pady=(14, 0))
        txt = tk.Text(fr, height=height, bg=PANEL, fg="#c9d0db", insertbackground=TEXT, relief="flat", bd=0,
                      font=("Consolas" if sys.platform == "win32" else "Menlo", 9), wrap="word", padx=10, pady=8)
        txt.pack(fill="both", expand=True, padx=1, pady=1)
        txt.configure(state="disabled")
        self.log = txt
        return txt

    def show(self, n):
        self.page = n
        for i, lab in enumerate(self.step_labels):
            lab.configure(fg=TEXT if i == n else (ACC if i < n else MUTE), bg=LINE if i == n else PANEL,
                          font=self.F(11, "bold" if i == n else "normal"))
        self.clear()
        self.log = None
        self.b_back.configure(state="normal" if n in (1, 2, 3) else "disabled", command=self.back)
        self.b_next.configure(text=self.g("next"), state="normal", command=self.next)
        self.b_cancel.configure(text=self.g("cancel"), state="normal")
        self.b_adv.configure(state="disabled" if n == 0 else "normal")
        [self.page_lang, self.page_welcome, self.page_notice, self.page_check, self.page_install, self.page_done][n]()

    def page_lang(self):
        tk.Label(self.body, text=self.g("lang_title"), font=self.F(22, "bold"), bg=BG, fg=TEXT, anchor="w").pack(fill="x")
        self.p(self.g("lang_sub"), MUTE, 11, (8, 0))
        row = tk.Frame(self.body, bg=BG)
        row.pack(fill="x", pady=(40, 0))
        for L, name, sub in ((1, "English", "Installer in English"), (0, "Deutsch", "Installer auf Deutsch")):
            b = self._button(row, "%s\n%s" % (name, sub), lambda L=L: self.set_lang(L),
                             font=self.F(15, "bold"), padx=26, pady=24, justify="center",
                             highlightthickness=2, highlightbackground=ACC if L == self.L else LINE)
            b.pack(side="left", expand=True, fill="x", padx=(0, 16) if L == 1 else (0, 0))
        self.b_next.configure(state="disabled")
        self.b_back.configure(state="disabled")

    def page_welcome(self):
        self.h1(self.zi.PRODUCT)
        self.p(self.g("welcome_sub"), TEXT, 13, (4, 0))
        self.p(self.g("welcome_body") % self.zi.FW_NAME, pady=(16, 0))
        box = tk.Frame(self.body, bg=PANEL, highlightthickness=1, highlightbackground=LINE)
        box.pack(fill="x", pady=(20, 0))
        tk.Label(box, text=self.g("needs"), font=self.F(11, "bold"), bg=PANEL, fg=ACC, anchor="w").pack(fill="x", padx=16, pady=(12, 4))
        items = list(self.g("needs_list")) + ([self.g("needs_win")] if sys.platform == "win32" else [])
        for it in items:
            tk.Label(box, text="•  " + it, font=self.F(10), bg=PANEL, fg=TEXT, anchor="w", justify="left",
                     wraplength=500).pack(fill="x", padx=16, pady=1)
        tk.Frame(box, bg=PANEL, height=10).pack()

    def page_notice(self):
        self.h1(self.g("notice_title"))
        fr = tk.Frame(self.body, bg=LINE)
        fr.pack(fill="both", expand=True, pady=(12, 0))
        txt = tk.Text(fr, bg=PANEL, fg=TEXT, relief="flat", bd=0, wrap="word", padx=14, pady=12,
                      font=self.F(10), height=14)
        txt.pack(fill="both", expand=True, padx=1, pady=1)
        body = "\n".join(l for l in self.zi.disclaimer_text().strip("\n").splitlines() if not l.startswith("====")).strip()
        lines = [l.strip() for l in body.splitlines()]
        para, out = [], []
        for l in lines:                             # Zeilen der Konsolenfassung zu Absaetzen zusammenfuegen
            if not l: out.append(" ".join(para)); para = []; continue
            if l.startswith("- ") and para: out.append(" ".join(para)); para = []
            para.append(l)
        if para: out.append(" ".join(para))
        txt.insert("end", out[0] + "\n\n", "h")
        txt.insert("end", "\n\n".join(x.replace("- ", "•  ", 1) for x in out[1:]))
        txt.tag_configure("h", font=self.F(12, "bold"), foreground=ACC)
        txt.configure(state="disabled")
        self.agree = tk.IntVar(value=1 if self.accepted else 0)
        if FLAT:                                      # eigenes Haekchen aus einem Label (macOS)
            cb = tk.Label(self.body, font=self.F(10, "bold"), bg=BG, fg=TEXT, anchor="w", justify="left",
                          wraplength=540, cursor="hand2")
            def toggle(_=None):
                self.agree.set(0 if self.agree.get() else 1); self._agree_changed()
            cb.bind("<Button-1>", toggle)
            self._agree_label, self._agree_toggle = cb, toggle
        else:
            cb = tk.Checkbutton(self.body, text=self.g("agree"), variable=self.agree, command=self._agree_changed,
                                font=self.F(10, "bold"), bg=BG, fg=TEXT, selectcolor=PANEL, activebackground=BG,
                                activeforeground=TEXT, anchor="w", justify="left", wraplength=540, cursor="hand2")
            self._agree_label = None
        cb.pack(fill="x", pady=(12, 0))
        self._agree_changed()

    def _agree_changed(self):
        self.accepted = bool(self.agree.get())
        if getattr(self, "_agree_label", None) is not None:
            self._agree_label.configure(text=("☑  " if self.accepted else "☐  ") + self.g("agree"),
                                        fg=TEXT if self.accepted else MUTE)
        self.b_next.configure(state="normal" if self.accepted else "disabled")

    def page_check(self):
        self.h1(self.g("check_title"))
        self.p(self.g("check_sub"))
        self.status = tk.Label(self.body, text="", font=self.F(13, "bold"), bg=BG, fg=TEXT, anchor="w",
                               justify="left", wraplength=540)
        self.status.pack(fill="x", pady=(14, 0))
        self.log_box()
        self.b_next.configure(state="disabled")
        self.run_check()

    def run_check(self):
        self.status.configure(text=self.g("running"), fg=MUTE)
        self.b_next.configure(state="disabled", text=self.g("next"), command=self.next)
        self.kind = None

        def work():
            inst = self._installer()
            try:
                kind = inst.check()[0]
                self.bcd = getattr(inst, "bcd", None)
                self.bridge_trial = getattr(inst, "bridge_trial", None)
                return kind
            finally:
                inst.b.close()

        def done(res, err):
            if err is not None:
                self.status.configure(text=self.g("res_err"), fg=BAD)
                self.b_next.configure(text=self.g("check_again"), state="normal", command=self.run_check)
                return
            self.kind = res
            zi = self.zi
            if res in ("source", "older"):
                self.status.configure(text="✓  " + self.g("res_ok" if res == "source" else "res_update"), fg=OK)
                self.b_next.configure(state="normal")
            elif res == "target":
                self.status.configure(text="✓  " + self.g("res_done") % self.zi.FW_NAME, fg=OK)
                self.b_next.configure(state="normal", command=lambda: self.show(5))
            elif res in ("factory_empty", "factory_junk"):     # Zwischenschritt (Tester-Funktion)
                key = "verdict_bridge" if res == "factory_empty" else "verdict_bridge_junk"
                self.status.configure(text="✓  " + zi.t(key).strip(), fg=OK)
                self.b_next.configure(state="normal")
            elif res in ("bridge", "bridge_other"):
                q = self.bridge_trial or {"state": 0, "starts": 0, "max": 3}
                st = zi.t("bridge_state")
                text = zi.t("bridge_running", st[q["state"]] if q["state"] < len(st) else str(q["state"]),
                            q["starts"], q["max"]).strip()
                if res == "bridge_other":
                    self.status.configure(text="!  " + text + "\n" + zi.t("bridge_other_advice").strip(), fg=BAD)
                    self.b_next.configure(text=self.g("check_again"), state="normal", command=self.run_check)
                else:
                    self.status.configure(text="✓  " + text, fg=OK)
                    self.b_next.configure(state="normal")
            else:
                self.status.configure(text="✗  " + self.g("res_no"), fg=BAD)
                self.b_next.configure(text=self.g("check_again"), state="normal", command=self.run_check)

        self.start(work, done)

    def page_install(self):
        self.h1(self.g("inst_title"))
        self.p(self.g("inst_warn"), TEXT)
        self.prog = ttk.Progressbar(self.body, style="Z.Horizontal.TProgressbar", maximum=100)
        self.prog.pack(fill="x", pady=(18, 0))
        self.status = tk.Label(self.body, text="", font=self.F(11, "bold"), bg=BG, fg=MUTE, anchor="w",
                               justify="left", wraplength=540)
        self.status.pack(fill="x", pady=(8, 0))
        self.log_box(8)
        self.b_back.configure(state="normal")
        self.b_next.configure(text=self.g("inst_btn"), command=self.run_install)

    def run_install(self):
        if not self.accepted: self.show(2); return
        zi = self.zi
        bridge_kinds = ("factory_empty", "factory_junk", "bridge")
        # every decision is taken HERE in the main thread; the worker only gets keyed answers (gui_answers)
        self.gui_answers = {"disclaimer": True, "confirm": False, "tester": False, "junk": False, "refresh": False}
        if self.kind in ("factory_empty", "factory_junk"):
            if not self.dialog(zi.t("bridge_warn_gui")): return
            if self.bcd not in zi.FACTORY_BCD_OK:
                ver = zi.FACTORY_BCD_TESTER.get(self.bcd)
                if ver is None: return
                if not self.dialog(zi.t("bridge_untested", ver, zi.BRIDGE_LOG, zi.t("tester_word")).rsplit("\n", 1)[0].strip()):
                    return
                self.gui_answers["tester"] = True
            if self.kind == "factory_junk":
                if not self.dialog(zi.t("junk_confirm", zi.t("tester_word")).rsplit("\n", 1)[0].strip()): return
                self.gui_answers["junk"] = True
            self.gui_answers["confirm"] = True
        elif self.kind == "bridge":
            q = self.bridge_trial or {"starts": 0, "max": 3}
            if q["starts"] < 2:
                self.dialog(zi.t("bridge_handoff").strip(), question=False); return
            if not self.dialog(zi.t("bridge_refresh_ask", q["starts"], q["max"], zi.t("yes_word")).rsplit("?", 1)[0].strip() + "?"):
                self.dialog(zi.t("bridge_handoff").strip(), question=False); return
            self.gui_answers["refresh"] = True
        elif self.kind in ("source", "older"):
            if not self.dialog(self.g("inst_ask") % self.zi.FW_NAME): return
            self.gui_answers["confirm"] = True
        else:
            return
        expect = self.kind
        self.b_next.configure(state="disabled"); self.b_back.configure(state="disabled")
        self.status.configure(text=self.g("running"), fg=MUTE)
        self.prog["value"] = 0

        def work():
            inst = self._installer()
            inst.on_progress = lambda pct: self.q.put(("progress", pct))
            self.writing = True
            try:
                ok = inst.install(expect_kind=expect)
                return (ok, inst.last_backup, getattr(inst, "bridge_write_started", False),
                        getattr(inst, "bridge_result", None), getattr(inst, "bridge_msg", None))
            finally:
                self.writing = False
                inst.b.close()

        def done(res, err):
            if err is None and res[0] and expect in bridge_kinds:
                q = res[3] or {"starts": 1, "max": 3}
                self.prog["value"] = 100
                self.status.configure(text="✓  " + zi.t("bridge_written", q["starts"], q["max"]).strip(), fg=OK)
                self.dialog(zi.t("bridge_handoff").strip(), question=False)
                self.b_back.configure(state="normal")
                self.b_next.configure(state="normal", text=self.g("close"), command=self.quit)
                return
            if err is None and res[0]:
                self.backup_path = res[1]
                self.show(5); return
            if err is None and expect in bridge_kinds and res[2]:          # writing had started
                self.dialog(zi.t(res[4] or "bridge_fallback").strip(), question=False)
            self.status.configure(text="✗  " + (self.g("inst_fail") if err is not None or res[2] else zi.t("cancel")), fg=BAD)
            self.b_back.configure(state="normal")
            self.b_next.configure(state="normal")

        self.start(work, done)

    def page_done(self):
        self.h1(self.g("done_title"))
        tk.Label(self.body, text="✓", font=self.F(54, "bold"), bg=BG, fg=OK, anchor="w").pack(fill="x", pady=(6, 0))
        self.p(self.g("done_body") % self.zi.FW_NAME, TEXT, 11)
        bp = getattr(self, "backup_path", None)
        if bp:
            self.p(self.g("done_backup"), MUTE, 10, (18, 0))
            self.p(bp, MUTE, 9, (2, 0))
        self.b_back.configure(state="disabled")
        self.b_next.configure(text=self.g("close"), command=self.quit)
        self.b_cancel.configure(state="disabled")

    # ------------------------------------------------------------------ Navigation
    def next(self):
        if self.busy: return
        if self.page == 0: return
        if self.page == 2 and not self.accepted: return
        self.show(min(self.page + 1, 5))

    def back(self):
        if self.busy: return
        self.show(max(self.page - 1, 0))

    def quit(self):
        if self.writing:
            self.dialog(self.g("quit_busy"), question=False); return
        try: self.root.after_cancel(self._after)
        except Exception: pass
        self.root.destroy()

    # ------------------------------------------------------------------ Erweitert
    def advanced(self):
        if self.busy:
            self.dialog(self.g("busy"), question=False); return
        top = tk.Toplevel(self.root, bg=BG)
        top.title(self.g("adv_title"))
        top.transient(self.root)
        top.resizable(False, False)
        tk.Label(top, text=self.g("adv_title"), font=self.F(16, "bold"), bg=BG, fg=TEXT).pack(anchor="w", padx=24, pady=(20, 10))

        def go(fn):
            top.destroy(); fn()
        tk.Label(top, text=self.g("adv_auto"), font=self.F(9), bg=BG, fg=MUTE, wraplength=380,
                 justify="left").pack(anchor="w", padx=24, pady=(0, 8))
        rb = self._button(top, self.g("adv_restore"), lambda: go(self.do_restore))
        rb.pack(fill="x", padx=24, pady=4)
        if not self.accepted:
            rb.configure(state="disabled")
            tk.Label(top, text=self.g("adv_need"), font=self.F(9), bg=BG, fg=MUTE, wraplength=380,
                     justify="left").pack(anchor="w", padx=24)
        self._button(top, self.g("adv_folder"), lambda: go(self.open_folder)).pack(fill="x", padx=24, pady=(4, 20))

    def _task_page(self, title):
        """Backup/Wiederherstellen laufen auf der Pruef-Seite mit eigenem Titel und Protokoll."""
        self.page = 3
        self.clear()
        self.h1(title)
        self.status = tk.Label(self.body, text=self.g("running"), font=self.F(12, "bold"), bg=BG, fg=MUTE, anchor="w")
        self.status.pack(fill="x", pady=(12, 0))
        self.prog = ttk.Progressbar(self.body, style="Z.Horizontal.TProgressbar", maximum=100)
        self.prog.pack(fill="x", pady=(10, 0))
        self.log_box()
        self.b_back.configure(state="disabled")
        self.b_next.configure(state="disabled", text=self.g("next"))

    def _task_done(self, ok):
        self.status.configure(text=("✓" if ok else "✗"), fg=OK if ok else BAD)
        self.b_back.configure(state="normal", command=lambda: self.show(1))
        self.b_next.configure(state="normal", text=self.g("next"), command=lambda: self.show(1))

    def do_restore(self):
        os.makedirs(self.backup_dir, exist_ok=True)
        path = filedialog.askopenfilename(parent=self.root, initialdir=self.backup_dir, title=self.g("adv_restore"),
                                          filetypes=[("Z2 backup", "*.z2backup"), ("*", "*")])
        if not path: return
        if not self.dialog(self.g("restore_ask") % os.path.basename(path)):
            return
        self.gui_answers = {"confirm": True}                 # the user just confirmed in the dialog above
        self._task_page(self.g("adv_restore"))

        def work():
            inst = self._installer()
            inst.on_progress = lambda pct: self.q.put(("progress", pct))
            self.writing = True
            try: return inst.restore(path)
            finally:
                self.writing = False
                inst.b.close()
        self.start(work, lambda res, err: self._task_done(err is None and res))

    def open_folder(self):
        os.makedirs(self.backup_dir, exist_ok=True)
        try:
            if sys.platform == "win32": os.startfile(self.backup_dir)
            elif sys.platform == "darwin": os.system('open "%s"' % self.backup_dir)
            else: os.system('xdg-open "%s"' % self.backup_dir)
        except Exception:
            pass

    # ------------------------------------------------------------------ Hintergrund-Arbeit
    def _installer(self):
        return self.zi.Installer(self.zi.make_backend(), self.backup_dir, make_gui_ask(self.zi, self))

    def start(self, work, done):
        self.busy = True
        self.b_adv.configure(state="disabled")
        # while the worker runs, "Weiter" must not look clickable: grey + "Bitte warten ..." (Windows keeps the
        # orange background of a disabled tk.Button, which looked active - tester feedback 26.11.2026)
        self._next_text = self.b_next.cget("text")
        self.b_next.configure(state="disabled", text=self.g("running"))
        self._sync_buttons()

        def run():
            res, err = None, None
            try:
                res = work()
            except Exception as e:              # Z2Error, OSError, alles andere: ins Protokoll
                err = e
                self.q.put(("log", "\n%s\n" % self.zi.t("err", e)))
            self.q.put(("done", (done, res, err)))
        threading.Thread(target=run, daemon=True).start()

    def _sync_buttons(self):
        """A disabled button looks disabled (grey, arrow cursor); an enabled primary button is orange again."""
        for b, primary in ((self.b_next, True), (self.b_back, False), (self.b_cancel, False), (self.b_adv, False)):
            try:
                off = str(b.cget("state")) == "disabled"
                b.configure(bg=PANEL if (off or not primary) else ACC, cursor="arrow" if off else "hand2",
                            highlightbackground=LINE)
            except (tk.TclError, AttributeError):
                pass

    def _pump(self):
        try:
            while True:
                kind, val = self.q.get_nowait()
                if kind == "log" and self.log is not None:
                    self.log.configure(state="normal")
                    self.log.insert("end", val.replace("\r", ""))
                    self.log.see("end")
                    self.log.configure(state="disabled")
                elif kind == "progress" and getattr(self, "prog", None) is not None:
                    try: self.prog["value"] = val
                    except tk.TclError: pass
                elif kind == "done":
                    self.busy = False
                    self.b_adv.configure(state="normal")
                    if self.b_next.cget("text") == self.g("running"):
                        self.b_next.configure(text=getattr(self, "_next_text", self.g("next")))
                    fn, res, err = val
                    fn(res, err)
                    self._sync_buttons()
        except queue.Empty:
            pass
        self._sync_buttons()                        # also catches state changes made outside start()/done
        self._after = self.root.after(60, self._pump)


def run(zi, backup_dir, intro=True):
    old = sys.stdout
    try:
        app = App(zi, backup_dir, intro)
        app.root.mainloop()
    finally:
        sys.stdout = old
    return 0
