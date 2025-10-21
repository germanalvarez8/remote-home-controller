from flask import Flask, request, jsonify, render_template
import tinytuya
import json

app = Flask(__name__)

# --- 1. CONFIGURACIÓN DE DISPOSITIVOS ---
# Cargar la configuración de todos los dispositivos desde el archivo JSON
try:
    with open('devices.json', 'r') as f:
        DEVICES = json.load(f)
except FileNotFoundError:
    print("ERROR: Archivo 'devices.json' no encontrado. Asegúrate de crearlo con las credenciales.")
    DEVICES = {}
except json.JSONDecodeError:
    print("ERROR: El archivo 'devices.json' no tiene un formato JSON válido.")
    DEVICES = {}

# Inicializar los objetos tinytuya para cada dispositivo
# Esto se hace una vez al iniciar el servidor para reusar las conexiones
DEVICES_OBJ = {}
for name, data in DEVICES.items():
    try:
        # Los dispositivos RGB necesitan inicializarse como BulbDevice
        if 'lampara_rgb' in name:
            d = tinytuya.BulbDevice(data['id'], data['ip'], data['key'])
        else:
            d = tinytuya.OutletDevice(data['id'], data['ip'], data['key'])
            
        d.set_version(data.get('version', 3.3)) # Usa la versión especificada o 3.3 por defecto
        DEVICES_OBJ[name] = d
        print(f"Dispositivo '{name}' inicializado correctamente.")
    except Exception as e:
        print(f"Advertencia: No se pudo inicializar el dispositivo '{name}'. Error: {e}")

# --- 2. ENDPOINTS BÁSICOS (Vista) ---

@app.route('/')
@app.route('/controlar', methods=['GET'])
def index():
    # Renderiza la interfaz HTML (index.html)
    return render_template('index.html')

# --- 3. ENDPOINTS AVANZADOS PARA LA EFI ---

def set_device_status(name, status=None, mode=None, colour=None):
    """Función auxiliar para enviar comandos a cualquier dispositivo."""
    dev = DEVICES_OBJ.get(name)
    if not dev:
        return f"Dispositivo '{name}' no encontrado o no inicializado."

    try:
        # Comando de Encendido/Apagado
        if status is not None:
            dev.set_status(status)
        
        # Comando de Modo (solo para lámparas)
        if mode and hasattr(dev, 'set_mode'):
            dev.set_mode(mode)
            
        # Comando de Color (solo para lámparas)
        if colour and hasattr(dev, 'set_colour'):
            # Los argumentos deben ser H, S, V (Hue, Saturation, Value)
            dev.set_colour(*colour)

        # Pequeña pausa para que los comandos se apliquen (opcional)
        # time.sleep(0.2) 
        
        return f"Comando '{name}' enviado."
    except Exception as e:
        return f"Error al controlar '{name}': {e}"


@app.route('/api/modo_cine', methods=['POST'])
def modo_cine():
    """
    Escenario 1: Demostración de Lógica Compleja.
    Involucra a los 3 dispositivos y diferentes tipos de comandos (On/Off, RGB).
    """
    print("\n--- INICIANDO ESCENARIO: MODO CINE ---")
    
    mensajes = []
    
    # 1. Enchufe 1: Apagar la TV (Demostración de control simple)
    mensajes.append(set_device_status("enchufe_oficina", status=False))
    
    # 2. Enchufe 2: Encender el Proyector
    mensajes.append(set_device_status("enchufe_proyector", status=True))
    
    # 3. Lámpara RGB: Poner en modo color Azul Oscuro (Demuestra manejo de DPS)
    # HUE=240 (Azul), SAT=1000 (Máxima), VALUE=300 (Bajo brillo)
    mensajes.append(set_device_status("lampara_rgb", status=True, mode='colour', colour=(240, 1000, 300)))
    
    print("\n".join(mensajes))
    return jsonify({"message": "Modo Cine activado. Se ejecutaron comandos complejos en la red segmentada.", "details": mensajes}), 200


@app.route('/api/modo_trabajo', methods=['POST'])
def modo_trabajo():
    """
    Escenario 2: Demostración de Segmentación de Red (controlando dispositivos de diferentes subredes lógicas).
    """
    print("\n--- INICIANDO ESCENARIO: MODO TRABAJO ---")

    mensajes = []

    # 1. Enchufe 1: Encender la Oficina
    mensajes.append(set_device_status("enchufe_oficina", status=True))

    # 2. Enchufe 2: Apagar el Proyector
    mensajes.append(set_device_status("enchufe_proyector", status=False))

    # 3. Lámpara RGB: Poner luz de trabajo (Blanca brillante)
    # HUE=0, SAT=0 (para blanco), VALUE=1000 (Brillo máximo)
    mensajes.append(set_device_status("lampara_rgb", status=True, mode='white', colour=(0, 0, 1000)))
    
    print("\n".join(mensajes))
    return jsonify({"message": "Modo Trabajo activado. Comunicación exitosa entre subredes lógicas.", "details": mensajes}), 200


@app.route('/api/apagar_todo', methods=['POST'])
def apagar_todo():
    """
    Endpoint de utilidad para apagar todos los dispositivos.
    """
    print("\n--- APAGANDO TODOS LOS DISPOSITIVOS ---")
    mensajes = []

    for name in DEVICES_OBJ.keys():
        mensajes.append(set_device_status(name, status=False))

    print("\n".join(mensajes))
    return jsonify({"message": "Todos los dispositivos IoT apagados.", "details": mensajes}), 200

# --- 4. INICIO DEL SERVIDOR ---

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001)