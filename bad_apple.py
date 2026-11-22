#!/usr/bin/env python3
"""
bad_apple.py — Reproduce cualquier video como arte ASCII, con audio sincronizado.

Inspirado en el clásico "Bad Apple!! en ASCII": ffmpeg decodifica el video a
cuadros pequeños, cada píxel se convierte en un carácter y el resultado se
dibuja en una ventana de Tkinter (o en la terminal). ffplay reproduce el audio
y un reloj mantiene ambos sincronizados.

Autor: Zaphkiel — Licencia MIT (ver LICENSE y README.md)

Requisitos:
  - Python 3.9+ (solo librería estándar)
  - ffmpeg, ffprobe y ffplay en el PATH  (https://ffmpeg.org/download.html)
    En Windows:  winget install ffmpeg

Uso:
  python bad_apple.py                          # abre el VIDEO de la configuración
  python bad_apple.py otro_video.mp4
  python bad_apple.py --estilo braille         # 8 veces más detalle
  python bad_apple.py --estilo bordes          # contornos con / | \\ -
  python bad_apple.py --cols 150 --multicolor  # cada letra con su color
  python bad_apple.py --terminal --bucle       # en la consola, repitiendo
  python bad_apple.py --precargar              # convierte todo antes (más fluido)
  python bad_apple.py --exportar salida.mp4    # guarda la animación como video

Teclas (ventana):   Espacio = pausa      ← / → = -5 / +5 s    ↑ / ↓ = +30 / -30 s
                    Inicio  = al principio   F11 = pantalla completa
                    + / -   = letra      0 = ajuste automático   Esc = salir
                    Clic en la barra de progreso = ir a ese punto
Teclas (terminal):  Espacio = pausa   ← → ↑ ↓ Inicio = saltar   Q o Esc = salir
"""

import argparse
import gzip
import hashlib
import json
import math
import os
import queue
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time

# =========================================================================== #
#  CONFIGURACIÓN — cambia estos valores a tu gusto y guarda el archivo.
#  (Lo que escribas en el comando, p. ej. --cols 140, tiene prioridad.)
# =========================================================================== #
VIDEO          = "badapple.mp4"  # video que se abre si no escribes ninguno
ESTILO         = "brillo"    # "brillo" (rampa), "bordes" (/ | \ -) o "braille" (⣿)
COLUMNAS       = 100         # ancho en caracteres: más = más detalle (60-200)
TAMANO_LETRA   = 7           # tamaño de letra inicial en la ventana (4-12)
FUENTE         = None        # None = automática. Ej: "Consolas", "Cascadia Mono"
COLOR_TEXTO    = "#ffffff"   # "#rrggbb" o un nombre: "verde", "ambar", "red"...
COLOR_FONDO    = "#000000"   # negro
FPS            = None        # None = los del video. Ej: 24 o 30
RAMPA          = " .:-=+*#%@"  # caracteres de oscuro a claro (brillo y bordes)
INVERTIR       = False       # True = intercambia claro y oscuro
SENSIBILIDAD   = 30          # estilo bordes: más bajo = más contornos (10-80)
CON_AUDIO      = True        # False = sin sonido
RETRASO_AUDIO  = 0.0         # ajuste fino (s): súbelo si el sonido va adelantado
EN_TERMINAL    = False       # True = dibuja en la consola, no en ventana
MULTICOLOR     = False       # True = cada carácter con el color del video
BUCLE          = False       # True = vuelve a empezar al terminar
AJUSTE_AUTO    = True        # True = la letra se adapta al tamaño disponible
PRECARGAR      = False       # True = convierte todo antes de reproducir
SALTO          = 5           # segundos que saltan las flechas ← →
SALTO_LARGO    = 30          # segundos que saltan las flechas ↑ ↓
CARPETA_CACHE  = ".cache_ascii"  # dónde se guardan los videos precargados
ALTO_EXPORTAR  = 720         # alto aproximado (px) del video con --exportar
# =========================================================================== #

EN_WINDOWS = sys.platform == "win32"
# .exe compilado "sin consola" (doble clic): no hay dónde escribir mensajes.
SIN_CONSOLA = sys.stdout is None
# Que ffmpeg/ffplay no abran ventanas negras de consola en Windows.
OCULTO = {"creationflags": subprocess.CREATE_NO_WINDOW} if EN_WINDOWS else {}
ESTILOS = ("brillo", "bordes", "braille")
VERSION_CACHE = 2
FIN = None          # señal de "se acabó el video" que viaja por la cola
NADA = object()     # "todavía no toca dibujar nada"
VACIOS = (" ", "\u2800")   # caracteres que no se ven (no necesitan color)

NOMBRES_COLOR = {
    "blanco": "#ffffff", "white": "#ffffff",
    "negro": "#000000", "black": "#000000",
    "gris": "#808080", "gray": "#808080", "grey": "#808080",
    "rojo": "#ff0000", "red": "#ff0000",
    "verde": "#00ff00", "green": "#00ff00", "lima": "#00ff00", "lime": "#00ff00",
    "matrix": "#00ff66",
    "azul": "#0000ff", "blue": "#0000ff",
    "amarillo": "#ffff00", "yellow": "#ffff00",
    "cian": "#00ffff", "cyan": "#00ffff",
    "magenta": "#ff00ff", "fucsia": "#ff00ff",
    "naranja": "#ffa500", "orange": "#ffa500",
    "rosa": "#ff77cc", "pink": "#ff77cc",
    "morado": "#b066ff", "purple": "#b066ff", "violeta": "#b066ff",
    "dorado": "#ffd700", "gold": "#ffd700",
    "ambar": "#ffb000", "amber": "#ffb000",
}


# --------------------------------------------------------------------------- #
#  Utilidades
# --------------------------------------------------------------------------- #
def carpeta_programa():
    """Carpeta de bad_apple.py, o del .exe si está compilado con PyInstaller."""
    if getattr(sys, "frozen", False):
        return os.path.dirname(os.path.abspath(sys.executable))
    return os.path.dirname(os.path.abspath(__file__))


def buscar_herramienta(nombre):
    """Busca ffmpeg/ffprobe/ffplay en el PATH o junto al programa."""
    ruta = shutil.which(nombre)
    if ruta:
        return ruta
    base = carpeta_programa()
    for sub in ("", "ffmpeg", os.path.join("ffmpeg", "bin")):
        for ext in ((".exe", "") if EN_WINDOWS else ("",)):
            candidata = os.path.join(base, sub, nombre + ext)
            if os.path.isfile(candidata):
                return candidata
    return None


def consola_propia():
    """True si la consola se abrió solo para este programa (doble clic)."""
    if not EN_WINDOWS:
        return False
    try:
        import ctypes
        lista = (ctypes.c_uint * 16)()
        n = ctypes.windll.kernel32.GetConsoleProcessList(lista, 16)
    except Exception:
        return False
    limite = 2 if getattr(sys, "frozen", False) else 1   # el .exe usa 2 procesos
    return 0 < n <= limite


def ocultar_consola():
    try:
        import ctypes
        ctypes.windll.user32.ShowWindow(ctypes.windll.kernel32.GetConsoleWindow(), 0)
    except Exception:
        pass


def resolver_color(texto):
    """'#abc', '#aabbcc', 'aabbcc' o un nombre conocido -> '#aabbcc' (o None)."""
    t = texto.strip().lower().translate(str.maketrans("áéíóú", "aeiou"))
    if t in NOMBRES_COLOR:
        return NOMBRES_COLOR[t]
    h = t.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    if len(h) == 6 and all(c in "0123456789abcdef" for c in h):
        return "#" + h
    return None


def color_rgb(hexa):
    return tuple(int(hexa[i:i + 2], 16) for i in (1, 3, 5))


def ansi_color(hexa):
    return "\033[38;2;%d;%d;%dm" % color_rgb(hexa)


def mmss(seg):
    seg = max(0, int(seg))
    return f"{seg // 60:02d}:{seg % 60:02d}"


def mostrar_progreso(hechos, total, t0, prefijo):
    if SIN_CONSOLA:
        return
    total = max(total, hechos, 1)
    frac = hechos / total
    barra = "#" * int(frac * 30)
    pasado = time.perf_counter() - t0
    resto = pasado / frac - pasado if frac > 0 else 0
    sys.stdout.write(f"\r  {prefijo} [{barra:<30}] {frac * 100:5.1f}%  "
                     f"{hechos}/{total}  quedan {mmss(resto)} ")
    sys.stdout.flush()


def info_video(ffprobe, ruta):
    """Devuelve (ancho, alto, fps, duración, tiene_audio) usando ffprobe."""
    cmd = [ffprobe, "-v", "error",
           "-show_entries", "stream=codec_type,width,height,r_frame_rate:format=duration",
           "-of", "json", ruta]
    datos = json.loads(subprocess.check_output(cmd, stdin=subprocess.DEVNULL, **OCULTO))
    flujos = datos.get("streams", [])
    v = next((s for s in flujos if s.get("codec_type") == "video"), None)
    if v is None:
        sys.exit(f"El archivo no tiene video: {ruta}")
    num, den = v.get("r_frame_rate", "30/1").split("/")
    fps = float(num) / float(den) if float(den or 0) else 30.0
    dur = float(datos.get("format", {}).get("duration", 0) or 0)
    tiene_audio = any(s.get("codec_type") == "audio" for s in flujos)
    return int(v["width"]), int(v["height"]), fps or 30.0, dur, tiene_audio


def elegir_familia(root, estilo, preferida):
    """Elige una fuente monoespaciada instalada. Para braille hace falta una
    que tenga esos caracteres al mismo ancho que el resto (Consolas no)."""
    import tkinter.font as tkfont
    familias = set(tkfont.families(root))
    if preferida:
        if preferida in familias:
            return preferida
        print(f"Aviso: no encontré la fuente {preferida!r}; uso una automática.")
    if estilo == "braille":
        candidatas = ("Cascadia Mono", "Cascadia Code", "DejaVu Sans Mono",
                      "Noto Sans Mono", "Consolas", "Courier New")
    else:
        candidatas = ("Consolas", "Cascadia Mono", "DejaVu Sans Mono", "Menlo",
                      "Courier New", "Courier")
    return next((f for f in candidatas if f in familias), "Courier")


# --------------------------------------------------------------------------- #
#  Conversión: bytes de un cuadro -> texto (o texto con colores)
# --------------------------------------------------------------------------- #
def tabla_caracteres(rampa, invertir):
    """Tabla de 256 entradas: brillo (0-255) -> carácter."""
    r = rampa[::-1] if invertir else rampa
    n = len(r)
    return [r[min(n - 1, v * n // 256)] for v in range(256)]


def tabla_bordes(sensibilidad):
    """(gx, gy) del filtro Sobel (con sesgo 128) -> carácter del borde o ''."""
    tabla = [""] * 65536
    for a in range(256):
        dx = a - 128
        for b in range(256):
            dy = b - 128
            if abs(dx) + abs(dy) < sensibilidad:
                continue
            # Las celdas son el doble de altas que anchas: se corrige el ángulo.
            ang = math.degrees(math.atan2(dy * 0.5, dx)) % 180
            if ang < 22.5 or ang >= 157.5:
                ch = "|"            # el brillo cambia en horizontal: borde vertical
            elif ang < 67.5:
                ch = "/"
            elif ang < 112.5:
                ch = "-"
            else:
                ch = "\\"
            tabla[a << 8 | b] = ch
    return tabla


# Puntos braille: (columna, fila, bit) y orden de una trama de Bayer de 2x4
# para simular grises con puntos (ver https://es.wikipedia.org/wiki/Braille).
PUNTOS_BRAILLE = ((0, 0, 0x01), (0, 1, 0x02), (0, 2, 0x04), (1, 0, 0x08),
                  (1, 1, 0x10), (1, 2, 0x20), (0, 3, 0x40), (1, 3, 0x80))
TRAMA_BRAILLE = {(0, 0): 0, (1, 0): 4, (0, 1): 6, (1, 1): 2,
                 (0, 2): 1, (1, 2): 5, (0, 3): 7, (1, 3): 3}

NIVELES = [v * 255 // 7 for v in range(8)]   # 8 niveles por canal = 512 colores
SOBEL_X = "-1 0 1 -2 0 2 -1 0 1"
SOBEL_Y = "-1 -2 -1 0 0 0 1 2 1"


def color_de_indice(i):
    return NIVELES[i >> 6], NIVELES[(i >> 3) & 7], NIVELES[i & 7]


def escapar_ass(texto):
    """Texto plano -> texto seguro para un subtítulo ASS (libass)."""
    return (texto.replace("\\", "\u2216").replace("{", "\\{").replace("}", "\\}")
                 .replace(" ", "\\h").replace("\n", "\\N"))


class Conversor:
    """Convierte cuadros crudos de ffmpeg al formato que necesita cada salida.

    estilo: 'brillo' (rampa de caracteres), 'bordes' (contornos + rampa) o
            'braille' (cada carácter = 2x4 puntos).
    salida: 'texto' (str), 'tk' (lista texto/etiqueta para un Text de Tkinter),
            'ansi' (str con colores de terminal) o 'ass' (subtítulo ASS).

    ffmpeg entrega en un solo cuadro todos los "planos" que hacen falta, uno
    debajo de otro (vstack): color, brillo, gradientes Sobel...
    """

    def __init__(self, cols, filas, rampa, invertir, multicolor, salida,
                 estilo="brillo", sensibilidad=SENSIBILIDAD):
        self.cols, self.filas = cols, filas
        self.multicolor, self.salida, self.estilo = multicolor, salida, estilo
        self.tabla = tabla_caracteres(rampa, invertir)
        self.traduccion = {i: c for i, c in enumerate(self.tabla)}
        self.pix_fmt = "rgb24" if multicolor else "gray"
        n = cols * filas
        planos = {"brillo": 1, "bordes": 3, "braille": 8}[estilo]
        if multicolor:   # + un plano de color; braille: color de 2c x f
            planos += 2 if estilo == "braille" else 1
        self.tam = n * planos * (3 if multicolor else 1)
        if estilo == "bordes":
            self.bordes = tabla_bordes(sensibilidad)
        if estilo == "braille":
            self.tablas_braille = []
            for dx, dy, bit in PUNTOS_BRAILLE:
                umbral = (TRAMA_BRAILLE[dx, dy] + 0.5) * 32
                encendido = (lambda v: 255 - v > umbral) if invertir else (lambda v: v > umbral)
                self.tablas_braille.append(
                    (dx, dy, bytes(bit if encendido(v) else 0 for v in range(256))))
            self.traduccion_braille = {i: chr(0x2800 + i) for i in range(256)}
        self.codigos_ansi = ["\033[38;2;%d;%d;%dm" % color_de_indice(i) for i in range(512)]
        self.codigos_ass = ["{\\c&H%02X%02X%02X&}" % color_de_indice(i)[::-1] for i in range(512)]

    def filtro(self, fps):
        c, f = self.cols, self.filas
        esc = f"scale={c}:{f}:flags=area"
        sx = f"convolution=0m='{SOBEL_X}':0rdiv=0.125:0bias=128"
        sy = f"convolution=0m='{SOBEL_Y}':0rdiv=0.125:0bias=128"
        if self.estilo == "braille":
            alta = f"scale={2 * c}:{4 * f}:flags=area,format=gray"
            if not self.multicolor:
                g = alta
            else:
                g = (f"split[a][b];[a]{alta},format=rgb24[g];"
                     f"[b]{esc},format=rgb24,pad={2 * c}:{f}:0:0:black[k];[g][k]vstack=2")
        elif self.estilo == "bordes":
            sobel = f"split=3[l][a][b];[a]{sx}[x];[b]{sy}[y]"
            if not self.multicolor:
                g = f"{esc},format=gray,{sobel};[l][x][y]vstack=3"
            else:
                g = (f"{esc},split[k][g];[k]format=rgb24[k2];[g]format=gray,{sobel};"
                     "[l]format=rgb24[l2];[x]format=rgb24[x2];[y]format=rgb24[y2];"
                     "[k2][l2][x2][y2]vstack=4")
        else:
            if not self.multicolor:
                g = f"{esc},format=gray"
            else:
                g = (f"{esc},split[k][g];[k]format=rgb24[k2];"
                     "[g]format=gray,format=rgb24[g2];[k2][g2]vstack=2")
        return f"fps={fps},{g},format={self.pix_fmt}"

    def __call__(self, datos):
        c, f = self.cols, self.filas
        n = c * f
        colores = None
        if self.estilo == "braille":
            if self.multicolor:
                alta = datos[:n * 8 * 3][0::3]
                resto = datos[n * 8 * 3:]
                ancho = 2 * c * 3
                colores = b"".join(resto[y * ancho:y * ancho + c * 3] for y in range(f))
            else:
                alta = datos
            chars = self._braille(alta)
        else:
            if self.multicolor:
                colores, planos = datos[:n * 3], datos[n * 3:][0::3]
            else:
                planos = datos
            chars = planos[:n].decode("latin-1").translate(self.traduccion)
            if self.estilo == "bordes":
                # El borde se marca solo en la celda del lado claro: así la
                # línea sale de 1 carácter de grosor y no doble.
                tb = self.bordes
                chars = "".join([e if l > 127 and (e := tb[a << 8 | b]) else ch
                                 for l, a, b, ch in zip(planos[:n], planos[n:2 * n],
                                                        planos[2 * n:3 * n], chars)])
        return self._formatear(chars, colores)

    def _braille(self, alta):
        c, f = self.cols, self.filas
        ancho = 2 * c
        total = 0
        for dx, dy, tabla in self.tablas_braille:
            trozo = b"".join(alta[(y * 4 + dy) * ancho + dx:(y * 4 + dy + 1) * ancho:2]
                             for y in range(f))
            total += int.from_bytes(trozo.translate(tabla), "big")   # bits distintos: suma = OR
        return total.to_bytes(c * f, "big").decode("latin-1").translate(self.traduccion_braille)

    def _formatear(self, chars, colores):
        if colores is None:
            c = self.cols
            texto = "\n".join(chars[i:i + c] for i in range(0, len(chars), c))
            return escapar_ass(texto) if self.salida == "ass" else texto
        tramos = self._tramos(chars, colores)
        if self.salida == "tk":
            plano = []
            for t, col in tramos:
                plano += (t, "" if col is None else f"c{col}")
            return plano
        if self.salida == "ansi":
            return "".join((self.codigos_ansi[col] if col is not None else "") + t
                           for t, col in tramos)
        if self.salida == "ass":
            return "".join((self.codigos_ass[col] if col is not None else "") + escapar_ass(t)
                           for t, col in tramos)
        return "".join(t for t, _ in tramos)

    def _tramos(self, chars, colores):
        """Agrupa caracteres seguidos del mismo color: [(texto, color), ...]."""
        cols = self.cols
        tramos, actual, color = [], [], None
        for i, ch in enumerate(chars):
            if i and not i % cols:
                actual.append("\n")
            if ch not in VACIOS:                     # los espacios no tienen color
                j = 3 * i
                cc = (colores[j] >> 5) << 6 | (colores[j + 1] >> 5) << 3 | (colores[j + 2] >> 5)
                if cc != color:
                    if actual:
                        tramos.append(("".join(actual), color))
                    actual, color = [], cc
            actual.append(ch)
        if actual:
            tramos.append(("".join(actual), color))
        return tramos


# --------------------------------------------------------------------------- #
#  Fuentes de cuadros: ffmpeg en vivo o un archivo precargado
# --------------------------------------------------------------------------- #
class LectorFFmpeg:
    """Itera los cuadros del video (desde el segundo `desde`) ya convertidos."""

    def __init__(self, ffmpeg, ruta, fps, conv, desde=0.0):
        self.conv = conv
        salto = ["-ss", f"{desde:.3f}"] if desde > 0 else []
        self.proc = subprocess.Popen(
            [ffmpeg, "-v", "error", *salto, "-i", ruta, "-vf", conv.filtro(fps),
             "-f", "rawvideo", "-pix_fmt", conv.pix_fmt, "-"],
            stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, **OCULTO)

    def __iter__(self):
        tam, leer = self.conv.tam, self.proc.stdout.read
        try:
            while True:
                datos = leer(tam)
                if len(datos) < tam:
                    break
                yield self.conv(datos)
        finally:
            self.cerrar()

    def cerrar(self):
        try:
            if self.proc.poll() is None:
                self.proc.kill()
            self.proc.stdout.close()
        except Exception:
            pass


class LectorCache:
    """Itera los cuadros guardados por precargar(), saltándose los primeros."""

    def __init__(self, ruta, saltar=0):
        self.archivo = gzip.open(ruta, "rt", encoding="utf-8")
        self.archivo.readline()  # cabecera
        for _ in range(saltar):
            if not self.archivo.readline():
                break

    def __iter__(self):
        try:
            for linea in self.archivo:
                yield json.loads(linea)
        finally:
            self.cerrar()

    def cerrar(self):
        try:
            self.archivo.close()
        except Exception:
            pass


class Fuente(threading.Thread):
    """Hilo que va llenando una cola con cuadros listos para dibujar."""

    def __init__(self, fabrica, fps):
        super().__init__(daemon=True)
        self.cola = queue.Queue(maxsize=max(8, int(fps * 3)))
        self.terminado = False
        self._fabrica = fabrica
        self._lector = None
        self._parar = threading.Event()
        self.start()

    def _poner(self, cuadro):
        while not self._parar.is_set():
            try:
                self.cola.put(cuadro, timeout=0.1)
                return True
            except queue.Full:
                pass
        return False

    def run(self):
        try:
            self._lector = self._fabrica()
            if self._parar.is_set():
                self._lector.cerrar()
                return
            for cuadro in self._lector:
                if not self._poner(cuadro):
                    break
        except (ValueError, OSError, EOFError):
            pass   # el lector se cerró mientras leía (al salir, saltar o reiniciar)
        finally:
            self.terminado = True
            self._poner(FIN)

    def detener(self):
        self._parar.set()
        if self._lector:
            self._lector.cerrar()


def ruta_cache(args, conv):
    st = os.stat(args.video)
    clave = json.dumps([VERSION_CACHE, os.path.abspath(args.video), st.st_size,
                        st.st_mtime_ns, conv.cols, conv.filas, args.fps, args.rampa,
                        args.invertir, conv.multicolor, conv.salida, conv.estilo,
                        args.sensibilidad])
    h = hashlib.sha1(clave.encode("utf-8")).hexdigest()[:12]
    base = os.path.splitext(os.path.basename(args.video))[0]
    carpeta = os.path.join(carpeta_programa(), CARPETA_CACHE)
    return os.path.join(carpeta, f"{base}_{conv.estilo}_{conv.cols}x{conv.filas}_{h}.jsonl.gz")


def precargar(args, conv, total):
    """Convierte todo el video una sola vez y lo guarda comprimido."""
    ruta = ruta_cache(args, conv)
    if os.path.isfile(ruta):
        return ruta
    os.makedirs(os.path.dirname(ruta), exist_ok=True)
    print(f"Precargando {os.path.basename(args.video)} ({conv.estilo}, "
          f"{conv.cols}x{conv.filas}, {args.fps:g} fps). Solo la primera vez...")
    temporal = ruta + ".tmp"
    t0, n = time.perf_counter(), 0
    try:
        with gzip.open(temporal, "wt", encoding="utf-8", compresslevel=6) as f:
            f.write(json.dumps({"version": VERSION_CACHE, "cols": conv.cols,
                                "filas": conv.filas, "fps": args.fps}) + "\n")
            for cuadro in LectorFFmpeg(args.ffmpeg, args.video, args.fps, conv):
                f.write(json.dumps(cuadro, ensure_ascii=False) + "\n")
                n += 1
                if n % 10 == 0:
                    mostrar_progreso(n, total, t0, "Precarga")
        mostrar_progreso(n, n, t0, "Precarga")
        print()
        os.replace(temporal, ruta)
    except BaseException:
        print("\nPrecarga cancelada.")
        try:
            os.remove(temporal)
        except OSError:
            pass
        raise
    return ruta


# --------------------------------------------------------------------------- #
#  Audio, reloj y sesión (pausa, saltos, bucle)
# --------------------------------------------------------------------------- #
class Audio:
    """Reproduce el audio con ffplay.

    El audio se extrae antes a un WAV temporal: en un MP4, ffplay -ss salta
    al fotograma clave ANTERIOR del video (en badapple.mp4, hasta 7 s antes),
    y al reanudar o saltar el audio quedaba atrasado. En un WAV el salto es
    exacto.
    """

    def __init__(self, ffplay, ffmpeg, ruta):
        self.ffplay, self.ruta, self.proc = ffplay, ruta, None
        self.carpeta = None
        self.muestra = None    # (instante, segundo que sonaba) según ffplay
        carpeta = tempfile.mkdtemp(prefix="badapple_audio_")
        try:
            wav = os.path.join(carpeta, "audio.wav")
            subprocess.run([ffmpeg, "-v", "error", "-y", "-i", ruta, "-vn",
                            "-c:a", "pcm_s16le", wav],
                           stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                           stderr=subprocess.DEVNULL, check=True, **OCULTO)
            self.carpeta, self.ruta = carpeta, wav
        except (subprocess.CalledProcessError, OSError):
            shutil.rmtree(carpeta, ignore_errors=True)   # seguimos con el original

    def iniciar(self, desde=0.0):
        """Lanza ffplay. Con -stats, ffplay informa cada ~30 ms del segundo
        que está sonando; un hilo lo lee para que el video pueda seguirlo."""
        self.detener()
        cmd = [self.ffplay, "-nodisp", "-autoexit", "-hide_banner", "-loglevel", "info", "-stats"]
        if desde > 0:
            cmd += ["-ss", f"{desde:.3f}"]
        self.proc = subprocess.Popen(cmd + [self.ruta], stdin=subprocess.DEVNULL,
                                     stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, **OCULTO)
        threading.Thread(target=self._leer_reloj, args=(self.proc,), daemon=True).start()

    def _leer_reloj(self, proc):
        buf = b""
        try:
            while True:
                trozo = proc.stderr.read1(512)
                if not trozo:
                    break
                buf += trozo
                *lineas, buf = re.split(rb"[\r\n]", buf)
                for linea in lineas:
                    m = re.match(rb"\s*(\d+\.\d+)\s+M-A", linea)
                    if m and proc is self.proc:
                        self.muestra = (time.perf_counter(), float(m.group(1)))
        except (OSError, ValueError):
            pass

    def detener(self):
        self.muestra = None
        if self.proc and self.proc.poll() is None:
            self.proc.kill()
            self.proc.wait()
        self.proc = None

    def cerrar(self):
        self.detener()
        if self.carpeta:
            shutil.rmtree(self.carpeta, ignore_errors=True)
            self.carpeta = None


class Reloj:
    """Decide qué cuadro toca mostrar según el tiempo real."""

    def __init__(self, fps, retraso=0.0, inicial=0):
        self.fps = fps
        self.mostrados = inicial
        self.inicio = time.perf_counter() + retraso - inicial / fps
        self.fin = False

    def segundos(self):
        return self.mostrados / self.fps

    def reanudar(self, retraso=0.0):
        self.inicio = time.perf_counter() + retraso - self.mostrados / self.fps

    def siguiente(self, cola):
        """Devuelve (cuadro | NADA | FIN, segundos_de_espera). Si vamos
        atrasados, salta los cuadros sobrantes para no perder la sincronía."""
        if self.fin:
            return FIN, 0
        ahora = time.perf_counter()
        objetivo = int((ahora - self.inicio) * self.fps)
        if objetivo < self.mostrados:
            return NADA, self.inicio + self.mostrados / self.fps - ahora
        cuadro = NADA
        while self.mostrados <= objetivo:
            try:
                c = cola.get_nowait()
            except queue.Empty:
                break
            if c is FIN:
                self.fin = True
                break
            cuadro = c
            self.mostrados += 1
        if cuadro is NADA:
            return (FIN, 0) if self.fin else (NADA, 0.005)
        return cuadro, max(0.0, self.inicio + self.mostrados / self.fps - time.perf_counter())


class Sesion:
    """Une fuente + audio + reloj y gestiona la pausa, los saltos y el bucle.

    Sincronía: el audio manda. Al arrancar (o tras pausa o salto) el video
    espera a que ffplay empiece a sonar de verdad (la primera vez puede
    tardar casi 1 s) y luego corrige su reloj para seguir al de ffplay.
    """

    ESPERA_MAXIMA_AUDIO = 2.0   # si ffplay no informa, el video arranca igual

    def __init__(self, crear_fuente, fps, audio, retraso, bucle, duracion):
        self.crear_fuente, self.fps = crear_fuente, fps
        self.audio, self.bucle, self.duracion = audio, bucle, duracion
        self.retraso = retraso if audio else 0.0   # ajuste fino del usuario
        self.fuente = None
        self.pausado = False
        self._mostrar_uno = False
        self._espera_audio = None
        self._ultima_muestra = None
        self.iniciar()

    def _arrancar_audio(self, desde):
        self.audio.iniciar(desde)
        self._ultima_muestra = None
        self._espera_audio = time.perf_counter() + self.ESPERA_MAXIMA_AUDIO

    def _sincronizar(self):
        """Ajusta el reloj del video al segundo que está sonando.
        Devuelve False mientras el audio todavía no ha empezado."""
        m = self.audio.muestra
        ahora = time.perf_counter()
        if self._espera_audio is not None:
            if m is None:
                if ahora < self._espera_audio:
                    return False
                self.reloj.reanudar(0.0)        # ffplay no informa: seguimos sin él
            self._espera_audio = None
        if m is None or m is self._ultima_muestra or ahora - m[0] > 0.3:
            return True
        self._ultima_muestra = m
        sonando = m[1] + (ahora - m[0]) + self.retraso
        diferencia = sonando - (ahora - self.reloj.inicio)
        if abs(diferencia) > 0.3:
            self.reloj.inicio -= diferencia        # salto grande: corregir de golpe
        elif abs(diferencia) > 0.04:
            self.reloj.inicio -= diferencia * 0.5  # deriva pequeña: suavemente
        return True

    def iniciar(self, desde=0.0, pausado=False):
        """Empieza a reproducir desde `desde` segundos. Si `pausado`, se
        queda en pausa mostrando ese cuadro."""
        k = max(0, int(round(desde * self.fps)))
        desde = k / self.fps
        if self.fuente:
            self.fuente.detener()
        if self.audio:
            self.audio.detener()
        self.fuente = self.crear_fuente(desde)
        # Deja que se llene un poco el búfer para no saltarse el principio.
        meta = 1 if pausado else min(int(self.fps), self.fuente.cola.maxsize - 1)
        limite = time.perf_counter() + 5
        while (self.fuente.cola.qsize() < meta and not self.fuente.terminado
               and time.perf_counter() < limite):
            time.sleep(0.005)
        self.reloj = Reloj(self.fps, 0.0, k)
        self._espera_audio = None
        if self.audio and not pausado:
            self._arrancar_audio(desde)
        self.pausado = pausado
        self._mostrar_uno = pausado

    def segundos(self):
        return self.reloj.segundos()

    def saltar(self, delta=0.0, a=None):
        """Avanza/retrocede `delta` segundos, o va directamente al segundo `a`."""
        destino = self.segundos() + delta if a is None else a
        destino = min(max(0.0, destino), max(0.0, self.duracion - 1.0))
        self.iniciar(destino, pausado=self.pausado)

    def siguiente(self):
        if self.pausado:
            if not self._mostrar_uno:
                return NADA, 0.05
            try:
                c = self.fuente.cola.get_nowait()
            except queue.Empty:
                return NADA, 0.02
            self._mostrar_uno = False
            if c is FIN:
                return NADA, 0.05
            self.reloj.mostrados += 1
            return c, 0.05
        if self.audio and not self._sincronizar():
            return NADA, 0.01                       # esperando a que suene el audio
        cuadro, espera = self.reloj.siguiente(self.fuente.cola)
        if cuadro is FIN and self.bucle:
            self.iniciar()
            return NADA, 0
        return cuadro, espera

    def alternar_pausa(self):
        if self.pausado:
            self._mostrar_uno = False
            self.reloj.reanudar(0.0)
            if self.audio:
                self._arrancar_audio(self.reloj.segundos())
            self.pausado = False
        else:
            self.pausado = True
            self._espera_audio = None
            if self.audio:
                self.audio.detener()

    def cerrar(self):
        if self.fuente:
            self.fuente.detener()
        if self.audio:
            self.audio.cerrar()


# --------------------------------------------------------------------------- #
#  Reproductor en ventana (Tkinter)
# --------------------------------------------------------------------------- #
class ReproductorVentana:
    def __init__(self, root, args, sesion, cols, filas, duracion, familia):
        import tkinter as tk
        import tkinter.font as tkfont

        self.root, self.args, self.sesion = root, args, sesion
        self.cols, self.filas, self.duracion = cols, filas, duracion
        self.auto = args.ajustar
        self.completa = False
        self.cerrado = False
        self.terminado = False
        self._pendiente = None
        self._metricas = {}
        self._ultimo_estado = None
        self._arrastre = None
        self.t_fps, self.cuenta_fps, self.fps_real = time.perf_counter(), 0, 0.0

        self.fuente = tkfont.Font(root=root, family=familia, size=args.letra)
        self._medidor = tkfont.Font(root=root, family=familia, size=args.letra)
        if args.estilo == "braille" and (self._medidor.measure("\u28ff" * 10)
                                         != self._medidor.measure("M" * 10)):
            print(f"Aviso: la fuente {familia!r} no tiene caracteres braille del mismo "
                  "ancho; la imagen puede verse descuadrada. Prueba --fuente \"Cascadia Mono\".")

        root.title(f"Bad Apple ASCII — {os.path.basename(args.video)}")
        icono = os.path.join(getattr(sys, "_MEIPASS", carpeta_programa()), "icono.ico")
        if EN_WINDOWS and os.path.isfile(icono):
            try:
                root.iconbitmap(default=icono)
            except Exception:
                pass
        root.configure(bg=args.fondo)
        root.minsize(260, 150)
        self.estado = tk.Label(root, fg="#7f8fa6", bg=args.fondo, anchor="w",
                               font=(familia, 9))
        self.estado.pack(side="bottom", fill="x", padx=6, pady=(0, 4))
        self.barra = tk.Canvas(root, height=12, bg=args.fondo, highlightthickness=0,
                               bd=0, cursor="hand2")
        self.barra.pack(side="bottom", fill="x", padx=6, pady=(2, 2))
        self._pista = self.barra.create_rectangle(0, 4, 0, 8, fill="#2a2f3a", width=0)
        self._relleno = self.barra.create_rectangle(0, 4, 0, 8, fill="#7f8fa6", width=0)
        self.barra.bind("<Button-1>", self._barra_mover)
        self.barra.bind("<B1-Motion>", self._barra_mover)
        self.barra.bind("<ButtonRelease-1>", self._barra_soltar)
        self.barra.bind("<Configure>", lambda e: self._dibujar_barra())
        self.lienzo = tk.Frame(root, bg=args.fondo)
        self.lienzo.pack(fill="both", expand=True, padx=6, pady=6)

        if args.multicolor:
            self.pantalla = tk.Text(
                self.lienzo, font=self.fuente, fg=args.color, bg=args.fondo,
                width=cols, height=filas, bd=0, highlightthickness=0, padx=0, pady=0,
                wrap="none", cursor="arrow", takefocus=0, insertwidth=0,
                exportselection=0, selectbackground=args.fondo)
            for i in range(512):
                self.pantalla.tag_configure(f"c{i}", foreground="#%02x%02x%02x" % color_de_indice(i))
            self.pantalla.configure(state="disabled")
            self.dibujar = self._dibujar_color
        else:
            self.pantalla = tk.Label(self.lienzo, font=self.fuente, fg=args.color,
                                     bg=args.fondo, justify="left", bd=0, padx=0, pady=0)
            self.dibujar = lambda texto: self.pantalla.configure(text=texto)
        self.pantalla.place(relx=0.5, rely=0.5, anchor="center")

        for tecla, accion in (
                ("<Escape>", self._escape), ("<space>", self._espacio),
                ("<F11>", self.alternar_completa), ("<plus>", lambda e: self.zoom(+1)),
                ("<KP_Add>", lambda e: self.zoom(+1)), ("<minus>", lambda e: self.zoom(-1)),
                ("<KP_Subtract>", lambda e: self.zoom(-1)), ("0", self.activar_auto),
                ("<KP_0>", self.activar_auto), ("q", lambda e: self.cerrar()),
                ("<Left>", lambda e: self.saltar(-SALTO)),
                ("<Right>", lambda e: self.saltar(+SALTO)),
                ("<Up>", lambda e: self.saltar(+SALTO_LARGO)),
                ("<Down>", lambda e: self.saltar(-SALTO_LARGO)),
                ("<Home>", lambda e: self.saltar(a=0.0))):
            root.bind(tecla, accion)
        root.protocol("WM_DELETE_WINDOW", self.cerrar)
        self.lienzo.bind("<Configure>", self._al_redimensionar)

        self._ajustar_ventana(limitar_a_pantalla=True)
        self.tick()

    # ---- tamaño de letra -------------------------------------------------- #
    def _metrica(self, tam):
        if tam not in self._metricas:
            self._medidor.configure(size=tam)
            self._metricas[tam] = (self._medidor.measure("M" * 20) / 20,
                                   self._medidor.metrics("linespace"))
        return self._metricas[tam]

    def _mejor_tamano(self, ancho, alto):
        mejor = 2
        for t in range(2, 97):
            cw, ls = self._metrica(t)
            if self.cols * cw <= ancho and self.filas * ls <= alto:
                mejor = t
        return mejor

    def _ajustar_ventana(self, limitar_a_pantalla=False):
        """Pone a la ventana el tamaño justo para la letra actual."""
        if self.completa or self.root.state() == "zoomed":
            return
        cw, ls = self._metrica(self.fuente.cget("size"))
        ancho = int(self.cols * cw) + 14
        alto = (int(self.filas * ls) + 14 + self.estado.winfo_reqheight()
                + self.barra.winfo_reqheight() + 8)
        if limitar_a_pantalla:
            ancho = min(ancho, int(self.root.winfo_screenwidth() * 0.92))
            alto = min(alto, int(self.root.winfo_screenheight() * 0.85))
        self.root.geometry(f"{ancho}x{alto}")

    def _al_redimensionar(self, _evento):
        if not self.auto:
            return
        if self._pendiente:
            self.root.after_cancel(self._pendiente)
        self._pendiente = self.root.after(60, self._autoajustar)

    def _autoajustar(self):
        self._pendiente = None
        tam = self._mejor_tamano(self.lienzo.winfo_width(), self.lienzo.winfo_height())
        if tam != self.fuente.cget("size"):
            self.fuente.configure(size=tam)
        self._estado()

    def zoom(self, d):
        self.auto = False
        self.fuente.configure(size=max(2, self.fuente.cget("size") + d))
        self._ajustar_ventana()
        self._estado()

    def activar_auto(self, _evento=None):
        self.auto = True
        self._autoajustar()

    def alternar_completa(self, _evento=None):
        self.completa = not self.completa
        self.root.attributes("-fullscreen", self.completa)

    # ---- teclas, saltos y barra de progreso ------------------------------- #
    def _escape(self, _evento):
        if self.completa:
            self.alternar_completa()
        else:
            self.cerrar()

    def _espacio(self, _evento):
        if self.terminado:
            self.terminado = False
            self.sesion.iniciar()
            self.tick()
        else:
            self.sesion.alternar_pausa()
            self._estado()

    def saltar(self, delta=0.0, a=None):
        self.sesion.saltar(delta, a)
        if self.terminado:           # el bucle de tick estaba parado
            self.terminado = False
            self.tick()
        self._dibujar_barra()
        self._estado()

    def _fraccion(self, x):
        return min(1.0, max(0.0, x / max(1, self.barra.winfo_width())))

    def _barra_mover(self, evento):
        self._arrastre = self._fraccion(evento.x)
        self._dibujar_barra()
        self._estado()

    def _barra_soltar(self, evento):
        frac = self._fraccion(evento.x)
        self._arrastre = None
        self.saltar(a=frac * self.duracion)

    def _dibujar_barra(self):
        ancho = self.barra.winfo_width()
        if self._arrastre is not None:
            frac = self._arrastre
        else:
            frac = min(1.0, self.sesion.segundos() / self.duracion) if self.duracion else 0.0
        self.barra.coords(self._pista, 0, 4, ancho, 8)
        self.barra.coords(self._relleno, 0, 4, ancho * frac, 8)

    # ---- dibujo ----------------------------------------------------------- #
    def _dibujar_color(self, partes):
        p = self.pantalla
        p.configure(state="normal")
        p.delete("1.0", "end")
        p.insert("1.0", *partes)
        p.configure(state="disabled")

    def _estado(self):
        if self._arrastre is not None:
            texto = f"Ir a {mmss(self._arrastre * self.duracion)} / {mmss(self.duracion)}"
        elif self.terminado:
            texto = "Fin del video  ·  Espacio = repetir  ·  ← = retroceder  ·  Esc = salir"
        else:
            letra = f"letra {self.fuente.cget('size')}{' auto' if self.auto else ''}"
            texto = (f"{mmss(self.sesion.segundos())} / {mmss(self.duracion)}  ·  "
                     f"{self.cols}x{self.filas}  ·  {self.fps_real:4.1f} fps  ·  {letra}")
            if self.sesion.bucle:
                texto += "  ·  bucle"
            if self.sesion.pausado:
                texto += "  ·  ❚❚ PAUSA (Espacio para seguir)"
            else:
                texto += "  ·  Espacio pausa · ←→ saltar · F11 completa"
        if texto != self._ultimo_estado:
            self._ultimo_estado = texto
            self.estado.configure(text=texto)

    def tick(self):
        if self.cerrado or self.terminado:
            return
        cuadro, espera = self.sesion.siguiente()
        if cuadro is FIN:
            self.terminado = True
            self._dibujar_barra()
            self._estado()
            return
        if cuadro is not NADA:
            self.dibujar(cuadro)
            self._dibujar_barra()
            if not self.sesion.pausado:
                self.cuenta_fps += 1
            ahora = time.perf_counter()
            if ahora - self.t_fps >= 1:
                self.fps_real = self.cuenta_fps / (ahora - self.t_fps)
                self.t_fps, self.cuenta_fps = ahora, 0
        self._estado()
        self.root.after(max(1, int(espera * 1000)), self.tick)

    def cerrar(self):
        self.cerrado = True
        self.sesion.cerrar()
        self.root.destroy()


# --------------------------------------------------------------------------- #
#  Reproductor en terminal
# --------------------------------------------------------------------------- #
class Teclado:
    """Lee teclas sin bloquear (Windows y Linux/macOS). Las flechas llegan
    como 'izq', 'der', 'arr', 'aba' e 'inicio'."""

    FLECHAS_WIN = {"K": "izq", "M": "der", "H": "arr", "P": "aba", "G": "inicio"}
    FLECHAS_ANSI = {"\x1b[D": "izq", "\x1b[C": "der", "\x1b[A": "arr", "\x1b[B": "aba",
                    "\x1b[H": "inicio", "\x1b[1~": "inicio", "\x1bOH": "inicio"}

    def __enter__(self):
        self.fd = self.ajustes = None
        if not EN_WINDOWS and sys.stdin.isatty():
            import termios
            import tty
            self.fd = sys.stdin.fileno()
            self.ajustes = termios.tcgetattr(self.fd)
            tty.setcbreak(self.fd)
        return self

    def __exit__(self, *_):
        if self.ajustes is not None:
            import termios
            termios.tcsetattr(self.fd, termios.TCSADRAIN, self.ajustes)

    def teclas(self):
        res = []
        if EN_WINDOWS:
            import msvcrt
            while msvcrt.kbhit():
                k = msvcrt.getwch()
                if k in ("\x00", "\xe0"):             # tecla especial: flechas, F1...
                    nombre = self.FLECHAS_WIN.get(msvcrt.getwch())
                    if nombre:
                        res.append(nombre)
                    continue
                res.append(k)
        elif self.fd is not None:
            import select
            if select.select([self.fd], [], [], 0)[0]:
                trozo = os.read(self.fd, 64).decode("utf-8", "ignore")
                if trozo.startswith("\x1b") and len(trozo) > 1:
                    nombre = self.FLECHAS_ANSI.get(trozo)
                    if nombre:
                        res.append(nombre)
                    return res
                res.extend(trozo)
        return res


def reproducir_terminal(args, sesion, cols, filas, duracion):
    if EN_WINDOWS:
        os.system("")  # activa los códigos ANSI en la consola de Windows
    try:   # braille, ❚❚... necesitan UTF-8 aunque la salida esté redirigida
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass
    out = sys.stdout
    base = ansi_color(args.color)
    gris = "\033[38;2;127;143;166m"
    linea_estado = f"\033[{filas + 1};1H"
    ancho_estado = max(20, shutil.get_terminal_size().columns - 1)
    saltos = {"izq": (-SALTO, None), "der": (SALTO, None), "arr": (SALTO_LARGO, None),
              "aba": (-SALTO_LARGO, None), "inicio": (0.0, 0.0)}

    def estado(extra):
        seg = sesion.segundos()
        frac = min(1.0, seg / duracion) if duracion else 0.0
        ancho = max(10, min(40, ancho_estado - 60))
        llenos = int(frac * ancho)
        texto = (f"{mmss(seg)} [{'#' * llenos}{'-' * (ancho - llenos)}] {mmss(duracion)}"
                 f"   {extra}")
        out.write(f"{linea_estado}{gris}{texto[:ancho_estado]}\033[K{base}")

    ayuda = "[Espacio] pausa  [←→↑↓] saltar  [Q] salir"
    out.write("\033[2J\033[?25l" + base)
    terminado = False
    try:
        with Teclado() as teclado:
            while True:
                for k in teclado.teclas():
                    if k == " ":
                        if terminado:
                            terminado = False
                            sesion.iniciar()
                        else:
                            sesion.alternar_pausa()
                            estado("❚❚ PAUSA   " + ayuda if sesion.pausado else ayuda)
                            out.flush()
                    elif k in saltos:
                        delta, a = saltos[k]
                        sesion.saltar(delta, a)
                        terminado = False
                    elif k.lower() == "q" or k == "\x1b":
                        return
                if terminado:
                    time.sleep(0.05)
                    continue
                cuadro, espera = sesion.siguiente()
                if cuadro is FIN:
                    terminado = True
                    estado("Fin   [Espacio] repetir   [←] retroceder   [Q] salir")
                    out.flush()
                    continue
                if cuadro is not NADA:
                    out.write("\033[H" + base + cuadro)
                    pausa = "❚❚ PAUSA   " if sesion.pausado else ""
                    estado(pausa + ("bucle  " if sesion.bucle else "") + ayuda)
                    out.flush()
                time.sleep(min(espera, 0.03))
    except KeyboardInterrupt:
        pass
    finally:
        out.write(f"\033[0m\033[?25h{linea_estado}\n")
        out.flush()
        sesion.cerrar()


# --------------------------------------------------------------------------- #
#  Exportar
# --------------------------------------------------------------------------- #
def exportar_txt(args, conv, total, salida):
    t0, n = time.perf_counter(), 0
    with open(salida, "w", encoding="utf-8", newline="\n") as f:
        f.write(f"# Bad Apple ASCII — {os.path.basename(args.video)} — estilo {conv.estilo}"
                f" — {conv.cols}x{conv.filas} caracteres a {args.fps:g} fps\n")
        for cuadro in LectorFFmpeg(args.ffmpeg, args.video, args.fps, conv):
            seg = n / args.fps
            f.write(f"\n--- cuadro {n + 1} · {mmss(seg)}.{int(seg * 100) % 100:02d} ---\n")
            f.write(cuadro + ("\033[0m\n" if conv.multicolor else "\n"))
            n += 1
            if n % 25 == 0:
                mostrar_progreso(n, total, t0, "Exportando")
    mostrar_progreso(n, n, t0, "Exportando")
    print(f"\nListo: {salida}  ({n} cuadros)")


def tiempo_ass(seg):
    cs = int(round(seg * 100))
    return f"{cs // 360000}:{cs // 6000 % 60:02d}:{cs // 100 % 60:02d}.{cs % 100:02d}"


def cabecera_ass(ancho, alto, familia, letra, color_hex, alineacion=5):
    r, g, b = color_rgb(color_hex)
    return ("[Script Info]\nScriptType: v4.00+\n"
            f"PlayResX: {ancho}\nPlayResY: {alto}\nWrapStyle: 2\n\n"
            "[V4+ Styles]\nFormat: Name, Fontname, Fontsize, PrimaryColour, "
            "SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, "
            "StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, "
            "Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n"
            f"Style: A,{familia},{letra},&H00{b:02X}{g:02X}{r:02X},&H00FFFFFF,"
            f"&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,0,0,{alineacion},0,0,0,1\n\n"
            "[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, "
            "MarginR, MarginV, Effect, Text\n")


def medir_letra_ass(ffmpeg, familia, carpeta):
    """Mide cómo dibuja libass la fuente: (ancho de carácter, alto de línea)
    en proporción al tamaño de letra. Así el video exportado encaja justo."""
    w, h, tam = 2600, 300, 100
    texto = "M" + "\\h" * 18 + "M\\NM"
    ruta = os.path.join(carpeta, "medida.ass")
    with open(ruta, "w", encoding="utf-8") as f:
        f.write(cabecera_ass(w, h, familia, tam, "#ffffff", alineacion=7))
        f.write(f"Dialogue: 0,0:00:00.00,0:00:01.00,A,,0,0,0,,{texto}\n")
    try:
        px = subprocess.run(
            [ffmpeg, "-v", "error", "-f", "lavfi", "-i", f"color=black:s={w}x{h}:d=0.1",
             "-vf", "ass=medida.ass,format=gray", "-frames:v", "1",
             "-f", "rawvideo", "-"], cwd=carpeta, capture_output=True, check=True).stdout
        cols_tinta = [x for x in range(w) if any(px[y * w + x] > 80 for y in range(0, h, 2))]
        x0 = cols_tinta[0]
        x1 = next(x for a, x in zip(cols_tinta, cols_tinta[1:]) if x - a > tam // 2)
        filas_tinta = [y for y in range(h) if any(px[y * w + x] > 80 for x in range(x0, x0 + tam // 2))]
        y0 = filas_tinta[0]
        y1 = next(y for a, y in zip(filas_tinta, filas_tinta[1:]) if y - a > 2)
        return (x1 - x0) / 19 / tam, (y1 - y0) / tam
    except Exception:
        return 0.6, 1.2   # valores prudentes si la medida falla


def exportar_video(args, conv, total, duracion, tiene_audio, salida):
    """Dibuja cada cuadro como un subtítulo ASS y deja que ffmpeg (libass)
    lo convierta en video. Así no hace falta ninguna librería extra."""
    par = lambda v: v + (v % 2)
    if args.fuente:
        familia = args.fuente
    elif EN_WINDOWS:
        familia = "Cascadia Mono" if conv.estilo == "braille" else "Consolas"
    else:
        familia = "DejaVu Sans Mono"
    ext = os.path.splitext(salida)[1].lower()
    destino = os.path.abspath(salida)

    carpeta = tempfile.mkdtemp(prefix="badapple_")
    try:
        k_ancho, k_alto = medir_letra_ass(args.ffmpeg, familia, carpeta)
        letra = max(4, int((args.alto_exportar - 32) / (conv.filas * k_alto)))
        ancho = par(math.ceil(conv.cols * letra * k_ancho) + 32)
        alto = par(math.ceil(conv.filas * letra * k_alto) + 32)
        print(f"Paso 1/2: preparando {total} cuadros ({ancho}x{alto} px, {familia})...")
        t0, n = time.perf_counter(), 0
        with open(os.path.join(carpeta, "cuadros.ass"), "w", encoding="utf-8") as f:
            f.write(cabecera_ass(ancho, alto, familia, letra, args.color))
            for cuadro in LectorFFmpeg(args.ffmpeg, args.video, args.fps, conv):
                f.write(f"Dialogue: 0,{tiempo_ass(n / args.fps)},"
                        f"{tiempo_ass((n + 1) / args.fps)},A,,0,0,0,,{cuadro}\n")
                n += 1
                if n % 25 == 0:
                    mostrar_progreso(n, total, t0, "Cuadros")
        mostrar_progreso(n, n, t0, "Cuadros")
        print("\nPaso 2/2: generando el video con ffmpeg (puede tardar unos minutos)...")

        fondo = args.fondo.lstrip("#")
        cmd = [args.ffmpeg, "-y", "-hide_banner", "-v", "error", "-stats",
               "-f", "lavfi", "-i",
               f"color=c=0x{fondo}:s={ancho}x{alto}:r={args.fps:g}:d={n / args.fps:.3f}"]
        if ext == ".gif":
            cmd += ["-vf", "ass=cuadros.ass,split[a][b];[a]palettegen[p];[b][p]paletteuse",
                    "-loop", "0"]
        else:
            con_audio = args.audio and tiene_audio
            if con_audio:
                cmd += ["-i", os.path.abspath(args.video)]
            cmd += ["-vf", "ass=cuadros.ass", "-map", "0:v"]
            if con_audio:
                cmd += ["-map", "1:a:0", "-shortest"]
            if ext in (".mp4", ".mkv", ".mov"):
                cmd += ["-c:v", "libx264", "-crf", "20", "-tune", "animation"]
                if con_audio:
                    cmd += ["-c:a", "aac", "-b:a", "192k"]
            cmd += ["-pix_fmt", "yuv420p"]
        subprocess.run(cmd + [destino], cwd=carpeta, check=True)
        print(f"Listo: {salida}")
    except subprocess.CalledProcessError:
        sys.exit("ffmpeg no pudo generar el video (mira el mensaje de arriba).")
    finally:
        shutil.rmtree(carpeta, ignore_errors=True)


# --------------------------------------------------------------------------- #
def crear_parser():
    si_no = argparse.BooleanOptionalAction
    p = argparse.ArgumentParser(
        description="Reproduce un video como arte ASCII.",
        epilog="Teclas en ventana: Espacio pausa, ←/→ ±5 s, ↑/↓ ±30 s, Inicio, "
               "F11 pantalla completa, +/- letra, 0 ajuste automático, Esc salir; "
               "clic en la barra para ir a ese punto. "
               "En terminal: Espacio pausa, flechas saltar, Q salir.")
    p.add_argument("video", nargs="?", default=VIDEO,
                   help=f"ruta del video (mp4, webm, mkv...). Por defecto: {VIDEO}")
    g = p.add_argument_group("imagen")
    g.add_argument("--estilo", choices=ESTILOS, default=ESTILO,
                   help=f"brillo = rampa de caracteres, bordes = contornos / | \\ -, "
                        f"braille = puntos ⣿ con 8 veces más detalle ({ESTILO})")
    g.add_argument("--cols", type=int, default=COLUMNAS, help=f"columnas de caracteres ({COLUMNAS})")
    g.add_argument("--fps", type=float, default=FPS, help="cuadros por segundo (por defecto, los del video)")
    g.add_argument("--rampa", default=RAMPA, help="caracteres de oscuro a claro")
    g.add_argument("--invertir", action=si_no, default=INVERTIR, help="invierte claro/oscuro")
    g.add_argument("--sensibilidad", type=int, default=SENSIBILIDAD,
                   help=f"estilo bordes: más bajo = más contornos ({SENSIBILIDAD})")
    g.add_argument("--multicolor", action=si_no, default=MULTICOLOR,
                   help="cada carácter con el color del video original")
    g = p.add_argument_group("apariencia")
    g.add_argument("--color", default=COLOR_TEXTO, help=f"color del texto ({COLOR_TEXTO})")
    g.add_argument("--fondo", default=COLOR_FONDO, help=f"color de fondo ({COLOR_FONDO})")
    g.add_argument("--letra", type=int, default=TAMANO_LETRA, help=f"tamaño de letra inicial ({TAMANO_LETRA})")
    g.add_argument("--fuente", default=FUENTE, help="tipo de letra (por defecto, automático)")
    g.add_argument("--ajustar", action=si_no, default=AJUSTE_AUTO,
                   help="adapta la letra a la ventana (o las columnas a la terminal)")
    g = p.add_argument_group("reproducción")
    g.add_argument("--audio", action=si_no, default=CON_AUDIO, help="reproducir sonido")
    g.add_argument("--sin-audio", dest="audio", action="store_false", default=CON_AUDIO,
                   help="igual que --no-audio")
    g.add_argument("--retraso-audio", type=float, default=RETRASO_AUDIO,
                   help="ajuste fino de la sincronía en segundos: súbelo si el sonido "
                        "va adelantado, bájalo (negativo) si va atrasado (0)")
    g.add_argument("--terminal", action=si_no, default=EN_TERMINAL,
                   help="dibujar en la consola en vez de una ventana")
    g.add_argument("--bucle", action=si_no, default=BUCLE, help="repetir al terminar")
    g.add_argument("--precargar", action=si_no, default=PRECARGAR,
                   help="convertir todo antes de reproducir (más fluido; se guarda en caché)")
    g.add_argument("--limpiar-cache", action="store_true", help="borra los videos precargados y sale")
    g = p.add_argument_group("exportar")
    g.add_argument("--exportar", metavar="ARCHIVO",
                   help="guarda la animación en vez de reproducirla (.txt, .mp4, .gif, .webm, .mkv)")
    g.add_argument("--alto-exportar", type=int, default=ALTO_EXPORTAR,
                   help=f"alto aproximado en píxeles del video exportado ({ALTO_EXPORTAR})")
    g = p.add_argument_group("ffmpeg")
    g.add_argument("--ffmpeg", default=buscar_herramienta("ffmpeg"))
    g.add_argument("--ffplay", default=buscar_herramienta("ffplay"))
    g.add_argument("--ffprobe", default=buscar_herramienta("ffprobe"))
    return p


def nombre_comando():
    if getattr(sys, "frozen", False):
        return os.path.basename(sys.executable)
    return "python bad_apple.py"


def main(propia=False):
    for flujo in (sys.stdout, sys.stderr):   # que ⣿, ❚❚... nunca rompan un mensaje
        try:
            flujo.reconfigure(errors="replace")
        except (AttributeError, ValueError):
            pass
    if SIN_CONSOLA and any(a in sys.argv[1:] for a in ("-h", "--help", "--terminal",
                                                        "--exportar", "--limpiar-cache")):
        sys.exit("Esta versión (sin consola) solo reproduce en ventana.\n"
                 "Para --terminal, --exportar, --limpiar-cache o --help usa "
                 "BadAppleASCII-consola.exe desde una terminal.")
    args = crear_parser().parse_args()

    if args.limpiar_cache:
        shutil.rmtree(os.path.join(carpeta_programa(), CARPETA_CACHE), ignore_errors=True)
        print("Caché borrada.")
        return
    if not os.path.isfile(args.video) and not os.path.isabs(args.video):
        junto = os.path.join(carpeta_programa(), args.video)   # p. ej. al lado del .exe
        if os.path.isfile(junto):
            args.video = junto
    if not os.path.isfile(args.video):
        sys.exit(f"No encuentro el video: {args.video}\n"
                 f"Pon el video en esta carpeta o escribe su ruta: {nombre_comando()} \"mi video.mp4\"\n"
                 "(El video de Bad Apple!! no viene incluido; ver README.md.)")
    if not args.ffmpeg or not args.ffprobe:
        sys.exit("Falta ffmpeg/ffprobe. Instálalo (Windows: winget install ffmpeg) o pon "
                 "ffmpeg.exe y ffprobe.exe junto al programa, y vuelve a intentar.")
    if len(args.rampa) < 2:
        sys.exit("La rampa necesita al menos 2 caracteres.")
    if args.cols < 2 or (args.fps is not None and args.fps <= 0) or args.letra < 2:
        sys.exit("Revisa --cols (mínimo 2), --fps (mayor que 0) y --letra (mínimo 2).")

    exportando = bool(args.exportar)
    en_ventana = not args.terminal and not exportando
    if args.audio and not args.ffplay and not exportando:
        print("Aviso: no encontré ffplay, sigo sin audio.")
        args.audio = False

    root = None
    if en_ventana:
        import tkinter as tk
        root = tk.Tk()
        root.withdraw()
    for nombre in ("color", "fondo"):
        valor = getattr(args, nombre)
        hexa = resolver_color(valor)
        if hexa is None and root is not None:
            try:   # la ventana también acepta los nombres de color de Tk
                r, g, b = root.winfo_rgb(valor)
                hexa = "#%02x%02x%02x" % (r >> 8, g >> 8, b >> 8)
            except Exception:
                pass
        if hexa is None:
            sys.exit(f"Color no válido para --{nombre}: {valor!r}. Usa \"#rrggbb\" "
                     f"o un nombre: {', '.join(sorted(NOMBRES_COLOR))}.")
        setattr(args, nombre, hexa)

    ancho, alto, fps_video, duracion, tiene_audio = info_video(args.ffprobe, args.video)
    args.fps = args.fps or min(fps_video, 60)
    proporcion = alto / ancho * 0.5   # un carácter es ~2 veces más alto que ancho
    cols = args.cols
    if args.terminal and args.ajustar and not exportando:
        tc, tl = shutil.get_terminal_size()
        limite = max(10, min(tc - 1, int((tl - 2) / proporcion)))
        if cols > limite:
            print(f"La terminal es pequeña: uso {limite} columnas en vez de {cols} "
                  "(--no-ajustar para evitarlo).")
            cols = limite
            time.sleep(1)
    filas = max(1, round(cols * proporcion))
    total = max(1, round(duracion * args.fps))

    def conversor(salida):
        return Conversor(cols, filas, args.rampa, args.invertir, args.multicolor,
                         salida, args.estilo, args.sensibilidad)

    if exportando:
        ext = os.path.splitext(args.exportar)[1].lower()
        if ext == ".txt":
            exportar_txt(args, conversor("ansi" if args.multicolor else "texto"),
                         total, args.exportar)
        else:
            exportar_video(args, conversor("ass"), total, duracion, tiene_audio, args.exportar)
        return

    salida = ("ansi" if args.terminal else "tk") if args.multicolor else "texto"
    conv = conversor(salida)
    if args.precargar:
        try:
            ruta = precargar(args, conv, total)
        except KeyboardInterrupt:
            sys.exit(1)
        fabrica = lambda desde: LectorCache(ruta, int(round(desde * args.fps)))
    else:
        fabrica = lambda desde: LectorFFmpeg(args.ffmpeg, args.video, args.fps, conv, desde)

    audio = Audio(args.ffplay, args.ffmpeg, args.video) if args.audio and tiene_audio else None
    sesion = Sesion(lambda desde: Fuente(lambda: fabrica(desde), args.fps), args.fps,
                    audio, args.retraso_audio, args.bucle, duracion)

    if args.terminal:
        reproducir_terminal(args, sesion, cols, filas, duracion)
        return
    familia = elegir_familia(root, args.estilo, args.fuente)
    if propia:
        ocultar_consola()   # abierto con doble clic: la consola sobra
    root.deiconify()
    ReproductorVentana(root, args, sesion, cols, filas, duracion, familia)
    root.mainloop()


def avisar_en_ventana(mensaje):
    """Sin consola, los errores se muestran en un cuadro de diálogo."""
    try:
        import tkinter as tk
        from tkinter import messagebox
        r = tk.Tk()
        r.withdraw()
        messagebox.showerror("Bad Apple ASCII", mensaje)
        r.destroy()
    except Exception:
        pass


if __name__ == "__main__":
    PROPIA = consola_propia()
    try:
        main(PROPIA)
    except SystemExit as e:
        if SIN_CONSOLA and e.code not in (None, 0):
            avisar_en_ventana(e.code if isinstance(e.code, str) else "Error inesperado.")
            raise
        if PROPIA and e.code not in (None, 0):
            # Abierto con doble clic: que el mensaje no desaparezca al instante.
            if isinstance(e.code, str):
                print(e.code)
            input("\nPulsa Enter para cerrar...")
            sys.exit(1)
        raise
    except Exception:
        if SIN_CONSOLA:
            import traceback
            avisar_en_ventana("Error inesperado:\n\n" + traceback.format_exc(limit=3))
            raise
        if not PROPIA:
            raise
        import traceback
        traceback.print_exc()
        input("\nPulsa Enter para cerrar...")
        sys.exit(1)
