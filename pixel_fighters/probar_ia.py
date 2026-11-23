"""Prueba SOLO la IA (sin abrir el juego) y muestra el error real de cada proveedor:
    py -3.11 probar_ia.py mi_foto.jpg

Ensenya los rasgos que devuelve cada uno y guarda data/tmp/avatar_<proveedor>.png
con el munyeco dibujado, para comparar OpenAI vs Gemini vs local.
"""
import os
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
import pygame

import avatar
import config as C
import rasgos

if len(sys.argv) < 2:
    print("Uso: python probar_ia.py foto.jpg   (una foto tuya de cara y hombros)")
    sys.exit(1)
ruta = sys.argv[1]

pygame.init()
pygame.display.set_mode((10, 10))
print("Config: AI_PROVIDER =", C.AI_PROVIDER,
      "| OPENAI key:", "si" if C.OPENAI_API_KEY else "NO", f"({C.OPENAI_VISION_MODEL})",
      "| GEMINI key:", "si" if C.GEMINI_API_KEY else "NO", f"({C.GEMINI_VISION_MODEL})")

pruebas = dict(rasgos.PROVEEDORES, local=rasgos.local)
for nombre, fn in pruebas.items():
    print(f"\n=== {nombre} ===")
    try:
        r = fn(ruta)
        for k, v in r.items():
            print(f"   {k:16s} {v}")
        av = avatar.Avatar(r, "equilibrado", "karate", 4)
        out = C.TMP_DIR / f"avatar_{nombre}.png"
        pygame.image.save(av.frame("reposo0"), str(out))
        print("OK ->", out)
    except Exception as e:
        print("FALLO:", e)
