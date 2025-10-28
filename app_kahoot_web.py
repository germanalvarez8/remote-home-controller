# app_kahoot_web.py
from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit, join_room

app = Flask(__name__)
# ¡IMPORTANTE! Reemplaza 'tu_clave_secreta_aqui' con una clave real y segura.
app.config['SECRET_KEY'] = 'tu_clave_secreta_aqui'
socketio = SocketIO(app)

# --- CONFIGURACIÓN DE RED Y ROLES ---
# *** DEBES CAMBIAR ESTA IP *** con la IP estática real de tu MacBook asignada por el TP-Link.
ADMIN_IP = '192.168.1.101'
SERVER_HOST = '192.168.1.100' # IP Estática del Servidor
SERVER_PORT = 5001

# --- BASE DE DATOS DEL JUEGO ---
PREGUNTAS = [
    {"id": 1, "texto": "¿Cuál es el protocolo de la Capa de Transporte que garantiza la entrega de paquetes?", "opciones": ["A) UDP", "B) TCP", "C) ICMP"], "correcta": "B"},
    {"id": 2, "texto": "¿Qué utilidad de red se usa para probar la conectividad (ICMP)?", "opciones": ["A) Telnet", "B) SSH", "C) Ping"], "correcta": "C"},
    {"id": 3, "texto": "¿Qué tecnología evita el Port Forwarding tradicional y nos obligó a usar DMZ/ngrok?", "opciones": ["A) IPv6", "B) CG NAT", "C) VLAN"], "correcta": "B"},
]

# --- ESTADO GLOBAL DEL JUEGO ---
ESTADO_JUEGO = {
    "activo": False,
    "ronda_actual": -1, # -1 indica que el juego no ha comenzado
    "puntuaciones": {} # {session_id: {"nombre": "Nombre", "puntuacion": 0}}
}


# --- RUTAS DE NAVEGACIÓN (Control de Acceso por IP) ---

@app.route('/')
def index():
    """Ruta principal que diferencia entre Administrador y Jugador."""
    # request.remote_addr obtiene la IP del cliente (será la IP local si la conexión entra por el TP-Link).
    cliente_ip = request.remote_addr

    # Lógica de Diferenciación: Solo la IP estática de la MacBook obtiene la vista de Admin.
    if cliente_ip == ADMIN_IP:
        return render_template('admin.html', ip_admin=ADMIN_IP)

    # Cualquier otra IP (jugadores) recibe la vista de juego.
    return render_template('jugador.html') 


# --- GESTIÓN DE SOCKETS (Comunicación en Tiempo Real) ---

@socketio.on('conectar_jugador')
def handle_join(data):
    """Maneja la unión de un nuevo jugador o la reconexión."""
    session_id = request.sid
    nombre = data.get('nombre', 'Jugador Anónimo')

    if session_id not in ESTADO_JUEGO["puntuaciones"]:
        # Inicializa la puntuación para la nueva sesión
        ESTADO_JUEGO["puntuaciones"][session_id] = {"nombre": nombre, "puntuacion": 0, "respondido": False}
        
    join_room('jugadores') # Agrega al cliente a la sala de broadcast
    print(f"[CONEXION] Jugador {nombre} ({request.remote_addr}) unido.")
    
    # Envía a TODOS el estado de puntuaciones actualizado
    socketio.emit('actualizar_lista', ESTADO_JUEGO["puntuaciones"])


@socketio.on('enviar_respuesta')
def handle_respuesta(data):
    """Procesa la respuesta enviada por un jugador."""
    session_id = request.sid
    respuesta_opcion = data.get('respuesta').upper() # Espera 'A', 'B', o 'C'

    if not ESTADO_JUEGO["activo"] or ESTADO_JUEGO["ronda_actual"] == -1:
        emit('mensaje', 'El juego no está activo o esperando una pregunta.')
        return
        
    # Verificar si ya respondió en esta ronda
    if ESTADO_JUEGO["puntuaciones"][session_id]["respondido"]:
        emit('mensaje', 'Ya has respondido en esta ronda.')
        return

    # Lógica de puntuación
    pregunta = PREGUNTAS[ESTADO_JUEGO["ronda_actual"]]
    ESTADO_JUEGO["puntuaciones"][session_id]["respondido"] = True

    if respuesta_opcion == pregunta["correcta"]:
        ESTADO_JUEGO["puntuaciones"][session_id]["puntuacion"] += 10
        emit('mensaje', '¡CORRECTO! +10 puntos.', room=session_id)
    else:
        emit('mensaje', 'Respuesta incorrecta.', room=session_id)

    # Notificar a todos sobre la actualización de puntuaciones
    socketio.emit('actualizar_puntuacion', ESTADO_JUEGO["puntuaciones"])


@socketio.on('comando_admin')
def handle_comando_admin(data):
    """Procesa comandos solo si provienen de la IP del Administrador."""
    # Control de Acceso por IP: La IP de origen DEBE ser la del Admin.
    if request.remote_addr != ADMIN_IP:
        print(f"[SEGURIDAD] Intento de comando Admin desde IP no autorizada: {request.remote_addr}")
        return

    comando = data.get('comando')

    if comando == 'iniciar':
        ESTADO_JUEGO["activo"] = True
        ESTADO_JUEGO["ronda_actual"] = -1
        ESTADO_JUEGO["puntuaciones"] = {} # Reiniciar puntuaciones
        socketio.emit('mensaje_broadcast', '¡El juego ha iniciado! Administrador cargando la primera pregunta...', room='jugadores')

    elif comando == 'siguiente':
        ESTADO_JUEGO["ronda_actual"] += 1

        if ESTADO_JUEGO["ronda_actual"] < len(PREGUNTAS):
            # Restablecer estado de respuesta para la nueva ronda
            for info in ESTADO_JUEGO["puntuaciones"].values():
                info["respondido"] = False
                
            pregunta_data = PREGUNTAS[ESTADO_JUEGO["ronda_actual"]]
            
            # Envía la pregunta a TODOS los jugadores en la sala 'jugadores'
            socketio.emit('nueva_pregunta', pregunta_data, room='jugadores')
            print(f"[ADMIN] Pregunta {ESTADO_JUEGO['ronda_actual'] + 1} enviada.")
        else:
            socketio.emit('mensaje_broadcast', 'No hay más preguntas. Finalizando juego...', room='jugadores')
            comando_admin({'comando': 'finalizar'})

    elif comando == 'finalizar':
        ESTADO_JUEGO["activo"] = False
        ESTADO_JUEGO["ronda_actual"] = -1
        socketio.emit('mensaje_broadcast', '¡Juego Finalizado! Revisen la puntuación final.', room='jugadores')
        
    # El admin siempre recibe el estado actual para la interfaz
    socketio.emit('admin_estado', ESTADO_JUEGO, room=request.sid)


if __name__ == '__main__':
    print(f"[*] Servidor corriendo en http://{SERVER_HOST}:{SERVER_PORT}")
    print(f"[*] IP de Administrador esperada: {ADMIN_IP}")
    # Enlaza el servidor a la IP estática local, esencial para el ruteo.
    socketio.run(app, port=SERVER_PORT, allow_unsafe_werkzeug=True)
    # socketio.run(app, host=SERVER_HOST, port=SERVER_PORT, allow_unsafe_werkzeug=True)