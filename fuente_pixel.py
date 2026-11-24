"""Fuente pixel-art propia (diseñada a mano, sin archivos ni licencias).

Se usa igual que pygame.font.Font:
    f = FuentePixel(32);  img = f.render("HOLA", True, (255, 255, 0))
Ademas:
    titulo(p, "PIXEL FIGHTERS", 90, (480, 95))      -> letras con degradado, contorno y sombra
"""
import pygame

# Cada glifo: 8 filas (la 0 es para la tilde de la Ñ). '#' = pixel encendido.
_G = {
    "A": [".###.", "#...#", "#...#", "#####", "#...#", "#...#", "#...#"],
    "B": ["####.", "#...#", "#...#", "####.", "#...#", "#...#", "####."],
    "C": [".###.", "#...#", "#....", "#....", "#....", "#...#", ".###."],
    "D": ["####.", "#...#", "#...#", "#...#", "#...#", "#...#", "####."],
    "E": ["#####", "#....", "#....", "####.", "#....", "#....", "#####"],
    "F": ["#####", "#....", "#....", "####.", "#....", "#....", "#...."],
    "G": [".###.", "#...#", "#....", "#.###", "#...#", "#...#", ".####"],
    "H": ["#...#", "#...#", "#...#", "#####", "#...#", "#...#", "#...#"],
    "I": ["###", ".#.", ".#.", ".#.", ".#.", ".#.", "###"],
    "J": ["..###", "...#.", "...#.", "...#.", "#..#.", "#..#.", ".##.."],
    "K": ["#...#", "#..#.", "#.#..", "##...", "#.#..", "#..#.", "#...#"],
    "L": ["#....", "#....", "#....", "#....", "#....", "#....", "#####"],
    "M": ["#...#", "##.##", "#.#.#", "#.#.#", "#...#", "#...#", "#...#"],
    "N": ["#...#", "##..#", "#.#.#", "#..##", "#...#", "#...#", "#...#"],
    "O": [".###.", "#...#", "#...#", "#...#", "#...#", "#...#", ".###."],
    "P": ["####.", "#...#", "#...#", "####.", "#....", "#....", "#...."],
    "Q": [".###.", "#...#", "#...#", "#...#", "#.#.#", "#..#.", ".##.#"],
    "R": ["####.", "#...#", "#...#", "####.", "#.#..", "#..#.", "#...#"],
    "S": [".####", "#....", "#....", ".###.", "....#", "....#", "####."],
    "T": ["#####", "..#..", "..#..", "..#..", "..#..", "..#..", "..#.."],
    "U": ["#...#", "#...#", "#...#", "#...#", "#...#", "#...#", ".###."],
    "V": ["#...#", "#...#", "#...#", "#...#", "#...#", ".#.#.", "..#.."],
    "W": ["#...#", "#...#", "#...#", "#.#.#", "#.#.#", "##.##", "#...#"],
    "X": ["#...#", "#...#", ".#.#.", "..#..", ".#.#.", "#...#", "#...#"],
    "Y": ["#...#", "#...#", ".#.#.", "..#..", "..#..", "..#..", "..#.."],
    "Z": ["#####", "....#", "...#.", "..#..", ".#...", "#....", "#####"],
    "0": [".###.", "#...#", "#..##", "#.#.#", "##..#", "#...#", ".###."],
    "1": [".#.", "##.", ".#.", ".#.", ".#.", ".#.", "###"],
    "2": [".###.", "#...#", "....#", "...#.", "..#..", ".#...", "#####"],
    "3": ["####.", "....#", "....#", ".###.", "....#", "....#", "####."],
    "4": ["...#.", "..##.", ".#.#.", "#..#.", "#####", "...#.", "...#."],
    "5": ["#####", "#....", "####.", "....#", "....#", "#...#", ".###."],
    "6": [".###.", "#....", "#....", "####.", "#...#", "#...#", ".###."],
    "7": ["#####", "....#", "...#.", "..#..", ".#...", ".#...", ".#..."],
    "8": [".###.", "#...#", "#...#", ".###.", "#...#", "#...#", ".###."],
    "9": [".###.", "#...#", "#...#", ".####", "....#", "....#", ".###."],
    " ": ["...", "...", "...", "...", "...", "...", "..."],
    ".": [".", ".", ".", ".", ".", ".", "#"],
    ",": [".", ".", ".", ".", ".", "#", "#"],
    ":": [".", "#", ".", ".", ".", "#", "."],
    ";": [".", "#", ".", ".", ".", "#", "#"],
    "!": ["#", "#", "#", "#", "#", ".", "#"],
    "¡": ["#", ".", "#", "#", "#", "#", "#"],
    "?": [".###.", "#...#", "....#", "...#.", "..#..", ".....", "..#.."],
    "¿": ["..#..", ".....", "..#..", ".#...", "#....", "#...#", ".###."],
    "-": ["...", "...", "...", "###", "...", "...", "..."],
    "_": ["....", "....", "....", "....", "....", "....", "####"],
    "+": ["...", "...", ".#.", "###", ".#.", "...", "..."],
    "=": ["...", "...", "###", "...", "###", "...", "..."],
    "/": ["....#", "...#.", "...#.", "..#..", ".#...", ".#...", "#...."],
    "(": [".#", "#.", "#.", "#.", "#.", "#.", ".#"],
    ")": ["#.", ".#", ".#", ".#", ".#", ".#", "#."],
    "[": ["##", "#.", "#.", "#.", "#.", "#.", "##"],
    "]": ["##", ".#", ".#", ".#", ".#", ".#", "##"],
    "<": ["...#", "..#.", ".#..", "#...", ".#..", "..#.", "...#"],
    ">": ["#...", ".#..", "..#.", "...#", "..#.", ".#..", "#..."],
    "%": ["#...#", "#..#.", "...#.", "..#..", ".#...", ".#..#", "#...#"],
    "'": ["#", "#", ".", ".", ".", ".", "."],
    '"': ["#.#", "#.#", "...", "...", "...", "...", "..."],
    "#": [".#.#.", "#####", ".#.#.", ".#.#.", "#####", ".#.#.", "....."],
    "|": ["#", "#", "#", "#", "#", "#", "#"],
    "*": [".....", "#.#.#", ".###.", "#####", ".###.", "#.#.#", "....."],
}
# Ñ = N con barrita encima (fila 0)
_TILDE = {"Ñ": ("N", "#####")}
_EQUIV = str.maketrans("ÁÉÍÓÚÀÈÌÒÙÄËÏÖÜÂÊÎÔÛÇ&", "AEIOUAEIOUAEIOUAEIOUC+")
ALTO = 8


def _normalizar(c):
    if c in ("ñ", "Ñ"):
        return "Ñ"
    c = c.translate(_EQUIV).upper().translate(_EQUIV)
    return c


def _filas(c):
    if c in _TILDE:
        base, tilde = _TILDE[c]
        filas = _G[base]
        return [tilde.ljust(len(filas[0]), ".")[:len(filas[0])]] + filas
    filas = _G.get(c) or _G["?"]
    return ["." * len(filas[0])] + filas


def escala_para(tam):
    """Convierte el 'tamano' estilo pygame.font a escala de pixel."""
    if tam <= 16:
        return 1
    if tam <= 26:
        return 2
    return max(3, round(tam / 11))


class FuentePixel:
    def __init__(self, tam=None, escala=None):
        self.s = escala or escala_para(tam or 32)
        self._cache = {}

    def get_height(self):
        return ALTO * self.s

    def size(self, texto):
        w = 0
        for c in texto:
            w += (len(_filas(_normalizar(c))[0]) + 1) * self.s
        return max(0, w - self.s), self.get_height()

    def _glifo(self, c, color):
        clave = (c, tuple(color))
        if clave not in self._cache:
            filas = _filas(c)
            w = len(filas[0])
            g = pygame.Surface((w * self.s, ALTO * self.s), pygame.SRCALPHA)
            for y, fila in enumerate(filas):
                for x, ch in enumerate(fila):
                    if ch == "#":
                        g.fill(color, (x * self.s, y * self.s, self.s, self.s))
            self._cache[clave] = g
        return self._cache[clave]

    def render(self, texto, aa=True, color=(255, 255, 255), fondo=None):
        color = tuple(color)[:3]
        w, h = self.size(texto)
        surf = pygame.Surface((max(1, w), h), pygame.SRCALPHA)
        if fondo is not None:
            surf.fill(fondo)
        x = 0
        for c in texto:
            c = _normalizar(c)
            g = self._glifo(c, color)
            surf.blit(g, (x, 0))
            x += g.get_width() + self.s
        return surf

    def render_degradado(self, texto, arriba, abajo, brillo=True):
        """Relleno con degradado vertical (estilo logo arcade) y linea de brillo."""
        base = self.render(texto, True, (255, 255, 255))
        w, h = base.get_size()
        grad = pygame.Surface((w, h), pygame.SRCALPHA)
        for fila in range(ALTO):
            f = max(0, fila - 1) / (ALTO - 2)
            col = tuple(int(arriba[i] + (abajo[i] - arriba[i]) * f) for i in range(3))
            grad.fill(col, (0, fila * self.s, w, self.s))
        if brillo:                                   # reflejo claro en la primera fila
            grad.fill((255, 255, 255), (0, 1 * self.s, w, max(1, self.s // 3)))
        base.blit(grad, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
        return base


_fuentes = {}


def fuente(tam):
    if tam not in _fuentes:
        _fuentes[tam] = FuentePixel(tam)
    return _fuentes[tam]


def titulo(p, texto, tam, centro, arriba=(255, 240, 120), abajo=(255, 120, 20),
           borde=(40, 10, 30), sombra=(0, 0, 0)):
    """Rotulo grande: degradado + contorno grueso + sombra desplazada."""
    f = fuente(tam)
    s = f.s
    relleno = f.render_degradado(texto, arriba, abajo)
    mascara = f.render(texto, True, borde)
    r = relleno.get_rect(center=centro)
    g = max(2, s // 2 + 1)
    som = f.render(texto, True, sombra)
    som.set_alpha(150)
    p.blit(som, r.move(g + s, g + s))
    for dx in range(-g, g + 1, max(1, g // 2)):
        for dy in range(-g, g + 1, max(1, g // 2)):
            if dx or dy:
                p.blit(mascara, r.move(dx, dy))
    p.blit(relleno, r)
    return r
