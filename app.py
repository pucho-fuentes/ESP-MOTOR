import eventlet
eventlet.monkey_patch()

from flask import Flask, jsonify, Response, send_file
from flask_socketio import SocketIO
from datetime import datetime
import sqlite3
import os
import math

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="eventlet")

DB_NAME = "imu_data.db"
VIBRATION_THRESHOLD = 15

last_alert = False

# -------------------------
# DB
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
    return "🚀 Servidor IMU Socket.IO activo"

@app.route("/monitor")
def monitor():
    return send_file("monitor.html")

# -------------------------
# SOCKET.IO RECEIVE ESP32
# -------------------------
@socketio.on("imu")
def handle_imu(data):
    global last_alert

    ax = float(data.get("ax", 0))
    ay = float(data.get("ay", 0))
    az = float(data.get("az", 0))

    magnitude = math.sqrt(ax**2 + ay**2 + az**2)
    timestamp = datetime.now().isoformat()

    last_alert = magnitude > VIBRATION_THRESHOLD

    # guardar DB
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute(
        "INSERT INTO imu_data (ax, ay, az, magnitude, timestamp) VALUES (?, ?, ?, ?, ?)",
        (ax, ay, az, magnitude, timestamp)
    )
    conn.commit()
    conn.close()

    payload = {
        "ax": ax,
        "ay": ay,
        "az": az,
        "magnitude": magnitude,
        "alert": last_alert,
        "timestamp": timestamp
    }

    print("📡 IMU →", payload)

    # 🔥 ENVIAR A TODOS LOS HTML CONECTADOS
    socketio.emit("imu_update", payload)

# -------------------------
# CSV
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
# RUN
# -------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    socketio.run(app, host="0.0.0.0", port=port)
