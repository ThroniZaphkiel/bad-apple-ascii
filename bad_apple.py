#!/usr/bin/env python3
"""
bad_apple.py — Reproduce cualquier video como arte ASCII, con audio sincronizado.

Inspirado en el clásico "Bad Apple!! en ASCII": ffmpeg decodifica el video a
cuadros pequeños en escala de grises, cada píxel se convierte en un carácter
según su brillo y el resultado se dibuja en una ventana de Tkinter (o en la
terminal). ffplay reproduce el audio y el video se sincroniza con el reloj.

Requisitos:
  - Python 3.8+ (solo librería estándar)
  - ffmpeg y ffplay en el PATH  (https://ffmpeg.org/download.html)
    En Windows:  winget install ffmpeg

Uso:
  python bad_apple.py                     # abre el VIDEO de la configuración
  python bad_apple.py otro_video.mp4
  python bad_apple.py video.mp4 --cols 120 --fps 30
  python bad_apple.py video.mp4 --terminal          # sin ventana, en la consola
  python bad_apple.py video.mp4 --sin-audio --color "#00ff66"

Teclas (modo ventana):  Esc = salir   +/- = tamaño de letra
"""

import argparse
import json
import os
import queue
import shutil
import subprocess
import sys
import threading
import time

# =========================================================================== #
#  CONFIGURACIÓN — cambia estos valores a tu gusto y guarda el archivo.
#  (Lo que escribas en el comando, p. ej. --cols 140, tiene prioridad.)
# =========================================================================== #
VIDEO          = "badapple.mp4"  # video que se abre si no escribes ninguno
COLUMNAS       = 100         # ancho en caracteres: más = más detalle (60-200)
TAMANO_LETRA   = 7           # tamaño de letra en la ventana (4-12)
COLOR_TEXTO    = "#ffffff"   # blanco. Ej: "#3d8bff" azul, "#00ff66" verde
COLOR_FONDO    = "#000000"   # negro
FPS            = None        # None = los del video. Ej: 24 o 30
RAMPA          = " .:-=+*#%@"  # caracteres de oscuro a claro
INVERTIR       = False       # True = intercambia claro y oscuro
CON_AUDIO      = True        # False = sin sonido
RETRASO_AUDIO  = 0.15        # súbelo si el sonido va adelantado
EN_TERMINAL    = False       # True = dibuja en la consola, no en ventana
# =========================================================================== #


# --------------------------------------------------------------------------- #
#  Video -> cuadros ASCII
# --------------------------------------------------------------------------- #
def info_video(ffprobe, ruta):
    """Devuelve (ancho, alto, fps, duración) usando ffprobe."""
    cmd = [ffprobe, "-v", "error", "-select_streams", "v:0",
           "-show_entries", "stream=width,height,r_frame_rate:format=duration",
           "-of", "json", ruta]
    datos = json.loads(subprocess.check_output(cmd))
    s = datos["streams"][0]
    num, den = s.get("r_frame_rate", "30/1").split("/")
    fps = float(num) / float(den or 1) if float(den or 1) else 30.0
    dur = float(datos.get("format", {}).get("duration", 0) or 0)
    return int(s["width"]), int(s["height"]), fps, dur


def tabla_caracteres(rampa, invertir):
    """Tabla de 256 entradas: brillo (0-255) -> carácter."""
    r = rampa[::-1] if invertir else rampa
    n = len(r)
    return [r[min(n - 1, v * n // 256)] for v in range(256)]


def cuadro_a_texto(datos, cols, filas, tabla):
    """Convierte un cuadro gris crudo (bytes) en un string multilínea."""
    lineas = []
    for y in range(filas):
        fila = datos[y * cols:(y + 1) * cols]
        lineas.append("".join(tabla[b] for b in fila))
    return "\n".join(lineas)


class LectorCuadros(threading.Thread):
    """Hilo que lee cuadros de ffmpeg y los deja convertidos en una cola."""

    def __init__(self, ffmpeg, ruta, cols, filas, fps, tabla):
        super().__init__(daemon=True)
        self.cols, self.filas, self.tabla = cols, filas, tabla
        self.cola = queue.Queue(maxsize=int(fps * 3))
        self.terminado = False
        self.proc = subprocess.Popen(
            [ffmpeg, "-v", "error", "-i", ruta,
             "-vf", f"fps={fps},scale={cols}:{filas},format=gray",
             "-f", "rawvideo", "-pix_fmt", "gray", "-"],
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)

    def run(self):
        tam = self.cols * self.filas
        while True:
            datos = self.proc.stdout.read(tam)
            if len(datos) < tam:
                break
            self.cola.put(cuadro_a_texto(datos, self.cols, self.filas, self.tabla))
        self.terminado = True
        self.cola.put(None)  # señal de fin

    def detener(self):
        try:
            self.proc.kill()
        except Exception:
            pass


def iniciar_audio(ffplay, ruta):
    if not ffplay:
        return None
    return subprocess.Popen(
        [ffplay, "-nodisp", "-autoexit", "-loglevel", "quiet", ruta],
        stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL)


# --------------------------------------------------------------------------- #
#  Reloj compartido: decide qué cuadro toca mostrar
# --------------------------------------------------------------------------- #
class Reloj:
    def __init__(self, fps, retraso_audio=0.0):
        self.fps = fps
        self.inicio = time.perf_counter() + retraso_audio
        self.mostrados = 0

    def siguiente(self, cola):
        """Saca de la cola el cuadro que corresponde al tiempo actual,
        saltando los atrasados. Devuelve (texto | None si terminó | '' si
        todavía no toca, espera_en_segundos)."""
        objetivo = int((time.perf_counter() - self.inicio) * self.fps)
        if objetivo < self.mostrados:
            return "", (self.mostrados - objetivo) / self.fps
        texto = ""
        while self.mostrados <= objetivo:
            try:
                texto = cola.get(timeout=0.5)
            except queue.Empty:
                return "", 0.01
            if texto is None:
                return None, 0
            self.mostrados += 1
        espera = self.inicio + self.mostrados / self.fps - time.perf_counter()
        return texto, max(0.0, espera)


# --------------------------------------------------------------------------- #
#  Reproductor en ventana (Tkinter)
# --------------------------------------------------------------------------- #
class Player:
    def __init__(self, root, path, fps, cols, filas, audio, ffmpeg, ffplay,
                 color, fondo, tam_letra, tabla, retraso_audio):
        import tkinter as tk
        import tkinter.font as tkfont

        self.root = root
        self.path = path
        self.fps = fps
        self.cols, self.filas = cols, filas
        self.lector = LectorCuadros(ffmpeg, path, cols, filas, fps, tabla)
        self.audio = iniciar_audio(ffplay, path) if audio else None
        self.cerrado = False

        root.title(f"Bad Apple ASCII — {os.path.basename(path)}")
        root.configure(bg=fondo)
        self.fuente = tkfont.Font(family="Consolas" if sys.platform == "win32"
                                  else "Courier", size=tam_letra)
        self.pantalla = tk.Label(root, font=self.fuente, fg=color, bg=fondo,
                                 justify="left", anchor="nw")
        self.pantalla.pack(fill="both", expand=True, padx=6, pady=6)
        self.estado = tk.Label(root, fg="#7f8fa6", bg=fondo, anchor="w",
                               font=(self.fuente.actual("family"), 9))
        self.estado.pack(fill="x", padx=6)

        root.bind("<Escape>", lambda e: self.cerrar())
        root.bind("<plus>", lambda e: self.zoom(+1))
        root.bind("<minus>", lambda e: self.zoom(-1))
        root.protocol("WM_DELETE_WINDOW", self.cerrar)

        self.lector.start()
        self.reloj = Reloj(fps, retraso_audio if self.audio else 0.0)
        self.t_fps = time.perf_counter()
        self.cuenta_fps = 0
        self.fps_real = 0.0
        self.tick()

    def zoom(self, d):
        self.fuente.configure(size=max(2, self.fuente.cget("size") + d))

    def tick(self):
        if self.cerrado:
            return
        texto, espera = self.reloj.siguiente(self.lector.cola)
        if texto is None:
            self.estado.config(text="Fin del video. Esc para salir.")
            return
        if texto:
            self.pantalla.config(text=texto)
            self.cuenta_fps += 1
            ahora = time.perf_counter()
            if ahora - self.t_fps >= 1:
                self.fps_real = self.cuenta_fps / (ahora - self.t_fps)
                self.t_fps, self.cuenta_fps = ahora, 0
            seg = self.reloj.mostrados / self.fps
            self.estado.config(
                text=f"{int(seg // 60):02d}:{int(seg % 60):02d}  ·  "
                     f"{self.cols}x{self.filas}  ·  {self.fps_real:4.1f} fps")
        self.root.after(max(1, int(espera * 1000)), self.tick)

    def cerrar(self):
        self.cerrado = True
        self.lector.detener()
        if self.audio:
            self.audio.kill()
        self.root.destroy()


# --------------------------------------------------------------------------- #
#  Reproductor en terminal
# --------------------------------------------------------------------------- #
def hex_a_ansi(color):
    c = color.lstrip("#")
    r, g, b = int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16)
    return f"\033[38;2;{r};{g};{b}m"


def reproducir_terminal(args, cols, filas, tabla):
    if sys.platform == "win32":
        os.system("")  # activa los códigos ANSI en la consola de Windows
    lector = LectorCuadros(args.ffmpeg, args.video, cols, filas, args.fps, tabla)
    audio = None if args.sin_audio else iniciar_audio(args.ffplay, args.video)
    lector.start()
    reloj = Reloj(args.fps, args.retraso_audio if audio else 0.0)
    out = sys.stdout
    out.write("\033[2J\033[?25l" + hex_a_ansi(args.color))
    try:
        while True:
            texto, espera = reloj.siguiente(lector.cola)
            if texto is None:
                break
            if texto:
                out.write("\033[H" + texto)
                out.flush()
            if espera:
                time.sleep(espera)
    except KeyboardInterrupt:
        pass
    finally:
        out.write("\033[0m\033[?25h\n")
        lector.detener()
        if audio:
            audio.kill()


# --------------------------------------------------------------------------- #
def main():
    p = argparse.ArgumentParser(description="Reproduce un video como arte ASCII.")
    p.add_argument("video", nargs="?", default=VIDEO,
                   help=f"ruta del video (mp4, webm, mkv...). Por defecto: {VIDEO}")
    p.add_argument("--cols", type=int, default=COLUMNAS, help=f"columnas de caracteres ({COLUMNAS})")
    p.add_argument("--fps", type=float, default=FPS, help="cuadros por segundo (por defecto, los del video)")
    p.add_argument("--color", default=COLOR_TEXTO, help=f"color del texto ({COLOR_TEXTO})")
    p.add_argument("--fondo", default=COLOR_FONDO, help=f"color de fondo ({COLOR_FONDO})")
    p.add_argument("--letra", type=int, default=TAMANO_LETRA, help=f"tamaño de letra en la ventana ({TAMANO_LETRA})")
    p.add_argument("--rampa", default=RAMPA, help="caracteres de oscuro a claro")
    p.add_argument("--invertir", action="store_true", default=INVERTIR, help="invierte claro/oscuro")
    p.add_argument("--sin-audio", action="store_true", default=not CON_AUDIO, help="no reproducir sonido")
    p.add_argument("--retraso-audio", type=float, default=RETRASO_AUDIO,
                   help="segundos que tarda ffplay en arrancar (ajusta si se desfasa)")
    p.add_argument("--terminal", action="store_true", default=EN_TERMINAL,
                   help="dibujar en la consola en vez de una ventana")
    p.add_argument("--ffmpeg", default=shutil.which("ffmpeg"))
    p.add_argument("--ffplay", default=shutil.which("ffplay"))
    p.add_argument("--ffprobe", default=shutil.which("ffprobe"))
    args = p.parse_args()

    if not os.path.isfile(args.video):
        sys.exit(f"No encuentro el video: {args.video}")
    if not args.ffmpeg or not args.ffprobe:
        sys.exit("Falta ffmpeg/ffprobe. Instálalo (Windows: winget install ffmpeg) y vuelve a intentar.")
    if not args.ffplay and not args.sin_audio:
        print("Aviso: no encontré ffplay, sigo sin audio.")
        args.sin_audio = True

    ancho, alto, fps_video, _ = info_video(args.ffprobe, args.video)
    args.fps = args.fps or min(fps_video, 60)
    cols = args.cols
    # Un carácter es ~2 veces más alto que ancho, por eso el 0.5.
    filas = max(1, round(cols * alto / ancho * 0.5))
    tabla = tabla_caracteres(args.rampa, args.invertir)

    if args.terminal:
        reproducir_terminal(args, cols, filas, tabla)
        return

    import tkinter as tk
    root = tk.Tk()
    Player(root, args.video, args.fps, cols, filas, not args.sin_audio,
           args.ffmpeg, args.ffplay, args.color, args.fondo, args.letra,
           tabla, args.retraso_audio)
    root.mainloop()


if __name__ == "__main__":
    main()
