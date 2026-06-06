@echo off
chcp 65001 > nul
echo ===================================================
echo    INSTALADOR Y CONFIGURADOR COMPLETO DESDE CERO
echo ===================================================
echo.

cd /d "%~dp0"

:: 1. Crear entorno virtual si no existe
if not exist .venv (
    echo [INFO] Creando entorno virtual .venv de Python...
    python -m venv .venv
    if %errorlevel% neq 0 (
        echo [ERROR] No se pudo crear el entorno virtual.
        echo Asegúrate de tener Python instalado y en tu PATH de Windows.
        pause
        exit /b 1
    )
) else (
    echo [INFO] El entorno virtual .venv ya existe.
)

:: 2. Activar entorno virtual
echo [INFO] Activando entorno virtual...
call .venv\Scripts\activate

:: 3. Actualizar pip
echo [INFO] Actualizando pip...
python -m pip install --upgrade pip

:: 4. Instalar PyTorch CPU-Only (Evita errores de c10.dll en servidores)
echo.
echo [INFO] Instalando PyTorch CPU-Only (versión ligera compatible con servidores)...
pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu

if %errorlevel% neq 0 (
    echo [ERROR] Ocurrió un error al instalar PyTorch para CPU.
    pause
    exit /b 1
)

:: 5. Instalar resto de dependencias (EasyOCR, CustomTkinter, Pillow, Pytesseract)
echo.
echo [INFO] Instalando librerías adicionales (EasyOCR, CustomTkinter, Pillow, Pytesseract)...
pip install easyocr pytesseract customtkinter Pillow

if %errorlevel% neq 0 (
    echo [ERROR] Ocurrió un error al instalar las dependencias secundarias.
    pause
    exit /b 1
)

echo.
echo ===================================================
echo     VERIFICANDO LA CARGA DE EASYOCR
echo ===================================================
python -c "import easyocr; print('[OK] EasyOCR se ha configurado e iniciado correctamente!')"

if %errorlevel% neq 0 (
    echo.
    echo [ERROR] La verificación falló.
    echo Revisa los mensajes de error arriba.
) else (
    echo.
    echo ===================================================
    echo    ¡CONFIGURACIÓN DESDE CERO COMPLETADA CON ÉXITO!
    echo    El servidor ya está 100%% listo.
    echo    Puedes ejecutar generar_catalogo.bat para usar la app.
    echo ===================================================
)

echo.
pause
