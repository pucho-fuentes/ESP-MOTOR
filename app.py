from flask import Flask
from flask_socketio import SocketIO
from datetime import datetime
import sqlite3
import math

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="eventlet")

DB_NAME = "imu_data.db"

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
# SOCKET IMU
# -------------------------
@socketio.on("imu")
def handle_imu(data):
    ax = float(data["ax"])
    ay = float(data["ay"])
    az = float(data["az"])

    mag = math.sqrt(ax*ax + ay*ay + az*az)
    ts = datetime.now().isoformat()

    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute(
        "INSERT INTO imu_data (ax, ay, az, magnitude, timestamp) VALUES (?, ?, ?, ?, ?)",
        (ax, ay, az, mag, ts)
    )
    conn.commit()
    conn.close()

    print("📡 IMU RECIBIDO:", ax, ay, az, "MAG:", mag)

# -------------------------
# HOME
# -------------------------
@app.route("/")
def home():
    return "Servidor Socket.IO activo 🚀"

# -------------------------
# RUN
# -------------------------
if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=5000)
