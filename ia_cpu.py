"""Rival controlado por la maquina.

Cada cierto tiempo (tiempo de reaccion) mira la situacion y decide que "teclas"
pulsa: acercarse, golpear, bloquear, saltar proyectiles, huir del rayo, lanzar
su especial... El NIVEL cambia la rapidez de reaccion y lo bien que se defiende.
"""
import random

NIVELES = {
    #    reaccion(ms) bloqueo esquiva agresion especial
    1: dict(reaccion=420, bloqueo=0.10, esquiva=0.20, agresion=0.40, especial=0.20),
    2: dict(reaccion=330, bloqueo=0.22, esquiva=0.35, agresion=0.50, especial=0.30),
    3: dict(reaccion=260, bloqueo=0.35, esquiva=0.50, agresion=0.60, especial=0.40),
    4: dict(reaccion=200, bloqueo=0.48, esquiva=0.65, agresion=0.70, especial=0.50),
    5: dict(reaccion=150, bloqueo=0.60, esquiva=0.80, agresion=0.80, especial=0.60),
    6: dict(reaccion=110, bloqueo=0.72, esquiva=0.90, agresion=0.85, especial=0.70),
}
NIVEL_MAX = max(NIVELES)


class TeclasVirtuales:
    """Se usa igual que pygame.key.get_pressed(): teclas[codigo] -> True/False."""

    def __init__(self):
        self.on = set()

    def __getitem__(self, k):
        return k in self.on


class CPU:
    def __init__(self, yo, nivel=1):
        self.yo = yo
        self.nivel = max(1, min(NIVEL_MAX, nivel))
        self.p = NIVELES[self.nivel]
        self.teclas = TeclasVirtuales()
        self.t = 300                                   # pequena pausa al empezar

    def _amenaza(self, pelea):
        """Que ataque del rival me viene encima y como evitarlo."""
        yo = self.yo
        for a in pelea.ataques:
            if a.a is yo or not a.vivo:
                continue
            tipo = type(a).__name__
            if a.es_proyectil and getattr(a, "salido", False):
                d = (yo.rect.centerx - a.x) * a.dir
                if 0 < d < 280:
                    return "saltar"
            elif tipo == "GolpeSismico" and a.x is not None:
                d = (yo.rect.centerx - a.x) * a.dir
                if 0 < d < 240:
                    return "saltar"
            elif tipo == "TormentaLunar" and a.t < 550 and abs(a.x - yo.rect.centerx) < 90:
                return "huir"
            elif tipo in ("RayoFacial", "PunoEstelar", "TurboCombo"):
                return "bloquear"
        return None

    def actualizar(self, dt, pelea):
        """Devuelve (teclas_virtuales, acciones) con acciones en {'golpe', 'especial'}."""
        acciones = []
        self.t -= dt
        if self.t > 0:
            return self.teclas, acciones
        self.t = self.p["reaccion"] * random.uniform(0.7, 1.3)
        self.teclas.on.clear()

        yo, r = self.yo, self.yo.rival
        if yo.ko or r.ko or pelea.estado != "lucha":
            return self.teclas, acciones
        c = yo.controles
        delante = c["derecha"] if yo.direccion == 1 else c["izquierda"]
        atras = c["izquierda"] if yo.direccion == 1 else c["derecha"]
        dist = abs(r.rect.centerx - yo.rect.centerx)
        alcance = yo.zona_golpe().width + (yo.rect.width + r.rect.width) // 2 - 12

        # 1) defenderse de especiales
        amenaza = self._amenaza(pelea)
        if amenaza and random.random() < self.p["esquiva"]:
            if amenaza == "saltar" and random.random() < 0.7:
                self.teclas.on.add(c["salto"])
            elif amenaza == "huir":
                cerca_pared = yo.rect.left < 80 or yo.rect.right > pelea.ancho - 80
                self.teclas.on.add(delante if cerca_pared else atras)
            else:
                self.teclas.on.add(atras)                  # bloquear
            self.t = min(self.t, 220)
            return self.teclas, acciones

        # 2) bloquear golpes normales
        if r.atacando() and dist < alcance + 70 and random.random() < self.p["bloqueo"]:
            self.teclas.on.add(atras)
            return self.teclas, acciones

        # 3) especial si esta cargado y la distancia le viene bien
        if yo.carga_especial(pelea.reloj) >= 1 and random.random() < self.p["especial"]:
            rango = {"TURBO COMBO": alcance + 30, "PUNO ESTELAR": 340}.get(yo.personaje.especial, 10_000)
            if dist < rango:
                acciones.append("especial")
                return self.teclas, acciones

        # 4) moverse y golpear
        x = random.random()
        if dist > alcance:
            if x < self.p["agresion"]:
                self.teclas.on.add(delante)
            elif x < self.p["agresion"] + 0.2:
                self.teclas.on.add(atras)
            if random.random() < 0.05:
                self.teclas.on.add(c["salto"])
        else:
            if x < self.p["agresion"]:
                acciones.append("golpe")
            elif x < self.p["agresion"] + 0.15:
                self.teclas.on.add(atras)
            elif x < self.p["agresion"] + 0.22:
                self.teclas.on.update((c["salto"], delante))
        return self.teclas, acciones
