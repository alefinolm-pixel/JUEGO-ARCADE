"""Escenarios de pelea, uno por dificultad. Pixel art dibujado por codigo.

  normal   -> CAFETERIA RETRO (anos 80): neon, suelo de ajedrez, sofas turquesa,
              furgoneta roja de comida, jukebox con luces
  dificil  -> NOCHE GOTICA: luna, catedral con roseton, ciudad iluminada,
              murcielagos volando, niebla y relampagos
  experto  -> ESPACIO: estrellas en movimiento, nebulosa, planeta con anillos,
              cubierta de nave con luces de neon

Se dibujan a media resolucion (480x270) y se amplian x2: pixel art nitido.
"""
import math
import random

import pygame

import config as C
from fuente_pixel import FuentePixel

LW, LH = C.ANCHO // 2, C.ALTO // 2          # 480 x 270
SUELO = C.SUELO // 2                        # 220


def _mezcla(a, b, f):
    return tuple(int(a[i] + (b[i] - a[i]) * f) for i in range(3))


def _degradado(s, arriba, abajo, y0, y1):
    for y in range(y0, y1):
        s.fill(_mezcla(arriba, abajo, (y - y0) / max(1, y1 - y0 - 1)), (0, y, s.get_width(), 1))


def _caja(s, col, r, borde=None, radio=0):
    pygame.draw.rect(s, col, r, border_radius=radio)
    if borde:
        pygame.draw.rect(s, borde, r, 1, border_radius=radio)


class Escenario:
    nombre = ""
    musica = "pelea"
    descripcion = ""

    def __init__(self):
        self.rng = random.Random(7)
        self.fijo = pygame.Surface((LW, LH))
        self.dibujar_fijo(self.fijo)
        self.lienzo = pygame.Surface((LW, LH))
        self.t = 0.0

    def dibujar_fijo(self, s):
        pass

    def animar(self, s, t, dt):
        pass

    def dibujar(self, p, dt):
        self.t += dt / 1000
        self.lienzo.blit(self.fijo, (0, 0))
        self.animar(self.lienzo, self.t, dt)
        pygame.transform.scale(self.lienzo, (C.ANCHO, C.ALTO), p)

    def miniatura(self, w, h):
        s = self.fijo.copy()
        self.animar(s, 1.0, 16)
        return pygame.transform.scale(s, (w, h))


# =====================================================================  CAFETERIA
class Cafeteria(Escenario):
    nombre = "CAFETERIA RETRO"
    musica = "normal"
    descripcion = "Neon y ajedrez"

    def dibujar_fijo(self, s):
        r = self.rng
        # pared y techo
        _degradado(s, (250, 240, 225), (235, 220, 205), 0, SUELO)
        s.fill((40, 36, 48), (0, 0, LW, 34))                         # techo
        s.fill((25, 22, 30), (0, 34, LW, 3))
        s.fill((60, 200, 190), (0, 150, LW, SUELO - 150))            # zocalo turquesa
        s.fill((200, 210, 220), (0, 148, LW, 3))                      # moldura cromada
        s.fill((255, 255, 255), (0, 148, LW, 1))
        for x in range(0, LW, 24):                                    # rayas del zocalo
            s.fill((50, 175, 168), (x, 151, 2, SUELO - 151))
        # cartel colgante (el neon se dibuja animado)
        _caja(s, (45, 48, 62), (108, 40, 264, 28), (20, 20, 30), 3)      # cartel de neon colgado
        s.fill((30, 30, 40), (150, 34, 2, 6)); s.fill((30, 30, 40), (328, 34, 2, 6))
        # ventana con cielo de atardecer
        _caja(s, (190, 200, 215), (376, 48, 92, 92), (120, 130, 150))
        _degradado(s.subsurface((380, 52, 84, 84)), (255, 140, 120), (255, 220, 160), 0, 84)
        pygame.draw.circle(s, (255, 240, 180), (440, 118), 10)
        for x, h in ((384, 18), (398, 26), (410, 14), (448, 22)):    # edificios lejanos
            s.fill((150, 110, 130), (x, 136 - h, 10, h))
        s.fill((190, 200, 215), (420, 48, 4, 92)); s.fill((190, 200, 215), (376, 92, 92, 3))
        # tele en la pared
        _caja(s, (30, 30, 35), (24, 76, 64, 40), (10, 10, 12), 2)
        s.fill((25, 25, 30), (52, 116, 8, 6))
        # pizarra de menu
        _caja(s, (40, 55, 45), (100, 76, 46, 40), (120, 80, 50), 2)
        for k in range(5):
            w = r.randint(16, 30)
            s.fill((230, 230, 220), (105, 81 + k * 6, w, 2))
            s.fill((250, 200, 90), (138, 81 + k * 6, 4, 2))
        # furgoneta roja de comida (fondo, centro)
        self._furgoneta(s, 186, 78)
        # sofas turquesa con mesas
        for x0, lado in ((8, 1), (338, -1)):
            self._sofa(s, x0, 166)
            self._sofa(s, x0 + 92, 166)
            _caja(s, (245, 245, 250), (x0 + 50, 176, 50, 6), (180, 180, 190))
            s.fill((150, 150, 160), (x0 + 73, 182, 4, 30))
            s.fill((20, 20, 25), (x0 + 60, 170, 6, 6)); s.fill((240, 60, 60), (x0 + 86, 167, 4, 9))
        # jukebox a la izquierda de la furgoneta
        _caja(s, (150, 40, 60), (150, 120, 30, 96), (60, 15, 25), 8)
        pygame.draw.ellipse(s, (255, 220, 150), (154, 124, 22, 30))
        s.fill((200, 200, 210), (156, 160, 18, 20))
        # suelo de ajedrez en perspectiva
        self._ajedrez(s)

    def _furgoneta(self, s, x, y):
        rojo, osc = (220, 30, 40), (150, 15, 25)
        _caja(s, rojo, (x, y + 30, 120, 96), osc, 12)                # caja trasera
        _caja(s, rojo, (x + 100, y + 56, 46, 70), osc, 10)          # cabina
        _caja(s, (170, 220, 240), (x + 112, y + 62, 28, 24), (60, 70, 90), 4)   # parabrisas
        s.fill((240, 240, 245), (x + 4, y + 112, 140, 4))           # franja cromada
        _caja(s, (30, 30, 35), (x + 12, y + 46, 80, 40), osc, 2)     # ventanilla de servicio
        for k in range(7):
            col = ((250, 210, 60), (90, 200, 90), (240, 90, 60), (90, 150, 240))[k % 4]
            s.fill(col, (x + 18 + k * 10, y + 70, 6, 12))
        s.fill((230, 230, 235), (x + 8, y + 84, 88, 5))              # mostrador
        pygame.draw.polygon(s, (200, 25, 35), [(x + 6, y + 44), (x + 98, y + 44), (x + 104, y + 26), (x, y + 26)])
        for k in range(0, 98, 12):                                    # toldo a rayas
            pygame.draw.polygon(s, (250, 250, 250), [(x + 6 + k, y + 44), (x + 12 + k, y + 44),
                                                     (x + 12 + k, y + 26), (x + 6 + k, y + 26)])
        for wx in (x + 24, x + 120):                                  # ruedas
            pygame.draw.circle(s, (20, 20, 25), (wx, y + 128), 11)
            pygame.draw.circle(s, (235, 235, 240), (wx, y + 128), 6)
        s.fill((255, 240, 180), (x + 142, y + 98, 5, 6))             # faro

    def _sofa(self, s, x, y):
        t, b = (60, 200, 190), (245, 245, 245)
        _caja(s, t, (x, y - 30, 46, 36), (30, 130, 125), 6)
        for k in range(4):
            s.fill(b, (x + 6 + k * 10, y - 26, 5, 28))
        _caja(s, t, (x - 2, y + 4, 50, 12), (30, 130, 125), 4)
        s.fill((30, 130, 125), (x + 2, y + 16, 4, 20)); s.fill((30, 130, 125), (x + 40, y + 16, 4, 20))

    def _ajedrez(self, s):
        filas = 7
        ys = [SUELO + int((LH - SUELO) * (k / filas) ** 1.5) for k in range(filas + 1)]
        cx = LW // 2
        for k in range(filas):
            y0, y1 = ys[k], ys[k + 1]
            w0, w1 = 22 + k * 5, 22 + (k + 1) * 5
            for i in range(-14, 15):
                col = (25, 22, 28) if (i + k) % 2 else (235, 230, 225)
                pygame.draw.polygon(s, col, [(cx + i * w0, y0), (cx + (i + 1) * w0, y0),
                                             (cx + (i + 1) * w1, y1), (cx + i * w1, y1)])
        s.fill((200, 40, 60), (0, SUELO - 2, LW, 3))

    def animar(self, s, t, dt):
        # neon con parpadeo ocasional
        f = FuentePixel(escala=2)
        apagado = (int(t * 10) % 37 == 0) or (int(t * 10) % 53 == 1)
        rosa = (120, 60, 80) if apagado else (255, 90, 160)
        texto = "BIENVENIDOS A LOS 80"
        img = f.render(texto, True, rosa)
        r = img.get_rect(center=(240, 54))
        if not apagado:
            pygame.draw.rect(s, (90, 40, 70), (112, 43, 256, 22), border_radius=3)
        if not apagado:
            halo = f.render(texto, True, (255, 150, 200))
            halo.set_alpha(90)
            for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                s.blit(halo, r.move(dx, dy))
        s.blit(img, r)
        # tele con imagen que cambia
        col = ((80, 160, 255), (255, 120, 80), (120, 230, 120))[int(t / 2) % 3]
        s.fill(col, (28, 80, 56, 32))
        for k in range(6):
            s.fill(tuple(min(255, c + 40) for c in col), (28, 80 + (int(t * 40) + k * 6) % 32, 56, 1))
        # luces del jukebox
        for k in range(5):
            h = (t * 3 + k * 0.7) % 3
            col = ((255, 80, 80), (80, 255, 120), (80, 160, 255))[int(h)]
            s.fill(col, (152, 186 + k * 6, 26, 2))


# =====================================================================  GOTICO
class Gotico(Escenario):
    nombre = "NOCHE GOTICA"
    musica = "gotico"
    descripcion = "Murcielagos y luna"

    def __init__(self):
        self.ventanas = []
        super().__init__()
        rr = random.Random(3)
        self.murcielagos = [[rr.uniform(0, LW), rr.uniform(20, 140), rr.uniform(25, 60) * rr.choice((-1, 1)),
                             rr.uniform(0, 6), rr.uniform(0.7, 1.3)] for _ in range(9)]
        self.niebla = [[rr.uniform(0, LW), rr.uniform(190, 230), rr.uniform(40, 90), rr.uniform(4, 10)]
                       for _ in range(7)]
        self.relampago = 0
        self.prox_rayo = 5.0

    def dibujar_fijo(self, s):
        r = self.rng
        _degradado(s, (8, 6, 26), (60, 28, 78), 0, SUELO)
        for _ in range(90):                                          # estrellas
            s.fill((200, 200, 255), (r.randrange(LW), r.randrange(150), 1, 1))
        # luna
        pygame.draw.circle(s, (70, 50, 100), (380, 62), 40)
        pygame.draw.circle(s, (110, 80, 130), (380, 62), 34)
        pygame.draw.circle(s, (245, 240, 210), (380, 62), 28)
        for cx, cy, cr in ((370, 54, 5), (392, 70, 4), (384, 50, 3), (372, 74, 3)):
            pygame.draw.circle(s, (215, 210, 185), (cx, cy), cr)
        # ciudad lejana con ventanas encendidas
        x = 0
        while x < LW:
            w, h = r.randint(18, 34), r.randint(40, 95)
            s.fill((28, 20, 48), (x, SUELO - 20 - h, w, h + 20))
            for wy in range(SUELO - 16 - h, SUELO - 22, 7):
                for wx in range(x + 3, x + w - 3, 6):
                    if r.random() < 0.38:
                        self.ventanas.append((wx, wy))
                        s.fill((255, 200, 90), (wx, wy, 2, 3))
            x += w + r.randint(1, 4)
        # catedral (centro)
        c = (34, 24, 52)
        s.fill(c, (150, 96, 180, 130))
        for tx in (150, 296):                                          # torres
            s.fill(c, (tx, 52, 34, 80))
            pygame.draw.polygon(s, c, [(tx - 2, 54), (tx + 17, 6), (tx + 36, 54)])
            s.fill((255, 170, 80), (tx + 14, 70, 6, 14))
            pygame.draw.polygon(s, (255, 170, 80), [(tx + 14, 70), (tx + 17, 64), (tx + 20, 70)])
        pygame.draw.polygon(s, c, [(184, 98), (240, 46), (296, 98)])  # tejado central
        pygame.draw.circle(s, (120, 30, 40), (240, 116), 20)           # roseton
        pygame.draw.circle(s, (255, 120, 60), (240, 116), 17)
        for k in range(8):
            a = k * math.pi / 4
            pygame.draw.line(s, (120, 30, 40), (240, 116), (240 + 17 * math.cos(a), 116 + 17 * math.sin(a)), 2)
        pygame.draw.circle(s, (255, 220, 120), (240, 116), 5)
        for wx in (172, 196, 272, 290):                                 # vidrieras ojivales
            s.fill((200, 90, 60), (wx, 150, 10, 26))
            pygame.draw.polygon(s, (200, 90, 60), [(wx, 150), (wx + 5, 141), (wx + 10, 150)])
        s.fill((20, 14, 30), (224, 176, 32, 50))                       # portico
        pygame.draw.polygon(s, (20, 14, 30), [(224, 176), (240, 158), (256, 176)])
        # balaustrada de piedra
        s.fill((70, 62, 88), (0, SUELO - 26, LW, 6))
        for x in range(4, LW, 14):
            _caja(s, (85, 76, 105), (x, SUELO - 20, 7, 20), (45, 40, 60), 2)
        s.fill((70, 62, 88), (0, SUELO - 3, LW, 4))
        # gargolas sobre pilares en los extremos
        for gx, d in ((18, 1), (LW - 38, -1)):
            s.fill((60, 54, 78), (gx, SUELO - 60, 20, 60))
            g = (40, 36, 56)
            pygame.draw.polygon(s, g, [(gx - 2, SUELO - 60), (gx + 22, SUELO - 60), (gx + 18, SUELO - 74),
                                       (gx + 10, SUELO - 70), (gx + 2, SUELO - 74)])
            pygame.draw.polygon(s, g, [(gx + 10 - 14 * d, SUELO - 74), (gx + 10, SUELO - 66),
                                       (gx + 10 - 6 * d, SUELO - 86)])        # ala
            s.fill((255, 60, 60), (gx + 6, SUELO - 70, 2, 2)); s.fill((255, 60, 60), (gx + 12, SUELO - 70, 2, 2))
        # suelo de losas
        _degradado(s, (75, 66, 90), (40, 34, 52), SUELO, LH)
        for y in range(SUELO, LH, 10):
            s.fill((35, 30, 45), (0, y, LW, 1))
            off = 0 if (y // 10) % 2 else 12
            for x in range(off, LW, 24):
                s.fill((35, 30, 45), (x, y, 1, 10))

    def animar(self, s, t, dt):
        k = dt / 1000
        # ventanas que se encienden / apagan
        rr = random.Random(int(t * 2))
        for _ in range(4):
            if self.ventanas:
                wx, wy = rr.choice(self.ventanas)
                s.fill((60, 40, 50) if rr.random() < 0.5 else (255, 240, 150), (wx, wy, 2, 3))
        # murcielagos
        for m in self.murcielagos:
            m[0] += m[2] * k
            m[3] += k * 12
            if m[0] < -20:
                m[0] = LW + 20
            elif m[0] > LW + 20:
                m[0] = -20
            x, y = int(m[0]), int(m[1] + 6 * math.sin(t * 2 + m[3] * 0.1))
            e = m[4]
            alas = -5 if math.sin(m[3]) > 0 else 3
            col = (12, 8, 18)
            pygame.draw.polygon(s, col, [(x, y), (x - int(9 * e), y + alas), (x - int(5 * e), y + 2)])
            pygame.draw.polygon(s, col, [(x, y), (x + int(9 * e), y + alas), (x + int(5 * e), y + 2)])
            s.fill(col, (x - 1, y - 1, 3, 4))
        # niebla que se desplaza
        capa = pygame.Surface((LW, 70), pygame.SRCALPHA)
        for n in self.niebla:
            n[0] = (n[0] + n[3] * k) % (LW + 120)
            pygame.draw.ellipse(capa, (170, 150, 200, 38), (n[0] - 60, n[1] - 190, n[2] * 2, 18))
        s.blit(capa, (0, 180))
        # relampago de vez en cuando
        self.prox_rayo -= k
        if self.prox_rayo <= 0:
            self.relampago = 0.25
            self.prox_rayo = random.uniform(6, 12)
        if self.relampago > 0:
            self.relampago -= k
            if int(self.relampago * 30) % 2 == 0:
                flash = pygame.Surface((LW, SUELO), pygame.SRCALPHA)
                flash.fill((200, 200, 255, 70))
                s.blit(flash, (0, 0))
                x = 60
                pts = [(x, 0)]
                for y in range(15, 120, 15):
                    x += random.randint(-10, 10)
                    pts.append((x, y))
                pygame.draw.lines(s, (240, 240, 255), False, pts, 2)


# =====================================================================  ESPACIO
class Espacio(Escenario):
    nombre = "ESTACION ESPACIAL"
    musica = "espacio"
    descripcion = "Espadas y cascos alien"

    def __init__(self):
        super().__init__()
        rr = random.Random(11)
        self.estrellas = [(rr.uniform(0, LW), rr.uniform(0, SUELO - 30), rr.choice((1, 1, 1, 2)),
                           rr.choice((4, 8, 16))) for _ in range(140)]
        self.asteroides = [[rr.uniform(0, LW), rr.uniform(30, 150), rr.uniform(3, 7), rr.uniform(4, 9)]
                           for _ in range(4)]
        self.fugaz = None

    def dibujar_fijo(self, s):
        r = self.rng
        _degradado(s, (4, 2, 14), (16, 10, 40), 0, SUELO)
        # nebulosa (manchas de color con transparencia)
        neb = pygame.Surface((LW, SUELO), pygame.SRCALPHA)
        for _ in range(14):                                        # nubes de gas brillante
            col = r.choice(((170, 70, 230), (50, 190, 230), (240, 80, 170)))
            x, y, rad = r.randint(70, 300), r.randint(30, 150), r.randint(18, 36)
            for k in range(5, 0, -1):                              # capas concentricas = brillo suave
                pygame.draw.circle(neb, col + (16 + (5 - k) * 11,), (x, y), int(rad * k / 5))
        s.blit(neb, (0, 0))
        # galaxia espiral pequena
        for k in range(60):
            a = k * 0.35
            d = k * 0.45
            s.fill((210, 200, 255), (int(110 + d * math.cos(a)), int(60 + d * 0.5 * math.sin(a)), 1, 1))
        # planeta con anillos
        pygame.draw.ellipse(s, (200, 150, 90), (316, 52, 110, 24), 3)        # anillo (parte de atras)
        pl = pygame.Surface((70, 70), pygame.SRCALPHA)
        pygame.draw.circle(pl, (230, 140, 70), (35, 35), 34)
        for k, col in enumerate(((245, 175, 105), (205, 115, 65), (250, 200, 140), (215, 125, 70))):
            pl.fill(col, (0, 14 + k * 11, 70, 4), special_flags=0)
        mascara = pygame.Surface((70, 70), pygame.SRCALPHA)
        pygame.draw.circle(mascara, (255, 255, 255, 255), (35, 35), 34)
        sombra = pygame.Surface((70, 70), pygame.SRCALPHA)
        pygame.draw.circle(sombra, (40, 10, 30, 150), (35, 35), 34)
        pygame.draw.circle(sombra, (0, 0, 0, 0), (25, 27), 34)               # luz arriba-izquierda
        pl.blit(sombra, (0, 0))
        pl.blit(mascara, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
        s.blit(pl, (335, 29))
        pygame.draw.arc(s, (235, 195, 125), (316, 52, 110, 24), math.pi, 2 * math.pi, 3)  # anillo delante
        # luna gris
        pygame.draw.circle(s, (150, 150, 165), (70, 40), 14)
        pygame.draw.circle(s, (120, 120, 135), (66, 36), 3)
        pygame.draw.circle(s, (120, 120, 135), (75, 46), 2)
        # marco de la ventana de la nave
        metal, osc = (70, 80, 100), (35, 40, 55)
        s.fill(metal, (0, 0, LW, 10)); s.fill(osc, (0, 10, LW, 2))
        for x in (0, LW - 14):
            s.fill(metal, (x, 0, 14, SUELO)); s.fill(osc, (x + (12 if x == 0 else 0), 0, 2, SUELO))
        for x in (160, 320):                                            # montantes de la ventana
            s.fill(metal, (x - 3, 0, 6, SUELO - 34)); s.fill(osc, (x + 1, 0, 2, SUELO - 34))
        # consola trasera
        s.fill((40, 46, 64), (0, SUELO - 34, LW, 34))
        s.fill((25, 28, 40), (0, SUELO - 34, LW, 2))
        for x in range(20, LW - 20, 40):
            _caja(s, (20, 24, 34), (x, SUELO - 28, 30, 14), (80, 90, 120), 2)
        # suelo metalico con paneles
        _degradado(s, (60, 68, 90), (28, 32, 46), SUELO, LH)
        for y in (SUELO + 12, SUELO + 28):
            s.fill((24, 26, 38), (0, y, LW, 1))
        for x in range(0, LW, 40):
            s.fill((24, 26, 38), (x, SUELO, 1, LH - SUELO))
            s.fill((110, 120, 150), (x + 4, SUELO + 4, 2, 2))

    def animar(self, s, t, dt):
        k = dt / 1000
        # estrellas en paralaje (la nave avanza)
        for x0, y, tam, vel in self.estrellas:
            x = int((x0 - t * vel) % (LW - 28)) + 14
            if y < 12:
                continue
            brillo = 150 + int(100 * (0.5 + 0.5 * math.sin(t * 3 + x0)))
            s.fill((brillo, brillo, 255), (x, int(y), tam, tam))
        # asteroides
        for a in self.asteroides:
            a[0] -= a[2] * k
            if a[0] < -20:
                a[0] = LW + 20
            pygame.draw.circle(s, (110, 95, 85), (int(a[0]), int(a[1])), int(a[3]))
            pygame.draw.circle(s, (80, 68, 62), (int(a[0]) + 2, int(a[1]) + 2), int(a[3] / 2.5))
        # estrella fugaz ocasional
        if self.fugaz is None and random.random() < 0.004:
            self.fugaz = [random.uniform(100, 400), random.uniform(15, 60), 0.0]
        if self.fugaz:
            fx, fy, ft = self.fugaz
            self.fugaz[2] += k
            x, y = int(fx - ft * 300), int(fy + ft * 90)
            pygame.draw.line(s, (255, 255, 255), (x, y), (x + 14, y - 4), 1)
            if ft > 0.6:
                self.fugaz = None
        # marco y suelo (se repinta encima de las estrellas)
        s.blit(self.fijo, (0, 0), (0, 0, 14, SUELO))
        s.blit(self.fijo, (LW - 14, 0), (LW - 14, 0, 14, SUELO))
        s.blit(self.fijo, (0, 0), (0, 0, LW, 12))
        s.blit(self.fijo, (0, SUELO - 34), (0, SUELO - 34, LW, LH - SUELO + 34))
        for x in (160, 320):
            s.blit(self.fijo, (x - 3, 0), (x - 3, 0, 6, SUELO - 34))
        # luces de neon que laten en el suelo y la consola
        p = 0.5 + 0.5 * math.sin(t * 3)
        cian = _mezcla((0, 120, 160), (80, 255, 255), p)
        s.fill(cian, (0, SUELO - 1, LW, 2))
        for x in range(20, LW - 20, 40):
            col = ((255, 80, 80), (80, 255, 120), (255, 220, 80))[(x // 40 + int(t * 2)) % 3]
            s.fill(col, (x + 4, SUELO - 24, 6, 3))
            s.fill(cian, (x + 14, SUELO - 24, 12, 2))


ESCENARIOS = {"normal": Cafeteria, "dificil": Gotico, "experto": Espacio}


def crear(dificultad):
    return ESCENARIOS.get(dificultad, Cafeteria)()
