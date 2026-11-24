"""Ataques especiales: cada uno se juega y se VE distinto.

  ONDA PIXEL      proyectil de pixeles             (se esquiva saltando)
  DRAGON ROJO     bola de fuego                    (se esquiva saltando)
  RAYO FACIAL     laser que sale de los ojos/gafas (rapido, alcance total)
  PUNO ESTELAR    embestida con estela de estrellas
  TURBO COMBO     rafaga de 5 punyetazos
  TORMENTA LUNAR  rayo que cae donde esta el rival (muevete al ver la marca!)
  GOLPE SISMICO   onda por el suelo                (se esquiva saltando)

Dos proyectiles que chocan se anulan.
"""
import math
import random

import pygame

import config as C
import sonido
from efectos import AMARILLO, BLANCO, NARANJA, dibujar_estrella, rayo_zigzag

DANO = {"ONDA PIXEL": 11, "DRAGON ROJO": 12, "RAYO FACIAL": 12, "PUNO ESTELAR": 14,
        "TURBO COMBO": 14, "TORMENTA LUNAR": 13, "GOLPE SISMICO": 15}
COOLDOWN = 1800          # ms entre especiales


def _claro(c, s=90):
    return tuple(min(255, v + s) for v in c)


class Ataque:
    pose = "especial"     # pose del luchador mientras lanza
    duracion_pose = 380
    es_proyectil = False

    def __init__(self, autor, rival, pelea):
        self.a, self.r, self.pelea, self.fx = autor, rival, pelea, pelea.fx
        self.t = 0
        self.vivo = True
        self.dir = autor.direccion
        self.color = autor.personaje.color
        self.dano = DANO.get(autor.personaje.especial, 12)
        self.golpeo = False

    def actualizar(self, dt):
        self.t += dt

    def dibujar(self, p, off):
        pass


# ------------------------------------------------------------------ proyectiles
class Proyectil(Ataque):
    es_proyectil = True
    estilo = "pixel"

    def __init__(self, autor, rival, pelea):
        super().__init__(autor, rival, pelea)
        self.x = autor.rect.centerx + self.dir * 45
        self.y = autor.rect.y + autor.rect.height * 0.42
        self.v = 9.5
        self.salido = False

    def caja(self):
        return pygame.Rect(self.x - 22, self.y - 18, 44, 36)

    def actualizar(self, dt):
        super().actualizar(dt)
        if self.t < 140:                    # el personaje "carga" antes de lanzar
            if self.t + dt >= 0:
                self.fx.estela(self.x, self.y, _claro(self.color), 5)
            return
        if not self.salido:
            self.salido = True
            sonido.play("proyectil")
            self.fx.anillo(self.x, self.y, _claro(self.color), 5, 40, 200, 3)
        self.x += self.v * self.dir * dt / 16.67
        if self.estilo == "fuego":
            for _ in range(2):
                self.fx.particulas.append(_llama(self.x, self.y, self.dir))
        else:
            self.fx.estela(self.x - self.dir * 18, self.y, self.color, random.randint(4, 8))
        if self.caja().colliderect(self.r.rect):
            self.pelea.impactar(self.a, self.r, self.dano, self.x, self.y, 7, 1.5, self.color)
            self.fx.estallido(self.x, self.y, self.color, 25, 7)
            self.vivo = False
        for otro in self.pelea.ataques:     # proyectiles que chocan se anulan
            if otro is not self and otro.vivo and otro.es_proyectil and otro.a is not self.a \
                    and getattr(otro, "salido", False) and self.caja().colliderect(otro.caja()):
                self.vivo = otro.vivo = False
                self.fx.estallido(self.x, self.y, BLANCO, 40, 10)
                self.fx.temblor(5, 150)
                sonido.play("golpe_fuerte")
        if self.x < -60 or self.x > C.ANCHO + 60:
            self.vivo = False

    def dibujar(self, p, off):
        if not self.salido:
            return
        x, y = int(self.x + off[0]), int(self.y + off[1])
        pulso = 3 * math.sin(self.t / 40)
        if self.estilo == "fuego":
            pygame.draw.circle(p, (200, 40, 20), (x, y), int(20 + pulso))
            pygame.draw.circle(p, NARANJA, (x, y), int(15 + pulso))
            pygame.draw.circle(p, AMARILLO, (x + self.dir * 3, y), int(9 + pulso / 2))
            pygame.draw.circle(p, BLANCO, (x + self.dir * 5, y), 4)
        else:
            c, cl = self.color, _claro(self.color)
            for k, tam in enumerate((30, 22, 14)):
                t = int(tam + pulso)
                col = (c, cl, BLANCO)[k]
                pygame.draw.rect(p, col, (x - t // 2 + self.dir * k * 3, y - t // 2, t, t))
            for k in range(1, 4):                      # cola de pixeles
                t = 12 - k * 3
                pygame.draw.rect(p, cl, (x - self.dir * (18 + k * 12) - t // 2, y - t // 2 + int(pulso), t, t))


class BolaFuego(Proyectil):
    estilo = "fuego"


def _llama(x, y, d):
    from efectos import Particula
    return Particula(x - d * random.uniform(8, 18), y + random.uniform(-10, 10),
                     -d * random.uniform(0.5, 2), random.uniform(-1.5, 0), random.randint(150, 300),
                     random.choice(((255, 90, 20), (255, 170, 40), (255, 230, 90))),
                     random.randint(4, 9), -0.05, "circulo", 0.95)


# ------------------------------------------------------------------ rayo de los ojos
class RayoFacial(Ataque):
    duracion_pose = 750

    def __init__(self, autor, rival, pelea):
        super().__init__(autor, rival, pelea)
        sonido.play("carga")
        self.disparo = False

    def ojos(self):
        return (self.a.rect.centerx + self.dir * 7 * C.ESCALA, self.a.rect.y + 10 * C.ESCALA)

    def actualizar(self, dt):
        super().actualizar(dt)
        ox, oy = self.ojos()
        if self.t < 320:                             # carga: particulas que se juntan en los ojos
            ang = random.uniform(0, 2 * math.pi)
            from efectos import Particula
            self.fx.particulas.append(Particula(ox + math.cos(ang) * 50, oy + math.sin(ang) * 50,
                                                -math.cos(ang) * 3, -math.sin(ang) * 3, 260,
                                                _claro(self.color), 3, 0, "chispa", 1.0))
            return
        if not self.disparo:
            self.disparo = True
            sonido.play("rayo")
            self.fx.temblor(4, 300)
        if not self.golpeo and self.t > 360:
            haz = self.caja_haz()
            if haz.colliderect(self.r.rect):
                self.golpeo = True
                hx = self.r.rect.centerx - self.dir * 20
                self.pelea.impactar(self.a, self.r, self.dano, hx, oy, 6, 1.4, self.color)
        if self.t > 700:
            self.vivo = False

    def caja_haz(self):
        ox, oy = self.ojos()
        if self.dir == 1:
            return pygame.Rect(ox, oy - 12, C.ANCHO - ox, 24)
        return pygame.Rect(0, oy - 12, ox, 24)

    def dibujar(self, p, off):
        ox, oy = self.ojos()
        ox += off[0]; oy += off[1]
        if self.t < 320:
            r = int(4 + self.t / 40)
            pygame.draw.circle(p, _claro(self.color), (ox, oy), r)
            pygame.draw.circle(p, BLANCO, (ox, oy), r // 2)
            return
        f = min(1, (self.t - 320) / 60) * max(0, min(1, (700 - self.t) / 120))
        grosor = int((14 + 4 * math.sin(self.t / 25)) * f)
        fin = C.ANCHO + 20 if self.dir == 1 else -20
        if grosor > 1:
            pygame.draw.line(p, self.color, (ox, oy), (fin, oy), grosor + 10)
            pygame.draw.line(p, _claro(self.color), (ox, oy), (fin, oy), grosor + 4)
            pygame.draw.line(p, BLANCO, (ox, oy), (fin, oy), max(2, grosor // 2))
            pygame.draw.circle(p, BLANCO, (ox, oy), grosor)
            for _ in range(3):                         # chispas a lo largo del haz
                x = random.randint(min(ox, fin), max(ox, fin))
                pygame.draw.rect(p, BLANCO, (x, oy + random.randint(-grosor, grosor), 4, 2))


# ------------------------------------------------------------------ embestida
class PunoEstelar(Ataque):
    pose = "puno"
    duracion_pose = 420

    def __init__(self, autor, rival, pelea):
        super().__init__(autor, rival, pelea)
        sonido.play("estrella")
        autor.dash = 260
        autor.vx = 15 * self.dir

    def actualizar(self, dt):
        super().actualizar(dt)
        a = self.a
        if a.dash > 0:
            a.fantasmas.append([a.frame_actual, a.pos_dibujo, 160])
            if random.random() < 0.7:
                self.fx.particulas.append(_estrella(a.rect.centerx - self.dir * 20, a.rect.centery))
            if not self.golpeo and a.rect.inflate(16, 0).colliderect(self.r.rect):
                self.golpeo = True
                a.dash = 0
                a.vx = -2 * self.dir
                x = (a.rect.centerx + self.r.rect.centerx) // 2
                self.pelea.impactar(a, self.r, self.dano, x, a.rect.y + 45, 12, 2.0, AMARILLO)
                for _ in range(8):
                    self.fx.particulas.append(_estrella(x, a.rect.y + 45, rapida=True))
        if self.t > 420:
            self.vivo = False


def _estrella(x, y, rapida=False):
    from efectos import Particula
    v = 6 if rapida else 1.5
    return Particula(x, y + random.uniform(-25, 25), random.uniform(-v, v), random.uniform(-v, v),
                     random.randint(300, 600), random.choice((AMARILLO, BLANCO, (255, 200, 120))),
                     random.randint(3, 5), 0.05, "estrella", 0.96)


# ------------------------------------------------------------------ rafaga
class TurboCombo(Ataque):
    pose = "puno"
    duracion_pose = 700
    GOLPES = 5

    def __init__(self, autor, rival, pelea):
        super().__init__(autor, rival, pelea)
        self.n = 0
        self.punos = []        # [x, y, vida]

    def actualizar(self, dt):
        super().actualizar(dt)
        a = self.a
        a.pose_forzada = "puno" if (self.t // 70) % 2 == 0 else "carga"
        while self.n < self.GOLPES and self.t >= 80 + self.n * 110:
            self.n += 1
            sonido.play("aire", 0.7)
            zona = a.zona_golpe(42 * C.ESCALA)
            x = zona.centerx + random.randint(-15, 15)
            y = zona.centery + random.randint(-25, 20)
            self.punos.append([x, y, 160])
            if zona.colliderect(self.r.rect):
                ultimo = self.n == self.GOLPES
                d = self.dano - (self.dano // self.GOLPES) * (self.GOLPES - 1) if ultimo \
                    else self.dano // self.GOLPES
                self.pelea.impactar(a, self.r, d, x, y, 9 if ultimo else 1.5,
                                    1.6 if ultimo else 0.7, self.color)
        for q in self.punos:
            q[2] -= dt
        self.punos = [q for q in self.punos if q[2] > 0]
        if self.t > 700:
            a.pose_forzada = None
            self.vivo = False

    def dibujar(self, p, off):
        for x, y, v in self.punos:
            f = v / 160
            r = int(10 + 8 * (1 - f))
            x, y = int(x + off[0]), int(y + off[1])
            pygame.draw.circle(p, self.a.personaje.guante, (x, y), r)
            pygame.draw.circle(p, (24, 18, 36), (x, y), r, 2)
            for k in range(3):
                yy = y - 8 + k * 8
                pygame.draw.line(p, BLANCO, (x - self.dir * (r + 6), yy), (x - self.dir * (r + 30), yy), 2)


# ------------------------------------------------------------------ rayo del cielo
class TormentaLunar(Ataque):
    duracion_pose = 450

    def __init__(self, autor, rival, pelea):
        super().__init__(autor, rival, pelea)
        self.x = rival.rect.centerx
        sonido.play("carga")
        self.cayo = False

    def actualizar(self, dt):
        super().actualizar(dt)
        if self.t < 550:                              # aviso: marca en el suelo
            if random.random() < 0.4:
                self.fx.estela(self.x + random.uniform(-30, 30), random.uniform(0, 80), _claro(self.color), 3)
            return
        if not self.cayo:
            self.cayo = True
            sonido.play("trueno")
            self.fx.flash((200, 200, 255), 120)
            self.fx.temblor(7, 250)
            self.fx.estallido(self.x, C.SUELO - 5, _claro(self.color), 30, 8)
            self.fx.polvo(self.x, C.SUELO - 3, 12)
            if abs(self.r.rect.centerx - self.x) < 24 * C.ESCALA:
                self.pelea.impactar(self.a, self.r, self.dano, self.r.rect.centerx,
                                    self.r.rect.centery, 5, 1.6, (200, 200, 255))
        if self.t > 850:
            self.vivo = False

    def dibujar(self, p, off):
        x = int(self.x + off[0])
        if self.t < 550:
            f = self.t / 550
            r = int(55 - 25 * f)
            col = self.color if (self.t // 80) % 2 else _claro(self.color)
            pygame.draw.ellipse(p, col, (x - r, C.SUELO - 8 + off[1], r * 2, 14), 3)
            pygame.draw.ellipse(p, (40, 30, 70), (x - 70, -20, 140, 60))   # nube
            pygame.draw.ellipse(p, (70, 55, 110), (x - 50, -10, 100, 40))
        else:
            for _ in range(2):
                rayo_zigzag(p, _claro(self.color, 120), x, 0, x + random.randint(-10, 10),
                            C.SUELO + off[1], 10, 22, 5)


# ------------------------------------------------------------------ onda por el suelo
class GolpeSismico(Ataque):
    duracion_pose = 500

    def __init__(self, autor, rival, pelea):
        super().__init__(autor, rival, pelea)
        autor.vy = -7                                  # pisoton: salta un poco y cae
        self.x = None

    def actualizar(self, dt):
        super().actualizar(dt)
        if self.x is None:
            if self.t > 200 and self.a.en_suelo:
                self.x = self.a.rect.centerx + self.dir * 30
                sonido.play("sismo")
                self.fx.temblor(9, 350)
                self.fx.polvo(self.a.rect.centerx, C.SUELO - 2, 16)
                self.fx.anillo(self.a.rect.centerx, C.SUELO - 4, (200, 170, 120), 10, 90, 300, 4)
            return
        self.x += 8.5 * self.dir * dt / 16.67
        if random.random() < 0.8:
            self.fx.polvo(self.x, C.SUELO - 2, 2, (190, 160, 120))
        if not self.golpeo and self.r.en_suelo and abs(self.r.rect.centerx - self.x) < 15 * C.ESCALA:
            self.golpeo = True
            self.pelea.impactar(self.a, self.r, self.dano, self.r.rect.centerx, C.SUELO - 30, 6, 1.8,
                                (230, 190, 120))
            self.r.vy = -8                             # lo levanta del suelo
        if self.x < -40 or self.x > C.ANCHO + 40 or self.t > 2500:
            self.vivo = False

    def dibujar(self, p, off):
        if self.x is None:
            return
        for k in range(5):                             # rocas que salen del suelo
            xx = int(self.x - self.dir * k * 16 + off[0])
            alto = max(0, 34 - k * 7) + random.randint(-2, 2)
            pygame.draw.polygon(p, (150, 120, 90), [(xx - 9, C.SUELO + off[1]), (xx, C.SUELO - alto + off[1]),
                                                    (xx + 9, C.SUELO + off[1])])
            pygame.draw.polygon(p, (24, 18, 36), [(xx - 9, C.SUELO + off[1]), (xx, C.SUELO - alto + off[1]),
                                                  (xx + 9, C.SUELO + off[1])], 2)


TIPOS = {"ONDA PIXEL": Proyectil, "DRAGON ROJO": BolaFuego, "RAYO FACIAL": RayoFacial,
         "PUNO ESTELAR": PunoEstelar, "TURBO COMBO": TurboCombo,
         "TORMENTA LUNAR": TormentaLunar, "GOLPE SISMICO": GolpeSismico}


def crear(autor, rival, pelea):
    return TIPOS.get(autor.personaje.especial, Proyectil)(autor, rival, pelea)
