from flask import Flask, request, jsonify, render_template
import tinytuya

app = Flask(__name__)

# Reemplaza con tus credenciales reales
DISPOSITIVO_ID = "eb0404f443e26b74b5ep9l"
LOCAL_KEY = "*LgcIA9:``/?SoH_"
IP_LOCAL_DISPOSITIVO = "192.168.100.52" # Opcional, pero recomendado para estabilidad

d = tinytuya.OutletDevice(DISPOSITIVO_ID, IP_LOCAL_DISPOSITIVO, LOCAL_KEY)
d.set_version(3.4) # Esto es importante para la mayoria de los dispositivos Tuya modernos

@app.route('/controlar', methods=['GET'])
def index():
    return render_template('cliente.html')

@app.route('/controlar', methods=['POST'])
def controlar():
    # Aquí puedes agregar lógica para encender/apagar el enchufe
    # Por ahora, solo imprimiremos los datos recibidos
    try:
        data = request.json
        print(f"Datos recibidos: {data}")

        comando = data.get("comando")

        status=d.status() # Obtiene el estado actual del enchufe
        print(f"Estado actual del enchufe: {status}")

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