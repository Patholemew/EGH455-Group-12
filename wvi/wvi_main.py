from flask import Flask, render_template, request, jsonify, abort, send_file, send_from_directory
import sqlite3
import time
from pathlib import Path
from datetime import datetime, timezone
import os 
import json 
import re
from werkzeug.exceptions import HTTPException

app = Flask(__name__)
DATA = Path(os.environ.get("WVI_DATA_DIR", str(Path(__file__).resolve().parent / "data")))
DATABASE = DATA / "wvi.sqlite3"
FRAME = Path(os.environ.get("WVI_FRAME_FILE", str(DATA / "liveimage.jpg")))
FRAME_META = FRAME.with_suffix(".json")
SNAPSHOTS = DATA / "snapshots"
HEARTBEAT_MESSAGE = "Heartbeat: API responded"

def connect():
    con = sqlite3.connect(DATABASE, timeout=5)
    con.row_factory = sqlite3.Row
    return con

from contextlib import closing

def init_db():
    DATA.mkdir(exist_ok=True)
    SNAPSHOTS.mkdir(parents=True, exist_ok=True)

    with closing(connect()) as con, con:
        con.execute("PRAGMA journal_mode=WAL")

        con.execute("""
            CREATE TABLE IF NOT EXISTS air_readings (
                id INTEGER PRIMARY KEY,
                captured_at REAL NOT NULL,
                received_at REAL NOT NULL,
                temperature_c REAL NOT NULL,
                pressure_hpa REAL NOT NULL,
                humidity_pct REAL NOT NULL,
                light_lux REAL NOT NULL,
                gas_reducing REAL NOT NULL,
                gas_oxidising REAL NOT NULL,
                gas_ammonia REAL NOT NULL
            )
        """)

        con.execute("""
            CREATE TABLE IF NOT EXISTS logs(
            id INTEGER PRIMARY KEY,
            time REAL NOT NULL,
            source TEXT NOT NULL,
            message TEXT NOT NULL
            )
        """)

        con.execute("""
            CREATE INDEX IF NOT EXISTS air_captured
            ON air_readings(captured_at)
        """)

        con.execute("""
            CREATE TABLE IF NOT EXISTS detections (
                id INTEGER PRIMARY KEY,
                event_id TEXT NOT NULL,
                type TEXT NOT NULL,
                captured_at REAL NOT NULL,
                received_at REAL NOT NULL,
                confidence REAL,
                image_filename TEXT,
                valve_state TEXT,
                marker_id INTEGER,
                x REAL, y REAL, z REAL,
                coordinate_frame TEXT,
                gauge_reading REAL,
                gauge_unit TEXT
            )
        """)
        con.execute("""
            CREATE INDEX IF NOT EXISTS detections_event
            ON detections(event_id, captured_at)
        """)

init_db()
    
def parse_timestamp(value):
    stamp = datetime.fromisoformat(value)
    if stamp.tzinfo is None:
        abort(400, "captured_at must include a timezone")
    return stamp.timestamp()


@app.errorhandler(HTTPException)
def api_errors(error):
    if request.path.startswith("/api/"):
        return jsonify(error=error.description), error.code
    return error

@app.get("/")
def index():
    return render_template("dashboard.html", page="dashboard")

@app.get("/charts")
def charts_page():
    return render_template("charts.html", page="charts")

@app.get("/targets")
def targets_page():
    return render_template("targets.html", page="targets")

@app.get("/logs")
def logs_page():
    return render_template("logs.html", page="logs")

@app.get("/live.jpg")
def live_frame():
    if not FRAME.is_file():
        abort(404, "No annotated frame has arrived")
    return send_file(FRAME, mimetype="image/jpeg", max_age=0)

@app.get("/snapshots/<filename>")
def snapshot(filename):
    return send_from_directory(SNAPSHOTS, filename)

@app.post("/api/heartbeat")
def heartbeat():
    with closing(connect()) as con, con:
        con.execute("INSERT INTO logs (time, source, message) VALUES (?, ?, ?)",
                    (time.time(), "WVI", HEARTBEAT_MESSAGE))
    return jsonify(ok=True), 201

@app.get("/api/logs")
def logs():
    source = request.args.get("source", "all")
    if source not in {"all", "WVI", "AQ", "AIP"}:
        abort(400, "Unknown log source")

    clause, values = "", []
    if source != "all":
        clause, values = " WHERE source = ?", [source]

    with closing(connect()) as con:
        rows = con.execute(
            "SELECT * FROM logs" + clause + " ORDER BY id DESC LIMIT 100", values).fetchall()
        first, last, count = con.execute(
            "SELECT MIN(time), MAX(time), COUNT(*) FROM logs WHERE message = ?",
            (HEARTBEAT_MESSAGE,)).fetchone()

    return jsonify(
        rows=[dict(row) for row in rows],
        heartbeat={"first": first, "last": last, "count": count,
                   "span_seconds": (last - first) if first is not None else 0})

@app.post("/api/air")
def ingest_air():
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        abort(400, "Send a JSON object with Content-Type: application/json")
    try:
        captured = parse_timestamp(payload["captured_at"])
        gas = payload["gas"]
        values = (
            captured, time.time(),
            float(payload["temperature_c"]), float(payload["pressure_hpa"]),
            float(payload["humidity_pct"]), float(payload["light_lux"]),
            float(gas["reducing"]), float(gas["oxidising"]), float(gas["ammonia"]),
        )
    except (KeyError, TypeError, ValueError):
        abort(400, "Missing or non-numeric air reading fields")

    with closing(connect()) as con, con:
        con.execute("""
            INSERT INTO air_readings (captured_at, received_at, temperature_c,
                pressure_hpa, humidity_pct, light_lux,
                gas_reducing, gas_oxidising, gas_ammonia)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, values)
        con.execute(
            "INSERT INTO logs (time, source, message) VALUES (?, ?, ?)",
            (time.time(), "AQ", "Reading received and stored"))
    return jsonify(ok=True), 201

def video_status(now):
    if not FRAME.is_file():
        return {"available": False, "frame_id": None, "age_seconds": None, "stale": True}
    try:
        meta = json.loads(FRAME_META.read_text())
        captured = datetime.fromisoformat(meta["captured_at"]).timestamp()
    except (OSError, ValueError, KeyError, TypeError):
        return {"available": True, "frame_id": None, "age_seconds": None, "stale": True}
    age = now - captured
    return {"available": True, "frame_id": meta.get("frame_id"),
            "age_seconds": age, "stale": age > 4}

@app.get("/api/data")
def current_data():
    now = time.time()
    with closing(connect()) as con:
        row = con.execute("""
            SELECT * FROM air_readings
            ORDER BY captured_at DESC, id DESC
            LIMIT 1
        """).fetchone()
    air = dict(row) if row else None
    if air:
        air["age_seconds"] = now - air["captured_at"]
        air["stale"] = air["age_seconds"] > 4 
    return jsonify(server_time=now, air=air, video=video_status(now))

@app.get("/api/history")
def history():
    choice = request.args.get("minutes", "10")
    if choice == "all":
        cutoff = 0
    else:
        try:
            minutes = int(choice)
            if not 1 <= minutes <= 60:
                raise ValueError()
        except ValueError:
            abort(400, "minutes must be 'all' or an integer from 1 to 60")
        cutoff = time.time() - minutes * 60

    with closing(connect()) as con:
        rows = con.execute("""
            SELECT captured_at, temperature_c, pressure_hpa, humidity_pct, light_lux
            FROM air_readings
            WHERE captured_at >= ?
            ORDER BY captured_at ASC, id ASC
        """, (cutoff,)).fetchall()

    return jsonify(rows=[dict(row) for row in rows], minutes=choice)

@app.post("/api/target")
def ingest_target():
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        abort(400, "Send a JSON object with Content-Type: application/json")

    kind = payload.get("type")
    if kind not in {"valve", "aruco", "gauge"}:
        abort(400, "type must be valve, aruco or gauge")

    row = {
        "type": kind, "received_at": time.time(),
        "valve_state": None, "marker_id": None, "x": None, "y": None, "z": None,
        "coordinate_frame": None, "gauge_reading": None, "gauge_unit": None,
    }

    try:
        row["captured_at"] = parse_timestamp(payload["captured_at"])
        row["event_id"] = str(payload["event_id"])

        filename = payload.get("image_filename")
        if filename is not None and not re.fullmatch(r"[A-Za-z0-9_-]+\.jpg", filename):
            raise ValueError()
        row["image_filename"] = filename

        confidence = payload.get("confidence")
        row["confidence"] = None if confidence is None else float(confidence)

        if kind == "valve":
            if payload["state"] not in {"open", "closed", "unknown"}:
                raise ValueError()
            row["valve_state"] = payload["state"]

        elif kind == "aruco":
            marker_id = payload["marker_id"]
            if not isinstance(marker_id, int) or isinstance(marker_id, bool) or marker_id < 0:
                raise ValueError()
            position = payload["position_m"]
            if not isinstance(position, dict):
                raise ValueError()
            frame = payload["coordinate_frame"]
            if not isinstance(frame, str) or not frame.strip():
                raise ValueError()

            row["marker_id"] = marker_id
            row["x"] = float(position["x"])
            row["y"] = float(position["y"])
            row["z"] = float(position["z"])
            row["coordinate_frame"] = frame

        elif kind == "gauge":
            unit = payload["unit"]
            if not isinstance(unit, str) or not unit.strip():
                raise ValueError()

            row["gauge_reading"] = float(payload["reading"])
            row["gauge_unit"] = unit

    except (KeyError, TypeError, ValueError):
        abort(400, f"Invalid {kind} detection payload")

    with closing(connect()) as con, con:
        seen = con.execute(
            "SELECT 1 FROM detections WHERE event_id = ? LIMIT 1",
            (row["event_id"],)).fetchone()
        con.execute("""
            INSERT INTO detections (event_id, type, captured_at, received_at, confidence,
                image_filename, valve_state, marker_id, x, y, z, coordinate_frame,
                gauge_reading, gauge_unit)
            VALUES (:event_id, :type, :captured_at, :received_at, :confidence,
                :image_filename, :valve_state, :marker_id, :x, :y, :z, :coordinate_frame,
                :gauge_reading, :gauge_unit)
        """, row)
        if not seen:
            con.execute(
                "INSERT INTO logs (time, source, message) VALUES (?, ?, ?)",
                (row["received_at"], "AIP", f"New {kind} detected: {row['event_id']}"))

    return jsonify(ok=True), 201

@app.get("/api/targets")
def targets():
    kind = request.args.get("type", "all")
    if kind not in {"all", "valve", "aruco", "gauge"}:
        abort(400, "Unknown target filter")

    conditions = ["id IN (SELECT MIN(id) FROM detections GROUP BY event_id)"]
    values = []
    if kind != "all":
        conditions.append("type = ?")
        values.append(kind)

    query = ("SELECT * FROM detections WHERE " + " AND ".join(conditions)
             + " ORDER BY id DESC LIMIT 100")

    with closing(connect()) as con:
        rows = con.execute(query, values).fetchall()
    return jsonify(rows=[dict(row) for row in rows])

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8000, debug=True)