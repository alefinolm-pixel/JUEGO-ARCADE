"""Escenas: Menu -> Seleccion -> Pelea  y  Menu -> Crear luchador (camara + IA + personalizar)."""
import math
import os
import random
import threading

import pygame

import avatar
import escenarios
import config as C
import rasgos
import roster
import sonido
from camera import Camara
from efectos import AMARILLO as AMA_FX, NARANJA, Efectos, texto_borde
from fuente_pixel import titulo
from fighter import CTRL_JUGADOR, CTRL_P2, Luchador, es_tecla, superficie_personaje
from ia_cpu import CPU, NIVEL_MAX
from teclado import Teclado

BLANCO = (255, 255, 255)
AMARILLO = (255, 220, 30)
ROJO = (230, 35, 45)
AZUL = (35, 100, 240)
GRIS = (150, 150, 170)
OSCURO = (15, 12, 45)

ARRIBA = (pygame.K_w, pygame.K_UP)
ABAJO = (pygame.K_s, pygame.K_DOWN)
ACEPTAR = (pygame.K_f, pygame.K_k, pygame.K_RETURN, pygame.K_SPACE)

_publico = [(x, random.randint(0, 2), random.random() * 6.28,
             random.choice([(60, 45, 100), (75, 50, 115), (50, 40, 90)]))
            for x in range(10, C.ANCHO, 26)]


_fondo_fijo = None


def dibujar_fondo(p, t=0.0, publico=True):
    global _fondo_fijo
    if _fondo_fijo is None:                                   # parte estatica: se dibuja 1 vez
        _fondo_fijo = pygame.Surface((C.ANCHO, C.ALTO))
        _fondo_fijo.fill(OSCURO)
        for i in range(0, C.ANCHO, 80):
            pygame.draw.rect(_fondo_fijo, (35, 25, 75), (i, 150, 40, 230))
    p.blit(_fondo_fijo, (0, 0))
    for i in range(0, C.ANCHO, 160):                          # focos
        a = math.sin(t * 0.8 + i) * 0.25
        pygame.draw.polygon(p, (30, 24, 70), [(i + 80, 0), (i + 40 + int(200 * a), C.SUELO),
                                              (i + 120 + int(200 * a), C.SUELO)])
    if publico:
        for x, fila, fase, col in _publico:                   # publico que bota
            y = 360 + fila * 12 - abs(int(6 * math.sin(t * 6 + fase)))
            pygame.draw.circle(p, col, (x + fila * 8, y), 10)
            pygame.draw.rect(p, col, (x + fila * 8 - 12, y + 8, 24, 40))
    pygame.draw.rect(p, (90, 65, 105), (0, C.SUELO, C.ANCHO, C.ALTO - C.SUELO))
    pygame.draw.line(p, (240, 120, 220), (0, C.SUELO), (C.ANCHO, C.SUELO), 4)
    for i in range(0, C.ANCHO, 60):
        pygame.draw.line(p, (120, 90, 140), (i, C.SUELO), (i - 40, C.ALTO), 2)


DIFICULTADES = {
    "normal":  dict(nombre="NORMAL",  nivel=1, color=(90, 230, 130), estrellas=1),
    "dificil": dict(nombre="DIFICIL", nivel=3, color=(255, 170, 40), estrellas=2),
    "experto": dict(nombre="EXPERTO", nivel=5, color=(255, 60, 90), estrellas=3),
}
ORDEN_DIF = ["normal", "dificil", "experto"]


def poner(p, img, cuerpo_x, suelo_y, direccion, escala):
    """Coloca un luchador con el CENTRO DEL CUERPO en cuerpo_x y los pies en suelo_y."""
    x = cuerpo_x - (avatar.CX * escala if direccion == 1 else (avatar.W - avatar.CX) * escala)
    p.blit(img, (x, suelo_y - avatar.FY * escala))


def texto(p, fuente, s, color, x, y, centro=False):
    img = fuente.render(s, True, color)
    r = img.get_rect()
    if centro:
        r.midtop = (x, y)
    else:
        r.topleft = (x, y)
    p.blit(img, r)


def barra_stat(p, fuente, etiqueta, valor, x, y, ancho=150, color=AMARILLO):
    texto(p, fuente, etiqueta, GRIS, x, y)
    bx = x + 110
    pygame.draw.rect(p, (40, 30, 70), (bx, y + 4, ancho, 12))
    pygame.draw.rect(p, color, (bx, y + 4, int(ancho * max(0.08, min(1, valor))), 12))
    pygame.draw.rect(p, BLANCO, (bx, y + 4, ancho, 12), 1)


def stats_normalizados(pj):
    st = pj.stats
    return [("VIDA", (st["vida"] - 75) / 50), ("VELOCIDAD", (st["velocidad"] - 3.5) / 3.2),
            ("FUERZA", (st["golpe"] - 4.5) / 5), ("ESPECIAL", (pj.dano - 8) / 8)]


class Escena:
    def __init__(self, juego):
        self.j = juego
        self.t = 0.0

    def eventos(self, evs): pass
    def actualizar(self, dt): self.t += dt / 1000
    def dibujar(self, p): pass
    def salir(self): pass


# ---------------------------------------------------------------- MENU
class Menu(Escena):
    OPCIONES = ["JUGAR", "MULTIJUGADOR", "CREAR LUCHADOR", "SALIR"]

    def __init__(self, juego):
        super().__init__(juego)
        self.i = 0
        sonido.musica("menu")

    def eventos(self, evs):
        for e in evs:
            if e.type != pygame.KEYDOWN:
                continue
            if e.key in ARRIBA:
                self.i = (self.i - 1) % len(self.OPCIONES)
                sonido.play("menu_mover", variar=False)
            elif e.key in ABAJO:
                self.i = (self.i + 1) % len(self.OPCIONES)
                sonido.play("menu_mover", variar=False)
            elif e.key in ACEPTAR:
                sonido.play("menu_ok", variar=False)
                op = self.OPCIONES[self.i]
                if op == "JUGAR":
                    self.j.cambiar(Dificultad(self.j))
                elif op == "MULTIJUGADOR":
                    from escena_red import Multijugador      # import aqui: evita import circular
                    self.j.cambiar(Multijugador(self.j))
                elif op == "CREAR LUCHADOR":
                    self.j.cambiar(Crear(self.j))
                else:
                    self.j.salir()

    def dibujar(self, p):
        dibujar_fondo(p, self.t)
        titulo(p, "PIXEL FIGHTERS", 100, (C.ANCHO // 2, 92 + int(4 * math.sin(self.t * 3))))
        ros = self.j.roster
        for k, (x, d) in enumerate(((150, 1), (810, -1))):
            if len(ros) > k:
                pose = "reposo0" if int(self.t * 2 + k) % 2 else "reposo1"
                img = superficie_personaje(ros[(k * 2) % len(ros)], d, 3, pose)
                poner(p, img, x, C.SUELO + 8, d, 3)
        for k, op in enumerate(self.OPCIONES):
            sel = k == self.i
            col = AMARILLO if sel else BLANCO
            s = ("> " + op + " <") if sel else op
            texto_borde(p, s, 54 if sel else 46, col, (C.ANCHO // 2, 205 + k * 64))
        texto(p, self.j.f_chica, "W/S O FLECHAS PARA MOVER  -  F / K PARA ACEPTAR", GRIS, C.ANCHO // 2, 492, True)
        if not C.ENV_ENCONTRADO:
            texto(p, self.j.f_chica, "AVISO: falta el archivo .env en la carpeta del juego (camara 0 y sin IA)",
                  (255, 120, 120), C.ANCHO // 2, 522, True)


# ---------------------------------------------------------------- SELECCION
class Dificultad(Escena):
    """NORMAL / DIFICIL / EXPERTO. Cada una tiene su escenario, que se ve de fondo."""

    def __init__(self, juego, luchador=None):
        super().__init__(juego)
        self.luchador = luchador                  # si viene de crear, ya esta elegido
        self.i = ORDEN_DIF.index(getattr(juego, "dificultad", "normal"))
        self.escenarios = {k: escenarios.crear(k) for k in ORDEN_DIF}
        self.minis = {k: e.miniatura(240, 135) for k, e in self.escenarios.items()}
        sonido.musica("menu")

    def eventos(self, evs):
        for e in evs:
            if e.type != pygame.KEYDOWN:
                continue
            if e.key == pygame.K_ESCAPE:
                sonido.play("menu_atras")
                self.j.cambiar(Menu(self.j))
                return
            if e.key in (pygame.K_a, pygame.K_LEFT, pygame.K_w, pygame.K_UP):
                self.i = (self.i - 1) % 3
                sonido.play("menu_mover", variar=False)
            elif e.key in (pygame.K_d, pygame.K_RIGHT, pygame.K_s, pygame.K_DOWN):
                self.i = (self.i + 1) % 3
                sonido.play("menu_mover", variar=False)
            elif e.key in ACEPTAR:
                sonido.play("menu_ok", variar=False)
                self.j.dificultad = ORDEN_DIF[self.i]
                self.j.cambiar(Seleccion(self.j, luchador=self.luchador))
                return

    def dibujar(self, p):
        clave = ORDEN_DIF[self.i]
        self.escenarios[clave].dibujar(p, 16)                    # el escenario elegido, en vivo
        velo = pygame.Surface((C.ANCHO, C.ALTO), pygame.SRCALPHA)
        velo.fill((10, 5, 25, 150))
        p.blit(velo, (0, 0))
        titulo(p, "ELIGE DIFICULTAD", 60, (C.ANCHO // 2, 45))
        for k, cl in enumerate(ORDEN_DIF):
            d = DIFICULTADES[cl]
            esc = self.escenarios[cl]
            sel = k == self.i
            cx = 170 + k * 310
            y = 110 + (0 if sel else 12)
            marco = pygame.Rect(cx - 130, y, 260, 300)
            pygame.draw.rect(p, (20, 14, 40), marco, border_radius=10)
            pygame.draw.rect(p, d["color"] if sel else (90, 80, 120), marco, 4 if sel else 2, border_radius=10)
            p.blit(self.minis[cl], (cx - 120, y + 10))
            pygame.draw.rect(p, (0, 0, 0), (cx - 120, y + 10, 240, 135), 2)
            if sel:
                titulo(p, d["nombre"], 44, (cx, y + 175), arriba=tuple(min(255, c + 80) for c in d["color"]),
                       abajo=d["color"])
            else:
                texto_borde(p, d["nombre"], 38, (170, 160, 200), (cx, y + 175))
            texto(p, self.j.f_chica, esc.nombre, BLANCO, cx, y + 205, True)
            texto(p, self.j.f_chica, esc.descripcion.upper(), GRIS, cx, y + 228, True)
            for s_ in range(3):                                   # estrellas de dificultad
                col = d["color"] if s_ < d["estrellas"] else (60, 50, 80)
                from efectos import dibujar_estrella
                dibujar_estrella(p, col, cx - 30 + s_ * 30, y + 268, 11)
        texto(p, self.j.f_chica, "A / D  ELEGIR      F  ACEPTAR      ESC  MENU", GRIS, C.ANCHO // 2, 510, True)


class Seleccion(Escena):
    """El jugador elige su luchador; el rival lo sortea la maquina (ruleta)."""
    IZQ = (pygame.K_a, pygame.K_LEFT)
    DER = (pygame.K_d, pygame.K_RIGHT)
    OK = (pygame.K_f, pygame.K_k, pygame.K_RETURN, pygame.K_SPACE)
    ATRAS = (pygame.K_g, pygame.K_l)

    def __init__(self, juego, luchador=None):
        super().__init__(juego)
        n = len(self.j.roster)
        self.idx = n - 1 if n > 3 else 0          # empieza en el ultimo creado
        self.listo = False
        if luchador is not None:                  # viene de crear: ya elegido, directo a la ruleta
            ids = [p.id for p in self.j.roster]
            if luchador.id in ids:
                self.idx = ids.index(luchador.id)
                self.listo = True
        self.t_ruleta = 0
        self.rival_idx = 0
        sonido.musica("menu")

    def eventos(self, evs):
        n = len(self.j.roster)
        for e in evs:
            if e.type != pygame.KEYDOWN:
                continue
            if e.key == pygame.K_ESCAPE:
                sonido.play("menu_atras")
                self.j.cambiar(Dificultad(self.j))
                return
            if self.listo:
                continue
            if e.key in self.IZQ + self.DER:
                self.idx = (self.idx + (1 if e.key in self.DER else -1)) % n
                sonido.play("menu_mover", variar=False)
            elif e.key in self.OK:
                self.listo = True
                self.t_ruleta = 0
                sonido.play("menu_ok", variar=False)

    def actualizar(self, dt):
        super().actualizar(dt)
        if not self.listo:
            return
        n = len(self.j.roster)
        antes = self.t_ruleta
        self.t_ruleta += dt
        if self.t_ruleta < 1300:                    # ruleta del rival
            if int(self.t_ruleta / 90) != int(antes / 90):
                self.rival_idx = random.randrange(n)
                sonido.play("menu_mover", 0.6, variar=False)
        elif antes < 1300:
            self.rival_idx = elegir_rival(self.j.roster, self.idx)
            sonido.play("lucha", variar=False)
        elif self.t_ruleta > 2300:
            self.j.p1 = self.j.roster[self.idx]
            self.j.p2 = self.j.roster[self.rival_idx]
            self.j.racha = 0
            self.j.cambiar(Pelea(self.j))

    def dibujar(self, p):
        dibujar_fondo(p, self.t, publico=False)
        titulo(p, "ELIGE TU LUCHADOR", 56, (C.ANCHO // 2, 35))
        d = DIFICULTADES[self.j.dificultad]
        texto(p, self.j.f_chica, f"DIFICULTAD: {d['nombre']}", d["color"], C.ANCHO // 2, 505, True)
        f = self.j.fuente
        pj = self.j.roster[self.idx]
        cx = 300
        texto(p, f, "TU", ROJO, cx, 68, True)
        texto_borde(p, pj.nombre, 46, BLANCO, (cx, 112))
        texto(p, f, f"< {self.idx + 1}/{len(self.j.roster)} >", GRIS, cx, 132, True)
        pose = "victoria" if self.listo else ("reposo0" if int(self.t * 2) % 2 else "reposo1")
        img = superficie_personaje(pj, 1, 3, pose)
        poner(p, img, cx, 400, 1, 3)
        info = f"{avatar.STATS[pj.cuerpo]['nombre']} - {pj.traje.upper()} - {pj.especial}"
        texto(p, f, info, pj.color if sum(pj.color) > 200 else BLANCO, cx, 395, True)
        for j, (nom, v) in enumerate(stats_normalizados(pj)):
            barra_stat(p, self.j.f_chica, nom, v, cx - 135, 425 + j * 17, 160, ROJO)

        # rival
        rx = 720
        texto(p, f, "RIVAL (CPU)", AZUL, rx, 68, True)
        if not self.listo:
            texto_borde(p, "?", 160, (90, 80, 140), (rx, 260))
            texto(p, self.j.f_chica, "A / D  ELEGIR      F  ACEPTAR      ESC  VOLVER", GRIS, C.ANCHO // 2, 480, True)
            return
        rv = self.j.roster[self.rival_idx]
        fijo = self.t_ruleta >= 1300
        texto_borde(p, rv.nombre if fijo else "???", 46, BLANCO, (rx, 112))
        img = superficie_personaje(rv, -1, 3, "reposo0")
        if not fijo:
            img = img.copy()
            img.fill((60, 60, 90, 0), special_flags=pygame.BLEND_RGB_ADD)
        poner(p, img, rx, 400, -1, 3)
        if fijo:
            texto(p, f, f"{avatar.STATS[rv.cuerpo]['nombre']} - {rv.especial}", BLANCO, rx, 395, True)
            esc = 1 + max(0, (1700 - self.t_ruleta) / 400)
            texto_borde(p, "VS", int(90 * esc), AMARILLO, (C.ANCHO // 2, 250), grosor=4)


def elegir_rival(roster_, idx_jugador):
    """Rival al azar distinto del jugador (si hay mas de uno)."""
    opciones = [i for i in range(len(roster_)) if i != idx_jugador] or [idx_jugador]
    return random.choice(opciones)


# ---------------------------------------------------------------- PELEA
class Pelea(Escena):
    RONDAS_GANAR = 2
    TIEMPO = 60_000

    def __init__(self, juego):
        super().__init__(juego)
        self.fx = Efectos()
        self.ancho = C.ANCHO
        dif = DIFICULTADES[juego.dificultad]
        base = dif["nivel"]                                   # cada victoria seguida, rival mas dificil
        self.nivel = min(NIVEL_MAX, base + min(juego.racha, 1))
        self.escenario = escenarios.crear(juego.dificultad)
        self.tema = "espacio" if juego.dificultad == "experto" else None
        self.l1 = Luchador(240, juego.p1, 1, CTRL_JUGADOR, "P1", self.tema, (80, 200, 255))
        self.l2 = Luchador(720, juego.p2, -1, CTRL_P2, "CPU", self.tema, (255, 50, 50))
        self.cpu = CPU(self.l2, self.nivel)
        self.l1.rival, self.l2.rival = self.l2, self.l1
        for lu in (self.l1, self.l2):            # pre-dibuja todas las poses: sin tirones luego
            for pose in avatar.POSES:
                for d in (1, -1):
                    lu.av.frame(pose, d)
        self.victorias = [0, 0]
        self.ronda = 0
        self.reloj = 0
        sonido.musica(self.escenario.musica)
        self.nueva_ronda()

    def nueva_ronda(self):
        self.ronda += 1
        self.l1.reiniciar()
        self.l2.reiniciar()
        self.ataques = []
        self.combo = {self.l1: 0, self.l2: 0}
        self.estado = "intro"
        self.t_estado = 0
        self.tiempo = self.TIEMPO
        self.ganador_ronda = None
        self.ganador = None
        self.msg_fin = ""
        sonido.play("cuenta", variar=False)

    # ------------------------------------------------------------------ entrada
    def eventos(self, evs):
        for e in evs:
            if e.type != pygame.KEYDOWN:
                continue
            if e.key == pygame.K_ESCAPE:
                self.j.cambiar(Menu(self.j))
                return
            if self.estado == "fin":
                if e.key in (pygame.K_r, pygame.K_RETURN, pygame.K_f, pygame.K_k):
                    if self.ganador is self.l1:          # siguiente rival, mas dificil
                        idx = self.j.roster.index(self.j.p1) if self.j.p1 in self.j.roster else -1
                        self.j.p2 = self.j.roster[elegir_rival(self.j.roster, idx)]
                    self.j.cambiar(Pelea(self.j))
                continue
            if self.estado != "lucha":
                continue
            yo = self.l1                                  # solo el jugador usa el teclado/joystick
            if es_tecla(e.key, yo.controles["golpe"]):
                yo.pedir_golpe()
            elif es_tecla(e.key, yo.controles["especial"]):
                yo.pedir_especial(self)

    # ------------------------------------------------------------------ impactos
    def impactar(self, a, d, dano, x, y, empuje, fuerza=1.0, color=AMA_FX):
        """Unico sitio donde se hace dano: bloqueo, combo, efectos, sonido, K.O."""
        if d.ko or self.estado != "lucha":
            return None
        if d.bloqueando() and d.direccion == -a.direccion:
            chip = max(1, round(dano * 0.2))
            d.vida = max(1, d.vida - chip)                     # bloquear nunca te deja K.O.
            d.vx = a.direccion * empuje * 0.7
            self.fx.bloqueo(x, y, a.direccion)
            self.fx.congelar(45)
            self.fx.texto(x, y - 35, "BLOQUEO", (140, 210, 255), 30, 500)
            sonido.play("espada_choque" if self.tema == "espacio" else "bloqueo")
            return "bloqueo"

        self.combo[a] = self.combo[a] + 1 if d.t_golpeado > 0 else 1
        d.recibir(dano, empuje, a.direccion, int(230 + 90 * fuerza))
        if fuerza >= 1.5:                                      # golpe fuerte: lo levanta
            d.vy = -6
            d.en_suelo = False
        self.fx.chispa(x, y, a.direccion, color, fuerza)
        self.fx.texto(x, y - 40, str(dano), NARANJA if fuerza >= 1.4 else AMA_FX, int(30 + 10 * fuerza))
        self.fx.congelar(int(40 + 45 * fuerza))
        self.fx.temblor(int(2 + 4 * fuerza), int(100 + 100 * fuerza))
        if self.tema == "espacio" and fuerza < 1.4:
            sonido.play("espada_golpe")
        else:
            sonido.play("golpe_fuerte" if fuerza >= 1.4 else "golpe")
        if self.combo[a] >= 2:
            cx = 210 if a is self.l1 else C.ANCHO - 210
            self.fx.texto(cx, 175, f"{self.combo[a]} GOLPES!", AMARILLO, 44, 900, -0.3)

        if d.ko:
            self._ko(a, d, "K.O.!")
        return "golpe"

    def _ko(self, a, d, letrero):
        self.estado = "ko"
        self.t_estado = 0
        self.ganador_ronda = a
        self.msg_fin = letrero
        self.victorias[0 if a is self.l1 else 1] += 1
        if d.ko:
            d.vy, d.vx, d.en_suelo = -10, 9 * a.direccion, False
        self.fx.camara_lenta = 1500
        self.fx.flash((255, 255, 255), 220)
        self.fx.congelar(220)
        self.fx.temblor(10, 400)
        sonido.play("ko", variar=False)

    # ------------------------------------------------------------------ bucle
    def actualizar(self, dt):
        self._simular(dt, self._entradas_locales)

    def _entradas_locales(self, dt):
        """Modo arcade: el jugador con el teclado/joystick, el rival lo mueve la CPU.
        (los golpes del jugador llegan por eventos(); los de la CPU, por aqui)"""
        teclas_cpu, acciones = self.cpu.actualizar(dt, self)
        return pygame.key.get_pressed(), teclas_cpu, [], acciones

    def _simular(self, dt, entradas):
        """Un paso de la pelea. entradas(dt) -> (teclas_l1, teclas_l2, acciones_l1, acciones_l2).
        Lo usa tambien el modo multijugador (escena_red.py) con las teclas que llegan por la red."""
        Escena.actualizar(self, dt)
        self.fx.actualizar(dt)
        if self.fx.hitstop > 0:                    # congelado tras golpe: da "peso"
            self.fx.hitstop -= dt
            return
        dtj = dt * 0.3 if self.fx.camara_lenta > 0 else dt
        self.reloj += dtj
        self.t_estado += dt

        if self.estado == "intro":
            if self.t_estado >= 1200 and self.t_estado - dt < 1200:
                sonido.play("lucha", variar=False)
            if self.t_estado >= 1900:
                self.estado = "lucha"
        elif self.estado == "lucha":
            self.tiempo -= dt
            if self.tiempo <= 0:
                self.tiempo = 0
                r1 = self.l1.vida / self.l1.vida_max
                r2 = self.l2.vida / self.l2.vida_max
                ganador, perdedor = (self.l1, self.l2) if r1 >= r2 else (self.l2, self.l1)
                self._ko(ganador, perdedor, "TIEMPO!")
        elif self.estado == "ko":
            if self.t_estado > 1700 and self.ganador_ronda and not self.ganador_ronda.ganador:
                self.ganador_ronda.ganador = True
                sonido.play("victoria", variar=False)
            if self.t_estado > 3300:
                if max(self.victorias) >= self.RONDAS_GANAR:
                    self.estado = "fin"
                    self.ganador = self.ganador_ronda
                    self.j.racha = self.j.racha + 1 if self.ganador is self.l1 else 0
                else:
                    self.nueva_ronda()
                    return

        activo = self.estado == "lucha"
        t1, t2, acc1, acc2 = entradas(dt)
        teclas = {self.l1: t1, self.l2: t2}
        for yo in (self.l1, self.l2):
            if activo and yo.en_suelo and not yo.ocupado():   # mirar siempre al rival
                yo.direccion = 1 if yo.rival.rect.centerx > yo.rect.centerx else -1
            yo.entrada(teclas[yo], activo)
        if activo:
            for lu, acciones in ((self.l1, acc1), (self.l2, acc2)):
                for acc in acciones:
                    if acc == "golpe":
                        lu.pedir_golpe()
                    else:
                        lu.pedir_especial(self)
        for yo in (self.l1, self.l2):
            yo.actualizar(dtj, self)
        for atk in self.ataques:
            atk.actualizar(dtj)
        self.ataques = [a for a in self.ataques if a.vivo]
        self._separar()

    def _separar(self):
        a, b = self.l1, self.l2
        if a.ko or b.ko or not (a.en_suelo and b.en_suelo):
            return
        if a.rect.colliderect(b.rect):
            solape = (a.rect.width + b.rect.width) / 2 - abs(a.rect.centerx - b.rect.centerx)
            s = 1 if a.rect.centerx <= b.rect.centerx else -1
            a.x -= s * solape / 2
            b.x += s * solape / 2
            for l in (a, b):
                l.x = max(l.rect.width / 2, min(C.ANCHO - l.rect.width / 2, l.x))
                l.rect.centerx = int(l.x)

    # ------------------------------------------------------------------ HUD
    def _barra(self, p, lu, izquierda):
        ancho, alto, y = 330, 24, 48
        x = 92 if izquierda else C.ANCHO - 92 - ancho
        cab = avatar.cabeza(lu.av, 2)
        if cab.get_height() > 64:                         # con casco: reducir para que quepa
            cab = pygame.transform.scale(cab, (cab.get_width() * 64 // cab.get_height(), 64))
        cx = 14 if izquierda else C.ANCHO - 14 - 68
        pygame.draw.rect(p, (40, 30, 70), (cx - 2, 12, 72, 68))
        if not izquierda:
            cab = pygame.transform.flip(cab, True, False)
        p.blit(cab, cab.get_rect(center=(cx + 34, 46)))
        pygame.draw.rect(p, BLANCO, (cx - 2, 12, 72, 68), 2)

        f = lu.vida / lu.vida_max
        fv = lu.vida_visual / lu.vida_max
        col = (60, 220, 90) if f > 0.5 else (240, 200, 40) if f > 0.25 else (235, 50, 50)
        pygame.draw.rect(p, (70, 20, 30), (x, y, ancho, alto))
        for frac, c in ((fv, (255, 255, 255)), (f, col)):
            w = int(ancho * frac)
            pygame.draw.rect(p, c, (x + ancho - w, y, w, alto) if izquierda else (x, y, w, alto))
        pygame.draw.rect(p, (255, 255, 255, 60), (x, y + 3, ancho, 4))
        pygame.draw.rect(p, BLANCO, (x, y, ancho, alto), 2)
        nx = x if izquierda else x + ancho
        img = self.j.fuente.render(lu.personaje.nombre, True, BLANCO)
        p.blit(img, img.get_rect(bottomleft=(x, y - 4)) if izquierda else img.get_rect(bottomright=(nx, y - 4)))

        # carga del especial
        carga = lu.carga_especial(self.reloj)
        ey = y + alto + 6
        pygame.draw.rect(p, (30, 25, 60), (x, ey, ancho, 8))
        w = int(ancho * carga)
        llena = carga >= 1
        cesp = lu.personaje.color if not llena or int(self.t * 8) % 2 else BLANCO
        pygame.draw.rect(p, cesp, (x + ancho - w, ey, w, 8) if izquierda else (x, ey, w, 8))
        pygame.draw.rect(p, GRIS, (x, ey, ancho, 8), 1)
        if llena:
            t = self.j.f_chica.render("ESPECIAL!", True, AMARILLO)
            p.blit(t, t.get_rect(topright=(x + ancho, ey + 10)) if izquierda else t.get_rect(topleft=(x, ey + 10)))

        # rondas ganadas
        v = self.victorias[0 if izquierda else 1]
        for k in range(self.RONDAS_GANAR):
            rx = x + 12 + k * 22 if izquierda else x + ancho - 12 - k * 22
            pygame.draw.circle(p, AMARILLO if k < v else (50, 40, 80), (rx, ey + 22), 7)
            pygame.draw.circle(p, BLANCO, (rx, ey + 22), 7, 1)

    def dibujar(self, p):
        off = self.fx.desplazamiento()
        self.escenario.dibujar(p, 0 if self.fx.hitstop > 0 else 16)
        for lu in sorted((self.l1, self.l2), key=lambda l: l.atacando()):   # el que ataca, delante
            lu.dibujar(p, off)
        for atk in self.ataques:
            atk.dibujar(p, off)
        self.fx.dibujar(p, off)

        self._barra(p, self.l1, True)
        self._barra(p, self.l2, False)
        segs = math.ceil(self.tiempo / 1000)
        if segs <= 10:
            titulo(p, f"{segs:02d}", 54, (C.ANCHO // 2, 58), (255, 160, 160), (220, 20, 40))
        else:
            titulo(p, f"{segs:02d}", 54, (C.ANCHO // 2, 58), (255, 255, 255), (170, 190, 255))
        banda = pygame.Surface((C.ANCHO, 22), pygame.SRCALPHA)
        banda.fill((0, 0, 0, 150))
        p.blit(banda, (0, C.ALTO - 24))
        texto(p, self.j.f_chica, "Joystick: mover / arriba saltar / atras bloquear    F golpe    G especial",
              (210, 210, 230), C.ANCHO // 2, 520, True)
        self._rotulo_superior(p)

        if self.estado == "intro":
            if self.t_estado < 1200:
                titulo(p, f"RONDA {self.ronda}", 80, (C.ANCHO // 2, 220), (255, 255, 255), (160, 180, 255))
            else:
                esc = 1 + max(0, (1500 - self.t_estado) / 600)
                titulo(p, "¡A LUCHAR!", int(96 * esc), (C.ANCHO // 2, 220))
        elif self.estado == "ko":
            esc = 1 + max(0, (400 - self.t_estado) / 200)
            titulo(p, self.msg_fin, int(120 * esc), (C.ANCHO // 2, 210), (255, 140, 140), (210, 10, 40))
        elif self.estado == "fin":
            self._dibujar_fin(p)

    def _rotulo_superior(self, p):
        d = DIFICULTADES[self.j.dificultad]
        texto(p, self.j.f_chica, d["nombre"] + (f"  -  RACHA {self.j.racha}" if self.j.racha else ""),
              d["color"], C.ANCHO // 2, 8, True)

    def _dibujar_fin(self, p):
        if self.ganador is self.l1:
            titulo(p, "¡HAS GANADO!", 80, (C.ANCHO // 2, 195))
            texto_borde(p, f"RACHA: {self.j.racha}", 40, BLANCO, (C.ANCHO // 2, 250))
            texto_borde(p, "F: SIGUIENTE RIVAL    ESC: MENU", 34, BLANCO, (C.ANCHO // 2, 295))
        else:
            titulo(p, "HAS PERDIDO", 80, (C.ANCHO // 2, 195), (255, 140, 140), (210, 10, 40))
            texto_borde(p, "F: REVANCHA    ESC: MENU", 34, BLANCO, (C.ANCHO // 2, 265))


# ---------------------------------------------------------------- CREAR LUCHADOR
TRADUCE = {"normales": "gafas", "sol": "gafas de sol"}


def resumen_rasgos(r):
    partes = []
    if r["gafas"] != "no":
        partes.append(TRADUCE[r["gafas"]])
    partes.append({"calvo": "calvo", "rapado": "pelo rapado"}.get(r["pelo_largo"], f"pelo {r['pelo_largo']}"))
    if r["pelo_tipo"] != "liso":
        partes.append(r["pelo_tipo"])
    if r["peinado"] != "suelto":
        partes.append(r["peinado"])
    if r["barba"] != "no":
        partes.append(r["barba"] if r["barba"] in ("bigote", "perilla") else "barba")
    if r["accesorio"] != "ninguno":
        partes.append(r["accesorio"])
    return " - ".join(partes)


class Crear(Escena):
    """conectando -> preview -> cuenta -> analizando -> personalizar -> listo"""
    FILAS = ("CUERPO", "TRAJE")

    def __init__(self, juego):
        super().__init__(juego)
        self.camara = juego.camara_compartida()
        self.estado = "preview" if juego.camara_estado == "ok" else "conectando"
        self.caras, self.nuevos, self.errores, self.fuentes = [], [], [], []
        self.superficie = None
        self.n_frame = 0
        self.t_cuenta = 0
        self.msg = ""
        self.progreso = ""
        self.flash = 0
        self.fila = [0, 0]
        self.ok = [False, False]
        self.fase = ["opciones", "opciones"]   # opciones (cuerpo/traje) -> nombre (teclado)
        self.teclados = [None, None]
        self.guardados = False
        sonido.musica(None)

    def salir(self):
        # la camara NO se cierra: se queda abierta para la siguiente foto
        if self.guardados:
            self.j.recargar_roster()

    # ------------------------------------------------------------------ entrada
    def eventos(self, evs):
        for e in evs:
            if e.type != pygame.KEYDOWN:
                continue
            if e.key == pygame.K_ESCAPE and self.estado != "analizando":
                sonido.play("menu_atras")
                self.j.cambiar(Menu(self.j))
                return
            if self.estado == "personalizar":
                self._personalizar(e.key)
            elif e.key in ACEPTAR:
                if self.estado == "preview" and self.camara.abierta():
                    if self.caras:
                        self.estado, self.t_cuenta, self.msg = "cuenta", 3000, ""
                        sonido.play("cuenta", variar=False)
                    else:
                        self.msg = "No veo ninguna cara: acercate a la camara"
                elif self.estado == "listo":             # F: a luchar con el nuevo luchador
                    sonido.play("menu_ok", variar=False)
                    self.j.recargar_roster()
                    self.guardados = False
                    self.j.cambiar(Dificultad(self.j, luchador=self.nuevos[0]))
                    return
            elif e.key in (pygame.K_g, pygame.K_l) and self.estado == "listo":   # G: crear otro
                sonido.play("menu_ok", variar=False)
                self.j.cambiar(Crear(self.j))
                return

    def _personalizar(self, tecla):
        n = len(self.nuevos)
        p1 = (pygame.K_w, pygame.K_s, pygame.K_a, pygame.K_d, pygame.K_f, pygame.K_g)
        p2 = (pygame.K_UP, pygame.K_DOWN, pygame.K_LEFT, pygame.K_RIGHT, pygame.K_k, pygame.K_l)
        mandos = [(0, p1), (1 if n > 1 else 0, p2)]
        for k, (arr, aba, izq, der, ok, atras) in mandos:
            if self.ok[k] or tecla not in (arr, aba, izq, der, ok, atras):
                continue
            pj = self.nuevos[k]
            if self.fase[k] == "nombre":                     # ---- teclado en pantalla
                tec = self.teclados[k]
                if tecla in (arr, aba, izq, der):
                    tec.mover((tecla == der) - (tecla == izq), (tecla == aba) - (tecla == arr))
                    sonido.play("menu_mover", variar=False)
                elif tecla == ok:
                    r = tec.pulsar()
                    if r == "ok":
                        pj.nombre = " ".join(tec.texto.split()) or pj.nombre
                        self.ok[k] = True
                        sonido.play("menu_ok", variar=False)
                    else:
                        sonido.play("menu_atras" if r == "lleno" else "golpe", 0.4, variar=False)
                elif tecla == atras:
                    if tec.borrar():
                        sonido.play("menu_atras", variar=False)
                    else:                                    # vacio: volver a cuerpo/traje
                        self.fase[k] = "opciones"
                        sonido.play("menu_atras", variar=False)
                continue
            if tecla in (arr, aba):                          # ---- cuerpo / traje
                self.fila[k] = (self.fila[k] + (1 if tecla == aba else -1)) % len(self.FILAS)
                sonido.play("menu_mover", variar=False)
            elif tecla in (izq, der):
                paso = 1 if tecla == der else -1
                if self.FILAS[self.fila[k]] == "CUERPO":
                    ops = list(avatar.CUERPOS)
                    pj.cambiar(cuerpo=ops[(ops.index(pj.cuerpo) + paso) % len(ops)])
                else:
                    ops = avatar.TRAJES
                    pj.cambiar(traje=ops[(ops.index(pj.traje) + paso) % len(ops)])
                    pj.especial = roster.especial_para(pj)
                sonido.play("menu_mover", variar=False)
            elif tecla == ok:                                # siguiente paso: escribir el nombre
                self.fase[k] = "nombre"
                if self.teclados[k] is None:
                    self.teclados[k] = Teclado()
                sonido.play("menu_ok", variar=False)
        if all(self.ok[:n]):
            for pj in self.nuevos:
                roster.guardar(pj)
            self.guardados = True
            sonido.play("creado", variar=False)
            self.estado = "listo"

    # ------------------------------------------------------------------ bucle
    def actualizar(self, dt):
        super().actualizar(dt)
        self.flash = max(0, self.flash - dt)
        if self.estado == "conectando":
            if self.j.camara_estado == "ok":
                self.estado = "preview"
            elif self.j.camara_estado == "error":
                self.msg = "No hay camara. ESC: volver"
                self.estado = "error"
        if self.estado in ("preview", "cuenta") and self.camara.abierta():
            frame = self.camara.leer()
            if frame is not None:
                self.superficie = self.camara.a_surface(frame)
                self.n_frame += 1
                if self.n_frame % 4 == 0:      # detectar no en todos los frames (Raspberry Pi)
                    self.caras = self.camara.detectar_caras(frame)
        if self.estado == "cuenta":
            antes = math.ceil(self.t_cuenta / 1000)
            self.t_cuenta -= dt
            if 0 < math.ceil(self.t_cuenta / 1000) < antes:
                sonido.play("cuenta", variar=False)
            if self.t_cuenta <= 0:
                self._disparar()

    def _disparar(self):
        frame = self.camara.frame
        caras = self.camara.detectar_caras(frame, escala=1.0)
        if not caras:
            self.estado, self.msg = "preview", "No he podido ver ninguna cara, repite"
            return
        sonido.play("foto", variar=False)
        self.flash = 250
        caras = [max(caras, key=lambda c: c[2] * c[3])]   # solo un jugador: la cara mas cercana
        rutas = []
        for i, cara in enumerate(caras):
            ruta = C.TMP_DIR / f"cara_{i}.jpg"
            self.camara.guardar_recorte(frame, cara, ruta)
            rutas.append(ruta)
        self.estado = "analizando"
        threading.Thread(target=self._trabajo, args=(rutas,), daemon=True).start()

    def _trabajo(self, rutas):
        """Hilo en segundo plano: la API tarda unos segundos y no debe congelar el juego."""
        base_n = len(list(C.CHAR_DIR.glob("*/meta.json")))
        for i, ruta in enumerate(rutas):
            self.progreso = f"Analizando la cara {i + 1} de {len(rutas)}..."
            ra, fuente, errs = rasgos.analizar(ruta)
            self.errores += errs
            self.fuentes.append(fuente)
            self.nuevos.append(roster.nuevo(ra, f"JUGADOR {base_n + i + 1}"))
            try:
                os.remove(ruta)          # privacidad: no guardamos las fotos
            except OSError:
                pass
        sonido.musica("menu")
        self.estado = "personalizar"

    # ------------------------------------------------------------------ dibujo
    def dibujar(self, p):
        dibujar_fondo(p, self.t, publico=False)
        f, g = self.j.fuente, self.j.f_grande
        rotulo = "PERSONALIZA TU LUCHADOR" if self.estado == "personalizar" else "CREA TU LUCHADOR"
        titulo(p, rotulo, 52, (C.ANCHO // 2, 32))
        if self.estado in ("preview", "cuenta") and self.superficie:
            esc = 0.8
            img = pygame.transform.smoothscale(self.superficie, (int(640 * esc), int(480 * esc)))
            ox, oy = (C.ANCHO - img.get_width()) // 2, 70
            p.blit(img, (ox, oy))
            principal = max(self.caras, key=lambda c: c[2] * c[3]) if self.caras else None
            for cara in self.caras:
                x, y, w, h = cara
                col, g = (AMARILLO, 3) if cara == principal else (GRIS, 1)
                pygame.draw.rect(p, col, (int(ox + x * esc), int(oy + y * esc), int(w * esc), int(h * esc)), g)
            if self.estado == "cuenta":
                n = max(1, math.ceil(self.t_cuenta / 1000))
                frac = (self.t_cuenta % 1000) / 1000
                texto_borde(p, str(n), int(140 + 80 * frac), BLANCO, (C.ANCHO // 2, 250), grosor=5)
        if self.estado == "conectando":
            texto(p, f, "Conectando con la camara...", BLANCO, C.ANCHO // 2, 250, True)
        elif self.estado == "error":
            texto_borde(p, "NO SE PUDO CONECTAR LA CAMARA", 40, ROJO, (C.ANCHO // 2, 130))
            y = 180
            for linea in self.camara.diagnostico or [self.camara.error]:
                for k in range(0, len(linea), 80):              # parte lineas largas
                    texto(p, self.j.f_chica, linea[k:k + 80], BLANCO, C.ANCHO // 2, y, True)
                    y += 22
                y += 10
            pista = ("Revisa CAMERA_INDEX en .env (0, 1, 2... o la IP de DroidCam)" if C.ENV_ENCONTRADO else
                     "NO HAY ARCHIVO .env EN ESTA CARPETA: copia el tuyo (con CAMERA_INDEX y la clave)")
            texto(p, self.j.f_chica, pista, AMARILLO, C.ANCHO // 2, 440, True)
            texto(p, f, self.msg, GRIS, C.ANCHO // 2, 480, True)
        elif self.estado == "preview":
            texto(p, self.j.f_chica, f"camara: {self.camara.fuente}   (CAMERA_INDEX={C.CAMERA_INDEX})"
                  + ("" if C.ENV_ENCONTRADO else "   -  FALTA .env!"), GRIS, C.ANCHO // 2, 455, True)
            ayuda = ("Cara detectada  -  pulsa F para sacar la foto" if len(self.caras) == 1 else
                     "Varias caras: se usara la mas cercana (amarilla)  -  F para la foto" if self.caras else
                     "Ponte delante de la camara")
            texto(p, f, self.msg or ayuda, BLANCO, C.ANCHO // 2, 500, True)
        elif self.estado == "analizando":
            cx, cy, t = C.ANCHO // 2, 270, self.t
            pygame.draw.rect(p, OSCURO, (cx - 240, cy - 90, 480, 180))
            for k in range(8):
                a = t * 4 + k * math.pi / 4
                brillo = int(80 + 175 * (k / 8))
                pygame.draw.circle(p, (brillo, brillo, 255), (int(cx + 40 * math.cos(a)), int(cy - 10 + 40 * math.sin(a))), 7)
            texto(p, f, self.progreso or "Preparando...", BLANCO, cx, cy + 45, True)
            texto(p, self.j.f_chica, "La IA mira tu pelo, piel, gafas y ropa", GRIS, cx, cy + 72, True)
        elif self.estado in ("personalizar", "listo"):
            self._dibujar_personalizar(p)
        if self.flash > 0:
            capa = pygame.Surface((C.ANCHO, C.ALTO), pygame.SRCALPHA)
            capa.fill((255, 255, 255, int(255 * self.flash / 250)))
            p.blit(capa, (0, 0))

    def _dibujar_personalizar(self, p):
        f, fc = self.j.fuente, self.j.f_chica
        n = len(self.nuevos)
        poses = ["reposo0", "puno", "reposo1", "especial", "victoria"]
        for k, pj in enumerate(self.nuevos):
            cx = C.ANCHO * (k + 1) // (n + 1)
            pose = poses[int(self.t * 1.6) % len(poses)]
            img = superficie_personaje(pj, 1, 3, pose)
            poner(p, img, cx, 342, 1, 3)
            escribiendo = self.estado == "personalizar" and self.fase[k] == "nombre" and not self.ok[k]
            if escribiendo:
                texto(p, fc, "ESCRIBE TU NOMBRE", AMARILLO, cx, 66, True)
                self.teclados[k].dibujar_nombre(p, cx, 100, self.t, pj.nombre)
                self.teclados[k].dibujar(p, cx, 352, fc)
                ayuda = ("joystick mover   F letra   G borrar" if k == 0 else
                         "flechas mover   K letra   L borrar")
                if n == 1:
                    ayuda = "joystick mover   F/K letra   G/L borrar   OK terminar"
                texto(p, fc, ayuda, GRIS, cx, 522, True)
                continue
            texto_borde(p, pj.nombre, 40, BLANCO, (cx, 80))
            texto(p, fc, resumen_rasgos(pj.rasgos), (200, 200, 230), cx, 98, True)
            # muestras de color de piel / pelo / ropa
            for j, clave in enumerate(("piel", "pelo_color", "ropa_color")):
                pygame.draw.rect(p, rasgos.hex_a_rgb(pj.rasgos[clave]), (cx - 33 + j * 24, 116, 18, 12))
                pygame.draw.rect(p, BLANCO, (cx - 33 + j * 24, 116, 18, 12), 1)
            if self.estado == "personalizar":
                valores = (avatar.STATS[pj.cuerpo]["nombre"], pj.traje.upper())
                for j, (fila, val) in enumerate(zip(self.FILAS, valores)):
                    sel = self.fila[k] == j and not self.ok[k]
                    col = AMARILLO if sel else BLANCO
                    texto(p, f, f"{fila}:  < {val} >" if sel else f"{fila}:  {val}", col, cx, 344 + j * 27, True)
                texto(p, fc, "ESPECIAL: " + pj.especial, pj.color if sum(pj.color) > 200 else BLANCO, cx, 398, True)
                for j, (nom, v) in enumerate(stats_normalizados(pj)):
                    barra_stat(p, fc, nom, v, cx - 130, 418 + j * 17, 150)
                if self.ok[k]:
                    texto_borde(p, "LISTO!", 40, AMARILLO, (cx, 500))
                else:
                    ayuda = "W/S fila  A/D cambiar  F nombre" if k == 0 else "flechas  K nombre"
                    if n == 1:
                        ayuda = "arriba/abajo fila  izq/der cambiar  F siguiente"
                    texto(p, fc, ayuda, GRIS, cx, 488, True)
        fuente = self.fuentes[0] if self.fuentes else "local"
        if any(self.fase[k] == "nombre" and not self.ok[k] for k in range(n)) and self.estado == "personalizar":
            pass                                              # el teclado ocupa la parte de abajo
        elif fuente == "local":
            errs = [e for e in self.errores if "falta " not in e] or self.errores or ["AI_PROVIDER=local"]
            err = " ".join(errs[-1].split())                  # el ultimo = el servicio que de verdad se probo
            texto(p, fc, "Sin IA (modo local aproximado): " + err[:78], (255, 150, 150), C.ANCHO // 2, 506, True)
            if len(err) > 78:
                texto(p, fc, err[78:180], (255, 150, 150), C.ANCHO // 2, 523, True)
        else:
            texto(p, fc, f"Rasgos detectados con {fuente.upper()}", (150, 255, 170), C.ANCHO // 2, 510, True)
        if self.estado == "listo":
            texto_borde(p, "LUCHADOR GUARDADO!", 44, AMARILLO, (C.ANCHO // 2, 385))
            texto_borde(p, "F: A LUCHAR CONTRA LA MAQUINA!", 38, AMARILLO, (C.ANCHO // 2, 430))
            texto_borde(p, "G: CREAR OTRO      ESC: MENU", 30, BLANCO, (C.ANCHO // 2, 470))
