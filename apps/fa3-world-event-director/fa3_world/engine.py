"""FA3 World & Event Director: dependency-free CPU reference engine.

All weather defaults are AUTHOR_INVENTED preview inputs.  Historical observations
and independently admitted simulation providers must be supplied separately.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import date, datetime, timedelta, timezone
import json
import math
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

SCHEMA = "fa3.world-event-director.project.v0"
WORLDS = ("HISTORICAL", "HYBRID", "ALTERNATE_HISTORY", "FICTIONAL")
MODES = ("ART_DIRECTED", "PHYSICS_INFORMED", "DATA_GUIDED")
KINDS = ("STORM", "FLOOD", "FIRE", "EARTHQUAKE", "LANDSLIDE", "SNOW", "TREX", "ALIEN")
SCOPES = ("NATURAL", "CITY", "BUILDING", "INTERIOR")
ORIGINS = ("OBSERVED", "HISTORICAL_RECORD", "REANALYSIS", "DERIVED", "AUTHOR_INVENTED", "UNKNOWN")

# Demonstration locality anchors, NOT a substitute for period-accurate GIS data.
LOCATIONS = {
    "Budapest": (47.5079, 19.0458, "Europe/Budapest", "Europe", "Northern", "temperate"),
    "Cape Town": (-33.9249, 18.4241, "Africa/Johannesburg", "Africa", "Southern", "mediterranean"),
    "Singapore": (1.3521, 103.8198, "Asia/Singapore", "Asia", "Northern", "equatorial"),
    "Tromso": (69.6492, 18.9553, "Europe/Oslo", "Europe", "Northern", "subarctic"),
    "Nairobi": (-1.2921, 36.8219, "Africa/Nairobi", "Africa", "Southern", "tropical-highland"),
}


def season_at(latitude: float, month: int, climate: str = "temperate") -> str:
    if abs(latitude) < 23.5 or climate in ("equatorial", "tropical-highland"):
        return "REGIONAL_WET_DRY_UNRESOLVED"
    if not 1 <= month <= 12:
        raise ValueError("Invalid month")
    season = ("WINTER", "SPRING", "SUMMER", "AUTUMN")[(month % 12) // 3]
    if latitude < 0:
        season = {"WINTER": "SUMMER", "SUMMER": "WINTER", "SPRING": "AUTUMN", "AUTUMN": "SPRING"}[season]
    return season


def resolve_instant(day: str, clock: str | None, zone: str, fold: int | None = None) -> datetime | None:
    date.fromisoformat(day)
    if clock is None or not clock.strip():
        return None
    try:
        h, m = (int(x) for x in clock.split(":"))
        wall = datetime.combine(date.fromisoformat(day), datetime.min.time()).replace(hour=h, minute=m)
        tz = ZoneInfo(zone)
    except (ValueError, ZoneInfoNotFoundError) as exc:
        raise ValueError("Invalid local clock or unavailable time-zone database") from exc
    a, b = wall.replace(tzinfo=tz, fold=0), wall.replace(tzinfo=tz, fold=1)
    if a.utcoffset() != b.utcoffset() and fold is None:
        raise ValueError("Ambiguous/nonexistent local time: select a documented UTC offset")
    chosen = wall.replace(tzinfo=tz, fold=fold or 0)
    if chosen.astimezone(timezone.utc).astimezone(tz).replace(tzinfo=None) != wall:
        raise ValueError("Local clock time does not exist at this historical location")
    return chosen


def solar_position(local_dt: datetime, latitude: float, longitude: float) -> dict[str, float]:
    """NOAA/Meeus approximate solar ephemeris, true-north azimuth clockwise.

    This is a CPU preview, not survey-grade positional astronomy.
    """
    if local_dt.tzinfo is None or not -90 <= latitude <= 90 or not -180 <= longitude <= 180:
        raise ValueError("Timezone-aware clock and valid Earth coordinates required")
    utc = local_dt.astimezone(timezone.utc)
    jd = utc.timestamp() / 86400 + 2440587.5
    t = (jd - 2451545.0) / 36525
    rad = math.radians
    L0 = (280.46646 + t * (36000.76983 + t * 0.0003032)) % 360
    M = 357.52911 + t * (35999.05029 - 0.0001537 * t)
    ecc = 0.016708634 - t * (0.000042037 + 0.0000001267 * t)
    C = (1.914602 - t * (0.004817 + 0.000014 * t)) * math.sin(rad(M))
    C += (0.019993 - 0.000101 * t) * math.sin(rad(2*M)) + 0.000289 * math.sin(rad(3*M))
    apparent = L0 + C - 0.00569 - 0.00478 * math.sin(rad(125.04 - 1934.136*t))
    eps = 23 + (26 + (21.448 - t*(46.815 + t*(0.00059 - 0.001813*t)))/60)/60
    eps += 0.00256 * math.cos(rad(125.04 - 1934.136*t))
    decl = math.asin(math.sin(rad(eps)) * math.sin(rad(apparent)))
    y = math.tan(rad(eps)/2)**2
    eq = 4*math.degrees(y*math.sin(2*rad(L0)) - 2*ecc*math.sin(rad(M))
        + 4*ecc*y*math.sin(rad(M))*math.cos(2*rad(L0))
        - 0.5*y*y*math.sin(4*rad(L0)) - 1.25*ecc*ecc*math.sin(2*rad(M)))
    minute = utc.hour*60 + utc.minute + utc.second/60
    tst = (minute + eq + 4*longitude) % 1440
    ha = rad(tst/4 - 180)
    lat = rad(latitude)
    cz = max(-1., min(1., math.sin(lat)*math.sin(decl) + math.cos(lat)*math.cos(decl)*math.cos(ha)))
    elevation = 90 - math.degrees(math.acos(cz))
    azimuth = (math.degrees(math.atan2(math.sin(ha), math.cos(ha)*math.sin(lat) - math.tan(decl)*math.cos(lat))) + 180) % 360
    return {"elevation_deg": round(elevation, 2), "azimuth_deg_true_north": round(azimuth, 2), "equation_of_time_minutes": round(eq, 2)}


@dataclass
class Anchor:
    place: str = "Budapest"
    latitude: float = 47.5079
    longitude: float = 19.0458
    timezone_id: str = "Europe/Budapest"
    continent: str = "Europe"
    hemisphere: str = "Northern"
    climate: str = "temperate"
    date: str = "1976-07-23"
    local_time: str | None = "16:00"
    precision: str = "CITY_DEMO_ANCHOR"
    origin: str = "DERIVED"
    tzdb_version: str = "SYSTEM_INSTALLED_UNPINNED"


@dataclass
class Weather:
    temperature_c: float = 21.
    rain_mm_h: float = 5.
    wind_kmh: float = 25.
    wind_from_deg: float = 270.
    cloud_percent: int = 75
    origin: str = "AUTHOR_INVENTED"
    observed_source: str | None = None


@dataclass
class NarrativeEvent:
    event_id: str
    kind: str
    minute: int
    label: str
    origin: str = "AUTHOR_INVENTED"
    enabled: bool = True


@dataclass
class WorldProject:
    schema: str = SCHEMA
    project_id: str = "budapest-1976-environment-demo"
    title: str = "Budapest 1976 | Kossuth ter"
    anchor: Anchor = field(default_factory=Anchor)
    weather: Weather = field(default_factory=Weather)
    world_mode: str = "HYBRID"
    simulation_mode: str = "ART_DIRECTED"
    earth_anchor_locked: bool = True
    planetary_rule_override: str | None = None
    events: list[NarrativeEvent] = field(default_factory=lambda: [
        NarrativeEvent("storm-01", "STORM", 0, "Forgatokonyvi zivatar")
    ])
    branch: str = "STORM_SCENE"
    seed: int = 19760723
    world_bible_notes: str = "A nappali es az orankenti idojaras a demo pelda fiktiv adata."

    def validate(self) -> None:
        if self.schema != SCHEMA or self.world_mode not in WORLDS or self.simulation_mode not in MODES:
            raise ValueError("Unsupported project schema or creative mode")
        a, w = self.anchor, self.weather
        if not -90 <= a.latitude <= 90 or not -180 <= a.longitude <= 180:
            raise ValueError("Latitude/longitude out of range")
        date.fromisoformat(a.date)
        if a.hemisphere != ("Northern" if a.latitude >= 0 else "Southern"):
            raise ValueError("Hemisphere must match coordinates")
        resolve_instant(a.date, a.local_time, a.timezone_id)
        if not (-100 <= w.temperature_c <= 80 and 0 <= w.rain_mm_h <= 300
                and 0 <= w.wind_kmh <= 500 and 0 <= w.wind_from_deg <= 360
                and 0 <= w.cloud_percent <= 100):
            raise ValueError("Weather preview inputs out of range")
        if w.origin not in ORIGINS or any(e.kind not in KINDS or e.origin not in ORIGINS or e.minute < 0 for e in self.events):
            raise ValueError("Unsupported event or provenance type")
        if self.earth_anchor_locked and self.planetary_rule_override:
            raise ValueError("World-rule override requires explicit unlocked Earth anchor")
        if len({e.event_id for e in self.events}) != len(self.events):
            raise ValueError("Duplicate event ID")

    def seasonal_context(self) -> str:
        return season_at(self.anchor.latitude, date.fromisoformat(self.anchor.date).month, self.anchor.climate)

    def sky_context(self) -> dict[str, Any]:
        if self.planetary_rule_override:
            return {"sun": None, "daypart": "CUSTOM_WORLD_RULE", "season": "AUTHOR_DEFINED",
                    "utc_offset": None, "data_quality": "CUSTOM_WORLD_RULE_NO_EARTH_EPHEMERIS",
                    "world_rule": self.planetary_rule_override}
        instant = resolve_instant(self.anchor.date, self.anchor.local_time, self.anchor.timezone_id)
        if instant is None:
            return {"sun": None, "daypart": "UNKNOWN", "utc_offset": None,
                    "season": self.seasonal_context(), "data_quality": "DATE_ONLY"}
        sun = solar_position(instant, self.anchor.latitude, self.anchor.longitude)
        el = sun["elevation_deg"]
        daypart = "NIGHT" if el < -6 else "TWILIGHT" if el < 0 else "DAYLIGHT"
        return {"sun": sun, "daypart": daypart, "season": self.seasonal_context(),
                "utc_offset": instant.strftime("%z"), "data_quality": "APPROXIMATE_CPU_EPHEMERIS"}

    def use_location(self, place: str) -> None:
        if place not in LOCATIONS:
            raise ValueError("Unrecognized demonstration city; user coordinate editor may be added")
        lat, lon, tz, continent, hemisphere, climate = LOCATIONS[place]
        old_date, old_time = self.anchor.date, self.anchor.local_time
        self.anchor = Anchor(place, lat, lon, tz, continent, hemisphere, climate, old_date, old_time)
        self.validate()

    def add_event(self, kind: str, label: str | None = None, minute: int = 0) -> NarrativeEvent:
        if kind not in KINDS or minute < 0:
            raise ValueError("Unsupported event")
        ids = {e.event_id for e in self.events}
        serial = 1
        while f"event-{serial:03}" in ids:
            serial += 1
        event = NarrativeEvent(f"event-{serial:03}", kind, minute, label or kind.title())
        self.events.append(event)
        self.validate()
        return event

    def approve_world_rule(self, rule: str, approved: bool = False) -> None:
        if not approved or rule not in ("TWO_SUNS", "CUSTOM_ORBIT", "CUSTOM_GRAVITY"):
            raise PermissionError("Explicit human approval required for planetary-world-rule changes")
        self.earth_anchor_locked = False
        self.planetary_rule_override = rule

    def restore_earth_rules(self) -> None:
        self.planetary_rule_override = None
        self.earth_anchor_locked = True

    def effects(self, minute: int = 0) -> dict[str, list[str]]:
        """Deterministic *art-directed preview*, NOT hazard or engineering physics."""
        if minute < 0:
            raise ValueError("Invalid timeline position")
        w = self.weather
        outputs: dict[str, list[str]] = {scope: [] for scope in SCOPES}
        if w.cloud_percent >= 60:
            outputs["NATURAL"].append("Felhozat es valtozo napfeny")
            outputs["CITY"].append("Arnyekos utcafrontok")
        if w.wind_kmh >= 20:
            outputs["NATURAL"].append("Mozgo novenyzet es faagak")
            outputs["BUILDING"].append("Szeltol fuggő homlokzati terheles (art-directed)")
        if w.rain_mm_h > 0:
            outputs["NATURAL"].append("Csapadek es vizlefolyas")
            outputs["CITY"].append("Nedves utcak es feluleti viz")
            outputs["BUILDING"].append("Tetore eso eso, eresz viz")
            if w.rain_mm_h >= 15 and w.wind_kmh >= 25:
                outputs["INTERIOR"].append("Felteteles beazas (fiktiv forgatokonyvi hatas)")
        for event in self.events:
            if not event.enabled or event.minute > minute:
                continue
            if event.kind in ("STORM", "SNOW"):
                outputs["NATURAL"].append(event.label + ": idojarasi esemeny")
                outputs["CITY"].append("Forgatokonyvi forgalmi zavar")
            elif event.kind in ("FLOOD", "LANDSLIDE"):
                outputs["NATURAL"].append("Forgatokonyvi talaj/viz valtozas")
                outputs["CITY"].append("Esemennyel erintett utca")
                outputs["BUILDING"].append("Kulso szerkezeti kitetseg")
            elif event.kind == "FIRE":
                outputs["CITY"].append("Forgatokonyvi fust")
                outputs["BUILDING"].append("Homlokzati fust/hő")
                outputs["INTERIOR"].append("Beltéri fust, ha a jelenet engedi")
            elif event.kind == "EARTHQUAKE":
                outputs["NATURAL"].append("Forgatokonyvi talajmozgas")
                outputs["CITY"].append("Utca es infrastruktura valtozas")
                outputs["BUILDING"].append("Forgatokonyvi epuletreakcio")
            elif event.kind == "TREX":
                outputs["CITY"].append("Kitalalt T-Rex: menekulo szereplok es jarmuvek")
                outputs["BUILDING"].append("Esetleges kitalalt kozeli karok")
            elif event.kind == "ALIEN":
                outputs["CITY"].append("Fiktiv megszallasi jelenet")
                outputs["BUILDING"].append("Urhajo altali helyi arnyek/megvilagitas")
        return outputs

    def to_dict(self) -> dict[str, Any]:
        self.validate()
        data = asdict(self)
        data["provenance_notice"] = "Preview weather and all narrative events are authored, not archived observations."
        data["current_host_admitted"] = False
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "WorldProject":
        if not isinstance(data, dict) or data.get("schema") != SCHEMA:
            raise ValueError("Unsupported world-project file")
        allowed = {f.name for f in cls.__dataclass_fields__.values()}
        clean = {k: v for k, v in data.items() if k in allowed}
        clean["anchor"] = Anchor(**clean["anchor"])
        clean["weather"] = Weather(**clean["weather"])
        clean["events"] = [NarrativeEvent(**e) for e in clean["events"]]
        result = cls(**clean)
        result.validate()
        return result

    def save(self, path: str | Path) -> Path:
        target = Path(path).expanduser()
        if target.suffix != ".fa3world":
            raise ValueError("Project path must end with .fa3world")
        target.parent.mkdir(parents=True, exist_ok=True)
        tmp = target.with_suffix(".fa3world.tmp")
        tmp.write_text(json.dumps(self.to_dict(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        tmp.replace(target)
        return target

    @classmethod
    def load(cls, path: str | Path) -> "WorldProject":
        return cls.from_dict(json.loads(Path(path).read_text(encoding="utf-8")))

    def shot_handoff(self, shot_id: str = "shot-001", minute: int = 0) -> dict[str, Any]:
        self.validate()
        return {"schema": "fa3.world-event-director.shot-handoff.v0", "project_id": self.project_id,
                "shot_id": shot_id, "branch": self.branch, "world_mode": self.world_mode,
                "earth_anchor": asdict(self.anchor), "sky_context": self.sky_context(),
                "narrative_events": [asdict(e) for e in self.events if e.enabled and e.minute <= minute],
                "affected_scopes": self.effects(minute),
                "authority": "REFERENCE_METADATA_ONLY_NOT_A_FA3_EDITORIAL_TIMELINE",
                "historical_weather_status": "UNKNOWN_UNLESS_EXPLICITLY_SOURCED"}
