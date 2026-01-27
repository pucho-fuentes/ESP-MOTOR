from flask import Flask, request, jsonify, send_file
from datetime import datetime
import os

app = Flask(__name__)

# Guarda el último dato recibido
latest_data = {
    "ax": 0,
    "ay": 0,
    "az": 0,
    "time": ""
}

# -------------------------
# RUTA PRINCIPAL
# -------------------------
@app.route("/")
def home():
    return "Servidor IMU activo 🚀"

# -------------------------
# ESP32 ENVÍA DATOS AQUÍ
# -------------------------
@app.route("/data", methods=["POST"])
def receive_data():
    global latest_data
    data = request.json

    if not data:
        return jsonify({"error": "No JSON recibido"}), 400

    latest_data = {
        "ax": data.get("ax"),
        "ay": data.get("ay"),
        "az": data.get("az"),
        "time": datetime.now().isoformat()
    }

    print("📥 Datos recibidos:", latest_data)
    return jsonify({"status": "ok"})

# -------------------------
# HTML CONSULTA DATOS AQUÍ
# -------------------------
@app.route("/api/latest", methods=["GET"])
def api_latest():
    return jsonify({
        "ax": latest_data["ax"],
        "ay": latest_data["ay"],
        "az": latest_data["az"],
        "timestamp": latest_data["time"]
    })

# -------------------------
# SERVIR EL MONITOR HTML
# -------------------------
@app.route("/monitor")
def monitor():
    return send_file("monitor.html")

# -------------------------
# INICIO DEL SERVIDOR
# -------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
