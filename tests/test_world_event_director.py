"""Executable CPU-only tests of World & Event Director (no Qt needed)."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

APP=Path(__file__).resolve().parents[1]/"apps"/"fa3-world-event-director"
sys.path.insert(0,str(APP))
from fa3_world.engine import (WorldProject, Anchor, Weather, NarrativeEvent,
                              resolve_instant, season_at, solar_position)


class WorldEventDirectorTests(unittest.TestCase):
    def setUp(self):
        self.p=WorldProject()

    def test_default_preview_not_misrepresented_as_observation(self):
        self.assertEqual("AUTHOR_INVENTED",self.p.weather.origin)
        self.assertIn("authored",self.p.to_dict()["provenance_notice"].lower())
        self.assertFalse(self.p.to_dict()["current_host_admitted"])

    def test_historical_budapest_clock_not_present_daylight_saving(self):
        self.assertEqual("+0100",self.p.sky_context()["utc_offset"])
        self.assertEqual("SUMMER",self.p.seasonal_context())
        self.assertEqual("Northern",self.p.anchor.hemisphere)

    def test_solar_direction_and_height_near_budapest_afternoon(self):
        s=self.p.sky_context()["sun"]
        self.assertGreater(s["elevation_deg"],15)
        self.assertLess(s["elevation_deg"],65)
        self.assertGreater(s["azimuth_deg_true_north"],190)
        self.assertLess(s["azimuth_deg_true_north"],310)

    def test_unknown_clock_yields_no_instantaneous_solar_claim(self):
        self.p.anchor.local_time=None
        info=self.p.sky_context()
        self.assertIsNone(info["sun"])
        self.assertEqual("UNKNOWN",info["daypart"])
        self.assertIn("DATE_ONLY",info["data_quality"])

    def test_cape_town_same_date_means_winter(self):
        self.p.use_location("Cape Town")
        self.assertEqual("WINTER",self.p.seasonal_context())
        self.assertEqual("Southern",self.p.anchor.hemisphere)
        self.assertEqual("+0200",self.p.sky_context()["utc_offset"])

    def test_equatorial_climate_does_not_guess_four_seasons(self):
        self.p.use_location("Singapore")
        self.assertEqual("REGIONAL_WET_DRY_UNRESOLVED",self.p.seasonal_context())

    def test_nairobi_tropical_highland_not_forced_south_winter(self):
        self.p.use_location("Nairobi")
        self.assertEqual("REGIONAL_WET_DRY_UNRESOLVED",self.p.seasonal_context())

    def test_daypart_at_midnight(self):
        self.p.anchor.local_time="00:00"
        self.assertEqual("NIGHT",self.p.sky_context()["daypart"])

    def test_trex_cannot_change_earth_anchor_or_sun(self):
        before=json.dumps({"a":vars(self.p.anchor),"sky":self.p.sky_context()},sort_keys=True)
        self.p.add_event("TREX","Klónozott T-Rex a Kossuth téren")
        after=json.dumps({"a":vars(self.p.anchor),"sky":self.p.sky_context()},sort_keys=True)
        self.assertEqual(before,after)
        self.assertIsNone(self.p.planetary_rule_override)
        self.assertIn("T-Rex", " ".join(self.p.effects()["CITY"]))

    def test_alien_artificial_shadow_is_not_planetary_orbit_change(self):
        s=self.p.sky_context()["sun"]
        self.p.add_event("ALIEN","Űrhajó")
        self.assertEqual(s,self.p.sky_context()["sun"])
        self.assertTrue(any("arnyek" in x.lower() for x in self.p.effects()["BUILDING"]))

    def test_unapproved_planetary_override_fails_closed(self):
        with self.assertRaises(PermissionError):self.p.approve_world_rule("TWO_SUNS")
        self.assertTrue(self.p.earth_anchor_locked)

    def test_approved_custom_world_does_not_label_earth_sun(self):
        self.p.approve_world_rule("TWO_SUNS",approved=True)
        self.assertIsNone(self.p.sky_context()["sun"])
        self.assertEqual("CUSTOM_WORLD_RULE",self.p.sky_context()["daypart"])
        self.p.restore_earth_rules()
        self.assertTrue(self.p.earth_anchor_locked)
        self.assertIsNotNone(self.p.sky_context()["sun"])

    def test_unsupported_event_rejected(self):
        with self.assertRaises(ValueError):self.p.add_event("RAIN_DINOSAUR_LAWS")

    def test_storm_cross_scales_reproducible(self):
        self.p.weather.rain_mm_h=26
        self.p.weather.wind_kmh=45
        first=self.p.effects(minute=4)
        self.assertEqual(first,self.p.effects(minute=4))
        self.assertTrue(first["NATURAL"])
        self.assertTrue(first["CITY"])
        self.assertTrue(first["BUILDING"])
        self.assertTrue(first["INTERIOR"])
        self.assertIn("fiktiv"," ".join(first["INTERIOR"]))

    def test_dry_preview_no_invented_flood_claim(self):
        self.p.weather.rain_mm_h=0
        self.p.events.clear()
        self.assertEqual([],self.p.effects()["INTERIOR"])

    def test_events_obey_timeline(self):
        self.p.events.clear()
        self.p.add_event("TREX",minute=11)
        self.assertNotIn("T-Rex"," ".join(self.p.effects(minute=10)["CITY"]))
        self.assertIn("T-Rex"," ".join(self.p.effects(minute=11)["CITY"]))

    def test_field_validation_rejects_wrong_hemisphere(self):
        self.p.anchor.hemisphere="Southern"
        with self.assertRaises(ValueError):self.p.validate()

    def test_field_validation_rejects_unphysical_inputs(self):
        self.p.weather.rain_mm_h=-2
        with self.assertRaises(ValueError):self.p.validate()

    def test_daylight_saving_ambiguous_time_explicit_choice(self):
        with self.assertRaises(ValueError):resolve_instant("2026-10-25","02:30","Europe/Budapest")
        a=resolve_instant("2026-10-25","02:30","Europe/Budapest",fold=0)
        b=resolve_instant("2026-10-25","02:30","Europe/Budapest",fold=1)
        self.assertNotEqual(a.utcoffset(),b.utcoffset())

    def test_nonexistent_time_rejected_even_with_fold(self):
        with self.assertRaises(ValueError):resolve_instant("2026-03-29","02:30","Europe/Budapest",fold=0)

    def test_save_restore_native_sidecar_roundtrip(self):
        self.p.add_event("TREX",minute=12)
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/"example.fa3world"
            self.p.save(path)
            reloaded=WorldProject.load(path)
            self.assertEqual(self.p.to_dict(),reloaded.to_dict())
            self.assertEqual(reloaded.events[-1].minute,12)

    def test_duplicate_event_ids_fail_closed(self):
        self.p.events.append(self.p.events[0])
        with self.assertRaises(ValueError):self.p.validate()

    def test_shot_handoff_explicitly_reference_only(self):
        h=self.p.shot_handoff(shot_id="shot-03")
        self.assertEqual("shot-03",h["shot_id"])
        self.assertEqual("UNKNOWN_UNLESS_EXPLICITLY_SOURCED",h["historical_weather_status"])
        self.assertIn("NOT_A_FA3_EDITORIAL_TIMELINE",h["authority"])

    def test_cli_headless_preview_runs_without_gui(self):
        run=subprocess.run([sys.executable,str(APP/"launch.py"),"--headless-preview"],capture_output=True,text=True)
        self.assertEqual(0,run.returncode,run.stderr)
        payload=json.loads(run.stdout)
        self.assertEqual("SUMMER",payload["sky"]["season"])
        self.assertEqual(4,len(payload["four_scales"]))

    def test_integration_files_present(self):
        self.assertTrue((APP/"fa3_world"/"qml"/"Main.qml").exists())
        self.assertIn("WorldController",(APP/"fa3_world"/"qt_app.py").read_text())
        self.assertTrue((APP/"fa3_world"/"tk_app.py").exists())


if __name__=="__main__":unittest.main()
