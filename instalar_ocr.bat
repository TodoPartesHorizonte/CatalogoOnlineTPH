@echo off
chcp 65001 > nul
echo ===================================================
echo     INSTALADOR AUTOMATICO DE TESSERACT OCR
echo ===================================================
echo.

:: 1. Definir URL y ruta del archivo temporal
set "URL=https://digi.bib.uni-mannheim.de/tesseract/tesseract-ocr-w64-setup-5.3.3.20231005.exe"
set "TEMP_EXE=%TEMP%\tesseract_installer.exe"

:: 2. Verificar si ya está instalado en la ruta por defecto
if exist "C:\Program Files\Tesseract-OCR\tesseract.exe" (
    echo [OK] Tesseract OCR ya está instalado en:
    echo      C:\Program Files\Tesseract-OCR\tesseract.exe
    echo.
    pause
    exit /b 0
)

echo [INFO] Descargando instalador de Tesseract OCR...
echo [INFO] Por favor, espera a que termine de descargar...
echo.

:: Descargar usando PowerShell de forma silenciosa
powershell -Command "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -Uri '%URL%' -OutFile '%TEMP_EXE%'"

if %errorlevel% neq 0 (
    echo.
    echo [ERROR] No se pudo descargar el instalador. 
    echo Verifica tu conexión a internet o intenta descargar el archivo manualmente.
    pause
    exit /b 1
)

echo [INFO] Instalando Tesseract OCR de forma silenciosa en segundo plano...
echo [INFO] Por favor, espera unos 15-30 segundos...
echo.

:: Ejecutar instalador con el parámetro de instalación silenciosa (/S) y esperar a que termine
start /wait "" "%TEMP_EXE%" /S

:: Verificar si el ejecutable se instaló correctamente
if exist "C:\Program Files\Tesseract-OCR\tesseract.exe" (
    echo ===================================================
    echo    [OK] TESSERACT OCR INSTALADO CON ÉXITO
    echo    Ruta: C:\Program Files\Tesseract-OCR\tesseract.exe
    echo ===================================================
) else (
    echo.
    echo [ERROR] La instalación silenciosa falló.
    echo Se abrirá el instalador manual en pantalla para que lo instales tú mismo.
    start "" "%TEMP_EXE%"
    pause
    exit /b 1
)

:: Limpiar el archivo temporal descargado si la instalación fue exitosa
if exist "%TEMP_EXE%" del /q "%TEMP_EXE%"

echo.
pause
