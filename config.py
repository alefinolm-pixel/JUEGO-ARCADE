"""Configuracion global de PIXEL FIGHTERS."""
import os
import socket
import sys
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
ENV_PATH = BASE_DIR / ".env"
ENV_ENCONTRADO = ENV_PATH.exists()
load_dotenv(ENV_PATH)
if not ENV_ENCONTRADO:
    print("=" * 70)
    print(f"[config] AVISO: no existe {ENV_PATH}")
    print("[config] Sin .env se usa la camara 0 y no hay IA. Copia tu .env a esta carpeta.")
    print("=" * 70)

# Resolucion logica del juego. pygame.SCALED la adapta a la pantalla de 7"
ANCHO, ALTO = 960, 540
FPS = 60
SUELO = 440
FULLSCREEN = os.getenv("FULLSCREEN", "0") == "1" and "--ventana" not in sys.argv

# Camara: 0 = USB/webcam del PC, "192.168.1.133:4747" = DroidCam por WiFi.
# Se pueden poner varias separadas por comas: se usa la primera que de imagen.
#   CAMERA_INDEX=192.168.1.133:4747,192.168.1.181:4747,0
CAMERA_INDEX = os.getenv("CAMERA_INDEX", "0").strip()

# IA que analiza la foto: auto | openai | gemini | local  (local = sin internet)
AI_PROVIDER = os.getenv("AI_PROVIDER", "auto").strip().lower()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
OPENAI_VISION_MODEL = os.getenv("OPENAI_VISION_MODEL", "gpt-5-mini").strip()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
GEMINI_VISION_MODEL = os.getenv("GEMINI_VISION_MODEL", "gemini-3.8-flash").strip()
# auto | studio (clave de aistudio.google.com) | vertex (Vertex AI Express de Google Cloud)
GEMINI_MODO = os.getenv("GEMINI_MODO", "auto").strip().lower()

# Sonido (0.0 - 1.0)
VOLUMEN_SFX = float(os.getenv("VOLUMEN_SFX", "0.8"))
VOLUMEN_MUSICA = float(os.getenv("VOLUMEN_MUSICA", "0.35"))

# Datos (luchadores creados) y temporales (fotos, se borran tras analizar)
DATA_DIR = BASE_DIR / "data"
CHAR_DIR = DATA_DIR / "characters"
TMP_DIR = DATA_DIR / "tmp"
ASSETS_DIR = BASE_DIR / "assets"      # opcional: assets/sonidos/*.wav, assets/musica/*.ogg
for d in (CHAR_DIR, TMP_DIR):
    d.mkdir(parents=True, exist_ok=True)

# El munyeco se dibuja en una rejilla pequena (pixel art) y se amplia x ESCALA
ESCALA = 3

# ---------------------------------------------------------------- MULTIJUGADOR (red local)
# Nombre con el que esta arcade aparece en la lista de partidas de la otra
RED_NOMBRE = (os.getenv("RED_NOMBRE", "").strip() or socket.gethostname() or "ARCADE")[:16].upper()
# IP de la otra arcade (opcional): aparece ya escrita al pulsar UNIRSE > ESCRIBIR IP
RED_IP = os.getenv("RED_IP", "").strip()
# Puerto TCP de la partida (los anuncios van por RED_PUERTO + 1 en UDP)
RED_PUERTO = int(os.getenv("RED_PUERTO", "50505"))
# Pasos de retardo de los controles (1 paso = 1/60 s). 3 va bien en WiFi; con cable se puede bajar a 2
RED_RETARDO = max(1, min(10, int(os.getenv("RED_RETARDO", "3"))))
# PRUEBAS: "python main.py --bot" -> en multijugador tu luchador lo maneja la CPU
# (sirve para probar con dos ventanas en el mismo PC sin tener dos joysticks)
RED_BOT = "--bot" in sys.argv or os.getenv("RED_BOT", "0") == "1"
