===============================================================================
                         BAD APPLE!! ASCII PLAYER
                  Reproductor de video en arte ASCII con audio
===============================================================================

  Autor ........ Zaphkiel  (GitHub: ThroniZaphkiel)
  Tipo ......... Proyecto personal / hobby
  Lenguaje ..... Python 3 (solo librería estándar)
  Licencia ..... MIT (ver sección 15)
  Archivo ...... bad_apple.py
  Versión ...... 3.0


-------------------------------------------------------------------------------
 DESCARGA RÁPIDA (WINDOWS, SIN INSTALAR PYTHON)
-------------------------------------------------------------------------------
  1) Descarga "BadAppleASCII-v3.0-windows.zip" de la página de Releases:
       https://github.com/ThroniZaphkiel/bad-apple-ascii/releases/latest
     (en la sección "Assets", al final de la página).
  2) Descomprime el .zip en una carpeta (clic derecho > Extraer todo).
  3) Instala FFmpeg. Abre PowerShell y escribe:   winget install ffmpeg
     (o pon ffmpeg.exe, ffprobe.exe y ffplay.exe junto al programa).
  4) Consigue el video por tu cuenta (no viene incluido, ver sección 3) y
     guárdalo como "badapple.mp4" en la misma carpeta que el .exe.
  5) Doble clic en BadAppleASCII.exe. También puedes arrastrar cualquier
     video encima del .exe.

  Si Windows muestra "Windows protegió su PC" (SmartScreen), es porque el
  .exe no tiene firma digital: pulsa "Más información" > "Ejecutar de todas
  formas". Si prefieres no hacerlo, usa la versión en Python (sección 6).


-------------------------------------------------------------------------------
 ÍNDICE
-------------------------------------------------------------------------------
  1.  ¿Qué es esto?
  2.  "Bad Apple!! en todo": de dónde nace este proyecto
  3.  El video (no viene incluido)
  4.  Funciones
  5.  Contenido de la carpeta
  6.  Requisitos e instalación
  7.  Uso rápido
  8.  Versión .exe (sin instalar Python)
  9.  Opciones de línea de comandos
  10. Controles
  11. Cómo funciona por dentro
  12. Rendimiento y consejos
  13. Solución de problemas
  14. Historial de cambios e ideas
  15. Licencia y créditos


-------------------------------------------------------------------------------
 1. ¿QUÉ ES ESTO?
-------------------------------------------------------------------------------
Un reproductor que convierte cualquier video en arte ASCII (texto) cuadro a
cuadro y lo reproduce con su audio sincronizado:

  * en una ventana propia (Tkinter), o
  * directamente en la consola / terminal.

Tiene tres estilos de dibujo (rampa de caracteres, contornos y braille) y
puede guardar la animación como un video nuevo (.mp4, .gif...) o como texto.

Lo hice por hobby, como fan de Touhou.


-------------------------------------------------------------------------------
 2. "BAD APPLE!! EN TODO": DE DÓNDE NACE ESTE PROYECTO
-------------------------------------------------------------------------------
"Bad Apple!!" es un tema de Touhou Project. En 2009 se publicó en Nico Nico
Douga un video musical hecho solo con siluetas en blanco y negro (el "shadow
art PV"), sobre la versión cantada de Alstroemeria Records.

Como el video es puro blanco y negro, de alto contraste y con siluetas muy
claras, se convirtió en la prueba favorita para demostrar que cualquier cosa
con una pantalla puede reproducir video. Igual que con "¿corre Doom?", en
internet existe toda una cultura de "correr Bad Apple!! en todo":
osciloscopios, calculadoras gráficas, Minecraft, hojas de cálculo, el
Administrador de tareas de Windows, microcontroladores con pantallas
diminutas, consolas retro... y, por supuesto, la terminal en ASCII.

Este proyecto nace para eso: reproducir ese video en concreto como arte
ASCII. Con el tiempo creció y ahora sirve para cualquier video, pero Bad
Apple!! sigue siendo el que mejor se ve.


-------------------------------------------------------------------------------
 3. EL VIDEO (NO VIENE INCLUIDO)
-------------------------------------------------------------------------------
El video de Bad Apple!! NO se distribuye con este proyecto: la música y la
animación tienen derechos de autor de sus creadores (ver sección 15).

Para usarlo:
  1) Consigue por tu cuenta una copia del video (el PV de siluetas de
     Bad Apple!! es muy fácil de encontrar). Publicación original, en
     Nico Nico Douga:  https://www.nicovideo.jp/watch/sm8628149
  2) Guárdala como "badapple.mp4" en la misma carpeta que bad_apple.py
     (o que el .exe).
  3) Ejecuta el programa.

O usa cualquier otro video:   python bad_apple.py "mi video.mp4"

El repositorio de git ignora los archivos de video (.mp4, .mkv, .gif...),
así que nunca se suben por accidente.


-------------------------------------------------------------------------------
 4. FUNCIONES
-------------------------------------------------------------------------------
  * Tres estilos de dibujo:
      - brillo ... cada carácter según el brillo: " .:-=+*#%@"
      - bordes ... contornos con / | \ - sobre el relleno (o solo líneas)
      - braille .. cada carácter son 2x4 puntos (⣿): 8 veces más detalle
  * Reproducción en ventana o en terminal, con audio sincronizado.
  * Pausa, avanzar / retroceder con las flechas y barra de progreso en la
    que puedes hacer clic para ir a cualquier punto.
  * Pantalla completa con F11 y ajuste automático de la letra.
  * Modo multicolor: cada carácter con el color del video (512 colores).
  * Bucle y precarga (convierte el video una vez y lo guarda en caché).
  * Exportar a .mp4, .mkv, .webm, .gif o .txt.
  * Colores por nombre ("verde", "ambar"...) o en hexadecimal.
  * Versión .exe para Windows: doble clic, sin instalar Python.


-------------------------------------------------------------------------------
 5. CONTENIDO DE LA CARPETA
-------------------------------------------------------------------------------
  bad_apple.py ........ El reproductor (único archivo de código).
  README.txt .......... Este archivo.
  CONFIGURACIONES.txt . Referencia de todas las opciones y presets listos.
  construir_exe.bat ... Compila las versiones .exe (ver sección 8).
  icono.ico ........... Icono del programa (una manzana hecha con ASCII).
  LICENSE ............. Licencia MIT del código (ver sección 15).
  .gitignore .......... Lo que git no debe guardar (videos, caché, .exe).
  badapple.mp4 ........ (No incluido; ver sección 3.)
  .cache_ascii\ ....... (Se crea sola con --precargar.) Se puede borrar:
                        python bad_apple.py --limpiar-cache
  build\, dist\ ....... (Se crean al compilar el .exe.)


-------------------------------------------------------------------------------
 6. REQUISITOS E INSTALACIÓN
-------------------------------------------------------------------------------
  * Python 3.9 o superior (probado con 3.14). Solo usa la librería estándar:
    no hace falta instalar nada con pip.
      - Windows: https://www.python.org/downloads/ (marca "Add Python to
        PATH"). Tkinter ya viene incluido.
      - Linux: puede que necesites "sudo apt install python3-tk".

  * FFmpeg, con ffmpeg, ffprobe y ffplay:
       Windows ...... winget install ffmpeg
       Linux ........ sudo apt install ffmpeg
       macOS ........ brew install ffmpeg
    También vale poner ffmpeg.exe, ffprobe.exe y ffplay.exe junto al
    programa. Para exportar a video, ffmpeg debe incluir libass (las
    versiones "full" de Windows y las de Linux/macOS ya lo traen).

  * Para el estilo braille: una fuente con caracteres braille del mismo
    ancho que las letras. En Windows 11 se usa "Cascadia Mono", que ya viene
    instalada; en Linux, "DejaVu Sans Mono".

Comprueba que todo responde (en una terminal nueva):
    python --version
    ffmpeg -version


-------------------------------------------------------------------------------
 7. USO RÁPIDO
-------------------------------------------------------------------------------
  python bad_apple.py                            (configuración por defecto)
  python bad_apple.py otro_video.mp4             (otro video)
  python bad_apple.py --estilo braille           (máximo detalle)
  python bad_apple.py --estilo bordes            (contornos)
  python bad_apple.py --cols 150                 (más detalle)
  python bad_apple.py --multicolor               (con los colores del video)
  python bad_apple.py --terminal                 (en la consola)
  python bad_apple.py --color verde              (texto verde)
  python bad_apple.py --bucle --precargar        (repetir, muy fluido)
  python bad_apple.py --exportar bad_apple_ascii.mp4
  python bad_apple.py --help                     (ayuda completa)

También puedes cambiar los valores por defecto en el bloque "CONFIGURACIÓN"
del principio de bad_apple.py. Lo que escribas en el comando tiene
prioridad. Hay presets listos para copiar en CONFIGURACIONES.txt.


-------------------------------------------------------------------------------
 8. VERSIÓN .EXE (SIN INSTALAR PYTHON)
-------------------------------------------------------------------------------
La forma más fácil: descarga los .exe ya compilados de la página de Releases
(ver "Descarga rápida", al principio de este archivo).

Para compilarlos tú: doble clic en construir_exe.bat (necesita Python, solo
para compilar). Crea dos programas en la carpeta dist\:

  BadAppleASCII.exe .......... Para doble clic. Abre la ventana directamente,
                               sin consola. También puedes arrastrar
                               cualquier video encima del .exe.
  BadAppleASCII-consola.exe .. Para usar desde una terminal, con todas las
                               opciones: --terminal, --exportar, --help...

Para llevarlo a otro PC, copia junto al .exe:
  * el video (badapple.mp4), y
  * ffmpeg.exe, ffprobe.exe y ffplay.exe si ese PC no tiene FFmpeg
    instalado (también valen dentro de una subcarpeta "ffmpeg\bin\").

Los .exe no se suben al repositorio (cada uno los compila con el .bat).
Si los compartes, Windows SmartScreen puede avisar de "editor desconocido"
porque no están firmados: es normal en programas caseros.


-------------------------------------------------------------------------------
 9. OPCIONES DE LÍNEA DE COMANDOS
-------------------------------------------------------------------------------
  video                   Ruta del video. Por defecto: badapple.mp4

  IMAGEN
  --estilo ESTILO         brillo, bordes o braille. Por defecto: brillo
  --cols N                Ancho en caracteres. Por defecto: 100
  --fps N                 Cuadros por segundo. Por defecto: los del video
  --rampa "TEXTO"         Caracteres de oscuro a claro (brillo y bordes)
  --invertir / --no-invertir        Intercambia claro y oscuro
  --sensibilidad N        Estilo bordes: más bajo = más contornos. Def.: 30
  --multicolor / --no-multicolor    Cada carácter con el color del video

  APARIENCIA
  --color COLOR           Color del texto: "#RRGGBB" o un nombre
  --fondo COLOR           Color del fondo (ventana y exportación)
  --letra N               Tamaño de letra inicial en la ventana. Def.: 7
  --fuente NOMBRE         Tipo de letra. Por defecto: automático
  --ajustar / --no-ajustar          Ajuste automático al tamaño disponible

  REPRODUCCIÓN
  --audio / --no-audio    Con o sin sonido (--sin-audio también funciona)
  --retraso-audio S       Ajuste fino de la sincronía. Por defecto: 0
  --terminal / --no-terminal        En la consola o en una ventana
  --bucle / --no-bucle              Repetir al terminar
  --precargar / --no-precargar      Convertir todo antes de reproducir
  --limpiar-cache         Borra los videos precargados y sale

  EXPORTAR
  --exportar ARCHIVO      Guarda la animación: .mp4 .mkv .mov .webm .gif .txt
  --alto-exportar N       Alto aproximado del video exportado. Def.: 720

  FFMPEG
  --ffmpeg / --ffprobe / --ffplay RUTA   Rutas si no están en el PATH

Explicación detallada de cada opción: CONFIGURACIONES.txt


-------------------------------------------------------------------------------
 10. CONTROLES
-------------------------------------------------------------------------------
  Modo ventana:
    Espacio ........ Pausa / seguir (al terminar: repetir)
    ← / → .......... Retroceder / avanzar 5 segundos
    ↑ / ↓ .......... Avanzar / retroceder 30 segundos
    Inicio ......... Volver al principio
    Clic en la barra de progreso ... ir a ese punto (también arrastrando)
    F11 ............ Pantalla completa (entrar / salir)
    + / - .......... Agrandar / achicar la letra (desactiva el ajuste auto.)
    0 .............. Volver al ajuste automático de la letra
    Esc ............ Salir de pantalla completa; si no lo estás, cerrar
    Q .............. Cerrar

  Modo terminal:
    Espacio ........ Pausa / seguir
    ← → ↑ ↓ ........ Saltar (igual que en la ventana)
    Inicio ......... Volver al principio
    Q o Esc ........ Salir         Ctrl + C ... salir

  Los saltos funcionan también en pausa: se queda en pausa mostrando el
  nuevo punto.


-------------------------------------------------------------------------------
 11. CÓMO FUNCIONA POR DENTRO
-------------------------------------------------------------------------------
  1) ANÁLISIS. ffprobe lee el ancho, el alto, los FPS, la duración y si hay
     audio. Las filas se calculan para mantener la proporción (un carácter
     es ~2 veces más alto que ancho):  filas = columnas * alto / ancho * 0.5

  2) DECODIFICACIÓN (LectorFFmpeg + hilo Fuente). ffmpeg reescala el video y
     entrega cada cuadro como bytes crudos. Si hacen falta varios "planos"
     (color, brillo, gradientes...), ffmpeg los apila uno debajo de otro en
     el mismo cuadro (filtro vstack). Un hilo los convierte y los deja en una
     cola de ~3 s. Para saltar, se relanza ffmpeg con -ss en el punto pedido.

  3) CONVERSIÓN (clase Conversor):
     - brillo: una tabla de 256 entradas asigna un carácter a cada brillo y
       se aplica a todo el cuadro de una vez con str.translate.
     - bordes: ffmpeg calcula los gradientes horizontal y vertical (filtro
       Sobel). Una tabla precalculada de 65.536 entradas convierte cada par
       de gradientes en / | \ - según el ángulo. El borde se dibuja solo en
       el lado claro para que la línea tenga 1 carácter de grosor.
     - braille: el video se reescala a 2x4 píxeles por carácter. Cada punto
       se enciende si supera su umbral (una trama de Bayer de 2x4 que simula
       grises). Los 8 puntos se combinan con aritmética de enteros grandes,
       sin recorrer píxel a píxel.
     - multicolor: el color se reduce a 512 tonos y los caracteres seguidos
       del mismo color se agrupan para dibujarlos de una vez.

  4) PRECARGA (opcional). Los cuadros convertidos se guardan comprimidos en
     .cache_ascii\. Hay una caché distinta por cada combinación de ajustes.

  5) AUDIO (clase Audio). El audio se extrae a un WAV temporal y ffplay lo
     reproduce. En un MP4, "ffplay -ss" salta al fotograma clave anterior
     (hasta 7 s antes en badapple.mp4); en un WAV el salto es exacto.

  6) SINCRONÍA (clases Sesion y Reloj). El audio manda: ffplay informa cada
     ~30 ms del segundo que está sonando, y el reloj del video se corrige
     para seguirlo. Al arrancar, el video espera a que el audio suene de
     verdad (la primera vez ffplay puede tardar casi 1 s). Si el video se
     atrasa, salta los cuadros sobrantes. Desfase medido: unos 30 ms, que
     es lo que dura un cuadro.

  7) DIBUJO. Ventana: un Label de Tkinter, o un Text con 512 etiquetas de
     color en multicolor; al cambiar de tamaño se busca la letra más grande
     que cabe. Terminal: códigos ANSI de color de 24 bits; el teclado se lee
     sin bloquear (msvcrt en Windows, termios en Linux/macOS).

  8) EXPORTAR. Cada cuadro se escribe como un subtítulo ASS y ffmpeg
     (libass) lo dibuja sobre un fondo liso, con el audio original. Antes se
     mide la fuente dibujando una línea de prueba, para que el video tenga
     el tamaño justo. No hace falta Pillow ni ninguna otra librería.


-------------------------------------------------------------------------------
 12. RENDIMIENTO Y CONSEJOS
-------------------------------------------------------------------------------
  * Conversión medida a 100 columnas (cuadros por segundo; hacen falta 30):
        brillo ~2.800 · bordes ~1.500 · braille ~2.100
        multicolor: ~550-750 en cualquier estilo
  * Precargar Bad Apple!! completo en braille tardó unos 3 s y ocupa 2,4 MB.
  * Saltar con las flechas tarda menos de 0,2 s.
  * Exportar Bad Apple!! completo a .mp4 (100 columnas, 720p) tardó unos
    35 s en el PC de desarrollo y ocupa unos 60 MB. Los .gif pesan mucho
    más: usa menos columnas, --fps 15 y --alto-exportar 360.
  * El estilo braille ya tiene mucho detalle con 80-100 columnas.
  * Con el ajuste automático, solo agranda la ventana o pulsa F11.
  * En modo terminal, maximiza la consola y achica su fuente ANTES de
    empezar. Windows Terminal va mucho mejor que la consola clásica.


-------------------------------------------------------------------------------
 13. SOLUCIÓN DE PROBLEMAS
-------------------------------------------------------------------------------
  "No encuentro el video: ..."
      Falta badapple.mp4 (no viene incluido, ver sección 3) o la ruta está
      mal. Pon la ruta completa entre comillas.

  "Falta ffmpeg/ffprobe..."
      Instala FFmpeg (sección 6) y abre una terminal nueva, o pon los .exe
      de FFmpeg junto al programa.

  "Aviso: no encontré ffplay, sigo sin audio."
      Falta ffplay. Instala el FFmpeg completo o usa --ffplay RUTA.

  "Color no válido para --color: ..."
      Usa "#rrggbb", "#rgb" o uno de los nombres que muestra el mensaje.

  El braille se ve descuadrado
      La fuente no tiene caracteres braille del mismo ancho. Usa
      --fuente "Cascadia Mono" (Windows) o "DejaVu Sans Mono" (Linux). En
      modo terminal, cambia la fuente de la terminal.

  El sonido y la imagen no coinciden
      La sincronía es automática. Si aun así lo notas, ajusta
      --retraso-audio: positivo si el sonido va adelantado (p. ej. 0.05),
      negativo si va atrasado (p. ej. -0.05).

  La letra no cambia al agrandar la ventana
      Pulsaste + o -, y eso desactiva el ajuste automático. Pulsa 0.

  En la terminal salen símbolos raros como "←[38;2;..."
      Tu consola no admite códigos ANSI. Usa Windows Terminal o la ventana.

  "ffmpeg no pudo generar el video"
      Tu ffmpeg no tiene libass, o el formato no es válido. Prueba con .mp4.

  En el video exportado la \ se ve un poco distinta
      Se dibuja con el carácter ∖, porque \ tiene un significado especial en
      los subtítulos ASS.

  BadAppleASCII.exe dice que use la versión de consola
      La versión de doble clic solo reproduce en ventana. Para --terminal,
      --exportar o --help usa BadAppleASCII-consola.exe desde una terminal.

  "No module named tkinter" (Linux)
      sudo apt install python3-tk


-------------------------------------------------------------------------------
 14. HISTORIAL DE CAMBIOS E IDEAS
-------------------------------------------------------------------------------
  v3.0 (2026-11-21)
    [x] Estilos nuevos: bordes (contornos con / | \ -) y braille (2x4 puntos
        por carácter, con trama para simular grises).
    [x] Avanzar / retroceder con las flechas, ir al inicio, y barra de
        progreso con clic (en ventana) o dibujada (en terminal).
    [x] Sincronía con el audio como reloj maestro: el video sigue a ffplay y
        espera a que el audio suene de verdad (antes, el primer arranque en
        frío de ffplay podía dejar el audio ~0,65 s atrasado).
    [x] Versión .exe: BadAppleASCII.exe (doble clic, sin consola) y
        BadAppleASCII-consola.exe, con construir_exe.bat e icono propio.
    [x] Opción --fuente; el braille elige solo una fuente compatible.
    [x] Busca el video y FFmpeg también junto al programa.
    [x] Repositorio git; el video no se incluye por derechos de autor.

  v2.0 (2026-11-21)
    [x] Pausa, pantalla completa, ajuste automático, multicolor, bucle,
        precarga y exportar a .mp4 / .gif / .txt.
    [x] Opciones --no-* y colores por nombre.
    [x] Audio desde un WAV temporal (corrige el desfase al pausar).

  v1.0
    Reproducción en ventana y en terminal con audio sincronizado.

  Ideas para el futuro
    [ ] Estilo "medios bloques" (▀▄) con dos colores por carácter.
    [ ] Elegir la pista de audio en videos con varias.


-------------------------------------------------------------------------------
 15. LICENCIA Y CRÉDITOS
-------------------------------------------------------------------------------
CRÉDITOS
  * "Bad Apple!!" es una composición original de ZUN (Team Shanghai Alice),
    del juego Touhou Project 4: Lotus Land Story.
  * La versión cantada pertenece a Alstroemeria Records (feat. nomico).
  * El video de sombras original es obra de sus creadores en Nico Nico Douga
    (Anira y colaboradores).
  * Todo el contenido de Touhou Project y la música pertenecen a sus
    respectivos dueños. Este es un proyecto de fans sin fines de lucro, y no
    distribuye ni el video ni la música.
  * Herramientas: Python, FFmpeg (https://ffmpeg.org) y PyInstaller.

LICENCIA DEL CÓDIGO (bad_apple.py, construir_exe.bat, icono.ico)

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
