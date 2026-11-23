"""Teclado en pantalla para escribir con el joystick y los botones del arcade.

    tec = Teclado()
    tec.mover(dx, dy)      # joystick
    tec.pulsar()           # boton de golpe -> escribe la letra o ejecuta ESP / BORRAR / OK
    tec.borrar()           # boton de especial -> borra la ultima letra
    tec.dibujar(p, cx, y)
"""
import pygame

from efectos import texto_borde

FILAS = [
    list("ABCDEFG"),
    list("HIJKLMN"),
    list("ÑOPQRST"),
    list("UVWXYZ-"),
    list("0123456"),
    ["7", "8", "9", "!", "ESP", "<", "OK"],
]
MAX = 10

AMARILLO = (255, 220, 30)
BLANCO = (255, 255, 255)
FONDO = (40, 30, 80)
SEL = (255, 220, 30)


class Teclado:
    ANCHO_T, ALTO_T, HUECO = 40, 24, 4

    def __init__(self, texto=""):
        self.texto = texto[:MAX]
        self.f, self.c = 0, 0
        self.parpadeo = 0

    @property
    def tecla(self):
        return FILAS[self.f][self.c]

    def mover(self, dx, dy):
        self.f = (self.f + dy) % len(FILAS)
        self.c = (self.c + dx) % len(FILAS[self.f])

    def borrar(self):
        """Devuelve False si ya estaba vacio (sirve para 'volver atras')."""
        if not self.texto:
            return False
        self.texto = self.texto[:-1]
        return True

    def pulsar(self):
        """Devuelve 'ok' al pulsar OK; 'lleno' si no caben mas letras; None en otro caso."""
        t = self.tecla
        if t == "OK":
            return "ok"
        if t == "<":
            self.borrar()
            return None
        if len(self.texto) >= MAX:
            return "lleno"
        if t == "ESP":
            if self.texto and not self.texto.endswith(" "):
                self.texto += " "
            return None
        self.texto += t
        return None

    def dibujar(self, p, cx, y, fuente):
        w, h, g = self.ANCHO_T, self.ALTO_T, self.HUECO
        ancho = len(FILAS[0]) * (w + g) - g
        x0 = cx - ancho // 2
        for f, fila in enumerate(FILAS):
            for c, t in enumerate(fila):
                r = pygame.Rect(x0 + c * (w + g), y + f * (h + g), w, h)
                sel = (f, c) == (self.f, self.c)
                especial = t in ("ESP", "<", "OK")
                fondo = SEL if sel else ((70, 50, 120) if especial else FONDO)
                pygame.draw.rect(p, fondo, r, border_radius=4)
                pygame.draw.rect(p, BLANCO if sel else (110, 90, 160), r, 2, border_radius=4)
                img = fuente.render(t, True, (20, 15, 30) if sel else BLANCO)
                p.blit(img, img.get_rect(center=r.center))

    def dibujar_nombre(self, p, cx, y, t_seg, placeholder):
        """El nombre escrito en grande, con cursor parpadeante."""
        if self.texto:
            cursor = "_" if int(t_seg * 3) % 2 == 0 and len(self.texto) < MAX else " "
            texto_borde(p, self.texto + cursor, 42, AMARILLO, (cx, y))
        else:
            cursor = "_" if int(t_seg * 3) % 2 == 0 else " "
            texto_borde(p, cursor, 42, AMARILLO, (cx, y))
            img = __import__("fuente_pixel").fuente(16).render(f"(vacio = {placeholder})", True, (150, 150, 170))
            p.blit(img, img.get_rect(midtop=(cx, y + 18)))
