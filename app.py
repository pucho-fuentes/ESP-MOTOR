from flask import Flask, request, jsonify, send_file
from datetime import datetime
import os
import mysql.connector

app = Flask(__name__)

# -------------------------
# CONFIG DB (Railway)
# -------------------------
db_config = {
    "host": os.environ.get("MYSQLHOST"),
    "user": os.environ.get("MYSQLUSER"),
    "password": os.environ.get("MYSQLPASSWORD"),
    "database": os.environ.get("MYSQLDATABASE"),
    "port": int(os.environ.get("MYSQLPORT", 3306))
}

def get_db_connection():
    return mysql.connector.connect(**db_config)

# -------------------------
# GUARDA EL ÚLTIMO DATO
# -------------------------
latest_data = {
    "ax": 0,
    "ay": 0,
    "az": 0,
    "time": ""
}

# -------------------------
@app.route("/")
def home():
    return "Servidor IMU activo 🚀"

# -------------------------
# ESP32 ENVÍA DATOS
# -------------------------
@app.route("/data", methods=["POST"])
def receive_data():
    global latest_data
    data = request.json

    if not data:
        return jsonify({"error": "No JSON recibido"}), 400

    ax = data.get("ax")
    ay = data.get("ay")
    az = data.get("az")
    now = datetime.now()

    latest_data = {
        "ax": ax,
        "ay": ay,
        "az": az,
        "time": now.isoformat()
    }

    # ---- GUARDAR EN DB ----
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO imu_data (ax, ay, az, timestamp) VALUES (%s, %s, %s, %s)",
            (ax, ay, az, now)
        )
        conn.commit()
        cursor.close()
        conn.close()
    except Exception as e:
        print("❌ Error DB:", e)

    print("📥 Datos recibidos:", latest_data)
    return jsonify({"status": "ok"})

# -------------------------
# ÚLTIMO DATO (API)
# -------------------------
@app.route("/api/latest")
def api_latest():
    return jsonify(latest_data)

# -------------------------
# VER DATOS (JSON)
# -------------------------
@app.route("/api/all")
def api_all():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM imu_data ORDER BY timestamp DESC LIMIT 1000")
    data = cursor.fetchall()
    cursor.close()
    conn.close()
    return jsonify(data)

# -------------------------
# DESCARGAR CSV
# -------------------------
@app.route("/download")
def download_csv():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT ax, ay, az, timestamp FROM imu_data")
    rows = cursor.fetchall()

    filename = "imu_data.csv"
    with open(filename, "w") as f:
        f.write("ax,ay,az,timestamp\n")
        for r in rows:
            f.write(f"{r[0]},{r[1]},{r[2]},{r[3]}\n")

    cursor.close()
    conn.close()
    return send_file(filename, as_attachment=True)

# -------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
