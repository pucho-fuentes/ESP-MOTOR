# ⚠️ ESTO SIEMPRE VA PRIMERO
import eventlet
eventlet.monkey_patch()

from flask import Flask, jsonify, send_file, Response
from flask_socketio import SocketIO
from datetime import datetime
import sqlite3
import os
import math

# -------------------------
# APP CONFIG
# -------------------------
app = Flask(__name__)
app.config["SECRET_KEY"] = "imu-secret"

socketio = SocketIO(
    app,
    cors_allowed_origins="*",
    async_mode="eventlet"
)

DB_NAME = "imu_data.db"
VIBRATION_THRESHOLD = 15

last_data = {
    "ax": 0,
    "ay": 0,
    "az": 0,
    "magnitude": 0,
    "timestamp": ""
}

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
    return "🚀 Servidor IMU Socket.IO activo"

# -------------------------
# SOCKET.IO RECEIVE DATA
# -------------------------
@socketio.on("imu")
def handle_imu(data):
    global last_data

    try:
        ax = float(data.get("ax", 0))
        ay = float(data.get("ay", 0))
        az = float(data.get("az", 0))

        magnitude = math.sqrt(ax**2 + ay**2 + az**2)
        timestamp = datetime.now().isoformat()

        # guardar último
        last_data = {
            "ax": ax,
            "ay": ay,
            "az": az,
            "magnitude": magnitude,
            "timestamp": timestamp
        }

        # guardar en DB
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute(
            "INSERT INTO imu_data (ax, ay, az, magnitude, timestamp) VALUES (?, ?, ?, ?, ?)",
            (ax, ay, az, magnitude, timestamp)
        )
        conn.commit()
        conn.close()

        alert = magnitude > VIBRATION_THRESHOLD

        print(f"📡 IMU → ax:{ax:.2f} ay:{ay:.2f} az:{az:.2f} | MAG:{magnitude:.2f}")

        # reenviar a clientes web
        socketio.emit("imu_update", last_data)

        return {"status": "ok", "alert": alert}

    except Exception as e:
        print("❌ Error IMU:", e)
        return {"status": "error"}

# -------------------------
# API LATEST
# -------------------------
@app.route("/api/latest")
def latest():
    return jsonify(last_data)

# -------------------------
# API HISTORY
# -------------------------
@app.route("/api/history")
def history():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute(
        "SELECT ax, ay, az, magnitude, timestamp FROM imu_data ORDER BY id DESC LIMIT 500"
    )
    rows = c.fetchall()
    conn.close()

    return jsonify([
        {
            "ax": r[0],
            "ay": r[1],
            "az": r[2],
            "magnitude": r[3],
            "timestamp": r[4]
        }
        for r in rows
    ])

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
# RUN
# -------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    socketio.run(app, host="0.0.0.0", port=port)
