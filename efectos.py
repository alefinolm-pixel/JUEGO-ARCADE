"""Efectos visuales: particulas, chispas de impacto, numeros de dano, ondas,
temblor de pantalla, hitstop (congelar frames) y destellos."""
import math
import random

import pygame

BLANCO = (255, 255, 255)
AMARILLO = (255, 230, 60)
NARANJA = (255, 140, 30)

_fuentes = {}


def fuente(tam):
    from fuente_pixel import fuente as fp
    return fp(tam)


def texto_borde(p, s, tam, color, centro, borde=(20, 15, 35), grosor=3):
    """Texto con contorno grueso (estilo arcade)."""
    f = fuente(tam)
    base = f.render(s, True, borde)
    img = f.render(s, True, color)
    r = img.get_rect(center=centro)
    for dx in (-grosor, 0, grosor):
        for dy in (-grosor, 0, grosor):
            if dx or dy:
                p.blit(base, r.move(dx, dy))
    p.blit(img, r)
    return r


class Particula:
    __slots__ = ("x", "y", "vx", "vy", "vida", "max", "color", "tam", "grav", "forma", "roce")

    def __init__(self, x, y, vx, vy, vida, color, tam=4, grav=0.0, forma="cuadro", roce=0.98):
        self.x, self.y, self.vx, self.vy = x, y, vx, vy
        self.vida = self.max = vida
        self.color, self.tam, self.grav, self.forma, self.roce = color, tam, grav, forma, roce


class Efectos:
    def __init__(self):
        self.particulas = []
        self.textos = []          # [x, y, vy, vida, max, s, color, tam]
        self.anillos = []         # [x, y, r0, r1, vida, max, color, grosor]
        self.lineas = []          # lineas de velocidad: [x, y, ang, largo, vida, max, color]
        self.temblor_t = 0
        self.temblor_i = 0
        self.hitstop = 0          # ms que el combate queda congelado tras un golpe
        self.flash_t = 0
        self.flash_max = 1
        self.flash_color = BLANCO
        self.camara_lenta = 0     # ms a velocidad reducida (K.O.)

    # -------------------------------------------------------------- creadores
    def chispa(self, x, y, direccion, color=AMARILLO, fuerza=1.0):
        """Estallido de impacto: chispas en abanico + estrella + anillo."""
        n = int(14 * fuerza)
        for _ in range(n):
            ang = random.uniform(-1.1, 1.1) + (0 if direccion > 0 else math.pi)
            v = random.uniform(3, 9) * fuerza
            self.particulas.append(Particula(
                x, y, math.cos(ang) * v, math.sin(ang) * v - 1, random.randint(180, 380),
                random.choice((color, BLANCO, AMARILLO)), random.randint(3, 6), 0.25, "chispa", 0.9))
        self.anillos.append([x, y, 6, 50 * fuerza, 180, 180, BLANCO, 4])
        for k in range(8):
            ang = k * math.pi / 4 + random.uniform(-0.2, 0.2)
            self.lineas.append([x, y, ang, random.uniform(25, 45) * fuerza, 110, 110, BLANCO])

    def bloqueo(self, x, y, direccion):
        for _ in range(10):
            ang = random.uniform(-0.8, 0.8) + (math.pi if direccion > 0 else 0)
            v = random.uniform(2, 5)
            self.particulas.append(Particula(x, y, math.cos(ang) * v, math.sin(ang) * v, 220,
                                             (120, 200, 255), 4, 0.1, "chispa"))
        self.anillos.append([x, y, 10, 40, 160, 160, (120, 200, 255), 3])

    def polvo(self, x, y, n=8, color=(170, 150, 190)):
        for _ in range(n):
            self.particulas.append(Particula(
                x + random.uniform(-15, 15), y, random.uniform(-2.5, 2.5), random.uniform(-2, -0.3),
                random.randint(250, 450), color, random.randint(4, 8), 0.05, "circulo", 0.93))

    def estallido(self, x, y, color, n=30, vel=8, tam=(3, 8), forma="cuadro", vida=(300, 700)):
        for _ in range(n):
            ang = random.uniform(0, 2 * math.pi)
            v = random.uniform(1, vel)
            self.particulas.append(Particula(
                x, y, math.cos(ang) * v, math.sin(ang) * v, random.randint(*vida),
                random.choice((color, BLANCO)), random.randint(*tam), 0.12, forma, 0.95))

    def estela(self, x, y, color, tam=6, forma="cuadro"):
        self.particulas.append(Particula(
            x + random.uniform(-4, 4), y + random.uniform(-6, 6), random.uniform(-0.6, 0.6),
            random.uniform(-0.6, 0.6), random.randint(150, 320), color, tam, 0, forma, 0.9))

    def texto(self, x, y, s, color=AMARILLO, tam=40, vida=700, vy=-1.4):
        self.textos.append([x, y, vy, vida, vida, s, color, tam])

    def anillo(self, x, y, color, r0, r1, dur=250, grosor=4):
        self.anillos.append([x, y, r0, r1, dur, dur, color, grosor])

    def temblor(self, intensidad, dur):
        if intensidad >= self.temblor_i or self.temblor_t <= 0:
            self.temblor_i, self.temblor_t = intensidad, dur

    def congelar(self, ms):
        self.hitstop = max(self.hitstop, ms)

    def flash(self, color=BLANCO, dur=90):
        self.flash_color, self.flash_t, self.flash_max = color, dur, dur

    # -------------------------------------------------------------- bucle
    def desplazamiento(self):
        if self.temblor_t <= 0:
            return 0, 0
        i = self.temblor_i
        return random.randint(-i, i), random.randint(-i, i)

    def actualizar(self, dt):
        self.temblor_t = max(0, self.temblor_t - dt)
        self.flash_t = max(0, self.flash_t - dt)
        self.camara_lenta = max(0, self.camara_lenta - dt)
        k = dt / 16.67
        vivas = []
        for q in self.particulas:
            q.vida -= dt
            if q.vida <= 0:
                continue
            q.vx *= q.roce
            q.vy = q.vy * q.roce + q.grav * k
            q.x += q.vx * k
            q.y += q.vy * k
            vivas.append(q)
        self.particulas = vivas[-600:]
        for t in self.textos:
            t[1] += t[2] * k
            t[2] *= 0.95
            t[3] -= dt
        self.textos = [t for t in self.textos if t[3] > 0]
        for a in self.anillos:
            a[4] -= dt
        self.anillos = [a for a in self.anillos if a[4] > 0]
        for ln in self.lineas:
            ln[4] -= dt
        self.lineas = [ln for ln in self.lineas if ln[4] > 0]

    def dibujar(self, p, off=(0, 0)):
        ox, oy = off
        for a in self.anillos:
            f = 1 - a[4] / a[5]
            r = int(a[2] + (a[3] - a[2]) * (1 - (1 - f) ** 2))
            g = max(1, int(a[7] * (1 - f) + 1))
            pygame.draw.circle(p, a[6], (int(a[0] + ox), int(a[1] + oy)), r, g)
        for ln in self.lineas:
            f = 1 - ln[4] / ln[5]
            d0 = 18 + 40 * f
            d1 = d0 + ln[3] * (1 - f)
            c, s = math.cos(ln[2]), math.sin(ln[2])
            pygame.draw.line(p, ln[6], (ln[0] + c * d0 + ox, ln[1] + s * d0 + oy),
                             (ln[0] + c * d1 + ox, ln[1] + s * d1 + oy), 3)
        for q in self.particulas:
            f = q.vida / q.max
            t = max(1, int(q.tam * (0.4 + 0.6 * f)))
            x, y = int(q.x + ox), int(q.y + oy)
            if q.forma == "chispa":
                pygame.draw.line(p, q.color, (x, y), (int(x - q.vx * 2), int(y - q.vy * 2)), t)
            elif q.forma == "circulo":
                pygame.draw.circle(p, q.color, (x, y), t)
            elif q.forma == "estrella":
                dibujar_estrella(p, q.color, x, y, t * 2, q.vida * 0.01)
            else:
                pygame.draw.rect(p, q.color, (x - t // 2, y - t // 2, t, t))
        for t in self.textos:
            f = t[3] / t[4]
            tam = int(t[7] * (1.4 - 0.4 * min(1, (1 - f) * 5)))   # entra grande y se asienta
            texto_borde(p, t[5], tam, t[6], (int(t[0] + ox), int(t[1] + oy)))
        if self.flash_t > 0:
            capa = pygame.Surface(p.get_size(), pygame.SRCALPHA)
            capa.fill(self.flash_color + (int(150 * self.flash_t / self.flash_max),))
            p.blit(capa, (0, 0))


def dibujar_estrella(p, color, x, y, r, giro=0.0):
    pts = []
    for k in range(10):
        rr = r if k % 2 == 0 else r * 0.45
        a = giro + k * math.pi / 5 - math.pi / 2
        pts.append((x + math.cos(a) * rr, y + math.sin(a) * rr))
    pygame.draw.polygon(p, color, pts)


def rayo_zigzag(p, color, x0, y0, x1, y1, segmentos=9, desvio=18, grosor=4):
    """Rayo electrico entre dos puntos."""
    pts = [(x0, y0)]
    for k in range(1, segmentos):
        f = k / segmentos
        pts.append((x0 + (x1 - x0) * f + random.uniform(-desvio, desvio),
                    y0 + (y1 - y0) * f + random.uniform(-desvio * 0.3, desvio * 0.3)))
    pts.append((x1, y1))
    pygame.draw.lines(p, color, False, pts, grosor + 4)
    pygame.draw.lines(p, BLANCO, False, pts, max(1, grosor - 1))
