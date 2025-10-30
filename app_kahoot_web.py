# app_kahoot_web.py
from flask import Flask, render_template, request, redirect, url_for
from flask_socketio import SocketIO, emit, join_room

app = Flask(__name__)
# ¡IMPORTANTE! Reemplaza 'tu_clave_secreta_aqui' con una clave real y segura.
app.config['SECRET_KEY'] = 'tu_clave_secreta_aqui'
socketio = SocketIO(app)

# --- CONFIGURACIÓN DE RED Y ROLES ---
# Nota: La IP ADMIN_IP debe coincidir exactamente con la IP estática fijada de tu MacBook.
ADMIN_IP = '192.168.100.101'
SERVER_HOST = '192.168.10.100' # IP Estática del Servidor
SERVER_PORT = 8080
ADMIN_SESSION_ID = None

# --- BASE DE DATOS DEL JUEGO ---
PREGUNTAS = [
    {"id": 1, "texto": "¿Cuál es el protocolo de la Capa de Transporte que garantiza la entrega de paquetes?", "opciones": ["UDP", "TCP", "ICMP"], "correcta": "B"},
    {"id": 2, "texto": "¿Qué utilidad de red se usa para probar la conectividad (ICMP)?", "opciones": ["Telnet", "SSH", "Ping"], "correcta": "C"},
    {"id": 3, "texto": "¿Qué tecnología evita el Port Forwarding tradicional y nos obligó a usar DMZ/ngrok?", "opciones": ["IPv6", "CG NAT", "VLAN"], "correcta": "B"},
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
    return render_template('login_o_jugador.html')

@app.route('/admin_view')
def admin_view():
    """Ruta dedicada para la vista del administrador."""
    # En un sistema real, aquí se verificaría la sesión.
    # Para simplificar, si llegaste aquí, se asume que tu nombre fue 'Admin'.
    return render_template('admin.html', ip_admin=request.remote_addr)

@app.route('/jugador')
def jugador_view():
    """Ruta dedicada para la vista del jugador."""
    return render_template('jugador.html')

# --- GESTIÓN DE SOCKETS (Comunicación en Tiempo Real) ---
@socketio.on('conectar_jugador')
def handle_join(data):
    """Maneja la unión de un nuevo jugador, incluyendo la validación de 'Admin'."""
    global ADMIN_SESSION_ID
    session_id = request.sid
    nombre_ingresado = data.get('nombre', 'Jugador Anónimo').strip()
    
    # --- LÓGICA DE CONTROL DE ACCESO ADMIN ---
    if nombre_ingresado.upper() == "ADMIN":
        if ADMIN_SESSION_ID is None:
            # 1. Permite el acceso: La sesión es declarada como Administrador.
            ADMIN_SESSION_ID = session_id
            print(f"[ADMIN] Admin conectado desde {request.remote_addr}")
            
            # Notificamos al cliente que debe redirigir su navegador a la vista de admin.
            emit('redirigir', url_for('admin_view'), room=session_id)
            return
        else:
            # 2. Rechaza el acceso: Ya hay un administrador activo.
            emit('mensaje_error_login', 'ERROR: Ya hay un Administrador activo. Solo se permite uno.')
            return

    # --- Lógica de Jugador Estándar (Si no es 'Admin' o si el 'Admin' ya está ocupado) ---
    
    # 3. Inicializa el jugador (asegurando un nombre único si es necesario, aunque aquí lo simplificamos)
    nombre = nombre_ingresado
    
    if session_id not in ESTADO_JUEGO["puntuaciones"]:
        ESTADO_JUEGO["puntuaciones"][session_id] = {"nombre": nombre, "puntuacion": 0, "respondido": False}
        
    join_room('jugadores') 
    print(f"[CONEXION] Jugador {nombre} ({request.remote_addr}) unido.")
    if session_id not in ESTADO_JUEGO["puntuaciones"]:
        # Inicializa la puntuación para la nueva sesión
        ESTADO_JUEGO["puntuaciones"][session_id] = {"nombre": nombre, "puntuacion": 0, "respondido": False}
    
    join_room('jugadores') # Agrega al cliente a la sala de broadcast
    print(f"[CONEXION] Jugador {nombre} ({request.remote_addr}) unido.")

    # 1. CORRECCIÓN (Problema 1): Notifica al admin para actualizar la lista de jugadores.
    socketio.emit('admin_estado', ESTADO_JUEGO, room=ADMIN_IP)
    
    # Notificar al jugador sobre el estado actual
    if ESTADO_JUEGO["activo"]:
        if ESTADO_JUEGO["ronda_actual"] != -1 and ESTADO_JUEGO["ronda_actual"] < len(PREGUNTAS):
            # Si hay una pregunta activa, se la enviamos inmediatamente.
            pregunta_data = PREGUNTAS[ESTADO_JUEGO["ronda_actual"]]
            emit('nueva_pregunta', pregunta_data, room=session_id)
            emit('mensaje', '¡Bienvenido! Ya hay una pregunta activa.', room=session_id)
        else:
            # Si el juego está activo pero esperando una nueva pregunta.
            emit('mensaje', '¡Bienvenido! El juego está activo. Esperando la siguiente pregunta.', room=session_id)
    else:
        # El juego está inactivo.
        emit('mensaje', '¡Bienvenido! El juego está INACTIVO. Esperando que el Administrador inicie.', room=session_id)

    # Nota: La emisión 'actualizar_lista' fue eliminada ya que 'admin_estado' es más completo.

@socketio.on('enviar_respuesta')
def handle_respuesta(data):
    """Procesa la respuesta enviada por un jugador."""
    session_id = request.sid
    respuesta_opcion = data.get('respuesta').upper() # Espera 'A', 'B', o 'C'

    if not ESTADO_JUEGO["activo"] or ESTADO_JUEGO["ronda_actual"] == -1:
        emit('mensaje', 'El juego no está activo o esperando una pregunta.')
        return

    # Se mantiene la corrección del problema anterior (KeyError)
    if session_id not in ESTADO_JUEGO["puntuaciones"]:
        emit('mensaje', 'Error de conexión. Por favor, recarga y únete de nuevo.')
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

    # 2. CORRECCIÓN (Problema 2): Actualización de puntuación en tiempo real para el admin
    socketio.emit('admin_estado', ESTADO_JUEGO) # Emitimos a todos (incluido el admin)
    
    # Eliminamos la línea duplicada: socketio.emit('actualizar_puntuacion', ESTADO_JUEGO["puntuaciones"])


@socketio.on('comando_admin')
def handle_comando_admin(data):
    global ADMIN_SESSION_ID
    """Procesa comandos solo si provienen de la IP del Administrador."""
    if request.sid != ADMIN_SESSION_ID:
        print(f"[SEGURIDAD] Comando no autorizado desde SID: {request.sid}")
        return

    comando = data.get('comando')

    if comando == 'iniciar':
        ESTADO_JUEGO["activo"] = True
        ESTADO_JUEGO["ronda_actual"] = -1
        # 3. CORRECCIÓN (Problema 3): Se eliminan las puntuaciones, pero los jugadores permanecen en el ESTADO_JUEGO
        # Reiniciar puntuaciones para todos los jugadores existentes:
        for session_id in list(ESTADO_JUEGO["puntuaciones"].keys()):
            ESTADO_JUEGO["puntuaciones"][session_id]["puntuacion"] = 0
            ESTADO_JUEGO["puntuaciones"][session_id]["respondido"] = False

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
            # Llamamos al finalizador directamente con el diccionario de datos.
            handle_comando_admin({'comando': 'finalizar'})

    elif comando == 'finalizar':
        ESTADO_JUEGO["activo"] = False
        ESTADO_JUEGO["ronda_actual"] = -1
        socketio.emit('mensaje_broadcast', '¡Juego Finalizado! Revisen la puntuación final.', room='jugadores')
        
    # El admin siempre recibe el estado actual para la interfaz
    socketio.emit('admin_estado', ESTADO_JUEGO, room=request.sid)

@socketio.on('disconnect')
def handle_disconnect():
    """Libera el slot de administrador si el administrador actual se desconecta."""
    global ADMIN_SESSION_ID
    session_id = request.sid

    if session_id == ADMIN_SESSION_ID:
        ADMIN_SESSION_ID = None
        print("[ADMIN] Administrador se ha desconectado. Slot liberado.")
        # Opcional: Notificar a todos que el juego fue interrumpido.
        socketio.emit('mensaje_broadcast', 'El Administrador se ha desconectado.', room='jugadores')

    # Remoción de jugadores (lógica opcional si manejas la limpieza de puntuaciones)
    if session_id in ESTADO_JUEGO["puntuaciones"]:
        del ESTADO_JUEGO["puntuaciones"][session_id]
        socketio.emit('admin_estado', ESTADO_JUEGO)

if __name__ == '__main__':
    print(f"[*] Servidor corriendo en http://{SERVER_HOST}:{SERVER_PORT}")
    print(f"[*] IP de Administrador esperada: {ADMIN_IP}")
    # Enlaza el servidor a la IP estática local, esencial para el ruteo.
    socketio.run(app, host=SERVER_HOST, port=SERVER_PORT, allow_unsafe_werkzeug=True)