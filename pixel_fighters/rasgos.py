"""Analiza la foto y devuelve los RASGOS de la persona (no se genera ninguna imagen).

    {"piel": "#c68642", "pelo_color": "#2b1a10", "pelo_largo": "largo", "gafas": "normales", ...}

Con esos rasgos avatar.py dibuja un munyeco pixel-art: moreno, con gafas, pelo largo...
Proveedores (en orden, configurable con AI_PROVIDER en .env):
  1. OpenAI  (vision: gpt-5-mini -> gpt-4o-mini -> gpt-4.1-mini)
  2. Gemini  (gemini-2.5-flash -> gemini-3-flash-preview -> gemini-2.5-flash-lite)
  3. Local   (OpenCV: colores de piel/pelo/ropa, largo de pelo y gafas aproximados)

Pedir texto a un modelo de vision es mucho mas rapido (2-5 s) y barato que
generar una imagen, y el resultado SIEMPRE encaja con el estilo del juego.
"""
import base64
import json
import re

import cv2
import numpy as np

import config as C

# ------------------------------------------------------------------ esquema
OPCIONES = {
    "pelo_largo": ["calvo", "rapado", "corto", "medio", "largo"],
    "pelo_tipo": ["liso", "ondulado", "rizado", "afro"],
    "peinado": ["suelto", "coleta", "mono", "trenzas", "cresta"],
    "gafas": ["no", "normales", "sol"],
    "barba": ["no", "bigote", "perilla", "corta", "larga"],
    "ropa_tipo": ["camiseta", "sudadera", "camisa", "chaqueta", "otro"],
    "accesorio": ["ninguno", "gorra", "gorro", "diadema", "lazo", "pendientes"],
    "expresion": ["sonrisa", "seria"],
}
COLORES = ["piel", "pelo_color", "ojos_color", "gafas_color", "ropa_color", "accesorio_color"]

POR_DEFECTO = {
    "piel": "#e0ac85", "pelo_color": "#3b2416", "ojos_color": "#4a3020",
    "gafas_color": "#202028", "ropa_color": "#3060d0", "accesorio_color": "#e03040",
    "pelo_largo": "corto", "pelo_tipo": "liso", "peinado": "suelto", "flequillo": False,
    "gafas": "no", "barba": "no", "ropa_tipo": "camiseta", "accesorio": "ninguno",
    "expresion": "sonrisa",
}

PROMPT = (
    "You are helping an arcade game turn a player's photo into a cartoon pixel-art avatar. "
    "Look at the person whose face is in the CENTER of the photo and describe ONLY visible "
    "appearance traits "
    "so an artist can draw a cute look-alike doll. Do not identify the person. "
    "Answer with ONLY a JSON object with exactly these keys:\n"
    '  "piel": skin color as hex "#rrggbb" (as it looks in the photo, not too dark from shadows),\n'
    '  "pelo_color": hair color hex (if bald use the skin color),\n'
    '  "pelo_largo": one of ' + str(OPCIONES["pelo_largo"]) + ' (medio = to the chin/neck, '
    'largo = past the shoulders; if hair is tied back judge its real length),\n'
    '  "pelo_tipo": one of ' + str(OPCIONES["pelo_tipo"]) + ',\n'
    '  "peinado": one of ' + str(OPCIONES["peinado"]) + ' (suelto = loose/down, mono = bun, '
    'cresta = mohawk/spiky),\n'
    '  "flequillo": true if they have bangs/fringe over the forehead, else false,\n'
    '  "gafas": one of ' + str(OPCIONES["gafas"]) + ' (sol = sunglasses),\n'
    '  "gafas_color": frame color hex,\n'
    '  "barba": one of ' + str(OPCIONES["barba"]) + ',\n'
    '  "ojos_color": eye color hex,\n'
    '  "ropa_color": main color of the visible clothing (top) hex,\n'
    '  "ropa_tipo": one of ' + str(OPCIONES["ropa_tipo"]) + ',\n'
    '  "accesorio": one of ' + str(OPCIONES["accesorio"]) + ' (headwear or the most visible one),\n'
    '  "accesorio_color": hex,\n'
    '  "expresion": one of ' + str(OPCIONES["expresion"]) + ".\n"
    "Use exactly the Spanish option words given. If unsure, pick the most likely option."
)

_HEX = re.compile(r"^#?[0-9a-fA-F]{6}$")


def normalizar(d):
    """Valida lo que devuelve la IA: valores raros -> valor por defecto."""
    out = dict(POR_DEFECTO)
    if not isinstance(d, dict):
        return out
    for k in COLORES:
        v = str(d.get(k, "")).strip()
        if _HEX.match(v):
            out[k] = "#" + v.lstrip("#").lower()
    for k, ops in OPCIONES.items():
        v = str(d.get(k, "")).strip().lower()
        v = v.replace("ó", "o").replace("í", "i").replace("é", "e").replace("á", "a")
        if v in ops:
            out[k] = v
    f = d.get("flequillo")
    out["flequillo"] = f is True or str(f).lower() in ("true", "si", "yes", "1")
    return out


def hex_a_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def rgb_a_hex(c):
    return "#%02x%02x%02x" % tuple(int(max(0, min(255, v))) for v in c[:3])


def _json_de_texto(texto):
    texto = texto.strip()
    m = re.search(r"\{.*\}", texto, re.S)          # por si viene con ```json ... ```
    return json.loads(m.group(0) if m else texto)


# ------------------------------------------------------------------ errores
def _pista(texto):
    t = texto.lower()
    if "no module named 'google'" in t or "cannot import name 'genai'" in t:
        return "falta la libreria: pip install google-genai"
    if "no module named 'openai'" in t:
        return "falta la libreria: pip install openai"
    if "insufficient_quota" in t or "billing" in t or "exceeded your current quota" in t:
        return "sin saldo/cuota: revisa la facturacion de la cuenta"
    if "resource_exhausted" in t or "429" in t:
        return "cuota agotada o limite por minuto: espera o activa facturacion"
    if ("invalid_api_key" in t or "incorrect api key" in t or "api key not valid" in t
            or "api_key_invalid" in t or "401" in t):
        return "API key incorrecta o caducada"
    if "denied access" in t:
        return ("proyecto de Google denegado: verifica edad, telefono y 2 pasos en tu cuenta "
                "Google, o anyade facturacion en AI Studio, y crea una clave nueva")
    if "permission_denied" in t or "403" in t:
        return "la clave no tiene permiso para este modelo"
    if "model_not_found" in t or "does not exist" in t or "404" in t:
        return "ese modelo no existe o tu cuenta no tiene acceso"
    if "connection" in t or "timed out" in t or "timeout" in t or "getaddrinfo" in t:
        return "sin conexion a internet o la API tardo demasiado"
    return ""


def _err(quien, e):
    msg = " ".join(str(e).split())
    p = _pista(f"{type(e).__name__} {msg}")
    return f"{quien}: {p} ({msg[:120]})" if p else f"{quien}: {msg[:180]}"


def _graves(err):
    return any(k in err for k in ("API key", "libreria", "saldo", "internet"))


# ------------------------------------------------------------------ OpenAI
def _openai(ruta):
    if not C.OPENAI_API_KEY:
        raise RuntimeError("OpenAI: falta OPENAI_API_KEY en .env")
    try:
        from openai import OpenAI
    except ImportError as e:
        raise RuntimeError(_err("OpenAI", e))
    cliente = OpenAI(api_key=C.OPENAI_API_KEY, timeout=40, max_retries=1)
    b64 = base64.b64encode(open(ruta, "rb").read()).decode()
    mensajes = [{"role": "user", "content": [
        {"type": "text", "text": PROMPT},
        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}", "detail": "low"}},
    ]}]
    modelos = [C.OPENAI_VISION_MODEL] + [m for m in ("gpt-5-mini", "gpt-4o-mini", "gpt-4.1-mini")
                                         if m != C.OPENAI_VISION_MODEL]
    errores = []
    for modelo in modelos:
        try:
            extra = {"reasoning_effort": "minimal"} if modelo.startswith("gpt-5") else {}
            r = cliente.chat.completions.create(
                model=modelo, messages=mensajes,
                response_format={"type": "json_object"}, **extra)
            d = _json_de_texto(r.choices[0].message.content or "")
            print(f"[IA] OpenAI {modelo}: {d}")
            return normalizar(d)
        except Exception as e:
            print(f"[IA] OpenAI {modelo} fallo: {e}")
            errores.append(_err(modelo, e))
            if _graves(errores[-1]):
                break
    raise RuntimeError("OpenAI -> " + " || ".join(errores))


# ------------------------------------------------------------------ Gemini
# Google retira modelos para cuentas nuevas: si uno no existe, se prueba el que
# sugiera el propio error, luego esta lista, y por ultimo los que tenga la cuenta.
GEMINI_RESERVA = ("gemini-3.8-flash", "gemini-3.5-flash-lite", "gemini-3.7-flash",
                  "gemini-3.1-flash-lite", "gemini-2.5-flash")


_gem = {"cliente": None, "modo": None, "modelo": None, "sin_pensar": {}}   # cache entre fotos


def _cfg(types, modelo):
    """JSON + razonamiento minimo: para describir una cara no hace falta 'pensar' (mucho mas rapido)."""
    base = dict(response_mime_type="application/json", temperature=0.2)
    if _gem["sin_pensar"].get(modelo) is False:          # este modelo no acepta el ajuste
        return types.GenerateContentConfig(**base)
    if modelo.startswith("gemini-2.5"):
        tc = types.ThinkingConfig(thinking_budget=0)
    else:
        tc = types.ThinkingConfig(thinking_level="LOW")
    return types.GenerateContentConfig(thinking_config=tc, **base)


def _modelos_disponibles(cliente):
    """Pregunta a Google que modelos 'flash' puede usar esta clave."""
    try:
        nombres = []
        for m in cliente.models.list():
            nombre = (m.name or "").split("/")[-1]
            acciones = getattr(m, "supported_actions", None) or []
            if "flash" in nombre and "image" not in nombre and "tts" not in nombre \
                    and "audio" not in nombre and (not acciones or "generateContent" in acciones):
                nombres.append(nombre)
        print("[IA] modelos Gemini disponibles:", nombres)
        return sorted(nombres, reverse=True)[:4]
    except Exception as e:
        print("[IA] no se pudo listar modelos:", e)
        return []


def _gemini(ruta):
    if not C.GEMINI_API_KEY:
        raise RuntimeError("Gemini: falta GEMINI_API_KEY en .env")
    try:
        from google import genai
        from google.genai import types
    except ImportError as e:
        raise RuntimeError(_err("Gemini", e))
    # AI Studio ahora tambien da claves que empiezan por "AQ.", igual que Vertex AI Express.
    # Por eso se prueban los dos caminos (GEMINI_MODO=studio|vertex fuerza uno).
    modo = C.GEMINI_MODO
    if modo == "auto":
        modos = ["studio", "vertex"] if C.GEMINI_API_KEY.startswith("AQ.") else ["studio"]
    else:
        modos = [modo]
    imagen = types.Part.from_bytes(data=open(ruta, "rb").read(), mime_type="image/jpeg")
    if _gem["modo"] in modos:                       # ya funciono antes: empezar por ahi
        modos = [_gem["modo"]] + [m for m in modos if m != _gem["modo"]]
    errores = []
    for modo in modos:
        try:
            if _gem["cliente"] is not None and _gem["modo"] == modo:
                cliente = _gem["cliente"]
            else:
                cliente = genai.Client(vertexai=True, api_key=C.GEMINI_API_KEY) if modo == "vertex" \
                    else genai.Client(api_key=C.GEMINI_API_KEY)
        except Exception as e:
            errores.append(_err(f"[{modo}]", e))
            continue
        pendientes = [C.GEMINI_VISION_MODEL] + [m for m in GEMINI_RESERVA if m != C.GEMINI_VISION_MODEL]
        if _gem["modelo"] and _gem["modo"] == modo:  # el modelo que funciono en la foto anterior
            pendientes.insert(0, _gem["modelo"])
        probados, listado, clave_valida = set(), False, False
        while pendientes:
            modelo = pendientes.pop(0)
            if modelo in probados:
                continue
            probados.add(modelo)
            try:
                try:
                    r = cliente.models.generate_content(model=modelo, contents=[imagen, PROMPT],
                                                        config=_cfg(types, modelo))
                except Exception as e:
                    if "thinking" not in str(e).lower() or _gem["sin_pensar"].get(modelo) is False:
                        raise
                    _gem["sin_pensar"][modelo] = False           # reintento sin el ajuste
                    r = cliente.models.generate_content(model=modelo, contents=[imagen, PROMPT],
                                                        config=_cfg(types, modelo))
                if not r.text:
                    fb = getattr(r, "prompt_feedback", None)
                    raise RuntimeError(f"respuesta vacia ({getattr(fb, 'block_reason', '') or 'sin motivo'})")
                d = _json_de_texto(r.text)
                print(f"[IA] Gemini ({modo}) {modelo}: {d}")
                _gem.update(cliente=cliente, modo=modo, modelo=modelo)
                if modelo != C.GEMINI_VISION_MODEL:
                    print(f"[IA] CONSEJO: pon GEMINI_VISION_MODEL={modelo} en .env (ira mas rapido)")
                return normalizar(d)
            except Exception as e:
                msg = str(e)
                print(f"[IA] Gemini ({modo}) {modelo} fallo: {msg[:300]}")
                errores.append(_err(f"[{modo}] {modelo}", e))
                if "404" in msg or "NOT_FOUND" in msg:
                    clave_valida = True                 # la clave funciona, es el modelo
                    m = re.search(r"use models/([\w.\-]+)", msg)
                    if m:                               # Google dice que modelo usar: probarlo ya
                        pendientes.insert(0, m.group(1))
                    elif not pendientes and not listado:
                        listado = True
                        pendientes += _modelos_disponibles(cliente)
                elif _graves(errores[-1]) or "denegado" in errores[-1]:
                    break
        if clave_valida:
            break                                       # la clave es de AI Studio: no probar Vertex
    raise RuntimeError("Gemini -> " + " || ".join(errores))


# ------------------------------------------------------------------ Local (OpenCV)
def _mediana(img, x0, y0, x1, y1):
    h, w = img.shape[:2]
    x0, x1 = sorted((max(0, int(x0)), min(w, int(x1))))
    y0, y1 = sorted((max(0, int(y0)), min(h, int(y1))))
    zona = img[y0:y1, x0:x1].reshape(-1, 3)
    return np.median(zona, axis=0) if len(zona) else np.array([128, 128, 128])


def _caja_cara(bgr):
    try:
        det = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
        gris = cv2.equalizeHist(cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY))
        caras = det.detectMultiScale(gris, 1.1, 5, minSize=(60, 60))
        if len(caras):
            return [int(v) for v in max(caras, key=lambda c: c[2] * c[3])]
    except Exception:
        pass
    H, W = bgr.shape[:2]
    w = int(W / 3)
    return [(W - w) // 2, int(H * 0.22), w, w]


def local(ruta):
    """Estimacion sin internet. Colores fiables; largo de pelo y gafas aproximados."""
    bgr = cv2.imread(str(ruta))
    rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB).astype(np.float32)
    H, W = rgb.shape[:2]
    x, y, w, h = _caja_cara(bgr)
    d = dict(POR_DEFECTO)

    piel = (_mediana(rgb, x + .18 * w, y + .55 * h, x + .32 * w, y + .72 * h) +
            _mediana(rgb, x + .68 * w, y + .55 * h, x + .82 * w, y + .72 * h)) / 2
    d["piel"] = rgb_a_hex(piel * 1.05)
    pelo = _mediana(rgb, x + .3 * w, y - .12 * h, x + .7 * w, y + .02 * h)
    fondo = _mediana(rgb, 0, 0, W * .1, H * .1)
    d["pelo_color"] = rgb_a_hex(pelo)
    dist = lambda a, b: float(np.linalg.norm(np.asarray(a) - np.asarray(b)))

    if dist(pelo, piel) < 40:
        d["pelo_largo"] = "rapado"
    else:
        # pelo a los lados de la cara por debajo de la barbilla -> largo
        lados = np.concatenate([
            rgb[int(y + .9 * h):int(y + 1.3 * h), max(0, int(x - .25 * w)):int(x + .02 * w)].reshape(-1, 3),
            rgb[int(y + .9 * h):int(y + 1.3 * h), int(x + .98 * w):min(W, int(x + 1.25 * w))].reshape(-1, 3),
        ])
        if len(lados):
            parecido = (np.linalg.norm(lados - pelo, axis=1) < 45).mean()
            d["pelo_largo"] = "largo" if parecido > .45 else ("medio" if parecido > .25 else "corto")
        d["flequillo"] = dist(_mediana(rgb, x + .35 * w, y + .12 * h, x + .65 * w, y + .2 * h), pelo) < 40

    # gafas: la montura deja lineas horizontales fuertes bajo los ojos y en el puente
    gris = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    banda = gris[int(y + .30 * h):int(y + .55 * h), int(x + .12 * w):int(x + .88 * w)]
    if banda.size:
        sob = np.abs(cv2.Sobel(banda, cv2.CV_32F, 0, 1, ksize=3))
        filas = sob.mean(axis=1)
        if filas.max() > 3.2 * np.median(filas) and filas.max() > 40:
            d["gafas"] = "normales"
            d["gafas_color"] = "#202028"

    # ropa: franja inferior de la foto (hombros/pecho)
    ropa = _mediana(rgb, W * .25, min(H - 2, y + 1.55 * h), W * .75, H)
    if dist(ropa, fondo) > 30:
        d["ropa_color"] = rgb_a_hex(ropa)
    print(f"[IA] local: {d}")
    return d


PROVEEDORES = {"openai": _openai, "gemini": _gemini}


def analizar(ruta):
    """Devuelve (rasgos, fuente, errores). Nunca falla: como ultimo recurso usa local."""
    if C.AI_PROVIDER == "local":
        orden = []
    elif C.AI_PROVIDER == "auto":
        # en auto solo se prueban los servicios que tienen clave en el .env
        orden = [n for n, k in (("openai", C.OPENAI_API_KEY), ("gemini", C.GEMINI_API_KEY)) if k]
        if not orden:
            return local(ruta), "local", ["no hay ninguna clave (OPENAI_API_KEY / GEMINI_API_KEY) en .env"]
    else:
        orden = [C.AI_PROVIDER]            # openai o gemini: SOLO ese servicio
    errores = []
    for nombre in orden:
        if nombre not in PROVEEDORES:
            continue
        try:
            return PROVEEDORES[nombre](ruta), nombre, errores
        except Exception as e:
            errores.append(str(e))
    return local(ruta), "local", errores
