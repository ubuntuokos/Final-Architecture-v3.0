"""Qt 6 / QML primary FA3 world and environment desktop frontend.

Requires optional PySide6 installed into a Python virtual environment. Core
engine and Tk CPU preview do not require the Qt runtime.
"""
from __future__ import annotations

import json
from pathlib import Path
from PySide6.QtCore import QObject, Property, QUrl, Signal, Slot
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine
from .engine import LOCATIONS, WorldProject


class WorldController(QObject):
    revisionChanged = Signal()

    def __init__(self, project: WorldProject):
        super().__init__()
        self.project = project
        self._message = "CPU előnézet · időjárás: KITALÁLT ADAT · nincs aktuális HRB-runtime igazolás"

    def _notify(self, message: str | None = None):
        if message:
            self._message = message
        self.revisionChanged.emit()

    @Property(str, notify=revisionChanged)
    def place(self):return self.project.anchor.place

    @Property(str, notify=revisionChanged)
    def date(self):return self.project.anchor.date

    @Property(str, notify=revisionChanged)
    def clock(self):return self.project.anchor.local_time or ""

    @Property(str, notify=revisionChanged)
    def mode(self):return self.project.world_mode

    @Property(str, notify=revisionChanged)
    def sky(self):
        sky=self.project.sky_context()
        sun=sky["sun"]
        if self.project.planetary_rule_override:
            return "Jóváhagyott egyedi világszabály: " + self.project.planetary_rule_override
        if sun is None:
            return f"Napállás ismeretlen · {sky['season']} · óra nincs megadva"
        return (f"Nap: {sun['elevation_deg']:.1f}° · irány {sun['azimuth_deg_true_north']:.1f}° É-tól  "
                f"· {sky['season']} · történeti UTC {sky['utc_offset']}")

    @Property(str, notify=revisionChanged)
    def status(self):return self._message

    @Property(str, notify=revisionChanged)
    def events(self):return "  ·  ".join(e.kind for e in self.project.events if e.enabled) or "Nincs esemény"

    @Property(float, notify=revisionChanged)
    def temperature(self):return self.project.weather.temperature_c

    @Property(float, notify=revisionChanged)
    def rain(self):return self.project.weather.rain_mm_h

    @Property(float, notify=revisionChanged)
    def wind(self):return self.project.weather.wind_kmh

    @Property(float, notify=revisionChanged)
    def cloud(self):return float(self.project.weather.cloud_percent)

    @Property(str, notify=revisionChanged)
    def impactNatural(self):return " · ".join(self.project.effects()["NATURAL"]) or "Nincs aktív hatás"

    @Property(str, notify=revisionChanged)
    def impactCity(self):return " · ".join(self.project.effects()["CITY"]) or "Nincs aktív hatás"

    @Property(str, notify=revisionChanged)
    def impactBuilding(self):return " · ".join(self.project.effects()["BUILDING"]) or "Nincs aktív hatás"

    @Property(str, notify=revisionChanged)
    def impactInterior(self):return " · ".join(self.project.effects()["INTERIOR"]) or "Nincs aktív hatás"

    @Slot(str,str,str,str)
    def applyContext(self,place,day,clock,mode):
        try:
            updated=WorldProject.from_dict(self.project.to_dict())
            if place in LOCATIONS:
                updated.use_location(place)
            else:
                raise ValueError("Ismeretlen demóhelyszín")
            updated.anchor.date=day
            updated.anchor.local_time=clock or None
            updated.world_mode=mode
            updated.validate()
            self.project=updated
            self._notify("Hely és idő frissült; a történet külön rétegben megmaradt.")
        except Exception as exc:
            self._notify("HIBA: " +str(exc))

    @Slot(float,float,float,float)
    def updateWeather(self,temp,rain,wind,cloud):
        self.project.weather.temperature_c=round(temp,1)
        self.project.weather.rain_mm_h=round(rain,1)
        self.project.weather.wind_kmh=round(wind,1)
        self.project.weather.cloud_percent=round(cloud)
        self._notify("KITALÁLT időjárási előnézet frissült · 4 térbeli lépték")

    @Slot(str)
    def addEvent(self,kind):
        try:
            self.project.add_event(kind)
            self._notify("Narratív esemény: "+kind+"; a Föld földrajza és napállása változatlan.")
        except Exception as exc:
            self._notify("HIBA: "+str(exc))

    @Slot()
    def restoreEarth(self):
        self.project.restore_earth_rules()
        self._notify("Földi napállás és égtájak helyreállítva")

    @Slot()
    def approveTwoSuns(self):
        # Called only from the user-accepted QML dialog's onAccepted handler.
        self.project.approve_world_rule("TWO_SUNS",approved=True)
        self._notify("KÜLÖN JÓVÁHAGYOTT világszabály: két valódi Nap; Earth efemerisz nem használható")

    @Slot(str)
    def save(self,path):
        try:
            result=self.project.save(path)
            self._notify("Mentve: "+str(result))
        except Exception as exc:
            self._notify("MENTÉSI HIBA: "+str(exc))

    @Slot(str)
    def load(self,path):
        try:
            self.project=WorldProject.load(path)
            self._notify("Projekt megnyitva: "+path)
        except Exception as exc:
            self._notify("MEGNYITÁSI HIBA: "+str(exc))

    @Slot(str)
    def exportShot(self,path):
        try:
            Path(path).write_text(json.dumps(self.project.shot_handoff(),ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
            self._notify("Shot handoff JSON: "+path)
        except Exception as exc:
            self._notify("EXPORT HIBA: "+str(exc))


def run_qt(project: WorldProject | None = None) -> int:
    import sys
    app=QGuiApplication(sys.argv)
    engine=QQmlApplicationEngine()
    controller=WorldController(project or WorldProject())
    engine.rootContext().setContextProperty("world", controller)
    main=Path(__file__).parent/"qml"/"Main.qml"
    engine.load(QUrl.fromLocalFile(str(main)))
    if not engine.rootObjects():
        raise RuntimeError("Qt6 failed to load World & Environment Studio QML frontend")
    return app.exec()
