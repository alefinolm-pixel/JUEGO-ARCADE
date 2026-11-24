"""Prueba el multijugador SIN dos arcades y SIN pantalla.

    python probar_red.py               # 2 "arcades" en este PC, manejadas por la CPU
    python probar_red.py --lag 40      # simula una red con 40 ms de retraso
    python probar_red.py --pasos 20000 # prueba mas larga

Crea un anfitrion y un invitado que se conectan de verdad por TCP (127.0.0.1),
pelean bot contra bot (con revanchas) y al final comprueba que las dos maquinas
han visto EXACTAMENTE la misma pelea, paso a paso. Tambien prueba la desconexion.
"""
import argparse
import os
import random
import sys
import time

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame  # noqa: E402

import config as C  # noqa: E402
import red  # noqa: E402
import roster  # noqa: E402
from fuente_pixel import fuente  # noqa: E402


class JuegoFalso:
    """Lo minimo de main.Juego que usan las escenas."""

    def __init__(self):
        self.f_chica, self.fuente, self.f_grande = fuente(22), fuente(30), fuente(60)
        self.roster = roster.cargar_todos()
        self.p1 = self.p2 = None
        self.racha = 0
        self.dificultad = "normal"
        self.escena = None

    def cambiar(self, escena):
        if self.escena is not None:
            self.escena.salir()
        self.escena = escena


def estado(pelea):
    """Todo lo que importa de la pelea (si difiere en algo, hay desincronizacion)."""
    out = [pelea.estado, pelea.ronda, tuple(pelea.victorias), round(pelea.tiempo, 3), pelea.reloj,
           round(pelea.fx.hitstop, 3), len(pelea.ataques)]
    for lu in (pelea.l1, pelea.l2):
        out += [lu.x, tuple(lu.rect), lu.vx, lu.vy, lu.vida, lu.direccion, lu.t_ataque, lu.t_golpeado,
                lu.dash, lu.ultimo_especial, lu.en_suelo]
    return tuple(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pasos", type=int, default=8000, help="pasos de simulacion (60 = 1 segundo)")
    ap.add_argument("--lag", type=int, default=0, help="retraso simulado de la red en ms")
    ap.add_argument("--puerto", type=int, default=50605)
    ap.add_argument("--dibujar", action="store_true", help="dibuja tambien (mas lento, prueba el HUD)")
    args = ap.parse_args()

    red.LAG_PRUEBA = args.lag
    pygame.init()
    pantalla = pygame.display.set_mode((C.ANCHO, C.ALTO))
    from escena_red import PeleaRed, personaje_de_dict

    print(f"[1] Anfitrion escuchando en el puerto {args.puerto} (lag simulado: {args.lag} ms)")
    anf = red.Anfitrion("PRUEBA", args.puerto)
    if anf.error:
        sys.exit("ERROR: " + anf.error)
    bus = red.Buscador()
    con_inv = red.Conectar("127.0.0.1", args.puerto)
    t0 = time.monotonic()
    while (anf.conexion is None or not con_inv.terminado) and time.monotonic() - t0 < 5:
        time.sleep(0.02)
    if anf.conexion is None or con_inv.conexion is None:
        sys.exit("ERROR: no se conectaron: " + con_inv.error)
    print("[2] Conectados.  IPs de este equipo:", ", ".join(red.ips_locales()))
    time.sleep(1.2)
    vistas = bus.lista()
    print("[3] Anuncio UDP:", "visto " + str(vistas) if vistas else "NO visto (puede ser el cortafuegos; "
          "escribir la IP a mano sigue funcionando)")
    bus.cancelar()

    ja, ji = JuegoFalso(), JuegoFalso()
    pa, pi = ja.roster[0], ji.roster[min(2, len(ji.roster) - 1)]
    # cada lado recibe el luchador del otro como JSON, igual que por la red
    host = PeleaRed(ja, anf.conexion, True, pa, personaje_de_dict(pi.a_dict()), "experto", C.RED_RETARDO, bot=True)
    inv = PeleaRed(ji, con_inv.conexion, False, pi, personaje_de_dict(pa.a_dict()), "experto", C.RED_RETARDO,
                   bot=True)
    for lado in (host, inv):
        lado.CADA_CHK = 30
    hist = {host: {}, inv: {}}
    for lado in (host, inv):
        original = lado._tick

        def tick(b1, b2, lado=lado, original=original):
            original(b1, b2)
            hist[lado][lado.f] = estado(lado)
        lado._tick = tick

    print(f"[4] Pelea bot contra bot, {args.pasos} pasos...")
    partidas, ultimo_estado = 0, {host: None, inv: None}
    t0 = time.monotonic()
    paso_max_espera = 0
    while min(host.f, inv.f) < args.pasos:
        for lado in random.sample((host, inv), 2):               # orden y ritmo irregular, como en la vida real
            lado.actualizar(random.uniform(8, 30))
            if lado.estado == "fin" and ultimo_estado[lado] != "fin" and lado is host:
                partidas += 1
                g = "P1" if lado.ganador is lado.l1 else "P2"
                print(f"    partida {partidas}: gana {g} ({lado.victorias[0]}-{lado.victorias[1]})  paso {lado.f}")
            ultimo_estado[lado] = lado.estado
            paso_max_espera = max(paso_max_espera, lado.t_espera)
            if args.dibujar and lado.f % 7 == 0:
                lado.dibujar(pantalla)
        time.sleep(0.001)
        if host.desconectado or inv.desconectado:
            sys.exit("ERROR: desconexion inesperada: " + (host.desconectado or inv.desconectado))
        if time.monotonic() - t0 > 600:
            sys.exit("ERROR: demasiado lento")
    host.dibujar(pantalla)
    inv.dibujar(pantalla)
    pygame.image.save(pantalla, str(C.TMP_DIR / "prueba_red.png"))

    comunes = sorted(set(hist[host]) & set(hist[inv]))
    distintos = [f for f in comunes if hist[host][f] != hist[inv][f]]
    print(f"[5] Pasos comparados: {len(comunes)}   distintos: {len(distintos)}   "
          f"correcciones: {inv.correcciones}   partidas terminadas: {partidas}   "
          f"espera maxima: {paso_max_espera:.0f} ms   tiempo: {time.monotonic() - t0:.1f} s")
    if distintos:
        f = distintos[0]
        print("    primer paso distinto:", f)
        print("    anfitrion:", hist[host][f])
        print("    invitado: ", hist[inv][f])

    print("[6] Prueba de desconexion: el anfitrion sale al menu...")
    host.salir()
    t0 = time.monotonic()
    while not inv.desconectado and time.monotonic() - t0 < 3:
        inv.actualizar(16)
        time.sleep(0.01)
    print("    el invitado ve:", repr(inv.desconectado) if inv.desconectado else "NADA (ERROR)")

    ok = not distintos and inv.desconectado and len(comunes) > 0
    print("\nRESULTADO:", "TODO OK - el multijugador funciona" if ok else "HAY PROBLEMAS (mira arriba)")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
