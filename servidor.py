from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route('/controlar', methods=['POST'])
def controlar():
    # Aquí puedes agregar lógica para encender/apagar el enchufe
    # Por ahora, solo imprimiremos los datos recibidos
    try:
        data = request.json
        print(f"Datos recibidos: {data}")
        return jsonify({"mensaje": "Datos recibidos correctamente"}), 200
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"error": "Formato de datos incorrecto"}), 400

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)