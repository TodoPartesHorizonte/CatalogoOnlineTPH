@echo off
chcp 65001 > nul
echo ===================================================
echo     REPARACIÓN DE MOTOR OCR (EASYOCR CPU)
echo ===================================================
echo.

cd /d "%~dp0"

:: 1. Activar entorno virtual
if exist .venv\Scripts\activate (
    echo [INFO] Activando entorno virtual .venv...
    call .venv\Scripts\activate
) else (
    echo [ERROR] No se encontró el entorno virtual .venv.
    echo Por favor, ejecuta generar_catalogo.bat primero para crearlo.
    pause
    exit /b 1
)

echo [INFO] Desinstalando versiones pesadas [CUDA] de PyTorch...
pip uninstall -y torch torchvision

echo.
echo [INFO] Instalando versiones ultra-ligeras [CPU-Only] de PyTorch...
echo [INFO] Esto evitará los errores de DLL en el servidor y ocupará mucho menos espacio...
pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu

echo.
echo [INFO] Reinstalando EasyOCR...
pip install easyocr

echo.
echo ===================================================
echo     VERIFICANDO LA CARGA DE EASYOCR
echo ===================================================
python -c "import easyocr; print('[OK] EasyOCR se ha cargado correctamente en el servidor!')"

if %errorlevel% neq 0 (
    echo.
    echo [ERROR] La carga de EasyOCR sigue fallando.
    echo Por favor, copia el mensaje de error de arriba y compártelo.
) else (
    echo.
    echo ===================================================
    echo    ¡REPARACIÓN COMPLETADA CON ÉXITO!
    echo    Ahora puedes ejecutar el generador y el OCR
    echo    leerá los títulos perfectamente.
    echo ===================================================
)

echo.
pause
