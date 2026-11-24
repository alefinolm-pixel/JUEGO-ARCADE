"""Luchador: fisica, golpes con anticipacion, bloqueo, empuje, poses animadas."""
import math

import pygame

import avatar
import config as C
import especiales
import sonido

CTRL_P1 = {"izquierda": pygame.K_a, "derecha": pygame.K_d, "salto": pygame.K_w,
           "golpe": pygame.K_f, "especial": pygame.K_g}
CTRL_P2 = {"izquierda": pygame.K_LEFT, "derecha": pygame.K_RIGHT, "salto": pygame.K_UP,
           "golpe": pygame.K_k, "especial": pygame.K_l}
# Jugador humano en modo arcade: vale el joystick (WASD+F/G) y tambien las flechas (+K/L)
CTRL_JUGADOR = {"izquierda": (pygame.K_a, pygame.K_LEFT), "derecha": (pygame.K_d, pygame.K_RIGHT),
                "salto": (pygame.K_w, pygame.K_UP), "golpe": (pygame.K_f, pygame.K_k),
                "especial": (pygame.K_g, pygame.K_l)}


def pulsada(teclas, k):
    """teclas[k] admitiendo una tecla o una tupla de teclas equivalentes."""
    return any(teclas[x] for x in k) if isinstance(k, tuple) else teclas[k]


def es_tecla(codigo, k):
    return codigo in k if isinstance(k, tuple) else codigo == k

T_GOLPE = 290           # duracion total del punyetazo (ms)
T_CARGA = 75            # anticipacion (brazo atras) -> luego sale el golpe
T_ACTIVO = 200          # hasta aqui el brazo sigue extendido


def superficie_personaje(pj, direccion, escala=None, pose="reposo0"):
    """Imagen del personaje para menus (nitida, ampliacion entera)."""
    return pj.avatar.retrato(escala or C.ESCALA, pose, direccion)


class Luchador:
    def __init__(self, x, personaje, direccion, controles, etiqueta="P1", tema=None,
                 color_espada=(80, 200, 255)):
        self.x_inicial = x
        self.personaje = personaje
        self.tema = tema
        self.espada = tema == "espacio"
        self.color_espada = color_espada
        self.av = personaje.avatar_tema(tema, color_espada)   # aspecto segun el escenario
        self.direccion = direccion
        self.direccion_inicial = direccion
        self.controles = controles
        self.etiqueta = etiqueta
        self.rival = None
        self.reiniciar()

    # ------------------------------------------------------------------ estado
    def reiniciar(self):
        st = self.personaje.stats
        cu = avatar.CUERPOS[self.personaje.cuerpo]
        ancho = (cu["tw"] + 12) * C.ESCALA
        alto = (cu["ph"] + cu["th"] + 18) * C.ESCALA
        self.rect = pygame.Rect(0, 0, ancho, alto)
        self.rect.midbottom = (self.x_inicial, C.SUELO)
        self.x = float(self.rect.centerx)
        self.direccion = self.direccion_inicial
        self.vida = self.vida_max = st["vida"]
        self.vida_visual = float(self.vida)          # barra "fantasma" que baja despacio
        self.velocidad, self.dano_golpe = st["velocidad"], st["golpe"]
        self.fuerza_salto = st["salto"] * (C.ESCALA / 2) ** 0.5    # salto proporcional al tamano
        self.vx = self.vy = 0.0
        self.en_suelo = True
        self.t_ataque = 0
        self.golpe_hecho = False
        self.t_golpeado = 0
        self.t_golpeado_max = 1
        self.t_pose_especial = 0
        self.pose_especial = "especial"
        self.pose_forzada = None
        self.ultimo_especial = -especiales.COOLDOWN
        self.dash = 0
        self.fantasmas = []
        self.andando = False
        self.atras = False
        self.t_anim = 0
        self.aterrizaje = 0
        self.ganador = False
        self.t_ko = 0
        self.frame_actual = None
        self.pos_dibujo = (0, 0)

    @property
    def ko(self):
        return self.vida <= 0

    def ocupado(self):
        return self.t_golpeado > 0 or self.t_ataque > 0 or self.t_pose_especial > 0 or self.dash > 0

    def atacando(self):
        return self.t_ataque > 0 or self.t_pose_especial > 0 or self.dash > 0

    def bloqueando(self):
        """Bloquea si mantiene ATRAS, esta en el suelo y no esta haciendo otra cosa."""
        return self.atras and self.en_suelo and not self.ocupado() and not self.ko

    def carga_especial(self, ahora):
        return min(1.0, (ahora - self.ultimo_especial) / especiales.COOLDOWN)

    # ------------------------------------------------------------------ entrada
    def entrada(self, teclas, activo=True):
        self.andando = self.atras = False
        if not activo or self.ko or self.ocupado():
            return
        c = self.controles
        izq, der = pulsada(teclas, c["izquierda"]), pulsada(teclas, c["derecha"])
        self.atras = (izq and self.direccion == 1) or (der and self.direccion == -1)
        mov = (der - izq)
        if mov:
            factor = 0.7 if self.atras else 1.0                 # hacia atras se anda mas lento
            self.x += mov * self.velocidad * factor
            self.andando = True
        if pulsada(teclas, c["salto"]) and self.en_suelo:
            self.vy = -self.fuerza_salto
            self.vx = mov * 2.5
            self.en_suelo = False
            sonido.play("salto")

    def pedir_golpe(self):
        if self.ko or self.ocupado():
            return
        self.t_ataque = T_GOLPE
        self.golpe_hecho = False
        sonido.play("espada" if self.espada else "aire", 0.8)

    def pedir_especial(self, pelea):
        if self.ko or self.ocupado() or not self.en_suelo:
            return
        if self.carga_especial(pelea.reloj) < 1.0:
            return
        self.ultimo_especial = pelea.reloj
        atk = especiales.crear(self, self.rival, pelea)
        pelea.ataques.append(atk)
        self.t_pose_especial = atk.duracion_pose
        self.pose_especial = atk.pose
        pelea.fx.texto(self.rect.centerx, self.rect.y - 25, self.personaje.especial + "!",
                       self.personaje.color, 34, 900, -0.8)

    def zona_golpe(self, alcance=None):
        alcance = alcance or (31 + (12 if self.espada else 0)) * C.ESCALA     # la espada llega mas lejos
        y = self.rect.y + int(self.rect.height * 0.18)
        h = int(self.rect.height * 0.45)
        if self.direccion == 1:
            return pygame.Rect(self.rect.right - 6, y, alcance, h)
        return pygame.Rect(self.rect.left - alcance + 6, y, alcance, h)

    # ------------------------------------------------------------------ fisica
    def actualizar(self, dt, pelea):
        k = dt / 16.67
        self.t_anim += dt
        for nombre in ("t_ataque", "t_golpeado", "t_pose_especial", "dash", "aterrizaje"):
            setattr(self, nombre, max(0, getattr(self, nombre) - dt))
        if self.ko:
            self.t_ko += dt

        # empuje / embestida
        self.x += self.vx * k
        if self.dash <= 0:
            self.vx *= (0.80 if self.en_suelo else 0.97) ** k
            if abs(self.vx) < 0.1:
                self.vx = 0
        # gravedad
        self.vy += 0.8 * k
        self.rect.y += int(round(self.vy * k))
        if self.rect.bottom >= C.SUELO:
            self.rect.bottom = C.SUELO
            if not self.en_suelo:
                if self.vy > 5:
                    self.aterrizaje = 90
                    pelea.fx.polvo(self.rect.centerx, C.SUELO - 2, 6)
                self.en_suelo = True
            self.vy = 0
        # paredes
        medio = self.rect.width / 2
        if self.x < medio or self.x > C.ANCHO - medio:
            self.x = max(medio, min(C.ANCHO - medio, self.x))
            if abs(self.vx) > 4 and self.t_golpeado > 0:       # rebote contra la pared
                self.vx = -self.vx * 0.3
        self.rect.centerx = int(self.x)

        # punyetazo: sale tras la anticipacion
        if self.t_ataque > 0 and not self.golpe_hecho and T_GOLPE - self.t_ataque >= T_CARGA:
            self.golpe_hecho = True
            zona = self.zona_golpe()
            if zona.colliderect(self.rival.rect):
                x = self.rival.rect.centerx - self.direccion * self.rival.rect.width // 3
                pelea.impactar(self, self.rival, self.dano_golpe, x, zona.centery, 4.5, 1.0,
                               self.personaje.color)

        # vida que baja con retraso (barra blanca)
        if self.vida_visual > self.vida:
            self.vida_visual = max(self.vida, self.vida_visual - 0.06 * dt)

        for f in self.fantasmas:
            f[2] -= dt
        self.fantasmas = [f for f in self.fantasmas if f[2] > 0][-8:]

    def recibir(self, dano, empuje, direccion, aturdir):
        self.vida = max(0, self.vida - dano)
        self.vx = empuje * direccion
        self.t_golpeado = self.t_golpeado_max = aturdir
        self.t_ataque = 0
        self.t_pose_especial = 0
        self.dash = 0

    # ------------------------------------------------------------------ dibujo
    def pose(self):
        if self.ko:
            return "golpeado"
        if self.ganador:
            return "victoria"
        if self.pose_forzada:
            return self.pose_forzada
        if self.t_golpeado > 0:
            return "golpeado"
        if self.dash > 0:
            return "puno"
        if self.t_pose_especial > 0:
            return self.pose_especial
        if self.t_ataque > 0:
            t = T_GOLPE - self.t_ataque
            return "carga" if t < T_CARGA else "puno" if t < T_ACTIVO else "reposo0"
        if not self.en_suelo:
            return "salto"
        if self.atras and self.rival and self.rival.atacando() \
                and abs(self.rival.rect.centerx - self.rect.centerx) < 260:
            return "bloqueo"
        if self.andando:
            return "andar0" if (self.t_anim // 130) % 2 == 0 else "andar1"
        return "reposo0" if (self.t_anim // 450) % 2 == 0 else "reposo1"

    def dibujar(self, p, off=(0, 0)):
        av = self.av
        pose = self.pose()
        img = av.frame(pose, self.direccion)
        ex = C.ESCALA
        x0 = self.rect.centerx - av.pie_x(self.direccion)
        y0 = self.rect.bottom - avatar.FY * ex - ex

        if self.ko:                                         # cae de espaldas
            ang = min(90, self.t_ko / 3.5) * self.direccion
            img = pygame.transform.rotate(img, ang)
            r = img.get_rect(midbottom=(self.rect.centerx - self.direccion * 20,
                                        self.rect.bottom + int(min(90, self.t_ko / 3.5) / 3)))
            x0, y0 = r.topleft
        elif self.t_golpeado > 0 and self.t_golpeado > self.t_golpeado_max - 90:   # destello al recibir
            img = img.copy()
            img.fill((150, 150, 150, 0), special_flags=pygame.BLEND_RGB_ADD)
        elif self.aterrizaje > 0:                            # aplastado al caer
            w, h = img.get_size()
            img = pygame.transform.scale(img, (int(w * 1.08), int(h * 0.92)))
            x0 -= int(w * 0.04)
            y0 += int(h * 0.08)

        # sombra (se encoge al saltar)
        alto = max(0, C.SUELO - self.rect.bottom)
        sw = max(20, int(self.rect.width * 1.5 - alto * 0.25))
        sombra = pygame.Surface((sw, 12), pygame.SRCALPHA)
        pygame.draw.ellipse(sombra, (0, 0, 0, 110), sombra.get_rect())
        p.blit(sombra, (self.rect.centerx - sw // 2 + off[0], C.SUELO - 7 + off[1]))

        # estela de la embestida
        for f_img, (fx, fy), vida in self.fantasmas:
            g = f_img.copy()
            g.fill(self.personaje.color + (0,), special_flags=pygame.BLEND_RGB_MAX)
            g.set_alpha(int(150 * vida / 160))
            p.blit(g, (fx + off[0], fy + off[1]))

        p.blit(img, (x0 + off[0], y0 + off[1]))
        self.frame_actual, self.pos_dibujo = img, (x0, y0)

        # tajo de la espada de energia
        if self.espada and pose == "puno" and self.t_ataque > 0 and not self.ko:
            t = (T_GOLPE - self.t_ataque - T_CARGA) / (T_ACTIVO - T_CARGA)
            if 0 <= t <= 1:
                cx = self.rect.centerx + self.direccion * 20 * C.ESCALA + off[0]
                cy = self.rect.y + int(self.rect.height * 0.35) + off[1]
                r = 30 * C.ESCALA
                caja = pygame.Rect(cx - r, cy - r, 2 * r, 2 * r)
                a0 = -1.2 if self.direccion == 1 else math.pi - 0.3
                capa = pygame.Surface((C.ANCHO, C.ALTO), pygame.SRCALPHA)
                for k, (g, alfa) in enumerate(((14, 70), (8, 140), (3, 255))):
                    col = (255, 255, 255) if k == 2 else self.color_espada
                    pygame.draw.arc(capa, col + (int(alfa * (1 - t)),), caja, a0, a0 + 1.5, g)
                p.blit(capa, (0, 0))
        # trazo del punyetazo
        elif pose == "puno" and self.t_ataque > 0 and not self.ko:
            z = self.zona_golpe()
            cx = z.centerx + self.direccion * 8 + off[0]
            cy = self.rect.y + int(self.rect.height * 0.32) + off[1]
            for k in range(3):
                yy = cy - 10 + k * 10
                pygame.draw.line(p, (255, 255, 255), (cx - self.direccion * (40 - k * 6), yy),
                                 (cx - self.direccion * (12 + k * 4), yy), 3)

        # marcador P1/P2 encima de la cabeza
        if not self.ko:
            col = (230, 40, 50) if self.etiqueta == "P1" else (40, 110, 245)
            alto_casco = 13 * C.ESCALA if self.espada else 0        # por encima de las antenas
            tx = self.rect.centerx + off[0]
            ty = self.rect.y - 14 - alto_casco + off[1] + int(2 * math.sin(self.t_anim / 200))
            pygame.draw.polygon(p, col, [(tx - 7, ty - 8), (tx + 7, ty - 8), (tx, ty)])
