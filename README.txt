===============================================================================
                         BAD APPLE!! ASCII PLAYER
                  Reproductor de video en arte ASCII con audio
===============================================================================

  Autor ........ Zaphkiel
  Tipo ......... Proyecto personal / hobby
  Lenguaje ..... Python 3 (solo librería estándar)
  Licencia ..... MIT (ver sección 13)
  Archivo ...... bad_apple.py
  Versión ...... 2.0


-------------------------------------------------------------------------------
 ÍNDICE
-------------------------------------------------------------------------------
  1.  ¿Qué es esto?
  2.  Funciones
  3.  Contenido de la carpeta
  4.  Requisitos
  5.  Instalación
  6.  Uso rápido
  7.  Opciones de línea de comandos
  8.  Controles
  9.  Cómo funciona por dentro
  10. Rendimiento y consejos
  11. Solución de problemas
  12. Historial de cambios e ideas
  13. Licencia y créditos


-------------------------------------------------------------------------------
 1. ¿QUÉ ES ESTO?
-------------------------------------------------------------------------------
Es un homenaje al clásico de internet "Bad Apple!! en ASCII", la versión del
famoso video de sombras de Touhou Project dibujada solo con caracteres de
texto. Lo hice por hobby, como fan de Touhou.

El script toma cualquier video (por defecto badapple.mp4), lo convierte cuadro
a cuadro en arte ASCII y lo reproduce:

  * en una ventana propia (Tkinter), o
  * directamente en la consola / terminal,

con el audio original sincronizado. También puede guardar la animación como
un video nuevo (.mp4, .gif...) o como un archivo de texto.

Aunque está pensado para Bad Apple!!, funciona con cualquier video que ffmpeg
pueda leer (mp4, webm, mkv, avi, mov, gif...). Los videos de alto contraste,
como Bad Apple!!, son los que mejor se ven.


-------------------------------------------------------------------------------
 2. FUNCIONES
-------------------------------------------------------------------------------
  * Reproducción en ventana o en terminal, con audio sincronizado.
  * Pausa y reanudación con la barra espaciadora (el audio sigue donde iba).
  * Pantalla completa con F11.
  * Ajuste automático: la letra se adapta al tamaño de la ventana, y en la
    terminal las columnas se adaptan al tamaño de la consola.
  * Modo multicolor: cada carácter toma el color del píxel original
    (512 colores).
  * Bucle: vuelve a empezar al terminar.
  * Precarga: convierte el video entero una sola vez y lo guarda en caché,
    para que las reproducciones siguientes vayan totalmente fluidas.
  * Exportar a .mp4, .mkv, .webm, .gif (video ASCII, con audio si el formato
    lo admite) o a .txt (todos los cuadros como texto).
  * Colores por nombre ("verde", "ambar", "red"...) o en hexadecimal.
  * Todo configurable desde el archivo o desde el comando.


-------------------------------------------------------------------------------
 3. CONTENIDO DE LA CARPETA
-------------------------------------------------------------------------------
  bad_apple.py ........ El reproductor (único archivo de código).
  badapple.mp4 ........ Video de Bad Apple!!
                          - Video: H.264, 480x360, 30 fps
                          - Audio: AAC
                          - Duración: 3:39 aprox.
  README.txt .......... Este archivo.
  CONFIGURACIONES.txt . Referencia de todas las opciones y presets listos.
  .cache_ascii\ ....... (Se crea sola al usar --precargar.) Videos ya
                        convertidos. Se puede borrar sin problema:
                        python bad_apple.py --limpiar-cache
  .vs\ ................ Carpeta interna de Visual Studio (se puede ignorar;
                        no la necesita el programa).


-------------------------------------------------------------------------------
 4. REQUISITOS
-------------------------------------------------------------------------------
  * Python 3.9 o superior.
      - Probado con Python 3.14.
      - No hace falta instalar paquetes con pip: solo usa la librería
        estándar (argparse, subprocess, threading, tkinter, gzip...).
      - Tkinter viene incluido en el instalador oficial de Python para
        Windows. En Linux puede que tengas que instalarlo aparte
        (p. ej. "sudo apt install python3-tk").

  * FFmpeg, con sus tres herramientas en el PATH:
      - ffmpeg  -> decodifica el video y genera las exportaciones.
      - ffprobe -> lee la resolución, los FPS y la duración del video.
      - ffplay  -> reproduce el audio (opcional: sin él va sin sonido).
      Para exportar a video, ffmpeg debe incluir libass (las versiones
      "full" de Windows y las de Linux/macOS ya lo traen).

  * Sistema operativo: Windows, Linux o macOS.
      - En Windows usa la fuente Consolas; en el resto, Courier.


-------------------------------------------------------------------------------
 5. INSTALACIÓN
-------------------------------------------------------------------------------
  1) Instala Python desde https://www.python.org/downloads/
     (marca "Add Python to PATH" durante la instalación).

  2) Instala FFmpeg:
       Windows ...... winget install ffmpeg
       Linux ........ sudo apt install ffmpeg      (Debian/Ubuntu)
       macOS ........ brew install ffmpeg

  3) Cierra y vuelve a abrir la terminal, y comprueba que todo responde:
       python --version
       ffmpeg -version
       ffplay -version

  4) Listo. No hay nada que compilar.


-------------------------------------------------------------------------------
 6. USO RÁPIDO
-------------------------------------------------------------------------------
Abre una terminal en esta carpeta y ejecuta:

  python bad_apple.py

Eso abre badapple.mp4 en una ventana con la configuración por defecto.

Otros ejemplos:

  python bad_apple.py otro_video.mp4             (otro video)
  python bad_apple.py --cols 150                 (más detalle)
  python bad_apple.py --multicolor               (con los colores del video)
  python bad_apple.py --terminal                 (en la consola)
  python bad_apple.py --color verde              (texto verde)
  python bad_apple.py --bucle                    (repetir sin parar)
  python bad_apple.py --precargar                (más fluido)
  python bad_apple.py --no-audio                 (sin sonido)
  python bad_apple.py --exportar bad_apple_ascii.mp4
  python bad_apple.py --exportar bad_apple_ascii.txt
  python bad_apple.py --help                     (ayuda completa)

También puedes cambiar los valores por defecto editando el bloque
"CONFIGURACIÓN" al principio de bad_apple.py. Lo que escribas en el comando
siempre tiene prioridad sobre ese bloque.

Hay presets listos para copiar en CONFIGURACIONES.txt.


-------------------------------------------------------------------------------
 7. OPCIONES DE LÍNEA DE COMANDOS
-------------------------------------------------------------------------------
  video                   Ruta del video. Por defecto: badapple.mp4

  IMAGEN
  --cols N                Ancho en caracteres. Por defecto: 100
  --fps N                 Cuadros por segundo. Por defecto: los del video
                          (máximo 60).
  --rampa "TEXTO"         Caracteres, de oscuro a claro. Por defecto: " .:-=+*#%@"
  --invertir / --no-invertir        Intercambia claro y oscuro.
  --multicolor / --no-multicolor    Cada carácter con el color del video.

  APARIENCIA
  --color COLOR           Color del texto: "#RRGGBB" o un nombre.
                          Por defecto: #ffffff
  --fondo COLOR           Color del fondo (ventana y exportación).
                          Por defecto: #000000
  --letra N               Tamaño de letra inicial en la ventana. Por defecto: 7
  --ajustar / --no-ajustar          Ajuste automático al tamaño disponible.

  REPRODUCCIÓN
  --audio / --no-audio    Con o sin sonido. (--sin-audio también funciona.)
  --retraso-audio S       Segundos de margen para que arranque el audio.
                          Por defecto: 0.15
  --terminal / --no-terminal        En la consola o en una ventana.
  --bucle / --no-bucle              Repetir al terminar.
  --precargar / --no-precargar      Convertir todo antes de reproducir.
  --limpiar-cache         Borra los videos precargados y sale.

  EXPORTAR
  --exportar ARCHIVO      Guarda la animación en vez de reproducirla.
                          Formatos: .mp4 .mkv .mov .webm .gif .txt
  --alto-exportar N       Alto aproximado del video exportado, en píxeles.
                          Por defecto: 720

  FFMPEG
  --ffmpeg / --ffprobe / --ffplay RUTA   Rutas si no están en el PATH.

Cada opción que activa algo tiene su versión "--no-..." para desactivarla,
así que puedes anular desde el comando lo que pongas en el archivo.

La explicación detallada de cada opción está en CONFIGURACIONES.txt.


-------------------------------------------------------------------------------
 8. CONTROLES
-------------------------------------------------------------------------------
  Modo ventana:
    Espacio ........ Pausa / seguir (al terminar: repetir)
    F11 ............ Pantalla completa (entrar / salir)
    + / - .......... Agrandar / achicar la letra (desactiva el ajuste auto.)
    0 .............. Volver al ajuste automático de la letra
    Esc ............ Salir de pantalla completa; si no lo estás, cerrar
    Q .............. Cerrar
    Botón X ........ Cerrar (también detiene el audio)

  Modo terminal:
    Espacio ........ Pausa / seguir (al terminar: repetir)
    Q o Esc ........ Salir
    Ctrl + C ....... Salir (restaura el cursor y los colores)

  En la parte inferior se ve:
    tiempo / duración · resolución en caracteres · FPS reales · letra · estado


-------------------------------------------------------------------------------
 9. CÓMO FUNCIONA POR DENTRO
-------------------------------------------------------------------------------
  1) ANÁLISIS
     ffprobe lee el ancho, el alto, los FPS, la duración y si hay audio.

  2) CÁLCULO DE FILAS
     Con las columnas elegidas se calcula el número de filas que mantiene la
     proporción. Como un carácter es unas 2 veces más alto que ancho, se
     multiplica por 0.5:
         filas = columnas * alto / ancho * 0.5
     Ejemplo con badapple.mp4 (480x360) y 100 columnas -> 38 filas.

  3) DECODIFICACIÓN (clase LectorFFmpeg + hilo Fuente)
     ffmpeg reescala cada cuadro a columnas x filas y lo envía como bytes
     crudos: 1 byte por píxel (gris) o 3 bytes (RGB) en modo multicolor.
     Un hilo en segundo plano los convierte y los deja en una cola de unos
     3 segundos de búfer.

  4) CONVERSIÓN A ASCII (clase Conversor)
     - Gris: una tabla de 256 entradas asigna a cada brillo un carácter de
       la rampa; se aplica a todo el cuadro de una vez con str.translate
       (unos 2.800 cuadros por segundo a 100 columnas).
     - Multicolor: el brillo se calcula con la fórmula de luminancia
       (0.30 R + 0.59 G + 0.11 B) y el color se reduce a 512 tonos.
       Los caracteres seguidos del mismo color se agrupan en "tramos" para
       dibujarlos de una sola vez.

  5) PRECARGA (opcional)
     Con --precargar, los cuadros ya convertidos se guardan comprimidos en
     .cache_ascii\. El nombre del archivo depende del video y de los ajustes
     (columnas, FPS, rampa, colores...), así que si cambias algo se genera
     otra caché, y si no, se reutiliza al instante.

  6) AUDIO (clase Audio)
     Al empezar, el audio se extrae a un WAV temporal (tarda ~0.2 s y se
     borra al cerrar), y ffplay lo reproduce sin ventana. Al pausar se
     detiene; al seguir se vuelve a lanzar desde el segundo exacto (-ss).
     ¿Por qué un WAV? En un MP4, "ffplay -ss" salta al fotograma clave
     ANTERIOR del video, que en badapple.mp4 puede estar hasta 7 s antes:
     tras una pausa el audio quedaba varios segundos atrasado. En un WAV el
     salto es exacto (medido: unos 80 ms de diferencia, antes y después de
     pausar).

  7) SINCRONIZACIÓN (clase Reloj)
     El cuadro no se elige con un contador, sino con el reloj real:
         cuadro_objetivo = (tiempo_actual - inicio) * fps
     Si el programa se atrasa, salta los cuadros sobrantes. Por eso el video
     nunca se desfasa del audio aunque el PC vaya lento. Antes de empezar se
     espera a que el búfer tenga un segundo de video, y RETRASO_AUDIO
     compensa lo que tarda ffplay en arrancar.

  8) SESIÓN (clase Sesion)
     Une la fuente, el audio y el reloj, y se encarga de la pausa y del
     bucle (al terminar, crea una fuente nueva y vuelve a empezar).

  9) DIBUJO
     - Ventana: un Label de Tkinter (gris) o un Text con 512 etiquetas de
       color (multicolor), centrado. Al cambiar el tamaño de la ventana se
       busca la letra más grande que cabe.
     - Terminal: códigos ANSI para mover el cursor, ocultarlo y aplicar
       color real de 24 bits. El teclado se lee sin bloquear (msvcrt en
       Windows, termios en Linux/macOS).

  10) EXPORTAR A VIDEO
     Cada cuadro se escribe como un subtítulo ASS (con sus colores) y ffmpeg
     los dibuja con libass sobre un fondo liso, añadiendo el audio original.
     Así no hace falta ninguna librería de imágenes como Pillow.


-------------------------------------------------------------------------------
 10. RENDIMIENTO Y CONSEJOS
-------------------------------------------------------------------------------
  * Más columnas = más detalle, pero más trabajo. Entre 80 y 150 va bien en
    casi cualquier PC. Por encima de 200 puede bajar de FPS.
  * El modo multicolor es unas 3-4 veces más pesado que el gris. Si va a
    tirones, usa --precargar o menos columnas.
  * --precargar tarda unos segundos la primera vez; luego arranca al
    instante y va fluido incluso en PCs lentos.
  * Con el ajuste automático solo tienes que agrandar la ventana (o pulsar
    F11) para ver la imagen más grande.
  * En modo terminal, maximiza la consola y achica su fuente
    (Ctrl + rueda del ratón en Windows Terminal) ANTES de empezar: las
    columnas se ajustan al tamaño de la consola al arrancar.
  * Windows Terminal dibuja mucho más rápido y con mejores colores que la
    consola clásica (cmd.exe).
  * Exportar Bad Apple!! completo a .mp4 (100 columnas, 720p) tardó unos
    35 segundos en el PC de desarrollo y ocupa unos 60 MB. Los .gif son
    mucho más pesados: usa menos columnas, --fps 15 y --alto-exportar 360.


-------------------------------------------------------------------------------
 11. SOLUCIÓN DE PROBLEMAS
-------------------------------------------------------------------------------
  "No encuentro el video: ..."
      La ruta no existe. Ejecuta el script desde esta carpeta o pasa la ruta
      completa entre comillas.

  "Falta ffmpeg/ffprobe..."
      FFmpeg no está instalado o no está en el PATH. Instálalo (sección 5) y
      abre una terminal nueva. También puedes usar --ffmpeg y --ffprobe.

  "Aviso: no encontré ffplay, sigo sin audio."
      Falta ffplay. Instala el FFmpeg completo o usa --ffplay RUTA.

  "Color no válido para --color: ..."
      Usa "#rrggbb", "#rgb" o uno de los nombres que muestra el mensaje.
      (En la ventana también valen los nombres de color de Tkinter.)

  "La terminal es pequeña: uso N columnas..."
      El ajuste automático redujo las columnas para que quepa. Agranda la
      consola, achica su fuente o usa --no-ajustar.

  El audio va adelantado al video
      Sube --retraso-audio (p. ej. 0.3).

  El audio va atrasado respecto al video
      Baja --retraso-audio (p. ej. 0.05 o 0).

  La letra no cambia al agrandar la ventana
      Pulsaste + o -, y eso desactiva el ajuste automático. Pulsa 0.

  En la terminal salen símbolos raros como "←[38;2;..."
      Tu consola no admite códigos ANSI. Usa Windows Terminal o el modo
      ventana (sin --terminal).

  Los colores se ven al revés (fondo claro)
      Usa --invertir.

  "ffmpeg no pudo generar el video"
      Tu ffmpeg no tiene libass, o el formato no es válido. Prueba con .mp4
      o instala la versión completa de FFmpeg.

  En el video exportado algunos símbolos cambiaron
      Los caracteres { } \ tienen significado especial en los subtítulos
      ASS y se cambian por ( ) / al exportar a video.

  "No module named tkinter" (Linux)
      sudo apt install python3-tk


-------------------------------------------------------------------------------
 12. HISTORIAL DE CAMBIOS E IDEAS
-------------------------------------------------------------------------------
  v2.0 (2026-11-21)
    [x] Pausa / reanudar con la barra espaciadora (con el audio sincronizado).
    [x] Pantalla completa (F11).
    [x] Ajuste automático de la letra a la ventana y de las columnas a la
        terminal.
    [x] Modo multicolor (ventana, terminal y exportación).
    [x] Bucle.
    [x] Precarga con caché comprimida.
    [x] Exportar a .mp4 / .mkv / .webm / .gif / .txt.
    [x] Todas las opciones de interruptor tienen su "--no-..." para anularlas
        desde el comando.
    [x] Colores por nombre, y mensaje claro si el color no es válido (antes
        el modo terminal fallaba con nombres como "red").
    [x] El búfer se llena antes de arrancar, para no saltarse el principio.
    [x] Corregido: al reanudar tras una pausa el audio quedaba varios
        segundos atrasado (y ~0.6 s atrasado desde el inicio). Ahora el
        audio se reproduce desde un WAV temporal y el salto es exacto.

  v1.0
    Reproducción en ventana y en terminal con audio sincronizado.

  Ideas para el futuro
    [ ] Adelantar / retroceder con las flechas.
    [ ] Barra de progreso clicable en la ventana.
    [ ] Elegir la fuente (tipo de letra) desde la configuración.


-------------------------------------------------------------------------------
 13. LICENCIA Y CRÉDITOS
-------------------------------------------------------------------------------
CRÉDITOS
  * "Bad Apple!!" es una composición original de ZUN (Team Shanghai Alice),
    del juego Touhou Project 4: Lotus Land Story.
  * La versión cantada pertenece a Alstroemeria Records
    (feat. nomico).
  * El video de sombras original es obra de sus creadores en Nico Nico Douga
    (Anira y colaboradores).
  * Todo el contenido de Touhou Project y la música pertenecen a sus
    respectivos dueños. Este es un proyecto de fans sin fines de lucro.
  * El archivo badapple.mp4 NO está cubierto por la licencia MIT.
  * Herramientas: Python y FFmpeg (https://ffmpeg.org).

LICENCIA DEL CÓDIGO (bad_apple.py)

  MIT License

  Copyright (c) 2026 Zaphkiel

  Permission is hereby granted, free of charge, to any person obtaining a copy
  of this software and associated documentation files (the "Software"), to
  deal in the Software without restriction, including without limitation the
  rights to use, copy, modify, merge, publish, distribute, sublicense, and/or
  sell copies of the Software, and to permit persons to whom the Software is
  furnished to do so, subject to the following conditions:

  The above copyright notice and this permission notice shall be included in
  all copies or substantial portions of the Software.

  THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
  IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
  FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
  AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
  LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
  FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS
  IN THE SOFTWARE.

===============================================================================
                       Hecho con cariño por Zaphkiel
===============================================================================
