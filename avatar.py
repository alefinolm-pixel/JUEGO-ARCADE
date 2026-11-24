"""Munyeco pixel-art dibujado a partir de los RASGOS de la cara + CUERPO + TRAJE.

  rasgos  -> piel, pelo (color, largo, tipo, peinado, flequillo), gafas, barba, ojos,
             accesorio, expresion, color de la ropa  (vienen de rasgos.py)
  cuerpo  -> agil | equilibrado | fuerte   (cambia proporciones Y estadisticas)
  traje   -> karate | boxeo | ninja | calle

Se dibuja por capas (brazo/pierna/pelo trasero, cuerpo+cabeza, brazo delantero),
cada capa con su contorno oscuro, en una rejilla de 80x100 y se amplia x ESCALA
sin suavizar: pixel art nitido, no una foto pixelada.

Cada luchador tiene POSES (reposo, andar, punyo, especial, golpeado, bloqueo,
salto, victoria) para que los ataques se VEAN.
"""
import numpy as np
import pygame

import config as C
from rasgos import hex_a_rgb

W, H = 112, 100         # rejilla logica (ancha para que quepa la espada de energia)
CX, FY = 34, 98         # centro del cuerpo y linea de los pies
CONTORNO = (24, 18, 36)

CUERPOS = {
    #              ancho torso, alto torso, brazo, pierna(ancho, alto), punyo
    "agil":        dict(tw=14, th=19, br=4, pw=5, ph=25, pu=5),
    "equilibrado": dict(tw=18, th=21, br=5, pw=6, ph=22, pu=6),
    "fuerte":      dict(tw=25, th=22, br=7, pw=8, ph=20, pu=8),
}
# Estadisticas que dependen del cuerpo: el cuerpo no es solo estetico
STATS = {
    "agil":        dict(vida=90,  velocidad=6.3, salto=17.5, golpe=6, nombre="AGIL"),
    "equilibrado": dict(vida=100, velocidad=5.2, salto=16.0, golpe=7, nombre="EQUILIBRADO"),
    "fuerte":      dict(vida=118, velocidad=4.2, salto=14.5, golpe=9, nombre="FUERTE"),
}
TRAJES = ["karate", "boxeo", "ninja", "calle"]
# especial por defecto segun traje (con gafas -> RAYO FACIAL, sale de las gafas!)
ESPECIAL_TRAJE = {"karate": "ONDA PIXEL", "boxeo": "PUNO ESTELAR",
                  "ninja": "TORMENTA LUNAR", "calle": "TURBO COMBO"}

POSES = {
    "reposo0": dict(dx=0, dy=0, de="guardia", tr="guardia", pi="quieto"),
    "reposo1": dict(dx=0, dy=1, de="guardia", tr="guardia", pi="quieto"),
    "andar0":  dict(dx=1, dy=0, de="guardia", tr="guardia", pi="paso_a"),
    "andar1":  dict(dx=1, dy=1, de="guardia", tr="guardia", pi="paso_b"),
    "carga":   dict(dx=-2, dy=1, de="atras", tr="guardia", pi="abiertas"),
    "puno":    dict(dx=3, dy=0, de="puno", tr="atras", pi="abiertas", cara="grito"),
    "especial": dict(dx=2, dy=1, de="empuje", tr="empuje", pi="abiertas", cara="grito"),
    "golpeado": dict(dx=-4, dy=2, de="suelto", tr="suelto", pi="quieto", cara="dolor"),
    "bloqueo": dict(dx=-1, dy=2, de="bloqueo", tr="bloqueo", pi="abiertas", cara="seria"),
    "salto":   dict(dx=0, dy=-3, de="guardia", tr="guardia", pi="salto"),
    "victoria": dict(dx=0, dy=0, de="arriba", tr="guardia", pi="quieto", cara="sonrisa"),
}


# ------------------------------------------------------------------ utilidades
def _osc(c, f=0.72):
    return tuple(max(0, int(v * f)) for v in c[:3])


def _cla(c, f=1.25, suma=20):
    return tuple(min(255, int(v * f) + suma) for v in c[:3])


def _rect(s, c, x, y, w, h, sombra=True, r=0):
    """Rectangulo con sombra en el lado de atras y brillo arriba (aspecto 16 bits)."""
    x, y, w, h = int(x), int(y), int(w), int(h)
    if w <= 0 or h <= 0:
        return
    pygame.draw.rect(s, c, (x, y, w, h), border_radius=r)
    if sombra and w > 3 and h > 3:
        pygame.draw.rect(s, _osc(c), (x, y + (r // 2), 2, h - r))
        pygame.draw.rect(s, _cla(c, 1.1, 18), (x + 2, y, w - 2 - r // 2, 1))


def _miembro(s, c, p0, p1, g):
    """Brazo/pierna: segmento grueso con extremos cuadrados."""
    (x0, y0), (x1, y1) = p0, p1
    v = np.array([x1 - x0, y1 - y0], float)
    n = np.linalg.norm(v)
    if n < 1e-3:
        pygame.draw.rect(s, c, (x0 - g // 2, y0 - g // 2, g, g))
        return
    perp = np.array([-v[1], v[0]]) / n * (g / 2)
    pts = [(x0 + perp[0], y0 + perp[1]), (x1 + perp[0], y1 + perp[1]),
           (x1 - perp[0], y1 - perp[1]), (x0 - perp[0], y0 - perp[1])]
    pygame.draw.polygon(s, c, pts)
    pygame.draw.circle(s, c, (x0, y0), g // 2)
    pygame.draw.circle(s, c, (x1, y1), g // 2)


def _contorno(s, color=CONTORNO):
    """Anyade un contorno de 1 px alrededor de todo lo dibujado en la capa."""
    alfa = pygame.surfarray.array_alpha(s) > 0
    borde = np.zeros_like(alfa)
    borde[1:, :] |= alfa[:-1, :]
    borde[:-1, :] |= alfa[1:, :]
    borde[:, 1:] |= alfa[:, :-1]
    borde[:, :-1] |= alfa[:, 1:]
    borde &= ~alfa
    if borde.any():
        px = pygame.surfarray.pixels3d(s)
        pa = pygame.surfarray.pixels_alpha(s)
        px[borde] = color
        pa[borde] = 255
        del px, pa


# ------------------------------------------------------------------ paleta
def paleta(rasgos, traje):
    piel = hex_a_rgb(rasgos["piel"])
    ropa = hex_a_rgb(rasgos["ropa_color"])
    # ropa casi blanca/negra/gris -> le damos un poco de color para que luzca en pantalla
    if max(ropa) - min(ropa) < 25:
        ropa = ropa if 60 < sum(ropa) / 3 < 200 else (70, 90, 200) if sum(ropa) < 180 else (220, 220, 230)
    pal = dict(piel=piel, piel_osc=_osc(piel, 0.8), pelo=hex_a_rgb(rasgos["pelo_color"]),
               ojos=hex_a_rgb(rasgos["ojos_color"]), gafas=hex_a_rgb(rasgos["gafas_color"]),
               acc=hex_a_rgb(rasgos["accesorio_color"]), ropa=ropa, blanco=(245, 245, 245))
    if traje == "karate":
        pal.update(torso=ropa, manga=ropa, brazo=piel, guante=(240, 240, 240),
                   pantalon=ropa, bota=_osc(ropa, 0.45), cinturon=(30, 26, 36))
    elif traje == "boxeo":
        pal.update(torso=ropa, manga=piel, brazo=piel, guante=(220, 35, 45),
                   pantalon=_osc(ropa, 0.8), bota=(150, 25, 35), cinturon=(245, 245, 245))
    elif traje == "ninja":
        oscuro = _osc(ropa, 0.35)
        pal.update(torso=oscuro, manga=oscuro, brazo=oscuro, guante=_osc(ropa, 0.6),
                   pantalon=oscuro, bota=(30, 28, 40), cinturon=ropa)
    else:  # calle
        pal.update(torso=ropa, manga=ropa, brazo=ropa, guante=piel,
                   pantalon=(55, 85, 150), bota=(240, 240, 240), cinturon=_osc(ropa, 0.6))
    return pal


# ------------------------------------------------------------------ partes
def _brazo_puntos(modo, sx, sy, lado):
    """Codo y mano relativos al hombro. lado = 1 (delantero) o 0 (trasero)."""
    m = {
        "guardia": ((3, 9), (9, 1)) if lado else ((5, 9), (11, 3)),
        "puno":    ((8, 1), (19, 0)),
        "atras":   ((-5, 6), (-2, 1)),
        "empuje":  ((7, 4), (15, 2)) if lado else ((6, 6), (14, 5)),
        "suelto":  ((-2, 8), (-5, 15)),
        "bloqueo": ((7, 8), (8, -4)) if lado else ((6, 9), (9, -1)),
        "arriba":  ((2, -7), (3, -16)),
    }[modo]
    (ex, ey), (hx, hy) = m
    return (sx + ex, sy + ey), (sx + hx, sy + hy)


def _brazo(s, pal, cu, modo, hombro, lado, traje):
    codo, mano = _brazo_puntos(modo, *hombro, lado)
    br = cu["br"]
    _miembro(s, pal["manga"], hombro, codo, br + 1)
    _miembro(s, pal["brazo"], codo, mano, br)
    if traje == "karate":               # manga del gi hasta el codo
        _miembro(s, pal["manga"], hombro, ((hombro[0] + codo[0]) // 2 + (codo[0] - hombro[0]) // 3,
                                            (hombro[1] + codo[1]) // 2 + (codo[1] - hombro[1]) // 3), br + 2)
    pu = cu["pu"] + (3 if traje == "boxeo" else 0)
    _rect(s, pal["guante"], mano[0] - pu // 2, mano[1] - pu // 2, pu, pu, r=2)
    if traje in ("karate", "ninja"):    # venda de la munyeca
        pygame.draw.rect(s, _osc(pal["guante"], 0.85), (mano[0] - pu // 2, mano[1] + pu // 2 - 1, pu, 2))
    return mano


def _piernas(pi):
    """Desplazamiento x de pie (trasero, delantero) y flexion."""
    return {"quieto": (-3, 3, 0), "paso_a": (-6, 7, 0), "paso_b": (1, 0, 0),
            "abiertas": (-6, 7, 0), "salto": (-4, 5, 9)}[pi]


def _pierna(s, pal, cu, cadera, pie_x, flex, traje):
    hx, hy = cadera
    pie_y = FY - 4 - flex
    rodilla = ((hx + pie_x) // 2 + (3 if flex else 0), (hy + pie_y) // 2 - (flex // 2))
    _miembro(s, pal["pantalon"], cadera, rodilla, cu["pw"] + 1)
    _miembro(s, pal["pantalon"], rodilla, (pie_x, pie_y), cu["pw"])
    bota_w = cu["pw"] + 4
    alto = 6 if traje == "boxeo" else 4
    _rect(s, pal["bota"], pie_x - cu["pw"] // 2, pie_y - alto + 4, bota_w, alto, r=1)
    if traje == "calle":
        pygame.draw.rect(s, pal["ropa"], (pie_x - cu["pw"] // 2 + 1, pie_y + 1, bota_w - 2, 1))
    if traje == "boxeo":
        pygame.draw.rect(s, pal["blanco"], (pie_x - cu["pw"] // 2, pie_y - 2, bota_w, 1))


def _pelo_trasero(s, ra, pal, hx, hy, hw, hh, torso_top):
    """Pelo que queda DETRAS de la cabeza y del cuerpo (melena, coleta, afro...)."""
    c = pal["pelo"]
    largo, tipo, peinado = ra["pelo_largo"], ra["pelo_tipo"], ra["peinado"]
    if largo in ("calvo", "rapado"):
        return
    if tipo == "afro":
        r = hw // 2 + 6
        pygame.draw.circle(s, c, (hx + hw // 2 - 1, hy + hh // 2 - 3), r)
        return
    if peinado == "coleta":
        _miembro(s, c, (hx + 1, hy + 6), (hx - 5, hy + hh + (10 if largo == "largo" else 3)), 5)
        return
    if peinado == "trenzas":
        for k in (0, 4):
            for j in range(4):
                pygame.draw.circle(s, c, (hx + 1 + k - j, hy + hh - 2 + j * 4), 2)
        return
    if peinado == "mono":
        pygame.draw.circle(s, c, (hx + 5, hy - 1), 5)
        return
    if largo == "medio":
        _rect(s, c, hx - 2, hy + 2, hw - 6, hh + 2, r=4)
    elif largo == "largo":
        fin = torso_top + 17
        _rect(s, c, hx - 5, hy + 1, hw - 4, fin - hy, r=4)
        pygame.draw.polygon(s, c, [(hx - 5, fin - 4), (hx - 7, fin + 2), (hx + 4, fin)])  # puntas
        if tipo in ("ondulado", "rizado"):
            for k in range(hy + 8, fin, 5):
                pygame.draw.circle(s, c, (hx - 5, k), 3)
    if tipo == "rizado" and largo != "corto":
        for k in range(0, hw - 4, 5):
            pygame.draw.circle(s, c, (hx + k, hy + hh + 1), 3)


def _cabeza(s, ra, pal, hx, hy, hw, hh, cara):
    """Cara mirando a la derecha (3/4): ojos desplazados hacia delante."""
    piel, pelo = pal["piel"], pal["pelo"]
    _rect(s, piel, hx, hy, hw, hh, r=6)
    pygame.draw.rect(s, piel, (hx + hw - 1, hy + 11, 2, 3))                  # nariz (perfil)
    pygame.draw.rect(s, pal["piel_osc"], (hx + hw - 3, hy + 12, 1, 2))
    pygame.draw.rect(s, pal["piel_osc"], (hx + 4, hy + 9, 3, 5))             # oreja
    pygame.draw.rect(s, piel, (hx + 5, hy + 10, 1, 3))
    if ra["accesorio"] == "pendientes":
        pygame.draw.rect(s, pal["acc"], (hx + 5, hy + 15, 2, 2))

    # ---- ojos y cejas
    ey = hy + 9
    ojos = (hx + hw - 7, hx + hw - 14)
    oscuro = _osc(pelo, 0.6) if sum(pelo) > 120 else pelo
    for ox in ojos:
        if cara == "dolor":
            pygame.draw.line(s, CONTORNO, (ox - 1, ey - 1), (ox + 2, ey + 1))
            pygame.draw.line(s, CONTORNO, (ox - 1, ey + 3), (ox + 2, ey + 1))
        else:
            pygame.draw.rect(s, (250, 250, 250), (ox - 1, ey - 1, 4, 4))
            pygame.draw.rect(s, pal["ojos"], (ox + 1, ey, 2, 3))
            pygame.draw.rect(s, (15, 12, 20), (ox + 2, ey, 1, 2))
        ceja_y = ey - 3 - (1 if cara == "grito" else 0)
        if cara in ("grito", "seria"):                                       # ceno fruncido
            pygame.draw.line(s, oscuro, (ox - 1, ceja_y - 1), (ox + 3, ceja_y + 1))
        else:
            pygame.draw.rect(s, oscuro, (ox - 1, ceja_y, 4, 1))

    # ---- gafas
    if ra["gafas"] != "no":
        g = pal["gafas"]
        for ox in ojos:
            if ra["gafas"] == "sol":
                pygame.draw.rect(s, (20, 20, 30), (ox - 2, ey - 2, 6, 5))
                pygame.draw.rect(s, (120, 140, 200), (ox + 2, ey - 1, 1, 1))
            else:
                pygame.draw.rect(s, g, (ox - 2, ey - 2, 6, 6), 1)
        pygame.draw.line(s, g, (ojos[1] + 4, ey), (ojos[0] - 2, ey))             # puente
        pygame.draw.line(s, g, (ojos[1] - 2, ey), (hx + 6, ey - 1))              # patilla

    # ---- boca
    my = hy + hh - 5
    mx = hx + hw - 9
    if cara == "grito":
        pygame.draw.rect(s, (120, 20, 30), (mx, my - 1, 4, 3))
        pygame.draw.rect(s, (250, 250, 250), (mx, my - 1, 4, 1))
    elif cara == "dolor":
        pygame.draw.line(s, (120, 30, 40), (mx, my + 1), (mx + 3, my))
    elif ra["expresion"] == "sonrisa" or cara == "sonrisa":
        pygame.draw.rect(s, (130, 40, 50), (mx, my, 4, 1))
        pygame.draw.rect(s, (130, 40, 50), (mx + 4, my - 1, 1, 1))
        pygame.draw.rect(s, (130, 40, 50), (mx - 1, my - 1, 1, 1))
    else:
        pygame.draw.rect(s, (130, 40, 50), (mx, my, 4, 1))

    # ---- barba
    b = ra["barba"]
    if b == "bigote":
        pygame.draw.rect(s, pelo, (mx - 1, my - 2, 6, 2))
    elif b == "perilla":
        pygame.draw.rect(s, pelo, (mx, my + 2, 4, 3))
    elif b in ("corta", "larga"):
        extra = 5 if b == "larga" else 0
        pts = [(hx + 6, hy + 12), (hx + hw, hy + 13), (hx + hw, hy + hh - 2),
               (hx + hw - 5, hy + hh + extra), (hx + 9, hy + hh + extra // 2), (hx + 5, hy + hh - 4)]
        pygame.draw.polygon(s, pelo, pts)
        pygame.draw.rect(s, piel, (mx - 1, my - 1, 6, 3))                  # hueco de la boca
        pygame.draw.rect(s, (130, 40, 50), (mx, my, 4, 1))

    # ---- pelo por encima
    largo, tipo = ra["pelo_largo"], ra["pelo_tipo"]
    if largo == "rapado":
        pygame.draw.rect(s, _osc(pelo, 0.9), (hx + 1, hy, hw - 2, 3), border_radius=2)
    elif largo != "calvo" and tipo != "afro":
        _rect(s, pelo, hx - 1, hy - 2, hw + 2, 6, r=3)                       # casquete
        _rect(s, pelo, hx - 1, hy, 8, 9 if largo == "corto" else 13, r=2)    # nuca/lado
        if largo == "largo" and ra["peinado"] == "suelto":                   # mechon sobre el hombro
            _rect(s, pelo, hx + 1, hy + 6, 5, hh + 4, r=2)
            pygame.draw.rect(s, _osc(pelo, 0.8), (hx + 3, hy + 9, 1, hh - 2))
        if ra["flequillo"]:
            for k in range(0, hw - 6, 3):
                pygame.draw.rect(s, pelo, (hx + 6 + k, hy + 2, 3, 3 + (k // 3) % 2 * 2))
        else:
            pygame.draw.rect(s, pelo, (hx + hw - 8, hy + 2, 6, 2))          # mechon
        if tipo == "rizado":
            for k in range(0, hw + 1, 4):
                pygame.draw.circle(s, pelo, (hx + k, hy - 1), 3)
        if ra["peinado"] == "cresta":
            for k in range(3):
                pygame.draw.polygon(s, pelo, [(hx + 4 + k * 5, hy - 1), (hx + 7 + k * 5, hy - 8 + k),
                                              (hx + 10 + k * 5, hy - 1)])
    elif tipo == "afro" and largo != "calvo":
        pygame.draw.ellipse(s, pelo, (hx - 3, hy - 7, hw + 6, 13))

    # ---- accesorios
    a, ac = ra["accesorio"], pal["acc"]
    if a == "gorra":
        _rect(s, ac, hx - 1, hy - 4, hw + 1, 7, r=3)
        pygame.draw.rect(s, _osc(ac), (hx + hw - 3, hy + 1, 8, 2))
    elif a == "gorro":
        _rect(s, ac, hx - 2, hy - 6, hw + 3, 9, r=4)
        pygame.draw.rect(s, _osc(ac), (hx - 2, hy + 1, hw + 3, 2))
    elif a == "diadema":
        pygame.draw.rect(s, ac, (hx, hy + 1, hw, 2))
    elif a == "lazo":
        pygame.draw.polygon(s, ac, [(hx + 3, hy - 1), (hx - 3, hy - 5), (hx - 3, hy + 3)])
        pygame.draw.polygon(s, ac, [(hx + 3, hy - 1), (hx + 9, hy - 5), (hx + 9, hy + 3)])
        pygame.draw.rect(s, _osc(ac), (hx + 2, hy - 2, 3, 3))


def _torso(s, pal, cu, traje, tx, ty, tw, th):
    c = pal["torso"]
    if traje == "calle":                                      # capucha detras del cuello
        _rect(s, _osc(c, 0.85), tx + 1, ty - 4, tw - 6, 6, r=2)
    _rect(s, c, tx, ty, tw, th, r=3)
    if traje == "karate":
        pygame.draw.polygon(s, pal["piel"], [(tx + tw // 2 - 2, ty), (tx + tw - 2, ty), (tx + tw - 4, ty + 8)])
        pygame.draw.line(s, _cla(c), (tx + tw // 2 - 2, ty), (tx + tw - 4, ty + 9))
        pygame.draw.rect(s, pal["cinturon"], (tx, ty + th - 4, tw, 3))
        pygame.draw.rect(s, pal["cinturon"], (tx + tw - 6, ty + th - 2, 2, 4))
    elif traje == "boxeo":
        pygame.draw.rect(s, pal["piel"], (tx + 2, ty, 3, 4))
        pygame.draw.rect(s, pal["piel"], (tx + tw - 5, ty, 3, 4))
        pygame.draw.rect(s, pal["cinturon"], (tx, ty + th - 4, tw, 3))
    elif traje == "ninja":
        bu = pal["ropa"]                                      # bufanda
        pygame.draw.rect(s, bu, (tx - 1, ty, tw + 2, 4))
        pygame.draw.rect(s, bu, (tx, ty + th - 4, tw, 3))
        pygame.draw.line(s, _cla(c, 1.6, 25), (tx + tw - 4, ty + 5), (tx + tw - 8, ty + th - 5))
    else:
        pygame.draw.rect(s, _osc(c, 0.85), (tx + 3, ty + th - 8, tw - 6, 5))   # bolsillo
        pygame.draw.line(s, pal["blanco"], (tx + tw - 5, ty + 1), (tx + tw - 5, ty + 6))
        pygame.draw.line(s, pal["blanco"], (tx + tw - 8, ty + 1), (tx + tw - 8, ty + 5))


# ------------------------------------------------------------------ tema espacio
# direccion de la hoja segun la postura del brazo delantero
_DIR_ESPADA = {"guardia": (0.45, -0.9), "puno": (1.0, 0.05), "atras": (-0.55, -0.85),
               "empuje": (0.92, -0.38), "suelto": (0.25, 0.97), "bloqueo": (0.12, -1.0),
               "arriba": (0.15, -1.0)}
LARGO_ESPADA = 27


def _espada(s, mano, modo, color):
    """Espada de energia: empunadura metalica + hoja con nucleo blanco y halo."""
    dx, dy = _DIR_ESPADA.get(modo, (0.45, -0.9))
    n = (dx * dx + dy * dy) ** 0.5
    dx, dy = dx / n, dy / n
    x0, y0 = mano[0] + dx * 3, mano[1] + dy * 3
    x1, y1 = x0 + dx * LARGO_ESPADA, y0 + dy * LARGO_ESPADA
    halo = tuple(min(255, c // 2 + 20) for c in color)
    pygame.draw.line(s, halo + (110,), (x0, y0), (x1, y1), 7)          # resplandor
    pygame.draw.line(s, color + (255,), (x0, y0), (x1, y1), 4)
    pygame.draw.line(s, (255, 255, 255, 255), (x0, y0), (x1, y1), 2)  # nucleo
    hx, hy = mano[0] - dx * 3, mano[1] - dy * 3                        # empunadura
    pygame.draw.line(s, (60, 60, 70, 255), (hx, hy), (x0, y0), 4)
    pygame.draw.line(s, (200, 200, 215, 255), (hx, hy), (x0, y0), 2)


def _casco(s, hx, hy, hw, hh, color):
    """Casco de explorador alien: cupula de cristal alargada, antenas y aletas."""
    metal, osc = (150, 165, 185), (80, 90, 110)
    for lado in (-1, 1):                                               # aletas laterales
        bx = hx - 3 if lado < 0 else hx + hw + 3
        pygame.draw.polygon(s, color, [(bx, hy + 8), (bx + 6 * lado, hy - 2), (bx + 2 * lado, hy + 14)])
    pygame.draw.line(s, osc, (hx + 6, hy - 9), (hx + 1, hy - 19), 2)    # antenas
    pygame.draw.line(s, osc, (hx + hw - 5, hy - 9), (hx + hw + 1, hy - 18), 2)
    for ax, ay in ((hx + 1, hy - 20), (hx + hw + 1, hy - 19)):
        pygame.draw.circle(s, color, (ax, ay), 3)
        pygame.draw.rect(s, (255, 255, 255), (ax - 1, ay - 1, 1, 1))
    cupula = pygame.Surface((hw + 10, hh + 16), pygame.SRCALPHA)       # cristal (deja ver la cara)
    pygame.draw.ellipse(cupula, (170, 235, 255, 55), cupula.get_rect())
    pygame.draw.ellipse(cupula, (210, 245, 255, 200), cupula.get_rect(), 1)
    pygame.draw.arc(cupula, (255, 255, 255, 230), (3, 3, hw - 2, hh), 1.7, 2.9, 2)   # brillo
    s.blit(cupula, (hx - 5, hy - 11))
    pygame.draw.rect(s, metal, (hx - 3, hy + hh - 2, hw + 6, 4), border_radius=2)   # cuello
    pygame.draw.rect(s, color, (hx + 3, hy + hh - 1, 4, 2))
    pygame.draw.rect(s, color, (hx + hw - 7, hy + hh - 1, 4, 2))


def dibujar_pose(rasgos, cuerpo, traje, pose, tema=None, color_espada=(80, 200, 255)):
    """Devuelve Surface (W x H) de la pose, mirando a la derecha, a escala 1.
    tema='espacio' anyade casco alien y espada de energia."""
    cu = CUERPOS.get(cuerpo, CUERPOS["equilibrado"])
    pal = paleta(rasgos, traje)
    po = POSES[pose]
    dx, dy = po["dx"], po["dy"]
    cara = po.get("cara", "normal")
    tw, th = cu["tw"], cu["th"]
    fx_tr, fx_de, flex = _piernas(po["pi"])

    cadera_y = FY - cu["ph"] + dy + flex
    tx, ty = CX + dx - tw // 2, cadera_y + 2 - th
    hw, hh = 22, 21
    hx, hy = CX + dx - hw // 2 + 2, ty - hh + 3
    hombro_de = (tx + tw - 3, ty + 4)
    hombro_tr = (tx + 4, ty + 4)

    capas = []
    # 1) trasera: pelo largo, bufanda, brazo y pierna de atras
    s = pygame.Surface((W, H), pygame.SRCALPHA)
    _pelo_trasero(s, rasgos, pal, hx, hy, hw, hh, ty)
    if traje == "ninja":
        cola = 6 if pose in ("andar0", "andar1", "especial", "salto") else 2
        _miembro(s, pal["ropa"], (tx + 2, ty + 2), (tx - 12, ty + 4 + cola), 3)
        _miembro(s, pal["ropa"], (tx + 2, ty + 2), (tx - 10, ty + 9 + cola), 3)
    _pierna(s, pal, cu, (CX - 3 + dx // 2, cadera_y), CX + fx_tr, flex, traje)
    _brazo(s, _sombrear(pal), cu, po["tr"], hombro_tr, 0, traje)
    capas.append(s)
    # 2) cuerpo: pierna delantera, torso, cabeza
    s = pygame.Surface((W, H), pygame.SRCALPHA)
    _pierna(s, pal, cu, (CX + 3 + dx // 2, cadera_y), CX + fx_de, flex, traje)
    _torso(s, pal, cu, traje, tx, ty, tw, th)
    capas.append(s)
    s = pygame.Surface((W, H), pygame.SRCALPHA)
    _cabeza(s, rasgos, pal, hx, hy, hw, hh, cara)
    if tema == "espacio":
        _casco(s, hx, hy, hw, hh, color_espada)
    capas.append(s)
    # 3) brazo delantero (por encima de todo)
    s = pygame.Surface((W, H), pygame.SRCALPHA)
    mano = _brazo(s, pal, cu, po["de"], hombro_de, 1, traje)
    capas.append(s)

    final = pygame.Surface((W, H), pygame.SRCALPHA)
    for capa in capas:
        _contorno(capa)
        final.blit(capa, (0, 0))
    if tema == "espacio":                       # la espada brilla: sin contorno oscuro
        _espada(final, mano, po["de"], color_espada)
    return final


def _sombrear(pal):
    """Lo que esta detras se ve un poco mas oscuro: da profundidad."""
    return {k: (_osc(v, 0.82) if isinstance(v, tuple) else v) for k, v in pal.items()}


# ------------------------------------------------------------------ clase de alto nivel
class Avatar:
    """Todas las poses ya dibujadas, ampliadas y volteadas (cache)."""

    def __init__(self, rasgos, cuerpo="equilibrado", traje="karate", escala=None,
                 tema=None, color_espada=(80, 200, 255)):
        self.rasgos, self.cuerpo, self.traje = rasgos, cuerpo, traje
        self.tema, self.color_espada = tema, color_espada
        self.escala = escala or C.ESCALA
        self._frames = {}
        self._retratos = {}

    def frame(self, pose, direccion=1):
        clave = (pose, direccion)
        if clave not in self._frames:
            base = dibujar_pose(self.rasgos, self.cuerpo, self.traje, pose, self.tema, self.color_espada)
            img = pygame.transform.scale(base, (W * self.escala, H * self.escala))
            if direccion == -1:
                img = pygame.transform.flip(img, True, False)
            self._frames[clave] = img
        return self._frames[clave]

    def retrato(self, escala, pose="reposo0", direccion=1):
        """Version grande para menus (sigue nitida: ampliacion entera sin suavizar)."""
        clave = (escala, pose, direccion)
        if clave not in self._retratos:
            base = dibujar_pose(self.rasgos, self.cuerpo, self.traje, pose, self.tema, self.color_espada)
            img = pygame.transform.scale(base, (W * escala, H * escala))
            self._retratos[clave] = pygame.transform.flip(img, True, False) if direccion == -1 else img
        return self._retratos[clave]

    @staticmethod
    def pie_x(direccion, escala=None):
        """Posicion x (en la imagen ampliada) del centro del cuerpo."""
        e = escala or C.ESCALA
        return CX * e if direccion == 1 else (W - CX) * e


def caja_cabeza(cuerpo):
    """Rectangulo (rejilla logica) que contiene la cabeza en la pose de reposo."""
    cu = CUERPOS.get(cuerpo, CUERPOS["equilibrado"])
    ty = FY - cu["ph"] + 2 - cu["th"]
    hy = ty - 21 + 3
    return pygame.Rect(CX - 15, hy - 8, 34, 32)


def cabeza(av, escala=2):
    """Retrato de la cabeza para el marcador de vida (cacheado en el Avatar)."""
    clave = ("cabeza", escala)
    if clave not in av._retratos:
        base = dibujar_pose(av.rasgos, av.cuerpo, av.traje, "reposo0", av.tema, av.color_espada)
        r = caja_cabeza(av.cuerpo)
        if av.tema == "espacio":                 # el casco es mas alto
            r = pygame.Rect(r.x - 3, r.y - 12, r.w + 6, r.h + 12)
        r = r.clip(base.get_rect())
        trozo = base.subsurface(r).copy()
        av._retratos[clave] = pygame.transform.scale(trozo, (r.w * escala, r.h * escala))
    return av._retratos[clave]
