"""Personajes base + luchadores creados con la camara (data/characters/<id>/meta.json).

Un luchador = rasgos (de la foto) + cuerpo + traje + especial.  No se guarda ninguna foto.
"""
from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field

import avatar
import config as C
import rasgos as R


@dataclass
class Personaje:
    id: str
    nombre: str
    rasgos: dict
    cuerpo: str = "equilibrado"
    traje: str = "karate"
    especial: str = "ONDA PIXEL"
    _avatar: object = field(default=None, repr=False, compare=False)
    _temas: dict = field(default_factory=dict, repr=False, compare=False)

    @property
    def avatar(self):
        if self._avatar is None:
            self._avatar = avatar.Avatar(self.rasgos, self.cuerpo, self.traje)
        return self._avatar

    def avatar_tema(self, tema, color_espada=(80, 200, 255)):
        """Avatar con el aspecto del escenario (p. ej. casco y espada en el espacio)."""
        if not tema:
            return self.avatar
        clave = (tema, color_espada)
        if clave not in self._temas:
            self._temas[clave] = avatar.Avatar(self.rasgos, self.cuerpo, self.traje,
                                               tema=tema, color_espada=color_espada)
        return self._temas[clave]

    def cambiar(self, cuerpo=None, traje=None):
        """Cambia cuerpo/traje y regenera el dibujo (pantalla de personalizar)."""
        self.cuerpo = cuerpo or self.cuerpo
        self.traje = traje or self.traje
        self._avatar = None
        self._temas = {}

    @property
    def stats(self):
        return avatar.STATS[self.cuerpo]

    @property
    def color(self):
        return avatar.paleta(self.rasgos, self.traje)["ropa"]

    @property
    def guante(self):
        return avatar.paleta(self.rasgos, self.traje)["guante"]

    @property
    def dano(self):
        from especiales import DANO
        return DANO.get(self.especial, 12)

    def a_dict(self):
        return dict(id=self.id, nombre=self.nombre, rasgos=self.rasgos, cuerpo=self.cuerpo,
                    traje=self.traje, especial=self.especial)


def _base(id_, nombre, cuerpo, traje, especial, **r):
    return Personaje(id_, nombre, R.normalizar(r), cuerpo, traje, especial)


def base():
    return [
        _base("ray", "RAY", "equilibrado", "karate", "DRAGON ROJO",
              piel="#f0c09a", pelo_color="#5a3018", pelo_largo="corto", flequillo=True,
              ropa_color="#e02a36", accesorio="diadema", accesorio_color="#e02a36",
              ojos_color="#3a2a1a", expresion="seria"),
        _base("luna", "LUNA", "agil", "ninja", "TORMENTA LUNAR",
              piel="#e8b48c", pelo_color="#7a2ad0", pelo_largo="largo", peinado="coleta",
              ropa_color="#a040e6", ojos_color="#6030a0", expresion="sonrisa"),
        _base("tank", "TANK", "fuerte", "boxeo", "GOLPE SISMICO",
              piel="#a8704a", pelo_color="#1a1418", pelo_largo="rapado", barba="corta",
              ropa_color="#2a64f0", expresion="seria"),
    ]


def cargar_todos():
    lista = base()
    metas = sorted(C.CHAR_DIR.glob("*/meta.json"), key=lambda m: m.stat().st_mtime)
    for meta in metas:
        try:
            d = json.loads(meta.read_text(encoding="utf-8"))
            if "rasgos" not in d:          # luchador antiguo (version con sprite pegado)
                col = d.get("color", [60, 120, 220])
                d["rasgos"] = R.normalizar({"ropa_color": R.rgb_a_hex(col)})
            lista.append(Personaje(
                id=d["id"], nombre=d["nombre"], rasgos=R.normalizar(d["rasgos"]),
                cuerpo=d.get("cuerpo", "equilibrado") if d.get("cuerpo") in avatar.CUERPOS else "equilibrado",
                traje=d.get("traje", "karate") if d.get("traje") in avatar.TRAJES else "karate",
                especial=d.get("especial", "ONDA PIXEL"),
            ))
        except Exception as e:
            print("[roster] personaje danado:", meta, e)
    return lista


def siguiente_nombre():
    return f"JUGADOR {len(list(C.CHAR_DIR.glob('*/meta.json'))) + 1}"


def nuevo(rasgos, nombre=None):
    """Crea (sin guardar) un luchador a partir de los rasgos. Elige traje/especial
    segun lo que lleva puesto y si tiene gafas."""
    traje = {"sudadera": "calle", "chaqueta": "calle", "camisa": "karate"}.get(rasgos["ropa_tipo"], "karate")
    especial = "RAYO FACIAL" if rasgos["gafas"] != "no" else avatar.ESPECIAL_TRAJE[traje]
    return Personaje(uuid.uuid4().hex[:8], nombre or siguiente_nombre(), rasgos,
                     "equilibrado", traje, especial)


def especial_para(pj):
    """Al cambiar de traje en la personalizacion, el especial acompanya (gafas = rayo)."""
    return "RAYO FACIAL" if pj.rasgos["gafas"] != "no" else avatar.ESPECIAL_TRAJE[pj.traje]


def guardar(pj):
    carpeta = C.CHAR_DIR / pj.id
    carpeta.mkdir(parents=True, exist_ok=True)
    (carpeta / "meta.json").write_text(json.dumps(pj.a_dict(), ensure_ascii=False, indent=2),
                                       encoding="utf-8")
    try:                                   # vista previa para verlo fuera del juego
        import pygame
        pygame.image.save(pj.avatar.retrato(4), str(carpeta / "preview.png"))
    except Exception:
        pass
    return pj
