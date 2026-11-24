"""Red local para el modo MULTIJUGADOR (una maquina arcade contra otra).

Como funciona (lockstep):
  * Las dos maquinas simulan la MISMA pelea, paso a paso, a 60 pasos por segundo.
  * Por la red solo viajan los BOTONES de cada paso (unos pocos bytes).
  * El paso N solo se simula cuando ya se tienen los botones de los dos jugadores
    para ese paso. Lo que pulsas se aplica RETARDO pasos despues (3 = 50 ms),
    tiempo de sobra para que llegue a la otra maquina en una red de casa.
  * Como la fisica del juego no usa nada aleatorio, las dos pantallas ven lo mismo.
    Cada segundo el ANFITRION manda un resumen (vida, posiciones) para comprobarlo
    y, si algo se ha desviado, la otra maquina se corrige sola.

Conexion:
  * El ANFITRION ("CREAR PARTIDA") escucha en el puerto TCP RED_PUERTO (50505) y
    anuncia la partida por UDP (puerto RED_PUERTO + 1) para que la otra maquina
    la vea en la lista sin escribir la IP.
  * El INVITADO ("UNIRSE") elige la partida de la lista o escribe la IP.

Mensajes (una linea JSON por mensaje):
  hola  {v, pj, nombre}  (+ dif del anfitrion)       saludo y datos del luchador
  in    {f, b}                                       botones del paso f
  chk   {f, s}                                       resumen del estado (anfitrion)
  ping / pong {ts}                                   para medir la latencia
  bye                                                me voy
"""
import json
import os
import queue
import socket
import threading
import time

import config as C                                   # carga el .env antes de leer RED_*

VERSION = 1
PUERTO = C.RED_PUERTO
PUERTO_ANUNCIO = PUERTO + 1
LAG_PRUEBA = int(os.getenv("RED_LAG_MS", "0"))       # simula una red lenta (solo para pruebas)
FIRMA = "PIXELFIGHTERS"

# botones de un paso, en un numero
IZQ, DER, SALTO, GOLPE, ESPECIAL, OK = 1, 2, 4, 8, 16, 32
NOMBRES = {"izq": IZQ, "der": DER, "salto": SALTO, "golpe": GOLPE, "especial": ESPECIAL, "ok": OK}


def ips_locales():
    """IPs de esta maquina en la red local (la que hay que darle a la otra arcade)."""
    ips = []
    try:                                               # no envia nada: solo elige la interfaz de salida
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("10.255.255.255", 1))
        ips.append(s.getsockname()[0])
        s.close()
    except OSError:
        pass
    try:
        for info in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
            ip = info[4][0]
            if ip not in ips and not ip.startswith("127."):
                ips.append(ip)
    except OSError:
        pass
    return [ip for ip in ips if not ip.startswith("127.")] or ["127.0.0.1"]


def separar_direccion(texto, puerto=PUERTO):
    """'192.168.1.20' o '192.168.1.20:50505' -> (host, puerto)."""
    texto = texto.strip()
    host, _, p = texto.partition(":")
    return host, int(p) if p.isdigit() else puerto


# ---------------------------------------------------------------- conexion TCP
class Conexion:
    """Una conexion ya establecida. Lee en un hilo y deja los mensajes en una cola."""

    def __init__(self, sock, es_anfitrion):
        self.sock = sock
        self.es_anfitrion = es_anfitrion
        self.entrada = queue.Queue()
        self.cerrada = False
        self.motivo = ""
        self.ping_ms = None
        self._t_ping = 0.0
        self._lock = threading.Lock()
        sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)   # sin esperas: mensajes pequenos
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
        sock.settimeout(None)
        self._salida = queue.Queue() if LAG_PRUEBA > 0 else None
        threading.Thread(target=self._leer, daemon=True).start()
        if self._salida is not None:
            threading.Thread(target=self._enviar_con_lag, daemon=True).start()

    def remoto(self):
        try:
            return self.sock.getpeername()[0]
        except OSError:
            return "?"

    # -- enviar
    def enviar(self, **msg):
        if self.cerrada:
            return
        datos = (json.dumps(msg, separators=(",", ":")) + "\n").encode()
        if self._salida is not None:
            self._salida.put((time.monotonic() + LAG_PRUEBA / 1000, datos))
            return
        self._enviar_ya(datos)

    def _enviar_ya(self, datos):
        try:
            with self._lock:
                self.sock.sendall(datos)
        except OSError as e:
            self._cerrar(f"error al enviar: {e}")

    def _enviar_con_lag(self):
        while not self.cerrada:
            cuando, datos = self._salida.get()
            espera = cuando - time.monotonic()
            if espera > 0:
                time.sleep(espera)
            self._enviar_ya(datos)

    # -- recibir
    def _leer(self):
        buf = b""
        try:
            while True:
                trozo = self.sock.recv(65536)
                if not trozo:
                    self._cerrar("el otro jugador ha cerrado la conexion")
                    return
                buf += trozo
                while b"\n" in buf:
                    linea, buf = buf.split(b"\n", 1)
                    if not linea:
                        continue
                    try:
                        msg = json.loads(linea)
                    except ValueError:
                        continue
                    t = msg.get("t")
                    if t == "ping":
                        self.enviar(t="pong", ts=msg.get("ts"))
                    elif t == "pong":
                        try:
                            self.ping_ms = (time.monotonic() - float(msg["ts"])) * 1000
                        except (KeyError, TypeError, ValueError):
                            pass
                    elif t == "bye":
                        self._cerrar("el otro jugador ha salido")
                        return
                    else:
                        self.entrada.put(msg)
        except OSError as e:
            self._cerrar(f"conexion perdida: {e}")

    def mensajes(self):
        """Todos los mensajes que han llegado desde la ultima vez."""
        out = []
        while True:
            try:
                out.append(self.entrada.get_nowait())
            except queue.Empty:
                return out

    def medir_ping(self):
        """Llamar a menudo: manda un ping cada segundo."""
        ahora = time.monotonic()
        if ahora - self._t_ping > 1.0:
            self._t_ping = ahora
            self.enviar(t="ping", ts=ahora)

    def _cerrar(self, motivo):
        if not self.cerrada:
            self.cerrada = True
            self.motivo = motivo
        try:
            self.sock.close()
        except OSError:
            pass

    def cerrar(self):
        if not self.cerrada:
            try:
                with self._lock:
                    self.sock.sendall(b'{"t":"bye"}\n')
            except OSError:
                pass
        self._cerrar("has salido")


# ---------------------------------------------------------------- anfitrion
class Anfitrion:
    """Espera a que se conecte la otra maquina y anuncia la partida en la red local."""

    def __init__(self, nombre="ARCADE", puerto=PUERTO):
        self.nombre = nombre[:20]
        self.puerto = puerto
        self.conexion = None
        self.error = ""
        self._parar = False
        self.servidor = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.servidor.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            self.servidor.bind(("", puerto))
            self.servidor.listen(1)
            self.servidor.settimeout(0.5)
        except OSError as e:
            self.error = f"no puedo abrir el puerto {puerto}: {e}"
            self.servidor.close()
            return
        threading.Thread(target=self._aceptar, daemon=True).start()
        threading.Thread(target=self._anunciar, daemon=True).start()

    def _aceptar(self):
        while not self._parar and self.conexion is None:
            try:
                sock, _ = self.servidor.accept()
            except socket.timeout:
                continue
            except OSError:
                return
            self.conexion = Conexion(sock, es_anfitrion=True)
        try:
            self.servidor.close()
        except OSError:
            pass

    def _anunciar(self):
        """Grita por UDP 'aqui hay una partida' una vez por segundo."""
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        msg = json.dumps({"firma": FIRMA, "v": VERSION, "nombre": self.nombre,
                          "puerto": self.puerto}).encode()
        destinos = ["255.255.255.255", "127.0.0.1"]       # 127.0.0.1: pruebas en un solo PC
        for ip in ips_locales():                           # broadcast de la subred (p.ej. 192.168.1.255)
            partes = ip.split(".")
            if len(partes) == 4 and ip != "127.0.0.1":
                destinos.append(".".join(partes[:3] + ["255"]))
        while not self._parar and self.conexion is None:
            for d in destinos:
                try:
                    s.sendto(msg, (d, PUERTO_ANUNCIO))
                except OSError:
                    pass
            time.sleep(1.0)
        s.close()

    def cancelar(self):
        self._parar = True
        try:
            self.servidor.close()
        except OSError:
            pass


# ---------------------------------------------------------------- invitado
class Buscador:
    """Escucha los anuncios de partidas en la red local."""

    def __init__(self):
        self.partidas = {}               # (ip, puerto) -> {"nombre", "visto"}
        self.error = ""
        self._parar = False
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            self.sock.bind(("", PUERTO_ANUNCIO))
            self.sock.settimeout(0.5)
        except OSError as e:
            self.error = f"no puedo escuchar anuncios: {e}"
            return
        threading.Thread(target=self._escuchar, daemon=True).start()

    def _escuchar(self):
        while not self._parar:
            try:
                datos, (ip, _) = self.sock.recvfrom(2048)
            except socket.timeout:
                continue
            except OSError:
                return
            try:
                d = json.loads(datos)
            except ValueError:
                continue
            if d.get("firma") != FIRMA or d.get("v") != VERSION:
                continue
            self.partidas[(ip, int(d.get("puerto", PUERTO)))] = {
                "nombre": str(d.get("nombre", "ARCADE"))[:20], "visto": time.monotonic()}

    def lista(self):
        """Partidas vistas en los ultimos 3 segundos: [(ip, puerto, nombre)]."""
        ahora = time.monotonic()
        vivas = [(ip, p, d["nombre"]) for (ip, p), d in list(self.partidas.items())
                 if ahora - d["visto"] < 3.0]
        # si la misma partida se ve por 127.0.0.1 y por la IP de red, mostrarla una vez
        vistas, out = set(), []
        for ip, p, n in sorted(vivas, key=lambda x: x[0] == "127.0.0.1"):
            if (n, p) in vistas:
                continue
            vistas.add((n, p))
            out.append((ip, p, n))
        return out

    def cancelar(self):
        self._parar = True
        try:
            self.sock.close()
        except OSError:
            pass


class Conectar:
    """Conecta con un anfitrion en segundo plano (no congela la pantalla)."""

    def __init__(self, host, puerto=PUERTO, timeout=5.0):
        self.host, self.puerto = host, puerto
        self.conexion = None
        self.error = ""
        self.terminado = False
        threading.Thread(target=self._trabajo, args=(timeout,), daemon=True).start()

    def _trabajo(self, timeout):
        try:
            sock = socket.create_connection((self.host, self.puerto), timeout=timeout)
            self.conexion = Conexion(sock, es_anfitrion=False)
        except socket.timeout:
            self.error = f"{self.host}:{self.puerto} no responde (misma WiFi? juego abierto en CREAR PARTIDA?)"
        except ConnectionRefusedError:
            self.error = f"{self.host}:{self.puerto} rechaza la conexion (la otra arcade no esta en CREAR PARTIDA)"
        except OSError as e:
            self.error = f"no se pudo conectar con {self.host}:{self.puerto}: {e}"
        self.terminado = True


# ---------------------------------------------------------------- teclas
class TeclasRed:
    """Botones de un paso, usables como pygame.key.get_pressed(): teclas['izq']."""

    def __init__(self, bits=0):
        self.bits = bits

    def __getitem__(self, k):
        return bool(self.bits & NOMBRES.get(k, 0))


# controles de los luchadores en una pelea en red (se leen de TeclasRed)
CTRL_RED = {"izquierda": "izq", "derecha": "der", "salto": "salto", "golpe": "golpe",
            "especial": "especial"}
