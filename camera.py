"""Captura de camara (USB o DroidCam por WiFi) y deteccion de caras con OpenCV."""
import re
import sys
import threading
import time
import urllib.request

import cv2
import numpy as np
import pygame


def _urls(indice):
    """'192.168.1.162:4747' -> URLs de video que prueba (DroidCam Android/iOS, IP Webcam).

    /video/force/... echa a cualquier otro cliente que tenga la camara cogida
    (DroidCam solo admite UNA conexion: si el cliente de PC esta conectado, da "busy")."""
    s = str(indice).strip()
    if not s.startswith("http"):
        s = "http://" + s
    resto = s.split("://", 1)[1]
    if "/" in resto.rstrip("/"):           # ya trae ruta (/video, /mjpegfeed...)
        return [s]
    if ":" not in resto:
        s += ":4747"                       # puerto por defecto de DroidCam
    s = s.rstrip("/")
    return [s + "/video", s + "/video/force/640x480", s + "/mjpegfeed", s + "/videofeed"]


def _host_puerto(indice):
    s = str(indice).strip()
    s = s.split("://", 1)[-1].split("/", 1)[0]
    host, _, puerto = s.partition(":")
    return host, int(puerto or 4747)


def _ip_rara(host):
    """Avisa de IPs que no son de red local (p. ej. 198.162... en vez de 192.168...)."""
    p = host.split(".")
    if len(p) != 4 or not all(x.isdigit() for x in p):
        return False
    a, b = int(p[0]), int(p[1])
    return not (a in (10, 127) or (a == 192 and b == 168) or (a == 172 and 16 <= b <= 31))


def _alcanzable(host, puerto, timeout=2.0):
    """Comprobacion rapida: hay algo escuchando en ip:puerto?"""
    import socket
    try:
        with socket.create_connection((host, puerto), timeout=timeout):
            return ""
    except socket.timeout:
        return "no contesta (movil apagado/bloqueado, otra WiFi, o IP mal escrita)"
    except ConnectionRefusedError:
        return "el movil responde pero la app no escucha en ese puerto (abre DroidCam y deja la pantalla encendida)"
    except OSError as e:
        return f"no se puede llegar ({e})"


def fuentes_configuradas(valor):
    """'192.168.1.133:4747, 192.168.1.181:4747' o '0' -> lista de fuentes."""
    out = []
    for parte in str(valor).split(","):
        parte = parte.strip()
        if parte:
            out.append(int(parte) if parte.isdigit() else parte)
    return out or [0]


class Camara:
    def __init__(self, indice=0):
        self.fuentes = indice if isinstance(indice, list) else fuentes_configuradas(indice)
        self.indice = self.fuentes[0]
        self.cap = None            # camara local (cv2)
        self._resp = None          # conexion HTTP (DroidCam)
        self._buf = b""
        self.fuente = None
        self.error = ""
        self.diagnostico = []      # una linea por fuente probada
        self.frame = None
        self._crudo = None
        self._activo = False
        self._cerrado = False
        self._hilo = None
        try:
            self.detector = cv2.CascadeClassifier(
                cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
            )
        except AttributeError:      # OpenCV 5 sin el modulo clasico de caras
            print("[camara] AVISO: instala  pip install \"opencv-python<5\"  para detectar caras")
            self.detector = None

    # ------------------------------------------------------------ conexion
    def conectar(self):
        """Prueba las fuentes en orden (CAMERA_INDEX=ip1,ip2,0) y se queda con la primera
        que da imagen. Puede tardar unos segundos."""
        self.diagnostico = []
        for fuente in self.fuentes:
            if self._cerrado:
                return False
            self.indice = fuente
            ok = self._conectar_local() if isinstance(fuente, int) else self._conectar_http()
            self.diagnostico.append(f"{fuente}: {'OK' if ok else self.error}")
            print("[camara]", self.diagnostico[-1])
            if ok:
                break
        else:
            self.error = " || ".join(self.diagnostico)
            return False
        if self._cerrado:
            self.cerrar()
            return False
        self._activo = True
        objetivo = self._bucle_local if self.cap is not None else self._bucle_http
        self._hilo = threading.Thread(target=objetivo, daemon=True)
        self._hilo.start()
        print("[camara] conectada a:", self.fuente)
        return True

    def _conectar_local(self):
        if sys.platform.startswith("win"):
            backends = [cv2.CAP_DSHOW, cv2.CAP_MSMF, cv2.CAP_ANY]
        else:
            backends = [cv2.CAP_ANY]
        for b in backends:
            cap = cv2.VideoCapture(self.indice, b)
            if cap.isOpened() and cap.read()[0]:
                cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
                self.cap, self.fuente = cap, f"camara {self.indice}"
                return True
            cap.release()
        self.error = f"no hay imagen en la camara {self.indice}"
        return False

    def _conectar_http(self):
        """DroidCam/IP Webcam: lee el MJPEG directamente (sin FFMPEG)."""
        host, puerto = _host_puerto(self.indice)
        aviso = f" (OJO: {host} no parece una IP de casa, deberia empezar por 192.168.)" \
            if _ip_rara(host) else ""
        motivo = _alcanzable(host, puerto)
        if motivo:
            self.error = f"{host}:{puerto} {motivo}{aviso}"
            return False
        errores = []
        for url in _urls(self.indice):
            print("[camara] probando:", url)
            try:
                resp = urllib.request.urlopen(url, timeout=6)
                tipo = resp.headers.get("Content-Type", "")
                primer = resp.read(4096)
            except Exception as e:
                errores.append(f"{url.rsplit(':', 1)[-1]} -> {e}")
                print("[camara]   error:", e)
                continue
            if "multipart" in tipo or b"\xff\xd8" in primer:
                self._resp, self._buf, self.fuente = resp, primer, url
                return True
            texto = re.sub(r"<[^>]+>", " ", primer.decode("utf-8", "ignore"))
            texto = " ".join(texto.split())[:120]
            print(f"[camara]   respuesta no valida ({tipo}): {texto}")
            errores.append(texto or tipo)
            resp.close()
        unidos = " | ".join(errores).lower()
        if "ocupado" in unidos or "busy" in unidos:
            self.error = "DroidCam ocupado: cierra el cliente DroidCam del PC y pestanas del navegador"
        elif errores:
            self.error = "responde pero no da video: " + errores[0][:80]
        else:
            self.error = "sin respuesta"
        return False

    # ------------------------------------------------------------ lectura
    def _bucle_local(self):
        while self._activo and self.cap is not None:
            ok, f = self.cap.read()
            if ok:
                self._crudo = f
            else:
                time.sleep(0.05)

    def _bucle_http(self):
        """Lee el flujo MJPEG y se queda siempre con el ultimo frame."""
        buf = self._buf
        while self._activo:
            a = buf.find(b"\xff\xd8")
            b = buf.find(b"\xff\xd9", a + 2) if a != -1 else -1
            if a != -1 and b != -1:
                jpg, buf = buf[a:b + 2], buf[b + 2:]
                img = cv2.imdecode(np.frombuffer(jpg, np.uint8), cv2.IMREAD_COLOR)
                if img is not None:
                    self._crudo = img
                continue
            if a == -1:
                buf = buf[-2:]
            elif len(buf) > 3_000_000:
                buf = b""
            try:
                chunk = self._resp.read(8192)
            except Exception as e:
                print("[camara] conexion perdida:", e)
                break
            if not chunk:
                print("[camara] el movil cerro la conexion")
                break
            buf += chunk
        self._activo = False

    def abierta(self):
        return self._activo

    def leer(self):
        if self._crudo is not None:
            self.frame = cv2.flip(self._crudo, 1)  # efecto espejo
        return self.frame

    def detectar_caras(self, frame, escala=0.5):
        """Devuelve hasta 2 caras (x, y, w, h) ordenadas de izquierda a derecha."""
        if self.detector is None:
            return []
        gris = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        if escala != 1.0:
            gris = cv2.resize(gris, None, fx=escala, fy=escala)
        gris = cv2.equalizeHist(gris)
        caras = self.detector.detectMultiScale(
            gris, scaleFactor=1.2, minNeighbors=5, minSize=(int(80 * escala), int(80 * escala))
        )
        caras = [tuple(int(v / escala) for v in c) for c in caras]
        caras = sorted(caras, key=lambda c: c[2] * c[3], reverse=True)[:2]
        return sorted(caras, key=lambda c: c[0])

    def guardar_recorte(self, frame, cara, ruta, factor=3.0, bajar=0.5):
        """Recorta un cuadrado alrededor de la cara. Con factor=3 y bajar=0.5 entra
        el pelo entero (para saber si es largo), los hombros y el color de la ropa."""
        x, y, w, h = cara
        lado = int(max(w, h) * factor)
        cx, cy = x + w // 2, y + h // 2 + int(h * bajar)
        x0, y0 = cx - lado // 2, cy - lado // 2
        H, W = frame.shape[:2]
        x0c, y0c = max(0, x0), max(0, y0)
        x1c, y1c = min(W, x0 + lado), min(H, y0 + lado)
        recorte = frame[y0c:y1c, x0c:x1c]
        recorte = cv2.copyMakeBorder(
            recorte, y0c - y0, (y0 + lado) - y1c, x0c - x0, (x0 + lado) - x1c,
            cv2.BORDER_REPLICATE,
        )
        recorte = cv2.resize(recorte, (512, 512), interpolation=cv2.INTER_AREA)
        cv2.imwrite(str(ruta), recorte, [cv2.IMWRITE_JPEG_QUALITY, 90])

    @staticmethod
    def a_surface(frame):
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        return pygame.image.frombuffer(rgb.tobytes(), (rgb.shape[1], rgb.shape[0]), "RGB")

    def cerrar(self):
        self._cerrado = True
        self._activo = False
        if self._resp is not None:
            try:
                self._resp.close()
            except Exception:
                pass
            self._resp = None
        if self._hilo is not None:
            self._hilo.join(timeout=1.5)
        if self.cap is not None:
            self.cap.release()
            self.cap = None
