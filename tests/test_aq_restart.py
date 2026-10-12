"""Restart regression tests without connected sensor hardware."""

from contextlib import closing, redirect_stdout
import importlib.util
import io
from pathlib import Path
import sqlite3
import sys
import tempfile
import types
import unittest
from unittest.mock import Mock, mock_open, patch

ROOT = Path(__file__).resolve().parents[1]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class RestartTests(unittest.TestCase):
    def test_temperature_uses_only_five_recent_samples(self):
        bme = Mock()
        bme.get_temperature.return_value = 30
        with patch.dict(sys.modules, {
            "bme280": types.SimpleNamespace(BME280=lambda: bme),
            "ltr559": types.SimpleNamespace(LTR559=Mock()),
            "enviroplus": types.SimpleNamespace(gas=Mock()),
        }):
            aq = load("aq_functions_test", "aq/AQFunctions.py")
        with patch("builtins.open", mock_open(read_data="60000")):
            short, _ = aq.get_temperature([50] * 4)
            long, _ = aq.get_temperature([10] * 1000 + [50] * 4)
        self.assertEqual(short, long)
        self.assertAlmostEqual(short, 30 - (52 - 30) / 2.25)

    def run_collection(self, warmup, fail_read=None):
        with patch.dict(sys.modules, {
            "AQFunctions": Mock(), "post_air": Mock(), "requests": Mock(),
        }):
            aq = load("aq_main_test", "aq/aq_main.py")
        aq.requests.RequestException = type("RequestException", (Exception,), {})
        now, published = [0], []

        def record():
            if now[0] == fail_read:
                raise OSError("Sensor unavailable")

        def sleep(seconds):
            now[0] += seconds
            if now[0] >= 5:
                raise KeyboardInterrupt

        sensor = Mock(record_data=Mock(side_effect=record))
        with patch.object(aq.time, "monotonic", side_effect=lambda: now[0]), \
             patch.object(aq.time, "sleep", side_effect=sleep), \
             patch.object(aq, "send_to_wvi", side_effect=lambda _: published.append(now[0])), \
             redirect_stdout(io.StringIO()), self.assertRaises(KeyboardInterrupt):
            aq.collect_and_publish(sensor, warmup)
        return published

    def test_startup_samples_are_not_published(self):
        self.assertEqual(self.run_collection(3), [3, 4])

    def test_timer_starts_after_successful_sensor_read(self):
        self.assertEqual(self.run_collection(3, fail_read=0), [4])

    def test_first_sample_always_discarded(self):
        self.assertEqual(self.run_collection(0), [1, 2, 3, 4])


class CleanupTests(unittest.TestCase):
    def test_preview_and_backup_preserve_original_data(self):
        cleanup = load("clean_air_test", "scripts/clean_air_readings.py")
        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory) / "readings.sqlite3"
            backup = Path(directory) / "backup.sqlite3"
            with closing(sqlite3.connect(database)) as con, con:
                con.execute("CREATE TABLE air_readings (id INTEGER PRIMARY KEY, value REAL)")
                con.executemany("INSERT INTO air_readings VALUES (?, ?)", [(1, 100), (2, 20)])
                with redirect_stdout(io.StringIO()):
                    con.commit()
                    cleanup.clean(database, [1])
                    self.assertEqual(con.execute("SELECT COUNT(*) FROM air_readings").fetchone()[0], 2)
                    cleanup.clean(database, [1], backup)
                self.assertEqual(con.execute("SELECT id FROM air_readings").fetchall(), [(2,)])
            with closing(sqlite3.connect(backup)) as con:
                self.assertEqual(con.execute("SELECT * FROM air_readings").fetchall(), [(1, 100), (2, 20)])

    def test_missing_ids_and_existing_backup_abort_without_deleting(self):
        cleanup = load("clean_air_test", "scripts/clean_air_readings.py")
        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory) / "readings.sqlite3"
            backup = Path(directory) / "existing.sqlite3"
            backup.write_bytes(b"Keep this backup")
            with closing(sqlite3.connect(database)) as con, con:
                con.execute("CREATE TABLE air_readings (id INTEGER PRIMARY KEY)")
                con.execute("INSERT INTO air_readings VALUES (1)")
                con.commit()
                with self.assertRaises(ValueError):
                    cleanup.clean(database, [1, 2], backup)
                with redirect_stdout(io.StringIO()), self.assertRaises(FileExistsError):
                    cleanup.clean(database, [1], backup)
                self.assertEqual(con.execute("SELECT id FROM air_readings").fetchall(), [(1,)])
                self.assertEqual(backup.read_bytes(), b"Keep this backup")


if __name__ == "__main__":
    unittest.main()
