from flask import Flask, jsonify, send_file, Response
from flask_socketio import SocketIO
from datetime import datetime
import sqlite3
import os
import math
import time

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

DB_NAME = "imu_data.db"

SAVE_INTERVAL = 0.1   # 100 ms
VIBRATION_THRESHOLD = 15

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
    return "Servidor IMU por WebSocket 🚀"

# -------------------------
# SOCKET: DATOS DESDE ESP32
# -------------------------
@socketio.on("imu")
def handle_imu(data):
    global last_saved_time, last_alert

    now = time.time()
    if now - last_saved_time < SAVE_INTERVAL:
        return

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

    # 🔥 reenvía a todos los navegadores en TIEMPO REAL
    socketio.emit("imu", {
        "ax": ax,
        "ay": ay,
        "az": az,
        "magnitude": magnitude,
        "timestamp": timestamp,
        "alert": last_alert
    })

    print("📡 SOCKET:", ax, ay, az, "MAG:", magnitude)

# -------------------------
# API ÚLTIMO DATO
# -------------------------
@app.route("/api/latest")
def latest():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute(
        "SELECT ax, ay, az, magnitude, timestamp FROM imu_data ORDER BY id DESC LIMIT 1"
    )
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
    socketio.run(app, host="0.0.0.0", port=port)
