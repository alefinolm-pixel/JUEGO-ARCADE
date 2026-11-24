"""PIXEL FIGHTERS - punto de entrada.  Ejecutar:  python main.py"""
import sys
import threading

import pygame

import config as C
import roster
import sonido
from fuente_pixel import fuente
from camera import Camara
from scenes import Menu


class Juego:
    def __init__(self):
        sonido.preiniciar()
        pygame.init()
        flags = pygame.SCALED | (pygame.FULLSCREEN if C.FULLSCREEN else 0)
        self.pantalla = pygame.display.set_mode((C.ANCHO, C.ALTO), flags)
        pygame.display.set_caption("PIXEL FIGHTERS" + ("  [BOT]" if C.RED_BOT else ""))
        pygame.mouse.set_visible(not C.FULLSCREEN)
        sonido.iniciar()
        self.reloj = pygame.time.Clock()
        self.f_chica = fuente(22)             # fuente pixel propia (fuente_pixel.py)
        self.fuente = fuente(30)
        self.f_grande = fuente(60)
        self.roster = roster.cargar_todos()
        self.p1 = self.p2 = None
        self.racha = 0                        # victorias seguidas contra la CPU
        self.dificultad = "normal"            # normal | dificil | experto (cambia el escenario)
        self.camara = None
        self.camara_estado = "sin_abrir"      # sin_abrir | conectando | ok | error
        if not C.RED_BOT:                     # en pruebas de red (--bot) no hace falta camara
            self.camara_compartida()          # se abre ya en segundo plano: luego es instantanea
        self.escena = Menu(self)

    def camara_compartida(self):
        """Una sola camara para toda la partida: abrirla en Windows tarda varios
        segundos, asi que se abre una vez y se reutiliza para cada foto."""
        if self.camara is None or self.camara_estado == "error" or \
                (self.camara_estado == "ok" and not self.camara.abierta()):
            if self.camara is not None:
                self.camara.cerrar()
            self.camara = Camara(C.CAMERA_INDEX)
            self.camara_estado = "conectando"
            threading.Thread(target=self._abrir_camara, args=(self.camara,), daemon=True).start()
        return self.camara

    def _abrir_camara(self, cam):
        ok = cam.conectar()
        if cam is self.camara:
            self.camara_estado = "ok" if ok else "error"

    def recargar_roster(self):
        self.roster = roster.cargar_todos()

    def cambiar(self, escena):
        self.escena.salir()
        self.escena = escena

    def salir(self):
        self.escena.salir()
        if self.camara is not None:
            self.camara.cerrar()
        pygame.quit()
        sys.exit()

    def run(self):
        while True:
            dt = min(self.reloj.tick(C.FPS), 50)     # evita saltos si el sistema se atasca
            evs = pygame.event.get()
            if any(e.type == pygame.QUIT for e in evs):
                self.salir()
            self.escena.eventos(evs)
            self.escena.actualizar(dt)
            self.escena.dibujar(self.pantalla)
            pygame.display.flip()


if __name__ == "__main__":
    Juego().run()
