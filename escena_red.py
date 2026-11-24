"""MULTIJUGADOR: una maquina arcade contra otra por la red local.

  Menu > MULTIJUGADOR
     CREAR PARTIDA  -> eliges luchador y escenario -> la pantalla muestra TU IP y espera
     UNIRSE         -> eliges luchador -> eliges la partida de la lista (o escribes la IP)
  -> los dos ven "VS" -> PeleaRed (al mejor de 3 rondas, revancha si los dos pulsan F)

El anfitrion es siempre P1 (izquierda) y el invitado P2 (derecha), en las dos pantallas.
Ver red.py para el detalle de como se sincroniza.
"""
import json
import textwrap

import pygame

import avatar
import config as C
import escenarios
import red
import roster
import sonido
from efectos import Efectos, texto_borde
from fighter import CTRL_JUGADOR, es_tecla, pulsada, superficie_personaje
from fuente_pixel import titulo
from ia_cpu import CPU
from scenes import (AMARILLO, AZUL, BLANCO, DIFICULTADES, GRIS, ORDEN_DIF, ROJO, Escena, Menu, Pelea,
                    barra_stat, dibujar_fondo, poner, stats_normalizados, texto)
from teclado import FILAS_IP, Teclado

ARRIBA = (pygame.K_w, pygame.K_UP)
ABAJO = (pygame.K_s, pygame.K_DOWN)
IZQ = (pygame.K_a, pygame.K_LEFT)
DER = (pygame.K_d, pygame.K_RIGHT)
OK = (pygame.K_f, pygame.K_k, pygame.K_RETURN, pygame.K_SPACE)
ATRAS = (pygame.K_g, pygame.K_l, pygame.K_BACKSPACE)
VERDE = (90, 230, 130)

ARCHIVO_RED = C.DATA_DIR / "red.json"          # recuerda la ultima IP usada


def _ultima_ip():
    try:
        return json.loads(ARCHIVO_RED.read_text(encoding="utf-8")).get("ultima_ip", "") or C.RED_IP
    except (OSError, ValueError):
        return C.RED_IP


def _guardar_ip(ip):
    try:
        ARCHIVO_RED.write_text(json.dumps({"ultima_ip": ip}), encoding="utf-8")
    except OSError:
        pass


def personaje_de_dict(d):
    """El luchador del otro jugador llega como JSON (rasgos, cuerpo, traje...). No se guarda."""
    import rasgos as R
    cuerpo = d.get("cuerpo") if d.get("cuerpo") in avatar.CUERPOS else "equilibrado"
    traje = d.get("traje") if d.get("traje") in avatar.TRAJES else "karate"
    especial = d.get("especial") if d.get("especial") in __import__("especiales").TIPOS else "ONDA PIXEL"
    return roster.Personaje(id=str(d.get("id", "remoto"))[:16], nombre=str(d.get("nombre", "RIVAL"))[:12],
                            rasgos=R.normalizar(d.get("rasgos", {})), cuerpo=cuerpo, traje=traje,
                            especial=especial)


# ================================================================ LOBBY
class Multijugador(Escena):
    """rol -> luchador -> [escenario -> esperando] | [buscar -> (ip) -> conectando] -> saludo -> vs"""
    ROLES = ["CREAR PARTIDA", "UNIRSE A PARTIDA", "VOLVER"]

    def __init__(self, juego):
        super().__init__(juego)
        self.estado = "rol"
        self.i = 0
        self.anfitrion = False
        n = len(juego.roster)
        self.idx = n - 1 if n > 3 else 0
        self.dif = ORDEN_DIF.index(getattr(juego, "dificultad", "normal"))
        self.minis = None
        self.servidor = None                # red.Anfitrion
        self.buscador = None                # red.Buscador
        self.intento = None                 # red.Conectar
        self.con = None                     # red.Conexion
        self.teclado = None
        self.sel = 0                        # fila elegida en la lista de partidas
        self.msg = ""
        self.remoto = None                  # Personaje del otro jugador
        self.dif_remota = None
        self.retardo = C.RED_RETARDO
        self.pendientes = []                # mensajes que llegan antes de empezar la pelea
        self.t_vs = 0
        self.entregada = False              # la conexion ya la tiene la PeleaRed
        sonido.musica("menu")

    @property
    def pj(self):
        return self.j.roster[self.idx]

    # ------------------------------------------------------------ limpieza
    def _soltar_red(self):
        for obj in (self.servidor, self.buscador):
            if obj is not None:
                obj.cancelar()
        self.servidor = self.buscador = self.intento = None
        if self.con is not None and not self.entregada:
            self.con.cerrar()
        self.con = None

    def salir(self):
        if not self.entregada:
            self._soltar_red()
        elif self.servidor:                       # el anfitrion ya no anuncia
            self.servidor.cancelar()

    def _volver_menu(self):
        sonido.play("menu_atras")
        self.j.cambiar(Menu(self.j))

    # ------------------------------------------------------------ entrada
    def eventos(self, evs):
        for e in evs:
            if e.type != pygame.KEYDOWN:
                continue
            k = e.key
            st = self.estado
            if st == "rol":
                if k == pygame.K_ESCAPE:
                    return self._volver_menu()
                if k in ARRIBA + ABAJO:
                    self.i = (self.i + (1 if k in ABAJO else -1)) % len(self.ROLES)
                    sonido.play("menu_mover", variar=False)
                elif k in OK:
                    sonido.play("menu_ok", variar=False)
                    if self.i == 2:
                        return self._volver_menu()
                    self.anfitrion = self.i == 0
                    self.estado = "luchador"
            elif st == "luchador":
                if k == pygame.K_ESCAPE or k in ATRAS:
                    sonido.play("menu_atras")
                    self.estado = "rol"
                elif k in IZQ + DER:
                    self.idx = (self.idx + (1 if k in DER else -1)) % len(self.j.roster)
                    sonido.play("menu_mover", variar=False)
                elif k in OK:
                    sonido.play("menu_ok", variar=False)
                    if self.anfitrion:
                        self.estado = "escenario"
                        if self.minis is None:
                            self.minis = {d: escenarios.crear(d).miniatura(240, 135) for d in ORDEN_DIF}
                    else:
                        self._empezar_busqueda()
            elif st == "escenario":
                if k == pygame.K_ESCAPE or k in ATRAS:
                    sonido.play("menu_atras")
                    self.estado = "luchador"
                elif k in IZQ + DER + ARRIBA + ABAJO:
                    self.dif = (self.dif + (1 if k in DER + ABAJO else -1)) % 3
                    sonido.play("menu_mover", variar=False)
                elif k in OK:
                    sonido.play("menu_ok", variar=False)
                    self._empezar_espera()
            elif st == "esperando":
                if k == pygame.K_ESCAPE or k in ATRAS:
                    sonido.play("menu_atras")
                    self._soltar_red()
                    self.estado = "escenario"
            elif st == "buscar":
                filas = self._filas_busqueda()
                if k == pygame.K_ESCAPE or k in ATRAS:
                    sonido.play("menu_atras")
                    self._soltar_red()
                    self.estado = "luchador"
                elif k in ARRIBA + ABAJO:
                    self.sel = (self.sel + (1 if k in ABAJO else -1)) % len(filas)
                    sonido.play("menu_mover", variar=False)
                elif k in OK:
                    sonido.play("menu_ok", variar=False)
                    tipo, valor = filas[self.sel][0], filas[self.sel][1]
                    if tipo == "ip":
                        self.teclado = Teclado(_ultima_ip(), filas=FILAS_IP, maximo=21)
                        self.teclado.f, self.teclado.c = 2, 3          # cursor en OK
                        self.estado = "ip"
                    else:
                        self._conectar(*valor)
            elif st == "ip":
                tec = self.teclado
                if k == pygame.K_ESCAPE:
                    sonido.play("menu_atras")
                    self.estado = "buscar"
                elif k in IZQ + DER + ARRIBA + ABAJO:
                    tec.mover((k in DER) - (k in IZQ), (k in ABAJO) - (k in ARRIBA))
                    sonido.play("menu_mover", variar=False)
                elif k in ATRAS:
                    if not tec.borrar():
                        self.estado = "buscar"
                    sonido.play("menu_atras", variar=False)
                elif k in OK:
                    if tec.pulsar() == "ok" and tec.texto:
                        sonido.play("menu_ok", variar=False)
                        _guardar_ip(tec.texto)
                        self._conectar(*red.separar_direccion(tec.texto))
                    else:
                        sonido.play("menu_mover", variar=False)
            elif st == "error":
                if k == pygame.K_ESCAPE or k in OK + ATRAS:
                    sonido.play("menu_atras")
                    self._soltar_red()
                    self.estado = "escenario" if self.anfitrion else "buscar"
                    if not self.anfitrion:
                        self._empezar_busqueda()
            elif st in ("conectando", "saludo", "vs"):
                if k == pygame.K_ESCAPE:
                    self._soltar_red()
                    return self._volver_menu()

    # ------------------------------------------------------------ pasos
    def _empezar_espera(self):
        self.servidor = red.Anfitrion(C.RED_NOMBRE)
        if self.servidor.error:
            self._fallo(self.servidor.error)
            return
        self.ips = red.ips_locales()
        self.estado = "esperando"

    def _empezar_busqueda(self):
        if self.buscador is None:
            self.buscador = red.Buscador()
        self.sel = 0
        self.estado = "buscar"

    def _filas_busqueda(self):
        filas = []
        if self.buscador is not None:
            for ip, puerto, nombre in self.buscador.lista():
                filas.append(("partida", (ip, puerto), f"{nombre}   ({ip})"))
        filas.append(("ip", None, "ESCRIBIR IP A MANO"))
        return filas

    def _conectar(self, host, puerto=red.PUERTO):
        self.intento = red.Conectar(host, puerto)
        self.msg = f"{host}:{puerto}"
        self.estado = "conectando"

    def _fallo(self, msg):
        self.msg = msg
        self.estado = "error"
        sonido.play("menu_atras")

    def _saludar(self, con):
        self.con = con
        hola = dict(t="hola", v=red.VERSION, pj=self.pj.a_dict(), nombre=C.RED_NOMBRE)
        if self.anfitrion:
            hola.update(dif=ORDEN_DIF[self.dif], retardo=C.RED_RETARDO)
        con.enviar(**hola)
        self.estado = "saludo"

    # ------------------------------------------------------------ bucle
    def actualizar(self, dt):
        super().actualizar(dt)
        st = self.estado
        if st == "buscar" and self.buscador is not None:
            self.sel = min(self.sel, len(self._filas_busqueda()) - 1)
        elif st == "esperando" and self.servidor.conexion is not None:
            self._saludar(self.servidor.conexion)
            self.servidor.cancelar()                 # deja de anunciarse
        elif st == "conectando" and self.intento is not None and self.intento.terminado:
            if self.intento.conexion is None:
                self._fallo(self.intento.error)
            else:
                if self.buscador:
                    self.buscador.cancelar()
                    self.buscador = None
                self._saludar(self.intento.conexion)
        elif st == "saludo":
            if self.con.cerrada:
                self._fallo(self.con.motivo)
                return
            for m in self.con.mensajes():
                if self.remoto is not None:
                    self.pendientes.append(m)     # ya es de la pelea: se lo pasamos
                    continue
                if m.get("t") != "hola":
                    continue
                if m.get("v") != red.VERSION:
                    self._fallo(f"Version distinta: aqui {red.VERSION}, alli {m.get('v')}. "
                                f"Copia el mismo juego en las dos arcades.")
                    return
                self.remoto = personaje_de_dict(m.get("pj", {}))
                self.nombre_remoto = str(m.get("nombre", "ARCADE"))[:16]
                if not self.anfitrion:
                    self.dif_remota = m.get("dif") if m.get("dif") in ORDEN_DIF else "normal"
                    self.retardo = max(1, min(10, int(m.get("retardo", C.RED_RETARDO))))
                self.estado, self.t_vs = "vs", 0
                sonido.play("lucha", variar=False)
        elif st == "vs":
            if self.con.cerrada:
                self._fallo(self.con.motivo)
                return
            self.t_vs += dt
            if self.t_vs > 2600:
                self.entregada = True
                dif = ORDEN_DIF[self.dif] if self.anfitrion else self.dif_remota
                self.j.cambiar(PeleaRed(self.j, self.con, self.anfitrion, self.pj, self.remoto, dif,
                                        self.retardo, self.pendientes + self.con.mensajes()))

    # ------------------------------------------------------------ dibujo
    def dibujar(self, p):
        st = self.estado
        dibujar_fondo(p, self.t, publico=st == "rol")
        fc, f = self.j.f_chica, self.j.fuente
        titulo(p, "MULTIJUGADOR", 60, (C.ANCHO // 2, 45))
        if st == "rol":
            for k, op in enumerate(self.ROLES):
                sel = k == self.i
                texto_borde(p, ("> " + op + " <") if sel else op, 50 if sel else 42,
                            AMARILLO if sel else BLANCO, (C.ANCHO // 2, 190 + k * 70))
            texto(p, fc, "Las dos arcades tienen que estar en la misma red (WiFi o cable)",
                  GRIS, C.ANCHO // 2, 420, True)
            texto(p, fc, "Una CREA la partida y la otra se UNE", GRIS, C.ANCHO // 2, 444, True)
            texto(p, fc, "W/S MOVER   F ACEPTAR   ESC MENU", GRIS, C.ANCHO // 2, 500, True)
        elif st == "luchador":
            self._dibujar_luchador(p)
        elif st == "escenario":
            self._dibujar_escenario(p)
        elif st == "esperando":
            texto_borde(p, "ESPERANDO AL OTRO JUGADOR" + "." * (int(self.t * 2) % 4), 40, BLANCO,
                        (C.ANCHO // 2, 130))
            texto(p, f, "En la otra arcade:  MULTIJUGADOR  >  UNIRSE A PARTIDA", GRIS, C.ANCHO // 2, 175, True)
            texto(p, f, "Te vera en la lista como:", GRIS, C.ANCHO // 2, 220, True)
            texto_borde(p, C.RED_NOMBRE, 44, AMARILLO, (C.ANCHO // 2, 268))
            texto(p, f, "Si no aparece, que escriba esta IP:", GRIS, C.ANCHO // 2, 310, True)
            for k, ip in enumerate(self.ips[:2]):
                titulo(p, ip, 54, (C.ANCHO // 2, 368 + k * 52))
            if red.PUERTO != 50505:
                texto(p, fc, f"(puerto {red.PUERTO})", GRIS, C.ANCHO // 2, 470, True)
            pj = self.pj
            poner(p, superficie_personaje(pj, 1, 2, "reposo0" if int(self.t * 2) % 2 else "reposo1"),
                  110, 470, 1, 2)
            texto(p, fc, "G / ESC  CANCELAR", GRIS, C.ANCHO // 2, 505, True)
        elif st == "buscar":
            texto_borde(p, "ELIGE LA PARTIDA", 40, BLANCO, (C.ANCHO // 2, 120))
            filas = self._filas_busqueda()
            if len(filas) == 1:
                texto(p, f, "Buscando partidas en la red" + "." * (int(self.t * 2) % 4), GRIS,
                      C.ANCHO // 2, 175, True)
                texto(p, fc, "(en la otra arcade: MULTIJUGADOR > CREAR PARTIDA)", GRIS, C.ANCHO // 2, 205, True)
            for k, (_, _, rot) in enumerate(filas):
                sel = k == self.sel
                y = 250 + k * 50
                texto_borde(p, ("> " + rot + " <") if sel else rot, 36 if sel else 30,
                            AMARILLO if sel else BLANCO, (C.ANCHO // 2, y))
            if self.buscador is not None and self.buscador.error:
                texto(p, fc, self.buscador.error, ROJO, C.ANCHO // 2, 460, True)
            texto(p, fc, f"Mi IP: {', '.join(red.ips_locales()[:2])}", GRIS, C.ANCHO // 2, 480, True)
            texto(p, fc, "W/S ELEGIR   F CONECTAR   G VOLVER", GRIS, C.ANCHO // 2, 505, True)
        elif st == "ip":
            texto(p, f, "IP DE LA OTRA ARCADE (sale en su pantalla)", GRIS, C.ANCHO // 2, 105, True)
            self.teclado.dibujar_nombre(p, C.ANCHO // 2, 170, self.t, "192.168.1.20")
            self.teclado.dibujar(p, C.ANCHO // 2, 240, fc)
            texto(p, fc, "joystick mover   F pulsar   G borrar   OK conectar", GRIS, C.ANCHO // 2, 505, True)
        elif st == "conectando":
            texto_borde(p, "CONECTANDO" + "." * (int(self.t * 3) % 4), 48, BLANCO, (C.ANCHO // 2, 230))
            texto(p, f, self.msg, GRIS, C.ANCHO // 2, 280, True)
        elif st == "saludo":
            texto_borde(p, "CONECTADO!", 48, VERDE, (C.ANCHO // 2, 230))
            texto(p, f, "Intercambiando luchadores...", GRIS, C.ANCHO // 2, 280, True)
        elif st == "vs":
            self._dibujar_vs(p)
        elif st == "error":
            texto_borde(p, "NO SE PUDO CONECTAR", 46, ROJO, (C.ANCHO // 2, 170))
            for k, linea in enumerate(textwrap.wrap(self.msg, 50)[:4]):
                texto(p, f, linea, BLANCO, C.ANCHO // 2, 220 + k * 30, True)
            consejos = ["- Las dos arcades en la misma WiFi / router",
                        "- La otra arcade en MULTIJUGADOR > CREAR PARTIDA",
                        "- En Windows: permite Python en el cortafuegos (sale un aviso)"]
            for k, c in enumerate(consejos):
                texto(p, fc, c, GRIS, C.ANCHO // 2, 360 + k * 24, True)
            texto(p, fc, "F  VOLVER", AMARILLO, C.ANCHO // 2, 500, True)

    def _dibujar_luchador(self, p):
        f, fc = self.j.fuente, self.j.f_chica
        pj = self.pj
        cx = C.ANCHO // 2
        texto(p, f, "ELIGE TU LUCHADOR" + ("  (CREAS LA PARTIDA)" if self.anfitrion else "  (TE UNES)"),
              AMARILLO, cx, 88, True)
        texto_borde(p, pj.nombre, 46, BLANCO, (cx, 140))
        texto(p, f, f"< {self.idx + 1}/{len(self.j.roster)} >", GRIS, cx, 160, True)
        img = superficie_personaje(pj, 1, 3, "reposo0" if int(self.t * 2) % 2 else "reposo1")
        poner(p, img, cx, 400, 1, 3)
        texto(p, f, f"{avatar.STATS[pj.cuerpo]['nombre']} - {pj.traje.upper()} - {pj.especial}",
              pj.color if sum(pj.color) > 200 else BLANCO, cx, 395, True)
        for j, (nom, v) in enumerate(stats_normalizados(pj)):
            barra_stat(p, fc, nom, v, cx - 135, 425 + j * 17, 160, ROJO if self.anfitrion else AZUL)
        texto(p, fc, "A / D  ELEGIR      F  ACEPTAR      G  VOLVER", GRIS, cx, 505, True)

    def _dibujar_escenario(self, p):
        fc = self.j.f_chica
        texto(p, self.j.fuente, "ELIGE EL ESCENARIO", AMARILLO, C.ANCHO // 2, 88, True)
        for k, cl in enumerate(ORDEN_DIF):
            d = DIFICULTADES[cl]
            sel = k == self.dif
            cx = 170 + k * 310
            y = 130 + (0 if sel else 12)
            marco = pygame.Rect(cx - 130, y, 260, 230)
            pygame.draw.rect(p, (20, 14, 40), marco, border_radius=10)
            pygame.draw.rect(p, d["color"] if sel else (90, 80, 120), marco, 4 if sel else 2, border_radius=10)
            p.blit(self.minis[cl], (cx - 120, y + 10))
            nombre = escenarios.ESCENARIOS[cl].nombre or d["nombre"]
            texto_borde(p, nombre, 30 if sel else 26, AMARILLO if sel else (170, 160, 200), (cx, y + 175))
            if cl == "experto":
                texto(p, fc, "espadas de energia", GRIS, cx, y + 198, True)
        texto(p, fc, "En multijugador no hay CPU: el escenario solo cambia el decorado (y las espadas)",
              GRIS, C.ANCHO // 2, 400, True)
        texto(p, fc, "A / D  ELEGIR      F  CREAR PARTIDA      G  VOLVER", GRIS, C.ANCHO // 2, 505, True)

    def _dibujar_vs(self, p):
        izq, der = (self.pj, self.remoto) if self.anfitrion else (self.remoto, self.pj)
        for pj, x, d, col, quien in ((izq, 230, 1, ROJO, "P1"), (der, 730, -1, AZUL, "P2")):
            tu = pj is self.pj
            texto(p, self.j.fuente, f"{quien} - {'TU' if tu else self.nombre_remoto}", col, x, 100, True)
            texto_borde(p, pj.nombre, 46, BLANCO, (x, 150))
            poner(p, superficie_personaje(pj, d, 3, "victoria" if tu else "reposo0"), x, 430, d, 3)
        esc = 1 + max(0, (700 - self.t_vs) / 300)
        texto_borde(p, "VS", int(90 * esc), AMARILLO, (C.ANCHO // 2, 270), grosor=4)


# ================================================================ PELEA EN RED
DT = 16.67            # paso fijo (ms). Con 16.67 exacto, dt/16.67 = 1.0 y la fisica da igual en las dos maquinas


class PeleaRed(Pelea):
    """La misma Pelea, pero las teclas de los dos luchadores salen de la red, paso a paso."""
    CADA_CHK = 60     # cada cuantos pasos el anfitrion manda un resumen para comprobar

    def __init__(self, juego, con, soy_anfitrion, pj_local, pj_remoto, dificultad, retardo,
                 pendientes=(), bot=None):
        juego.dificultad = dificultad
        juego.p1, juego.p2 = (pj_local, pj_remoto) if soy_anfitrion else (pj_remoto, pj_local)
        juego.racha = 0
        super().__init__(juego)
        self.con = con
        self.anfitrion = soy_anfitrion
        self.l1.etiqueta, self.l2.etiqueta = "P1", "P2"
        for lu in (self.l1, self.l2):
            lu.controles = red.CTRL_RED
        self.yo_i = 0 if soy_anfitrion else 1
        self.otro_i = 1 - self.yo_i
        self.yo = (self.l1, self.l2)[self.yo_i]
        self.retardo = retardo
        self.f = 0                                    # siguiente paso a simular
        self.bits = [{k: 0 for k in range(retardo)}, {k: 0 for k in range(retardo)}]
        self.flancos = 0                              # golpe/especial/ok pulsados desde el ultimo envio
        self.acum = 0.0
        self.t_espera = 0
        self.listos = [False, False]
        self.mis_chk, self.chk_anfitrion = {}, {}
        self.correcciones = 0
        self.t_aviso_sync = 0
        self.desconectado = ""
        self.bot = CPU(self.yo, 4) if (C.RED_BOT if bot is None else bot) else None
        self.t_bot_ok = 0
        for m in pendientes:
            self._mensaje(m)

    # ------------------------------------------------------------ red
    def salir(self):
        self.con.cerrar()

    def _mensaje(self, m):
        t = m.get("t")
        if t == "in":
            try:
                self.bits[self.otro_i][int(m["f"])] = int(m["b"])
            except (KeyError, TypeError, ValueError):
                pass
        elif t == "chk" and not self.anfitrion:
            f = int(m.get("f", -1))
            self.chk_anfitrion[f] = m.get("s")
            self._comprobar(f)

    def _resumen(self):
        a, b = self.l1, self.l2
        return [round(a.x, 2), a.rect.y, a.vida, round(b.x, 2), b.rect.y, b.vida,
                self.victorias[0], self.victorias[1], self.ronda]

    def _comprobar(self, f):
        """El invitado compara su resumen con el del anfitrion. Si no cuadra, se corrige."""
        h, m = self.chk_anfitrion.get(f), self.mis_chk.get(f)
        if h is None or m is None:
            return
        del self.chk_anfitrion[f], self.mis_chk[f]
        if h == m:
            return
        self.correcciones += 1
        self.t_aviso_sync = 2000
        print(f"[red] paso {f}: las maquinas no coinciden, corrigiendo.  anfitrion={h}  aqui={m}")
        for lu, k in ((self.l1, 0), (self.l2, 3)):    # se aplica la diferencia de entonces a ahora
            lu.x += h[k] - m[k]
            lu.rect.y += h[k + 1] - m[k + 1]
            lu.rect.centerx = int(lu.x)
            lu.vida = max(0, min(lu.vida_max, lu.vida + h[k + 2] - m[k + 2]))
        self.victorias = [h[6], h[7]]

    # ------------------------------------------------------------ entrada local
    def eventos(self, evs):
        for e in evs:
            if e.type != pygame.KEYDOWN:
                continue
            if e.key == pygame.K_ESCAPE:
                self.j.cambiar(Menu(self.j))
                return
            if self.desconectado:
                if e.key in OK:
                    self.j.cambiar(Menu(self.j))
                    return
                continue
            if es_tecla(e.key, CTRL_JUGADOR["golpe"]):
                self.flancos |= red.GOLPE | red.OK
            elif es_tecla(e.key, CTRL_JUGADOR["especial"]):
                self.flancos |= red.ESPECIAL
            elif e.key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_r):
                self.flancos |= red.OK

    def _leer_mando(self):
        """Botones de ESTA maquina para el paso que se va a enviar."""
        if self.bot is not None:
            teclas, acciones = self.bot.actualizar(DT, self)
            b = sum(red.NOMBRES[n] for n in teclas.on if n in red.NOMBRES)
            b |= (red.GOLPE if "golpe" in acciones else 0) | (red.ESPECIAL if "especial" in acciones else 0)
            if self.estado == "fin":                      # el bot acepta la revancha a los 3 s
                self.t_bot_ok += DT
                if self.t_bot_ok > 3000:
                    b |= red.OK
            else:
                self.t_bot_ok = 0
            return b
        k = pygame.key.get_pressed()
        c = CTRL_JUGADOR
        b = ((red.IZQ if pulsada(k, c["izquierda"]) else 0) | (red.DER if pulsada(k, c["derecha"]) else 0) |
             (red.SALTO if pulsada(k, c["salto"]) else 0))
        b |= self.flancos
        self.flancos = 0
        return b

    # ------------------------------------------------------------ bucle
    def actualizar(self, dt):
        for m in self.con.mensajes():
            self._mensaje(m)
        self.t_aviso_sync = max(0, self.t_aviso_sync - dt)
        if self.desconectado:
            Escena.actualizar(self, dt)
            self.fx.actualizar(dt)
            return
        if self.con.cerrada:
            self.desconectado = self.con.motivo or "conexion perdida"
            sonido.play("menu_atras")
            return
        self.con.medir_ping()
        self.acum = min(self.acum + dt, DT * 6)
        pasos = 0
        while self.acum >= DT and pasos < 4:          # si vamos atrasados, ponerse al dia (poco a poco)
            if not self._paso():
                break
            self.acum -= DT
            pasos += 1
        self.t_espera = 0 if pasos else self.t_espera + dt

    def _paso(self):
        """Simula el paso self.f si ya estan los botones de los dos. False = hay que esperar."""
        futuro = self.f + self.retardo
        mios = self.bits[self.yo_i]
        if futuro not in mios:                       # lo que pulso ahora se juega dentro de 'retardo' pasos
            mios[futuro] = self._leer_mando()
            self.con.enviar(t="in", f=futuro, b=mios[futuro])
        if self.f not in self.bits[self.otro_i]:
            return False
        b1 = self.bits[0].pop(self.f)
        b2 = self.bits[1].pop(self.f)
        self._tick(b1, b2)
        self.f += 1
        return True

    def _tick(self, b1, b2):
        """Un paso de la simulacion, IDENTICO en las dos maquinas (mismos botones -> mismo resultado)."""
        if self.estado == "lucha":                   # golpes y especiales: como eventos() del modo arcade
            for lu, b in ((self.l1, b1), (self.l2, b2)):
                if b & red.GOLPE:
                    lu.pedir_golpe()
                if b & red.ESPECIAL:
                    lu.pedir_especial(self)
        elif self.estado == "fin":
            for k, b in enumerate((b1, b2)):
                if b & red.OK and not self.listos[k]:
                    self.listos[k] = True
                    sonido.play("menu_ok", variar=False)
            if all(self.listos):
                self._revancha()
        t1, t2 = red.TeclasRed(b1), red.TeclasRed(b2)
        self._simular(DT, lambda dt: (t1, t2, [], []))
        # redondear: evita que diferencias minusculas de coma flotante entre CPUs distintas crezcan
        for lu in (self.l1, self.l2):
            lu.x, lu.vx, lu.vy = round(lu.x, 3), round(lu.vx, 3), round(lu.vy, 3)
        for atk in self.ataques:
            if isinstance(getattr(atk, "x", None), float):
                atk.x = round(atk.x, 3)
        self.reloj = round(self.reloj, 3)
        if self.f % self.CADA_CHK == 0:
            res = self._resumen()
            if self.anfitrion:
                self.con.enviar(t="chk", f=self.f, s=res)
            else:
                self.mis_chk[self.f] = res
                self._comprobar(self.f)

    def _revancha(self):
        self.listos = [False, False]
        self.victorias = [0, 0]
        self.ronda = 0
        self.fx = Efectos()
        self.ataques = []
        self.nueva_ronda()

    # ------------------------------------------------------------ dibujo
    def _rotulo_superior(self, p):
        ping = self.con.ping_ms
        s = "MULTIJUGADOR" + (f"  -  {ping:.0f} ms" if ping is not None else "")
        if self.bot is not None:
            s += "  -  BOT"
        texto(p, self.j.f_chica, s, (150, 230, 255), C.ANCHO // 2, 8, True)

    def dibujar(self, p):
        super().dibujar(p)
        fc = self.j.f_chica
        x = 48 if self.yo_i == 0 else C.ANCHO - 48             # "TU" bajo tu retrato
        img = fc.render("TU", True, AMARILLO)
        p.blit(img, img.get_rect(midtop=(x, 84)))
        if self.t_aviso_sync > 0:
            texto(p, fc, "resincronizando...", (255, 200, 120), C.ANCHO // 2, 100, True)
        if self.desconectado:
            velo = pygame.Surface((C.ANCHO, C.ALTO), pygame.SRCALPHA)
            velo.fill((0, 0, 0, 170))
            p.blit(velo, (0, 0))
            titulo(p, "DESCONECTADO", 70, (C.ANCHO // 2, 200), (255, 140, 140), (210, 10, 40))
            for k, linea in enumerate(textwrap.wrap(self.desconectado, 50)[:2]):
                texto(p, self.j.fuente, linea, BLANCO, C.ANCHO // 2, 255 + k * 30, True)
            texto_borde(p, "F / ESC: MENU", 34, BLANCO, (C.ANCHO // 2, 330))
        elif self.t_espera > 400:
            texto_borde(p, "ESPERANDO AL OTRO JUGADOR" + "." * (int(self.t_espera / 300) % 4), 34,
                        AMARILLO, (C.ANCHO // 2, 330))
            if self.t_espera > 6000:
                texto(p, fc, "La conexion va muy lenta o se ha cortado.  ESC: salir al menu",
                      BLANCO, C.ANCHO // 2, 360, True)

    def _dibujar_fin(self, p):
        if self.ganador is self.yo:
            titulo(p, "¡HAS GANADO!", 80, (C.ANCHO // 2, 195))
        else:
            titulo(p, "HAS PERDIDO", 80, (C.ANCHO // 2, 195), (255, 140, 140), (210, 10, 40))
        if self.listos[self.yo_i]:
            msg = "ESPERANDO A QUE EL OTRO ACEPTE" + "." * (int(self.t * 2) % 4)
        elif self.listos[self.otro_i]:
            msg = "EL OTRO QUIERE REVANCHA!  F: ACEPTAR"
        else:
            msg = "F: REVANCHA    ESC: MENU"
        texto_borde(p, msg, 34, BLANCO, (C.ANCHO // 2, 265))
