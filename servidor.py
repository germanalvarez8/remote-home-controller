from flask import Flask, request, jsonify
import tinytuya

app = Flask(__name__)

# Reemplaza con tus credenciales reales
DISPOSITIVO_ID = "eb5015450734ad8b52a113"
LOCAL_KEY = "&DG&vL*M;MSg(ynH"
IP_LOCAL_DISPOSITIVO = "186.122.108.90" # Opcional, pero recomendado para estabilidad

d = tinytuya.OutletDevice(DISPOSITIVO_ID, IP_LOCAL_DISPOSITIVO, LOCAL_KEY)
d.set_version(3.3) # Esto es importante para la mayoria de los dispositivos Tuya modernos

@app.route('/controlar', methods=['POST'])
def controlar():
    # Aquí puedes agregar lógica para encender/apagar el enchufe
    # Por ahora, solo imprimiremos los datos recibidos
    try:
        data = request.json
        print(f"Datos recibidos: {data}")

        comando = data.get("comando")

        if comando == "encender":
            d.turn_on() # Enciende el enchufe
            print("Comando: ENCENDER")
            return jsonify({"mensaje": "Enchufe encendido"}), 200
        elif comando == "apagar":
            d.turn_off() # Apaga el enchufe
            print("Comando: APAGAR")
            return jsonify({"mensaje": "Enchufe apagado"}), 200
        else:
            return jsonify({"error": "Comando no valido"}), 400

    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"error": "Formato de datos incorrecto"}), 400

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)