@echo off
rem ==========================================================================
rem  Compila BadAppleASCII.exe con PyInstaller. El resultado queda en dist\
rem  Uso: doble clic en este archivo, o "construir_exe.bat" en una terminal.
rem ==========================================================================
cd /d "%~dp0"

echo [1/3] Instalando o actualizando PyInstaller...
python -m pip install --quiet --upgrade pyinstaller || goto error

echo [2/3] Compilando BadAppleASCII.exe (ventana, para doble clic)...
python -m PyInstaller --noconfirm --clean --onefile --windowed --name BadAppleASCII ^
    --icon icono.ico --add-data "icono.ico;." bad_apple.py || goto error

echo [3/3] Compilando BadAppleASCII-consola.exe (terminal, exportar, ayuda)...
python -m PyInstaller --noconfirm --onefile --console --name BadAppleASCII-consola ^
    --icon icono.ico --add-data "icono.ico;." bad_apple.py || goto error

echo.
echo Listo:
echo   dist\BadAppleASCII.exe          doble clic, o arrastra un video encima
echo   dist\BadAppleASCII-consola.exe  desde una terminal: --terminal, --exportar, --help
echo.
echo Para usarlo, pon junto al .exe:
echo   - el video (badapple.mp4), o arrastra cualquier video encima del .exe
echo   - ffmpeg.exe, ffprobe.exe y ffplay.exe, si el otro PC no tiene FFmpeg
echo     instalado (se pueden descargar de https://ffmpeg.org/download.html)
echo.
pause
exit /b 0

:error
echo.
echo La compilacion fallo. Revisa los mensajes de arriba.
pause
exit /b 1
