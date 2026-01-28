from flask import Flask, request, jsonify, send_file, Response
from datetime import datetime
import sqlite3
import os
import csv
import time
import math

app = Flask(__name__)
DB_NAME = "imu_data.db"

SAVE_INTERVAL = 0.1  # segundos (100 ms)
VIBRATION_THRESHOLD = 15  # umbral de vibración

last_saved_time = 0
last_alert = False

# -------------------------
# INIT DB
# -------------------------
def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS imu_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ax REAL,
            ay REAL,
            az REAL,
            magnitude REAL,
            timestamp TEXT
        )
    """)
    conn.commit()
    conn.close()

init_db()

# -------------------------
# HOME
# -------------------------
@app.route("/")
def home():
    return "Servidor IMU activo 🚀"

# -------------------------
# RECEIVE DATA ESP32
# -------------------------
@app.route("/data", methods=["POST"])
def receive_data():
    global last_saved_time, last_alert

    data = request.json
    if not data:
        return jsonify({"error": "No JSON"}), 400

    now = time.time()
    if now - last_saved_time < SAVE_INTERVAL:
        return jsonify({"status": "skipped"})

    ax = float(data.get("ax", 0))
    ay = float(data.get("ay", 0))
    az = float(data.get("az", 0))

    magnitude = math.sqrt(ax**2 + ay**2 + az**2)
    timestamp = datetime.now().isoformat()

    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute(
        "INSERT INTO imu_data (ax, ay, az, magnitude, timestamp) VALUES (?, ?, ?, ?, ?)",
        (ax, ay, az, magnitude, timestamp)
    )
    conn.commit()
    conn.close()

    last_saved_time = now
    last_alert = magnitude > VIBRATION_THRESHOLD

    print("📥 Guardado:", ax, ay, az, "MAG:", magnitude)

    return jsonify({"status": "ok", "alert": last_alert})

# -------------------------
# LATEST DATA
# -------------------------
@app.route("/api/latest")
def latest():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT ax, ay, az, magnitude, timestamp FROM imu_data ORDER BY id DESC LIMIT 1")
    row = c.fetchone()
    conn.close()

    if not row:
        return jsonify({"error": "sin datos"}), 404

    return jsonify({
        "ax": row[0],
        "ay": row[1],
        "az": row[2],
        "magnitude": row[3],
        "timestamp": row[4]
    })

# -------------------------
# HISTORY
# -------------------------
@app.route("/api/history")
def history():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT ax, ay, az, magnitude, timestamp FROM imu_data ORDER BY id DESC LIMIT 500")
    rows = c.fetchall()
    conn.close()

    return jsonify([
        {"ax": r[0], "ay": r[1], "az": r[2], "magnitude": r[3], "timestamp": r[4]}
        for r in rows
    ])

# -------------------------
# ALERT STATUS
# -------------------------
@app.route("/api/alert")
def alert():
    return jsonify({"alert": last_alert})

# -------------------------
# CSV EXPORT
# -------------------------
@app.route("/api/csv")
def export_csv():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT ax, ay, az, magnitude, timestamp FROM imu_data")
    rows = c.fetchall()
    conn.close()

    def generate():
        yield "ax,ay,az,magnitude,timestamp\n"
        for r in rows:
            yield f"{r[0]},{r[1]},{r[2]},{r[3]},{r[4]}\n"

    return Response(
        generate(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=imu_data.csv"}
    )

# -------------------------
# MONITOR
# -------------------------
@app.route("/monitor")
def monitor():
    return send_file("monitor.html")

# -------------------------
# RUN
# -------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
