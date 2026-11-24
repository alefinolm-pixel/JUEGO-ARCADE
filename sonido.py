"""Sonidos retro sintetizados con numpy (no hace falta ningun archivo).

Para cambiar un sonido por uno propio, deja un archivo con el mismo nombre en
assets/sonidos/  (p. ej. assets/sonidos/golpe.wav  u  .ogg).
Para musica propia: assets/musica/menu.ogg y assets/musica/pelea.ogg

Uso:  import sonido;  sonido.iniciar();  sonido.play("golpe")
"""
import random

import numpy as np
import pygame

import config as C

SR = 22050
_sonidos = {}
_ok = False
_musica_actual = None
_canal_musica = None


# ------------------------------------------------------------------ sintetizador
def _t(dur):
    return np.arange(int(SR * dur)) / SR


def _env(n, ataque=0.005, caida=None):
    """Envolvente: subida rapida y caida exponencial."""
    e = np.ones(n)
    a = max(1, int(SR * ataque))
    e[:a] = np.linspace(0, 1, a)
    caida = caida or n / SR
    e[a:] *= np.exp(-np.arange(n - a) / (SR * caida / 4))
    return e


def _cuadrada(f, t, ciclo=0.5):
    fase = np.cumsum(np.broadcast_to(f, t.shape) / SR) % 1.0
    return np.where(fase < ciclo, 1.0, -1.0)


def _seno(f, t):
    return np.sin(2 * np.pi * np.cumsum(np.broadcast_to(f, t.shape) / SR))


def _ruido(n, color=1.0):
    r = np.random.uniform(-1, 1, n)
    if color < 1.0:                     # ruido "grave" (media movil = paso bajo)
        v = max(1, int(1 / color))
        r = np.convolve(r, np.ones(v) / v, mode="same")
        r /= max(1e-6, np.abs(r).max())
    return r


def _sweep(f0, f1, dur, forma="cuadrada", curva=2.0):
    t = _t(dur)
    x = np.linspace(0, 1, len(t)) ** curva
    f = f0 + (f1 - f0) * x
    return (_cuadrada(f, t, 0.3) if forma == "cuadrada" else _seno(f, t)), t


def _mezcla(*partes):
    n = max(len(p) for p in partes)
    out = np.zeros(n)
    for p in partes:
        out[: len(p)] += p
    return out


def _crear():
    s = {}
    # --- menus
    t = _t(0.05); s["menu_mover"] = _cuadrada(880, t, 0.25) * _env(len(t)) * 0.35
    a = _cuadrada(660, _t(0.07), 0.5) * 0.4
    b = _cuadrada(990, _t(0.12), 0.5) * _env(int(SR * 0.12)) * 0.4
    s["menu_ok"] = np.concatenate([a, b])
    s["menu_atras"] = _sweep(600, 250, 0.15)[0] * _env(int(SR * 0.15)) * 0.35
    # --- combate
    n = int(SR * 0.12)
    s["aire"] = _ruido(n, 0.35) * np.sin(np.linspace(0, np.pi, n)) * 0.45          # whoosh
    n = int(SR * 0.16)
    golpe_ruido = _ruido(n) * _env(n, 0.001, 0.06)
    golpe_tono = _sweep(180, 55, 0.16, "seno")[0] * _env(n, 0.001, 0.14)
    s["golpe"] = _mezcla(golpe_ruido * 0.7, golpe_tono * 0.9)
    n = int(SR * 0.35)
    s["golpe_fuerte"] = _mezcla(_ruido(n, 0.6) * _env(n, 0.001, 0.2),
                                _sweep(140, 35, 0.35, "seno")[0] * _env(n, 0.001, 0.3) * 1.2)
    n = int(SR * 0.12)
    s["bloqueo"] = _mezcla(_cuadrada(1250, _t(0.12), 0.5) * _env(n, 0.001, 0.05) * 0.4,
                           _ruido(n) * _env(n, 0.001, 0.02) * 0.4)
    s["salto"] = _sweep(220, 520, 0.12, curva=0.6)[0] * _env(int(SR * 0.12)) * 0.25
    # --- especiales
    w, _ = _sweep(200, 1400, 0.35, curva=1.5); s["carga"] = w * np.linspace(0.1, 0.5, len(w))
    n = int(SR * 0.45)
    w, _ = _sweep(900, 300, 0.45); s["proyectil"] = _mezcla(w * _env(n, 0.002, 0.4) * 0.4,
                                                          _ruido(n, 0.3) * _env(n, 0.01, 0.3) * 0.3)
    t = _t(0.6)
    vib = 1200 + 300 * np.sin(2 * np.pi * 40 * t)
    s["rayo"] = (_cuadrada(vib, t, 0.5) * 0.25 + _ruido(len(t)) * 0.15) * _env(len(t), 0.005, 0.6)
    n = int(SR * 0.7)
    crack = _ruido(n) * _env(n, 0.001, 0.08)
    retumbo = _ruido(n, 0.05) * _env(n, 0.02, 0.7)
    s["trueno"] = _mezcla(crack * 0.8, retumbo * 1.0)
    n = int(SR * 0.6)
    s["sismo"] = _mezcla(_sweep(70, 30, 0.6, "seno")[0] * _env(n, 0.005, 0.6) * 1.2,
                         _ruido(n, 0.08) * _env(n, 0.005, 0.5) * 0.8)
    t = _t(0.25)
    s["estrella"] = _mezcla(*[_cuadrada(f, t, 0.5) * _env(len(t), 0.001, 0.2) * 0.18
                              for f in (1320, 1760, 2640)])
    # --- anuncios
    s["cuenta"] = _cuadrada(523, _t(0.15), 0.5) * _env(int(SR * 0.15), 0.002, 0.2) * 0.35
    notas = [523, 659, 784, 1047]
    s["lucha"] = np.concatenate([_cuadrada(f, _t(0.09), 0.5) * 0.35 for f in notas[:-1]] +
                                [_cuadrada(1047, _t(0.4), 0.5) * _env(int(SR * 0.4)) * 0.4])
    n = int(SR * 1.2)
    w, _ = _sweep(400, 40, 1.2, curva=0.7)
    s["ko"] = _mezcla(w * _env(n, 0.002, 1.2) * 0.4, _ruido(n, 0.1) * _env(n, 0.002, 0.8) * 0.8)
    melodia = [784, 659, 784, 1047, 988, 1047, 1319]
    s["victoria"] = np.concatenate([_cuadrada(f, _t(0.12), 0.5) * _env(int(SR * 0.12), 0.002, 0.3) * 0.3
                                    for f in melodia])
    n = int(SR * 0.18)
    s["foto"] = _mezcla(_ruido(n) * _env(n, 0.001, 0.03) * 0.6,
                        _ruido(n) * np.r_[np.zeros(n // 2), _env(n - n // 2, 0.001, 0.04)] * 0.5)
    s["creado"] = s["victoria"]
    # --- espadas de energia (escenario espacio)
    t = _t(0.28)
    zumbido = _seno(90 + 25 * np.sin(2 * np.pi * 7 * t), t) + 0.5 * _cuadrada(180, t, 0.5)
    barrido = _sweep(260, 120, 0.28, "seno")[0]
    s["espada"] = (zumbido * 0.25 + barrido * 0.35) * np.sin(np.linspace(0, np.pi, len(t)))
    n = int(SR * 0.3)
    s["espada_golpe"] = _mezcla(_sweep(1600, 300, 0.3)[0] * _env(n, 0.001, 0.25) * 0.3,
                                _ruido(n) * _env(n, 0.001, 0.08) * 0.5,
                                _seno(110, _t(0.3)) * _env(n, 0.001, 0.3) * 0.5)
    n = int(SR * 0.35)
    s["espada_choque"] = _mezcla(*[_cuadrada(f, _t(0.35), 0.5) * _env(n, 0.001, 0.3) * 0.15
                                   for f in (1480, 1975, 2490)], _ruido(n) * _env(n, 0.001, 0.05) * 0.5)
    return s


def _musica_sintetica(bpm=150, compases=4, tipo="pelea"):
    """Bucle chiptune: bajo + arpegio + bateria."""
    negra = 60 / bpm
    paso = negra / 2                                  # corcheas
    if tipo == "pelea":
        acordes = [(110, [440, 523, 659]), (87.3, [349, 440, 523]),
                   (98, [392, 494, 587]), (82.4, [330, 415, 494])]
    else:
        acordes = [(130.8, [523, 659, 784]), (110, [440, 523, 659]),
                   (87.3, [349, 440, 523]), (98, [392, 494, 587])]
    trozos = []
    for c in range(compases):
        bajo_f, arp = acordes[c % len(acordes)]
        for k in range(8):
            t = _t(paso)
            n = len(t)
            bajo = _cuadrada(bajo_f * (2 if k % 2 else 1), t, 0.5) * _env(n, 0.002, paso * 1.5) * 0.22
            nota = arp[k % 3] * (2 if (k // 3) % 2 else 1)
            ar = _cuadrada(nota, t, 0.25) * _env(n, 0.002, paso * 0.8) * 0.10
            bat = np.zeros(n)
            if tipo == "pelea" and k % 4 == 0:        # bombo
                bat += _sweep(150, 40, paso, "seno")[0] * _env(n, 0.001, paso * 0.6) * 0.5
            if k % 4 == 2:                            # caja
                bat += _ruido(n) * _env(n, 0.001, 0.06) * 0.22
            if tipo == "pelea":                       # charles
                hh = np.zeros(n); m = int(SR * 0.02)
                hh[:m] = _ruido(m) * np.linspace(1, 0, m) * 0.08
                bat += hh
            trozos.append(bajo + ar + bat)
    return np.concatenate(trozos)


def _musica_tema(tipo):
    """Bucles distintos por escenario."""
    if tipo == "normal":            # cafeteria: boogie alegre en mayor
        bpm, acordes = 168, [(130.8, [523, 659, 784]), (130.8, [523, 659, 784]),
                             (174.6, [698, 880, 1047]), (196.0, [784, 988, 1175])]
        paso_bajo, ciclo, bat = [1, 1.25, 1.5, 1.68], 0.5, "swing"
    elif tipo == "gotico":          # noche gotica: menor, lento, tipo organo
        bpm, acordes = 104, [(110.0, [440, 523, 659]), (87.3, [349, 440, 523]),
                             (73.4, [294, 349, 440]), (82.4, [330, 415, 494])]
        paso_bajo, ciclo, bat = [1, 1, 1.5, 1], 0.5, "lento"
    else:                           # espacio: sinte menor con eco
        bpm, acordes = 128, [(73.4, [587, 698, 880]), (58.3, [466, 587, 698]),
                             (65.4, [523, 659, 784]), (55.0, [440, 554, 659])]
        paso_bajo, ciclo, bat = [1, 2, 1, 2], 0.125, "sinte"
    paso = 60 / bpm / 2
    trozos = []
    for c in range(8):
        bajo_f, arp = acordes[c % len(acordes)]
        for k in range(8):
            t = _t(paso)
            n = len(t)
            fb = bajo_f * paso_bajo[k % 4]
            if tipo == "gotico":
                bajo = (_seno(fb, t) * 0.6 + _cuadrada(fb * 2, t, 0.5) * 0.15) * 0.3
                ar = sum(_seno(f, t) for f in arp) / 3 * 0.10 + _seno(arp[k % 3] * 2, t) * _env(n, 0.002, paso) * 0.06
            else:
                bajo = _cuadrada(fb, t, 0.5) * _env(n, 0.002, paso * 1.4) * 0.2
                ar = _cuadrada(arp[k % 3] * (2 if tipo == "espacio" and k % 2 else 1), t, ciclo) \
                    * _env(n, 0.002, paso * 0.7) * 0.09
            b = np.zeros(n)
            if bat != "lento" and k % 4 == 0:
                b += _sweep(150, 40, paso, "seno")[0] * _env(n, 0.001, paso * 0.6) * 0.45
            if k % 4 == 2:
                b += _ruido(n) * _env(n, 0.001, 0.05) * (0.12 if bat == "lento" else 0.22)
            if bat in ("swing", "sinte"):
                m = int(SR * 0.015)
                b[:m] += _ruido(m) * np.linspace(1, 0, m) * 0.07
            trozos.append(bajo + ar + b)
    onda = np.concatenate(trozos)
    if tipo == "espacio":           # eco
        d = int(SR * paso * 3)
        eco = np.zeros_like(onda)
        eco[d:] = onda[:-d] * 0.35
        onda = onda + eco
    return onda


def _a_sound(onda, volumen=1.0):
    freq, _fmt, canales = pygame.mixer.get_init()
    if freq != SR:                                    # remuestreo sencillo
        x = np.linspace(0, len(onda) - 1, int(len(onda) * freq / SR))
        onda = np.interp(x, np.arange(len(onda)), onda)
    onda = np.clip(onda * volumen, -1, 1)
    datos = (onda * 32000).astype(np.int16)
    if canales == 2:
        datos = np.column_stack([datos, datos])
    return pygame.sndarray.make_sound(np.ascontiguousarray(datos))


def _archivo(carpeta, nombre):
    for ext in (".wav", ".ogg", ".mp3"):
        p = C.ASSETS_DIR / carpeta / (nombre + ext)
        if p.exists():
            return p
    return None


# ------------------------------------------------------------------ API publica
def preiniciar():
    """Llamar ANTES de pygame.init() para tener poca latencia (Raspberry Pi)."""
    try:
        pygame.mixer.pre_init(44100, -16, 2, 512)
    except Exception:
        pass


def iniciar():
    global _ok, _canal_musica
    try:
        if not pygame.mixer.get_init():
            pygame.mixer.init(44100, -16, 2, 512)
        pygame.mixer.set_num_channels(24)
        pygame.mixer.set_reserved(1)
        _canal_musica = pygame.mixer.Channel(0)
    except Exception as e:
        print("[sonido] sin audio:", e)
        _ok = False
        return
    for nombre, onda in _crear().items():
        p = _archivo("sonidos", nombre)
        try:
            _sonidos[nombre] = pygame.mixer.Sound(str(p)) if p else _a_sound(onda)
            _sonidos[nombre].set_volume(C.VOLUMEN_SFX)
        except Exception as e:
            print("[sonido] no se pudo cargar", nombre, e)
    _ok = True


def play(nombre, volumen=1.0, variar=True):
    if not _ok or nombre not in _sonidos:
        return
    snd = _sonidos[nombre]
    canal = pygame.mixer.find_channel(True)
    if canal is None:
        return
    v = C.VOLUMEN_SFX * volumen * (random.uniform(0.85, 1.0) if variar else 1.0)
    canal.set_volume(v)
    canal.play(snd)


_cache_musica = {}


def musica(tipo):
    """tipo: 'menu' | 'pelea' | None (parar)."""
    global _musica_actual
    if not _ok or tipo == _musica_actual:
        return
    _musica_actual = tipo
    _canal_musica.stop()
    pygame.mixer.music.stop()
    if tipo is None:
        return
    p = _archivo("musica", tipo)
    if p:
        pygame.mixer.music.load(str(p))
        pygame.mixer.music.set_volume(C.VOLUMEN_MUSICA)
        pygame.mixer.music.play(-1)
        return
    if tipo not in _cache_musica:
        if tipo in ("normal", "gotico", "espacio"):
            _cache_musica[tipo] = _a_sound(_musica_tema(tipo))
        else:
            bpm = 150 if tipo == "pelea" else 110
            _cache_musica[tipo] = _a_sound(_musica_sintetica(bpm, 8, tipo))
    _canal_musica.set_volume(C.VOLUMEN_MUSICA)
    _canal_musica.play(_cache_musica[tipo], loops=-1)
