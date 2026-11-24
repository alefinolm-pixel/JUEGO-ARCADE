"""Prueba SOLO la camara (sin el juego) y dice POR QUE falla cada movil.

    py -3.11 probar_camara.py                         (usa CAMERA_INDEX del .env)
    py -3.11 probar_camara.py 192.168.1.133 192.168.1.181
"""
import sys

import cv2

import config as C
from camera import Camara, fuentes_configuradas

fuentes = fuentes_configuradas(",".join(sys.argv[1:])) if len(sys.argv) > 1 \
    else fuentes_configuradas(C.CAMERA_INDEX)
print("Probando:", fuentes, "\n")
cam = Camara(fuentes)
ok = cam.conectar()
print("\n===== RESUMEN =====")
for linea in cam.diagnostico:
    print("  ", linea)
if not ok:
    print("\nChecklist DroidCam:")
    print("  1. PC y moviles en la MISMA WiFi (no la de invitados; en el movil quita los datos moviles).")
    print("  2. App DroidCam ABIERTA en el movil, pantalla encendida, y la IP que pone la app.")
    print("  3. Cierra el cliente DroidCam del PC y cualquier pestana con http://ip:4747 (solo admite 1 conexion).")
    print("  4. Prueba en el navegador del PC:  http://IP:4747  -> debe verse la camara.")
    print("  5. iPhone: Ajustes > DroidCam > 'Red local' activado.")
    sys.exit(1)
print("\nCONECTADO a:", cam.fuente, "- pulsa ESC en la ventana para salir")
while True:
    f = cam.leer()
    if f is not None:
        for (x, y, w, h) in cam.detectar_caras(f):
            cv2.rectangle(f, (x, y), (x + w, y + h), (0, 220, 255), 3)
        cv2.imshow("Camara (ESC para salir)", f)
    if cv2.waitKey(30) == 27:
        break
cam.cerrar()
cv2.destroyAllWindows()
