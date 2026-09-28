"""Actual runnable stdlib/Tk GUI for offline FA3 environment preview.

Qt 6/QML is the primary integration target; this fallback is intentionally
usable and screenshot-testable without downloading any GUI packages.
"""
from __future__ import annotations

import json
import math
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from .engine import LOCATIONS, WORLDS, WorldProject

BG = "#0b121d"
SIDE = "#121f30"
PANEL = "#17283b"
EDGE = "#30455a"
TEXT = "#eef6ff"
MUTED = "#a3bdd0"
CYAN = "#4ad8ed"
BLUE = "#478ff4"
AMBER = "#ffce64"
MINT = "#73dfb0"


class WorldEventTk(tk.Tk):
    def __init__(self, project: WorldProject | None = None):
        super().__init__()
        self.project = project or WorldProject()
        self.title("FA3 World & Environment Studio | World & Event Director")
        self.geometry("1550x1040")
        self.minsize(1240, 785)
        self.configure(bg=BG)
        self.option_add("*Font", ("DejaVu Sans", 10))
        self._style()
        self.view = tk.StringVar(value="ALL")
        self.location = tk.StringVar(value=self.project.anchor.place)
        self.date = tk.StringVar(value=self.project.anchor.date)
        self.clock = tk.StringVar(value=self.project.anchor.local_time or "")
        self.mode = tk.StringVar(value=self.project.world_mode)
        self.temp = tk.DoubleVar(value=self.project.weather.temperature_c)
        self.rain = tk.DoubleVar(value=self.project.weather.rain_mm_h)
        self.wind = tk.DoubleVar(value=self.project.weather.wind_kmh)
        self.cloud = tk.DoubleVar(value=self.project.weather.cloud_percent)
        self.event_kind = tk.StringVar(value="STORM")
        self.minute = tk.IntVar(value=0)
        self._draw_ui()
        self.refresh()

    def _style(self):
        st = ttk.Style(self)
        st.theme_use("clam")
        st.configure("FA3.TCombobox", foreground=TEXT, fieldbackground=PANEL, background=PANEL, bordercolor=EDGE,
                     arrowcolor=CYAN, padding=(8, 5))
        st.map("FA3.TCombobox", fieldbackground=[("readonly", PANEL)], foreground=[("readonly", TEXT)])
        st.configure("FA3.Horizontal.TScale", background=SIDE, troughcolor=EDGE, sliderlength=18)

    def label(self, parent, s, size=10, color=TEXT, bold=False, bg=BG, **kw):
        return tk.Label(parent, text=s, font=("DejaVu Sans", size, "bold" if bold else "normal"),
                        bg=bg, fg=color, anchor="w", **kw)

    def button(self, parent, text, command, emphasis=False):
        return tk.Button(parent, text=text, command=command, relief="flat", cursor="hand2",
                         bg=BLUE if emphasis else PANEL, fg=TEXT, activebackground=CYAN,
                         activeforeground=BG, highlightthickness=0, padx=12, pady=8, borderwidth=0,
                         font=("DejaVu Sans", 9, "bold"))

    def _draw_ui(self):
        top = tk.Frame(self, bg=BG, height=83)
        top.pack(fill="x", padx=20, pady=(12, 5))
        top.pack_propagate(False)
        self.label(top, "◈  FA3 WORLD & ENVIRONMENT STUDIO", 17, TEXT, True).pack(side="left", pady=12)
        self.label(top, "WORLD & EVENT DIRECTOR   ·   LOCAL CPU PREVIEW", 9, CYAN, True).pack(side="right", pady=20)
        separator = tk.Frame(self, bg=EDGE, height=1)
        separator.pack(fill="x", padx=20)

        context = tk.Frame(self, bg=BG, height=48)
        context.pack(fill="x", padx=20, pady=8)
        self.label(context, "HELY", 9, MUTED, True).pack(side="left", padx=(0, 7))
        ttk.Combobox(context, textvariable=self.location, state="readonly", values=list(LOCATIONS),
                     width=15, style="FA3.TCombobox").pack(side="left", padx=(0, 16))
        self.label(context, "DÁTUM", 9, MUTED, True).pack(side="left", padx=(0, 7))
        tk.Entry(context, textvariable=self.date, width=13, bg=PANEL, fg=TEXT, insertbackground=TEXT,
                 relief="flat", font=("DejaVu Sans", 10)).pack(side="left", padx=(0, 16), ipady=8)
        self.label(context, "IDŐ", 9, MUTED, True).pack(side="left", padx=(0, 7))
        tk.Entry(context, textvariable=self.clock, width=6, bg=PANEL, fg=TEXT, insertbackground=TEXT,
                 relief="flat").pack(side="left", padx=(0, 16), ipady=8)
        self.label(context, "VILÁG", 9, MUTED, True).pack(side="left", padx=(0, 7))
        ttk.Combobox(context, textvariable=self.mode, state="readonly", values=WORLDS,
                     width=19, style="FA3.TCombobox").pack(side="left", padx=(0, 12))
        self.button(context, "ALKALMAZ", self.apply_context, True).pack(side="left")
        self.button(context, "MEGNYITÁS", self.open_project).pack(side="right", padx=(5, 0))
        self.button(context, "MENTÉS", self.save_project).pack(side="right")

        body = tk.Frame(self, bg=BG)
        body.pack(fill="both", expand=True, padx=20, pady=(5, 0))
        body.columnconfigure(0, weight=0, minsize=210)
        body.columnconfigure(1, weight=1)
        body.columnconfigure(2, weight=0, minsize=284)
        body.rowconfigure(0, weight=1)
        left = tk.Frame(body, bg=SIDE, width=210, highlightthickness=1, highlightbackground=EDGE)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        left.grid_propagate(False)
        self.label(left, "  VILÁG & ESEMÉNYEK", 12, TEXT, True, SIDE).pack(fill="x", pady=(17, 18), padx=10)
        for txt, key in (("◉  NÉGY KÖRNYEZET", "ALL"), ("◭  TERMÉSZET", "NATURAL"),
                         ("▦  TELEPÜLÉS", "CITY"), ("⌂  ÉPÜLET", "BUILDING"),
                         ("▤  BELSŐ TEREK", "INTERIOR")):
            b = self.button(left, txt, lambda k=key: self.set_view(k))
            b.pack(fill="x", padx=10, pady=3)
        tk.Frame(left, bg=EDGE, height=1).pack(fill="x", padx=16, pady=18)
        self.label(left, "  JELENSÉGEK", 11, MUTED, True, SIDE).pack(fill="x", padx=10)
        self.label(left, "  • zivatar · hó · szél · köd", 10, TEXT, bg=SIDE).pack(fill="x", padx=10, pady=(11, 5))
        self.label(left, "  • árvíz · tűz · földrengés", 10, TEXT, bg=SIDE).pack(fill="x", padx=10)
        tk.Frame(left, bg=EDGE, height=1).pack(fill="x", padx=16, pady=18)
        self.label(left, "  ELKÜLÖNÍTETT RÉTEGEK", 9, MUTED, True, SIDE).pack(fill="x", padx=10)
        self.label(left, "  FÖLDRAJZ / NAPÁLLÁS", 9, MINT, True, SIDE).pack(fill="x", padx=10, pady=(10, 3))
        self.label(left, "  NARRATÍV ESEMÉNYEK", 9, AMBER, True, SIDE).pack(fill="x", padx=10)
        self.label(left, "  VILÁGSZABÁLYOK", 9, CYAN, True, SIDE).pack(fill="x", padx=10, pady=(3, 0))

        center = tk.Frame(body, bg=BG)
        center.grid(row=0, column=1, sticky="nsew", padx=(0, 10))
        tk.Frame(center, bg=PANEL, height=38).pack(fill="x")
        self.viewtitle = self.label(center, "   KÖRNYEZETI ÁTTEKINTÉS · 4 TÉRBELI LÉPTÉK", 11, TEXT, True, PANEL)
        self.viewtitle.pack(fill="x", pady=(4, 0))
        self.canvas = tk.Canvas(center, bg="#172d45", highlightthickness=1, highlightbackground=EDGE,
                                width=930, height=446)
        self.canvas.pack(fill="both", expand=True, pady=(9, 0))
        self.canvas.bind("<Configure>", lambda _ev: self._draw_scene())
        info = tk.Frame(center, bg=SIDE, height=68, highlightthickness=1, highlightbackground=EDGE)
        info.pack(fill="x", pady=(10, 0))
        self.sunlabel = self.label(info, "Napállás számítása...", 11, AMBER, True, SIDE)
        self.sunlabel.pack(fill="x", padx=14, pady=(11, 0))
        self.scope_label = self.label(info, "A jelenet minden léptéke ugyanahhoz a környezeti eseményhez kapcsolódik.", 9, MUTED, bg=SIDE)
        self.scope_label.pack(fill="x", padx=14, pady=(4, 10))

        right = tk.Frame(body, bg=SIDE, width=284, highlightthickness=1, highlightbackground=EDGE)
        right.grid(row=0, column=2, sticky="nsew")
        right.grid_propagate(False)
        self.label(right, "  IDŐJÁRÁS & HATÁSOK", 12, TEXT, True, SIDE).pack(fill="x", pady=(18, 10), padx=10)
        self.entries = []
        for name, var, start, end, unit in (("HŐMÉRSÉKLET", self.temp, -20, 45, "°C"),
                                          ("CSAPADÉK", self.rain, 0, 60, "mm/h"),
                                          ("SZÉL", self.wind, 0, 120, "km/h"),
                                          ("FELHŐZET", self.cloud, 0, 100, "%")):
            row = tk.Frame(right, bg=SIDE)
            row.pack(fill="x", padx=18, pady=7)
            tk.Label(row, text=name, bg=SIDE, fg=MUTED, font=("DejaVu Sans", 9, "bold")).pack(side="left")
            value = tk.Label(row, text="", bg=SIDE, fg=CYAN, font=("DejaVu Sans", 10, "bold"))
            value.pack(side="right")
            scale = ttk.Scale(right, variable=var, from_=start, to=end, style="FA3.Horizontal.TScale",
                              command=lambda _v, v=var, t=value, suffix=unit: self._adjust(v, t, suffix))
            scale.pack(fill="x", padx=18, pady=(0, 3))
            self.entries.append((var, value, unit))
        tk.Frame(right, bg=EDGE, height=1).pack(fill="x", padx=16, pady=12)
        self.label(right, "  FORGATÓKÖNYVI ESEMÉNY", 9, AMBER, True, SIDE).pack(fill="x", padx=10)
        ttk.Combobox(right, textvariable=self.event_kind, values=("STORM", "FLOOD", "FIRE", "EARTHQUAKE", "SNOW", "TREX", "ALIEN"),
                     state="readonly", style="FA3.TCombobox").pack(fill="x", padx=18, pady=(11, 8))
        self.button(right, "+ ESEMÉNY HOZZÁADÁSA", self.add_event, emphasis=True).pack(fill="x", padx=18)
        self.button(right, "FÖLDI ALAP VISSZAÁLLÍTÁSA", self.reset_rules).pack(fill="x", padx=18, pady=(12, 0))
        self.button(right, "VILÁGSZABÁLY MÓDOSÍTÁSA…", self.confirm_world_rule).pack(fill="x", padx=18, pady=4)
        tk.Frame(right, bg=EDGE, height=1).pack(fill="x", padx=16, pady=12)
        self.label(right, "  FORRÁS / BIZONYOSSÁG", 9, MUTED, True, SIDE).pack(fill="x", padx=10)
        self.label(right, "  FÖLDRAJZ: MINTAHELY", 9, MINT, True, SIDE).pack(fill="x", padx=10, pady=(10, 4))
        self.label(right, "  NAPÁLLÁS: SZÁMÍTOTT", 9, MINT, True, SIDE).pack(fill="x", padx=10)
        self.label(right, "  IDŐJÁRÁS: KITALÁLT ADAT", 9, AMBER, True, SIDE).pack(fill="x", padx=10, pady=(4, 0))
        self.label(right, "  KORABELI UTCASZINT: ISMERETLEN", 8, MUTED, True, SIDE).pack(fill="x", padx=10, pady=(4, 0))

        timeline = tk.Frame(self, bg=SIDE, height=146, highlightthickness=1, highlightbackground=EDGE)
        timeline.pack(fill="x", padx=20, pady=(10, 5))
        timeline.pack_propagate(False)
        bar = tk.Frame(timeline, bg=SIDE)
        bar.pack(fill="x", padx=14, pady=(10, 5))
        self.label(bar, "ESEMÉNY-IDŐVONAL", 10, TEXT, True, SIDE).pack(side="left")
        self.button(bar, "SHOT HANDOFF JSON", self.export_handoff).pack(side="right")
        self.timeliner = tk.Canvas(timeline, bg=SIDE, height=89, highlightthickness=0)
        self.timeliner.pack(fill="both", expand=True, padx=15, pady=(0, 8))
        self.timeliner.bind("<Configure>", lambda _e: self._draw_timeline())
        self.timeliner.bind("<Button-1>", self.timeline_click)

        status = tk.Frame(self, bg=BG, height=30)
        status.pack(fill="x", padx=20, pady=(0, 5))
        self.status = self.label(status, "● CPU-only demó · helyi, determinisztikus előnézet; nem meteorológiai mérés", 9, MINT)
        self.status.pack(side="left")
        self.label(status, "HRB: nincs tényleges runtime-admission állítás", 9, MUTED).pack(side="right")

    def _adjust(self, var, t, suffix):
        t.configure(text=f"{var.get():.0f} {suffix}")
        self.project.weather.temperature_c = round(self.temp.get(), 1)
        self.project.weather.rain_mm_h = round(self.rain.get(), 1)
        self.project.weather.wind_kmh = round(self.wind.get(), 1)
        self.project.weather.cloud_percent = round(self.cloud.get())
        self.refresh()

    def apply_context(self):
        try:
            if self.location.get() != self.project.anchor.place:
                self.project.use_location(self.location.get())
            self.project.anchor.date = self.date.get()
            self.project.anchor.local_time = self.clock.get() or None
            self.project.world_mode = self.mode.get()
            self.project.validate()
        except Exception as exc:
            messagebox.showerror("Hely / idő", str(exc), parent=self)
            return
        self.status.configure(text="● A földrajzi és csillagászati alap frissült; a narratív események megmaradtak.")
        self.refresh()

    def set_view(self, mode):
        self.view.set(mode)
        self.refresh()

    def add_event(self):
        event = self.project.add_event(self.event_kind.get(), minute=self.minute.get())
        self.status.configure(text=f"● Narratív esemény hozzáadva: {event.kind}; a Nap pályája változatlan.")
        self.refresh()

    def reset_rules(self):
        self.project.restore_earth_rules()
        self.refresh()

    def confirm_world_rule(self):
        if messagebox.askyesno("Világszabály-felülírás", "Két valódi Napra módosítod a bolygó szabályait?\nA földi napállás ettől fogva nem irányadó.", parent=self):
            self.project.approve_world_rule("TWO_SUNS", approved=True)
            self.status.configure(text="● KÜLÖN JÓVÁHAGYOTT VILÁGSZABÁLY: TWO_SUNS · földi efemerisz nem használható")
            self.refresh()

    def save_project(self):
        p = filedialog.asksaveasfilename(defaultextension=".fa3world", filetypes=[("FA3 világprojekt", "*.fa3world")], parent=self)
        if p:
            try:
                self.project.save(p)
                self.status.configure(text=f"● Projekt mentve: {Path(p).name}")
            except Exception as exc:
                messagebox.showerror("Mentési hiba", str(exc), parent=self)

    def open_project(self):
        p = filedialog.askopenfilename(filetypes=[("FA3 világprojekt", "*.fa3world")], parent=self)
        if p:
            try:
                self.project = WorldProject.load(p)
                self.location.set(self.project.anchor.place)
                self.date.set(self.project.anchor.date)
                self.clock.set(self.project.anchor.local_time or "")
                self.mode.set(self.project.world_mode)
                for var, val in ((self.temp, self.project.weather.temperature_c), (self.rain, self.project.weather.rain_mm_h),
                                 (self.wind, self.project.weather.wind_kmh), (self.cloud, self.project.weather.cloud_percent)):
                    var.set(val)
                self.refresh()
            except Exception as exc:
                messagebox.showerror("Megnyitási hiba", str(exc), parent=self)

    def export_handoff(self):
        p = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("Shot handoff", "*.json")], parent=self)
        if p:
            Path(p).write_text(json.dumps(self.project.shot_handoff(minute=self.minute.get()),
                                           ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            self.status.configure(text=f"● Shot-handoff JSON: {Path(p).name}; nem FA3 Video Editor projekt")

    def timeline_click(self, event):
        w = max(1, self.timeliner.winfo_width() - 180)
        self.minute.set(max(0, min(60, round((event.x - 135)/w*60))))
        self.refresh()

    def refresh(self):
        for var, label, unit in self.entries:
            label.configure(text=f"{var.get():.0f} {unit}")
        sky = self.project.sky_context()
        sun = sky["sun"] if not self.project.planetary_rule_override else None
        if sun:
            solar = f"NAP: {sun['elevation_deg']:.1f}° magasság · {sun['azimuth_deg_true_north']:.1f}° É-tól · {sky['season']}"
        elif self.project.planetary_rule_override:
            solar = "EGYEDI VILÁGSZABÁLY · földi napállás külön jóváhagyással felülírva"
        else:
            solar = f"NAPÁLLÁS ISMERETLEN (nincs óramegadás) · {sky['season']}"
        self.sunlabel.configure(text="☼   " + solar)
        self.scope_label.configure(text=f"{self.project.anchor.continent} · {self.project.anchor.hemisphere} félteke · {sky['daypart']} · időjárás: KITALÁLT ADAT")
        self._draw_scene()
        self._draw_timeline()

    def _draw_scene(self):
        if not hasattr(self, "canvas"):
            return
        c = self.canvas
        c.delete("all")
        width = max(640, c.winfo_width())
        height = max(340, c.winfo_height())
        pad = 13
        gap = 12
        box_w = (width - 2*pad - gap)/2
        box_h = (height - 2*pad - gap)/2
        panels = [((pad, pad), "NATURAL", "01   TERMÉSZET / TÁJ"),
                  ((pad+box_w+gap, pad), "CITY", "02   LAKOTT TERÜLET"),
                  ((pad, pad+box_h+gap), "BUILDING", "03   ÉPÜLETKÖRNYEZET"),
                  ((pad+box_w+gap, pad+box_h+gap), "INTERIOR", "04   ÉPÜLET BELSEJE")]
        for (x,y), scope, title in panels:
            dim = self.view.get() not in ("ALL", scope)
            back = "#142538" if dim else "#1f364c"
            c.create_rectangle(x,y,x+box_w,y+box_h,fill=back,outline="#37536c",width=1)
            c.create_rectangle(x+1,y+1,x+box_w-1,y+31,fill="#15293c",outline="")
            c.create_text(x+13,y+16,text=title,anchor="w",fill=MUTED,font=("DejaVu Sans",10,"bold"))
            if dim:
                c.create_text(x+box_w/2,y+box_h/2,text="KIVÁLASZTOTT NÉZETEN KÍVÜL",fill="#66829a",font=("DejaVu Sans",10))
                continue
            self._panel_scene(c,x,y+33,box_w,box_h-34,scope)
            facts = self.project.effects(self.minute.get())[scope]
            footer = ";  ".join(facts[:2]) if facts else "Nincs aktív hatás ezen a léptéken"
            if len(footer)>68:footer=footer[:65]+"..."
            c.create_rectangle(x+1,y+box_h-27,x+box_w-1,y+box_h-1,fill="#122338",outline="")
            c.create_text(x+12,y+box_h-14,text=footer,anchor="w",fill=MINT if facts else MUTED,font=("DejaVu Sans",8))
        c.create_text(width-27,24,text="N ↑",anchor="e",fill=AMBER,font=("DejaVu Sans",12,"bold"))

    def _panel_scene(self,c,x,y,w,h,scope):
        rain=self.project.weather.rain_mm_h
        wind=self.project.weather.wind_kmh
        cloudy=self.project.weather.cloud_percent
        # All drawn shapes are the actual interactive preview's deterministic vector output.
        c.create_rectangle(x+1,y,x+w-1,y+h-26,fill="#243e54" if cloudy>=50 else "#426f97",outline="")
        cy = y+h-49
        c.create_oval(x+w*.72,y+5,x+w*.72+38,y+43,fill="#ffdb86",outline="")
        if scope=="NATURAL":
            c.create_polygon(x+1,cy,x+w*.32,y+42,x+w*.53,cy,fill="#547b73",outline="")
            c.create_polygon(x+w*.27,cy,x+w*.66,y+30,x+w-2,cy,fill="#376a68",outline="")
            c.create_rectangle(x+2,cy,x+w-2,y+h-27,fill="#3b6858",outline="")
            for t in range(6):
                tx=x+25+t*(w-50)/6
                ty=cy-16-(t%2)*9
                c.create_line(tx,ty+17,tx,cy+7,fill="#6f573d",width=4)
                c.create_polygon(tx-12,ty+11,tx,ty-14,tx+13,ty+11,fill="#397d65",outline="")
        elif scope=="CITY":
            c.create_rectangle(x+1,cy-33,x+w-2,cy+29,fill="#44515b",outline="")
            for idx in range(6):
                bx=x+14+idx*(w-28)/6
                bh=45+(idx%3)*13
                c.create_rectangle(bx,cy-bh,bx+43,cy-9,fill=["#8b989a","#8b7774","#a09380"][idx%3],outline="#3a4450")
                for xx in range(3):
                    for yy in range(3):
                        c.create_rectangle(bx+5+xx*13,cy-bh+8+yy*14,bx+12+xx*13,cy-bh+16+yy*14,fill="#dfbc83",outline="")
            c.create_rectangle(x+1,cy+23,x+w-2,y+h-27,fill="#3c4b58",outline="")
            if rain>1:
                for t in range(4):
                    px=x+60+t*(w-100)/4
                    c.create_oval(px,cy+26,px+36,cy+32,fill="#669db0",outline="")
        elif scope=="BUILDING":
            c.create_rectangle(x+1,cy,x+w-2,y+h-27,fill="#4a6659",outline="")
            bx=x+w*.29; by=cy-56
            c.create_rectangle(bx,by,bx+w*.42,cy+8,fill="#a8a094",outline="#d2bbb0",width=2)
            c.create_polygon(bx-11,by+1,bx+w*.21,by-43,bx+w*.42+11,by+1,fill="#8d6056",outline="")
            for col in range(2):
                win=bx+21+col*w*.19
                c.create_rectangle(win,by+17,win+27,by+47,fill="#91c7d5",outline="#cfe2df",width=2)
            c.create_line(bx+w*.42+7,by,bx+w*.42+7,cy+3,fill="#d5eced",width=4)
            if rain>5:
                c.create_line(bx+w*.42+7,cy+3,bx+w*.42+20,cy+16,fill="#72c6f4",width=3)
        else:
            c.create_rectangle(x+1,y+2,x+w-2,y+h-27,fill="#687b83",outline="")
            c.create_rectangle(x+w*.14,y+20,x+w*.55,cy+9,fill="#a9a6a0",outline="#dde4e9",width=4)
            c.create_rectangle(x+w*.175,y+28,x+w*.515,cy+1,fill="#5d8da5",outline="")
            c.create_line(x+w*.345,y+26,x+w*.345,cy+6,fill="#d1dde4",width=4)
            c.create_rectangle(x+w*.04,cy+10,x+w*.92,y+h-27,fill="#8b7568",outline="")
            c.create_rectangle(x+w*.62,cy-35,x+w*.87,cy+13,fill="#b5a391",outline="#665b56",width=2)
            if rain>=15 and wind>=25:
                c.create_line(x+w*.50,y+29,x+w*.57,cy+12,fill="#75cdf5",width=4)
                c.create_oval(x+w*.48,cy+7,x+w*.69,cy+20,fill="#79b3c9",outline="")
        if cloudy>=30:
            for idx in range(2 if cloudy<70 else 3):
                px=x+w*(.12+.24*idx)
                py=y+14+(idx%2)*8
                for dx,dy,rad in ((0,4,12),(15,0,17),(30,6,12)):
                    c.create_oval(px+dx-rad,py+dy-rad/2,px+dx+rad,py+dy+rad/1.3,fill="#afc5d0",outline="")
        if rain>0 and scope!="INTERIOR":
            count=15+min(55,int(rain*1.3))
            for i in range(count):
                # fixed deterministic pattern, not random pixels
                px=x+12+((i*73+self.project.seed%31) % max(15,int(w-25)))
                py=y+47+((i*41)%max(20,int(h-91)))
                c.create_line(px,py,px-3-min(8,wind/15),py+10,fill="#a1dfff",width=1)
        if wind>15:
            c.create_line(x+w-78,y+16,x+w-28,y+16,fill=CYAN,width=2,arrow="last")
            c.create_text(x+w-84,y+16,text="SZÉL",anchor="e",fill=CYAN,font=("DejaVu Sans",8,"bold"))

    def _draw_timeline(self):
        if not hasattr(self,"timeliner"):
            return
        c=self.timeliner
        c.delete("all")
        width=max(650,c.winfo_width())
        labels=[("NAP / ÉVSZAK",AMBER), ("IDŐJÁRÁS",CYAN), ("NARRATÍV ESEMÉNY", "#ed9f78")]
        left=140; right=width-20
        for row,(title,color) in enumerate(labels):
            yy=17+row*28
            c.create_text(4,yy,text=title,anchor="w",fill=color,font=("DejaVu Sans",8,"bold"))
            c.create_line(left,yy,right,yy,fill="#395267",width=6)
        sky=self.project.sky_context()
        sun=sky["sun"]
        if sun:
            c.create_text(left+10,17,text=f"{sky['season']} · {sun['elevation_deg']}°",anchor="w",fill=AMBER,font=("DejaVu Sans",8,"bold"))
        else:
            c.create_text(left+10,17,text="napállás ismeretlen / egyedi",anchor="w",fill=AMBER,font=("DejaVu Sans",8))
        c.create_line(left,45,right,45,fill="#347696",width=6 if self.project.weather.rain_mm_h>0 else 2)
        c.create_text(left+10,45,text=f"{self.project.weather.rain_mm_h:.0f} mm/h · KITALÁLT",anchor="w",fill="#d7eff5",font=("DejaVu Sans",8,"bold"))
        for e in self.project.events:
            if not e.enabled:continue
            x=left+e.minute/60*(right-left)
            c.create_polygon(x,64,x+5,73,x,82,x-5,73,fill="#ed9f78",outline="")
            c.create_text(min(x+7,right-100),73,text=e.kind,anchor="w",fill=TEXT,font=("DejaVu Sans",8))
        px=left+self.minute.get()/60*(right-left)
        c.create_line(px,1,px,86,fill=BLUE,width=2)
        c.create_text(px+5,2,text=f"+{self.minute.get()} perc",anchor="nw",fill=TEXT,font=("DejaVu Sans",8,"bold"))


def run_tk(screenshot: str | None = None) -> int:
    app=WorldEventTk()
    if screenshot:
        from PIL import ImageGrab
        def capture():
            app.update_idletasks()
            box=(app.winfo_rootx(),app.winfo_rooty(),app.winfo_rootx()+app.winfo_width(),app.winfo_rooty()+app.winfo_height())
            ImageGrab.grab(bbox=box).save(screenshot, optimize=True)
            app.after(50,app.destroy)
        app.after(600,capture)
    app.mainloop()
    return 0
