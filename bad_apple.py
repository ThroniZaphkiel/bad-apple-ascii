#!/usr/bin/env python3
"""
bad_apple.py — Reproduce cualquier video como arte ASCII, con audio sincronizado.

Inspirado en el clásico "Bad Apple!! en ASCII": ffmpeg decodifica el video a
cuadros pequeños, cada píxel se convierte en un carácter según su brillo y el
resultado se dibuja en una ventana de Tkinter (o en la terminal). ffplay
reproduce el audio y un reloj mantiene ambos sincronizados.

Autor: Zaphkiel — Licencia MIT (ver README.txt)

Requisitos:
  - Python 3.9+ (solo librería estándar)
  - ffmpeg, ffprobe y ffplay en el PATH  (https://ffmpeg.org/download.html)
    En Windows:  winget install ffmpeg

Uso:
  python bad_apple.py                          # abre el VIDEO de la configuración
  python bad_apple.py otro_video.mp4
  python bad_apple.py --cols 150 --multicolor  # cada letra con su color
  python bad_apple.py --terminal --bucle       # en la consola, repitiendo
  python bad_apple.py --precargar              # convierte todo antes (más fluido)
  python bad_apple.py --exportar salida.mp4    # guarda la animación como video
  python bad_apple.py --exportar salida.txt    # ...o como texto

Teclas (ventana):   Espacio = pausa   F11 = pantalla completa
                    + / -   = tamaño de letra   0 = ajuste automático
                    Esc     = salir de pantalla completa / salir
Teclas (terminal):  Espacio = pausa   Q o Esc = salir
"""

import argparse
import gzip
import hashlib
import json
import math
import os
import queue
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
COLUMNAS       = 100         # ancho en caracteres: más = más detalle (60-200)
TAMANO_LETRA   = 7           # tamaño de letra inicial en la ventana (4-12)
COLOR_TEXTO    = "#ffffff"   # "#rrggbb" o un nombre: "verde", "ambar", "red"...
COLOR_FONDO    = "#000000"   # negro
FPS            = None        # None = los del video. Ej: 24 o 30
RAMPA          = " .:-=+*#%@"  # caracteres de oscuro a claro
INVERTIR       = False       # True = intercambia claro y oscuro
CON_AUDIO      = True        # False = sin sonido
RETRASO_AUDIO  = 0.15        # súbelo si el sonido va adelantado
EN_TERMINAL    = False       # True = dibuja en la consola, no en ventana
MULTICOLOR     = False       # True = cada carácter con el color del video
BUCLE          = False       # True = vuelve a empezar al terminar
AJUSTE_AUTO    = True        # True = la letra se adapta al tamaño disponible
PRECARGAR      = False       # True = convierte todo antes de reproducir
CARPETA_CACHE  = ".cache_ascii"  # dónde se guardan los videos precargados
ALTO_EXPORTAR  = 720         # alto aproximado (px) del video con --exportar
# =========================================================================== #

EN_WINDOWS = sys.platform == "win32"
FAMILIA_LETRA = "Consolas" if EN_WINDOWS else "Courier"
VERSION_CACHE = 1
FIN = None          # señal de "se acabó el video" que viaja por la cola
NADA = object()     # "todavía no toca dibujar nada"

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
    datos = json.loads(subprocess.check_output(cmd))
    flujos = datos.get("streams", [])
    v = next((s for s in flujos if s.get("codec_type") == "video"), None)
    if v is None:
        sys.exit(f"El archivo no tiene video: {ruta}")
    num, den = v.get("r_frame_rate", "30/1").split("/")
    fps = float(num) / float(den) if float(den or 0) else 30.0
    dur = float(datos.get("format", {}).get("duration", 0) or 0)
    tiene_audio = any(s.get("codec_type") == "audio" for s in flujos)
    return int(v["width"]), int(v["height"]), fps or 30.0, dur, tiene_audio


# --------------------------------------------------------------------------- #
#  Conversión: bytes de un cuadro -> texto (o texto con colores)
# --------------------------------------------------------------------------- #
def tabla_caracteres(rampa, invertir):
    """Tabla de 256 entradas: brillo (0-255) -> carácter."""
    r = rampa[::-1] if invertir else rampa
    n = len(r)
    return [r[min(n - 1, v * n // 256)] for v in range(256)]


NIVELES = [v * 255 // 7 for v in range(8)]   # 8 niveles por canal = 512 colores


def color_de_indice(i):
    return NIVELES[i >> 6], NIVELES[(i >> 3) & 7], NIVELES[i & 7]


def escapar_ass(texto):
    """Texto plano -> texto seguro para un subtítulo ASS."""
    return (texto.replace("\\", "/").replace("{", "(").replace("}", ")")
                 .replace(" ", "\\h").replace("\n", "\\N"))


class Conversor:
    """Convierte cuadros crudos de ffmpeg al formato que necesita cada salida.

    salida: 'texto' (str), 'tk' (lista texto/etiqueta para un Text de Tkinter),
            'ansi' (str con colores de terminal) o 'ass' (subtítulo ASS).
    """

    def __init__(self, cols, filas, rampa, invertir, multicolor, salida):
        self.cols, self.filas = cols, filas
        self.multicolor, self.salida = multicolor, salida
        self.tabla = tabla_caracteres(rampa, invertir)
        self.traduccion = {i: c for i, c in enumerate(self.tabla)}
        self.pix_fmt = "rgb24" if multicolor else "gray"
        self.tam = cols * filas * (3 if multicolor else 1)
        # Pesos de luminancia (suman 1024 para poder usar >> 10).
        self.lr = [v * 306 for v in range(256)]
        self.lg = [v * 601 for v in range(256)]
        self.lb = [v * 117 for v in range(256)]
        self.codigos_ansi = ["\033[38;2;%d;%d;%dm" % color_de_indice(i) for i in range(512)]
        self.codigos_ass = ["{\\c&H%02X%02X%02X&}" % color_de_indice(i)[::-1] for i in range(512)]

    def __call__(self, datos):
        if not self.multicolor:
            s = datos.decode("latin-1").translate(self.traduccion)
            c = self.cols
            texto = "\n".join(s[i:i + c] for i in range(0, len(s), c))
            return escapar_ass(texto) if self.salida == "ass" else texto

        tramos = self._tramos(datos)
        if self.salida == "tk":
            plano = []
            for t, c in tramos:
                plano += (t, "" if c is None else f"c{c}")
            return plano
        if self.salida == "ansi":
            return "".join((self.codigos_ansi[c] if c is not None else "") + t
                           for t, c in tramos)
        if self.salida == "ass":
            return "".join((self.codigos_ass[c] if c is not None else "") + escapar_ass(t)
                           for t, c in tramos)
        return "".join(t for t, _ in tramos)

    def _tramos(self, datos):
        """Agrupa caracteres seguidos del mismo color: [(texto, color), ...]."""
        cols, tabla = self.cols, self.tabla
        lr, lg, lb = self.lr, self.lg, self.lb
        tramos, actual, color = [], [], None
        paso = cols * 3
        for y in range(self.filas):
            base = y * paso
            for i in range(base, base + paso, 3):
                r, g, b = datos[i], datos[i + 1], datos[i + 2]
                ch = tabla[(lr[r] + lg[g] + lb[b]) >> 10]
                if ch != " ":                       # los espacios no tienen color
                    c = (r >> 5) << 6 | (g >> 5) << 3 | (b >> 5)
                    if c != color:
                        if actual:
                            tramos.append(("".join(actual), color))
                        actual, color = [], c
                actual.append(ch)
            if y < self.filas - 1:
                actual.append("\n")
        if actual:
            tramos.append(("".join(actual), color))
        return tramos


# --------------------------------------------------------------------------- #
#  Fuentes de cuadros: ffmpeg en vivo o un archivo precargado
# --------------------------------------------------------------------------- #
class LectorFFmpeg:
    """Itera los cuadros del video ya convertidos por un Conversor."""

    def __init__(self, ffmpeg, ruta, fps, conv):
        self.conv = conv
        filtro = (f"fps={fps},scale={conv.cols}:{conv.filas}:flags=area,"
                  f"format={conv.pix_fmt}")
        self.proc = subprocess.Popen(
            [ffmpeg, "-v", "error", "-i", ruta, "-vf", filtro,
             "-f", "rawvideo", "-pix_fmt", conv.pix_fmt, "-"],
            stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)

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
    """Itera los cuadros guardados por precargar()."""

    def __init__(self, ruta):
        self.archivo = gzip.open(ruta, "rt", encoding="utf-8")
        self.archivo.readline()  # cabecera

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
            for cuadro in self._lector:
                if not self._poner(cuadro):
                    break
        except (ValueError, OSError, EOFError):
            pass   # el lector se cerró mientras leía (al salir o reiniciar)
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
                        args.invertir, conv.multicolor, conv.salida])
    h = hashlib.sha1(clave.encode("utf-8")).hexdigest()[:12]
    base = os.path.splitext(os.path.basename(args.video))[0]
    carpeta = os.path.join(os.path.dirname(os.path.abspath(__file__)), CARPETA_CACHE)
    return os.path.join(carpeta, f"{base}_{conv.cols}x{conv.filas}_{h}.jsonl.gz")


def precargar(args, conv, total):
    """Convierte todo el video una sola vez y lo guarda comprimido."""
    ruta = ruta_cache(args, conv)
    if os.path.isfile(ruta):
        return ruta
    os.makedirs(os.path.dirname(ruta), exist_ok=True)
    print(f"Precargando {os.path.basename(args.video)} "
          f"({conv.cols}x{conv.filas}, {args.fps:g} fps). Solo la primera vez...")
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
#  Audio, reloj y sesión (pausa, bucle)
# --------------------------------------------------------------------------- #
class Audio:
    """Reproduce el audio con ffplay.

    El audio se extrae antes a un WAV temporal: en un MP4, ffplay -ss salta
    al fotograma clave ANTERIOR del video (en badapple.mp4, hasta 7 s antes),
    y al reanudar tras una pausa el audio quedaba atrasado. En un WAV el
    salto es exacto.
    """

    def __init__(self, ffplay, ffmpeg, ruta):
        self.ffplay, self.ruta, self.proc = ffplay, ruta, None
        self.carpeta = None
        try:
            carpeta = tempfile.mkdtemp(prefix="badapple_audio_")
            wav = os.path.join(carpeta, "audio.wav")
            subprocess.run([ffmpeg, "-v", "error", "-y", "-i", ruta, "-vn",
                            "-c:a", "pcm_s16le", wav],
                           stdin=subprocess.DEVNULL, check=True)
            self.carpeta, self.ruta = carpeta, wav
        except (subprocess.CalledProcessError, OSError):
            shutil.rmtree(carpeta, ignore_errors=True)   # seguimos con el original

    def iniciar(self, desde=0.0):
        self.detener()
        cmd = [self.ffplay, "-nodisp", "-autoexit", "-loglevel", "quiet"]
        if desde > 0:
            cmd += ["-ss", f"{desde:.3f}"]
        self.proc = subprocess.Popen(cmd + [self.ruta], stdin=subprocess.DEVNULL,
                                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def detener(self):
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

    def __init__(self, fps, retraso=0.0):
        self.fps = fps
        self.inicio = time.perf_counter() + retraso
        self.mostrados = 0
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
    """Une fuente + audio + reloj y gestiona la pausa y el bucle."""

    def __init__(self, crear_fuente, fps, audio, retraso, bucle):
        self.crear_fuente, self.fps = crear_fuente, fps
        self.audio, self.bucle = audio, bucle
        self.retraso = retraso if audio else 0.0
        self.fuente = None
        self.pausado = False
        self.iniciar()

    def iniciar(self):
        if self.fuente:
            self.fuente.detener()
        self.fuente = self.crear_fuente()
        # Deja que se llene un poco el búfer para no saltarse el principio.
        meta = min(int(self.fps), self.fuente.cola.maxsize - 1)
        limite = time.perf_counter() + 5
        while (self.fuente.cola.qsize() < meta and not self.fuente.terminado
               and time.perf_counter() < limite):
            time.sleep(0.01)
        if self.audio:
            self.audio.iniciar(0.0)
        self.reloj = Reloj(self.fps, self.retraso)
        self.pausado = False

    def segundos(self):
        return self.reloj.segundos()

    def siguiente(self):
        if self.pausado:
            return NADA, 0.05
        cuadro, espera = self.reloj.siguiente(self.fuente.cola)
        if cuadro is FIN and self.bucle:
            self.iniciar()
            return NADA, 0
        return cuadro, espera

    def alternar_pausa(self):
        if self.pausado:
            self.reloj.reanudar(self.retraso)
            if self.audio:
                self.audio.iniciar(self.reloj.segundos())
            self.pausado = False
        else:
            self.pausado = True
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
    def __init__(self, root, args, sesion, cols, filas, duracion):
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
        self.t_fps, self.cuenta_fps, self.fps_real = time.perf_counter(), 0, 0.0

        self.fuente = tkfont.Font(root=root, family=FAMILIA_LETRA, size=args.letra)
        self._medidor = tkfont.Font(root=root, family=FAMILIA_LETRA, size=args.letra)

        root.title(f"Bad Apple ASCII — {os.path.basename(args.video)}")
        root.configure(bg=args.fondo)
        root.minsize(240, 140)
        self.estado = tk.Label(root, fg="#7f8fa6", bg=args.fondo, anchor="w",
                               font=(FAMILIA_LETRA, 9))
        self.estado.pack(side="bottom", fill="x", padx=6, pady=(0, 4))
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
                ("<KP_0>", self.activar_auto), ("q", lambda e: self.cerrar())):
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
        alto = int(self.filas * ls) + 14 + self.estado.winfo_reqheight() + 4
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

    # ---- teclas ----------------------------------------------------------- #
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

    # ---- dibujo ----------------------------------------------------------- #
    def _dibujar_color(self, partes):
        p = self.pantalla
        p.configure(state="normal")
        p.delete("1.0", "end")
        p.insert("1.0", *partes)
        p.configure(state="disabled")

    def _estado(self):
        if self.terminado:
            texto = "Fin del video  ·  Espacio = repetir  ·  Esc = salir"
        else:
            letra = f"letra {self.fuente.cget('size')}{' auto' if self.auto else ''}"
            texto = (f"{mmss(self.sesion.segundos())} / {mmss(self.duracion)}  ·  "
                     f"{self.cols}x{self.filas}  ·  {self.fps_real:4.1f} fps  ·  {letra}")
            if self.sesion.bucle:
                texto += "  ·  bucle"
            if self.sesion.pausado:
                texto += "  ·  ❚❚ PAUSA (Espacio para seguir)"
            else:
                texto += "  ·  Espacio pausa · F11 pantalla completa"
        if texto != self._ultimo_estado:
            self._ultimo_estado = texto
            self.estado.configure(text=texto)

    def tick(self):
        if self.cerrado or self.terminado:
            return
        cuadro, espera = self.sesion.siguiente()
        if cuadro is FIN:
            self.terminado = True
            self._estado()
            return
        if cuadro is not NADA:
            self.dibujar(cuadro)
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
    """Lee teclas sin bloquear (Windows y Linux/macOS)."""

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
                if k in ("\x00", "\xe0"):   # flechas, F1..F12: se ignoran
                    msvcrt.getwch()
                    continue
                res.append(k)
        elif self.fd is not None:
            import select
            if select.select([self.fd], [], [], 0)[0]:
                trozo = os.read(self.fd, 64).decode("utf-8", "ignore")
                if trozo.startswith("\x1b") and len(trozo) > 1:
                    return res               # secuencia de flecha, etc.
                res.extend(trozo)
        return res


def reproducir_terminal(args, sesion, cols, filas, duracion):
    if EN_WINDOWS:
        os.system("")  # activa los códigos ANSI en la consola de Windows
    out = sys.stdout
    base = ansi_color(args.color)
    gris = "\033[38;2;127;143;166m"
    linea_estado = f"\033[{filas + 1};1H"

    def estado(texto):
        out.write(f"{linea_estado}{gris}{texto}\033[K{base}")

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
                            if sesion.pausado:
                                estado(f"{mmss(sesion.segundos())} / {mmss(duracion)}"
                                       "   ❚❚ PAUSA   [Espacio] seguir   [Q] salir")
                                out.flush()
                    elif k.lower() == "q" or k == "\x1b":
                        return
                if terminado:
                    time.sleep(0.05)
                    continue
                cuadro, espera = sesion.siguiente()
                if cuadro is FIN:
                    terminado = True
                    estado("Fin del video   [Espacio] repetir   [Q] salir")
                    out.flush()
                    continue
                if cuadro is not NADA:
                    out.write("\033[H" + base + cuadro)
                    estado(f"{mmss(sesion.segundos())} / {mmss(duracion)}"
                           f"{'   bucle' if sesion.bucle else ''}"
                           "   [Espacio] pausa   [Q] salir")
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
        f.write(f"# Bad Apple ASCII — {os.path.basename(args.video)} — "
                f"{conv.cols}x{conv.filas} caracteres a {args.fps:g} fps\n")
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


def exportar_video(args, conv, total, duracion, tiene_audio, salida):
    """Dibuja cada cuadro como un subtítulo ASS y deja que ffmpeg (libass)
    lo convierta en video. Así no hace falta ninguna librería extra."""
    par = lambda v: v + (v % 2)
    letra = max(4, (args.alto_exportar - 32) // conv.filas)
    proporcion = 0.4688 if EN_WINDOWS else 0.52   # ancho de carácter / alto de línea
    ancho = par(math.ceil(conv.cols * letra * proporcion) + 32)
    alto = par(conv.filas * letra + 32)
    familia = "Consolas" if EN_WINDOWS else "DejaVu Sans Mono"
    r, g, b = color_rgb(args.color)
    ext = os.path.splitext(salida)[1].lower()
    destino = os.path.abspath(salida)

    carpeta = tempfile.mkdtemp(prefix="badapple_")
    try:
        print(f"Paso 1/2: preparando {total} cuadros ({ancho}x{alto} px)...")
        t0, n = time.perf_counter(), 0
        with open(os.path.join(carpeta, "cuadros.ass"), "w", encoding="utf-8") as f:
            f.write("[Script Info]\nScriptType: v4.00+\n"
                    f"PlayResX: {ancho}\nPlayResY: {alto}\nWrapStyle: 2\n\n"
                    "[V4+ Styles]\nFormat: Name, Fontname, Fontsize, PrimaryColour, "
                    "SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, "
                    "StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, "
                    "Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n"
                    f"Style: A,{familia},{letra},&H00{b:02X}{g:02X}{r:02X},&H00FFFFFF,"
                    "&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,0,0,5,0,0,0,1\n\n"
                    "[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, "
                    "MarginR, MarginV, Effect, Text\n")
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
        epilog="Teclas en ventana: Espacio pausa, F11 pantalla completa, +/- letra, "
               "0 ajuste automático, Esc salir. En terminal: Espacio pausa, Q salir.")
    p.add_argument("video", nargs="?", default=VIDEO,
                   help=f"ruta del video (mp4, webm, mkv...). Por defecto: {VIDEO}")
    g = p.add_argument_group("imagen")
    g.add_argument("--cols", type=int, default=COLUMNAS, help=f"columnas de caracteres ({COLUMNAS})")
    g.add_argument("--fps", type=float, default=FPS, help="cuadros por segundo (por defecto, los del video)")
    g.add_argument("--rampa", default=RAMPA, help="caracteres de oscuro a claro")
    g.add_argument("--invertir", action=si_no, default=INVERTIR, help="invierte claro/oscuro")
    g.add_argument("--multicolor", action=si_no, default=MULTICOLOR,
                   help="cada carácter con el color del video original")
    g = p.add_argument_group("apariencia")
    g.add_argument("--color", default=COLOR_TEXTO, help=f"color del texto ({COLOR_TEXTO})")
    g.add_argument("--fondo", default=COLOR_FONDO, help=f"color de fondo ({COLOR_FONDO})")
    g.add_argument("--letra", type=int, default=TAMANO_LETRA, help=f"tamaño de letra inicial ({TAMANO_LETRA})")
    g.add_argument("--ajustar", action=si_no, default=AJUSTE_AUTO,
                   help="adapta la letra a la ventana (o las columnas a la terminal)")
    g = p.add_argument_group("reproducción")
    g.add_argument("--audio", action=si_no, default=CON_AUDIO, help="reproducir sonido")
    g.add_argument("--sin-audio", dest="audio", action="store_false", default=CON_AUDIO,
                   help="igual que --no-audio")
    g.add_argument("--retraso-audio", type=float, default=RETRASO_AUDIO,
                   help="segundos que tarda ffplay en arrancar (ajusta si se desfasa)")
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
    g.add_argument("--ffmpeg", default=shutil.which("ffmpeg"))
    g.add_argument("--ffplay", default=shutil.which("ffplay"))
    g.add_argument("--ffprobe", default=shutil.which("ffprobe"))
    return p


def main():
    args = crear_parser().parse_args()

    if args.limpiar_cache:
        carpeta = os.path.join(os.path.dirname(os.path.abspath(__file__)), CARPETA_CACHE)
        shutil.rmtree(carpeta, ignore_errors=True)
        print("Caché borrada.")
        return
    if not os.path.isfile(args.video):
        sys.exit(f"No encuentro el video: {args.video}")
    if not args.ffmpeg or not args.ffprobe:
        sys.exit("Falta ffmpeg/ffprobe. Instálalo (Windows: winget install ffmpeg) y vuelve a intentar.")
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

    if exportando:
        ext = os.path.splitext(args.exportar)[1].lower()
        if ext == ".txt":
            conv = Conversor(cols, filas, args.rampa, args.invertir, args.multicolor,
                             "ansi" if args.multicolor else "texto")
            exportar_txt(args, conv, total, args.exportar)
        else:
            conv = Conversor(cols, filas, args.rampa, args.invertir, args.multicolor, "ass")
            exportar_video(args, conv, total, duracion, tiene_audio, args.exportar)
        return

    salida = ("ansi" if args.terminal else "tk") if args.multicolor else "texto"
    conv = Conversor(cols, filas, args.rampa, args.invertir, args.multicolor, salida)
    if args.precargar:
        try:
            ruta = precargar(args, conv, total)
        except KeyboardInterrupt:
            sys.exit(1)
        fabrica = lambda: LectorCache(ruta)
    else:
        fabrica = lambda: LectorFFmpeg(args.ffmpeg, args.video, args.fps, conv)

    audio = Audio(args.ffplay, args.ffmpeg, args.video) if args.audio and tiene_audio else None
    sesion = Sesion(lambda: Fuente(fabrica, args.fps), args.fps, audio,
                    args.retraso_audio, args.bucle)

    if args.terminal:
        reproducir_terminal(args, sesion, cols, filas, duracion)
        return
    root.deiconify()
    ReproductorVentana(root, args, sesion, cols, filas, duracion)
    root.mainloop()


if __name__ == "__main__":
    main()
