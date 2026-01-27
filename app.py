from flask import Flask, request, jsonify
from datetime import datetime

app = Flask(__name__)

# Guardar último dato recibido
latest_data = {
    "ax": 0,
    "ay": 0,
    "az": 0,
    "time": ""
}

@app.route("/")
def home():
    return "Servidor IMU activo 🚀"

# ESP32 manda datos aquí
@app.route("/data", methods=["POST"])
def receive_data():
    global latest_data
    data = request.json

    latest_data = {
        "ax": data.get("ax"),
        "ay": data.get("ay"),
        "az": data.get("az"),
        "time": datetime.now().isoformat()
    }

    print("📥 Datos recibidos:", latest_data)
    return jsonify({"status": "ok"})

# La web consulta aquí
@app.route("/data", methods=["GET"])
def send_data():
    return jsonify(latest_data)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
