@echo off
chcp 65001 > nul
echo ===================================================
echo     INSTALACIÓN COMPLETA DESDE CERO DEL CATÁLOGO
echo ===================================================
echo.

:: 1. Definir ruta destino
set "DEST_DIR=C:\Sistemas\Catalogo Online"

:: 2. Crear carpeta contenedora si no existe
if not exist "C:\Sistemas" mkdir "C:\Sistemas"

:: 3. Descargar el código de desarrollo de GitHub
echo [INFO] Clonando repositorio de desarrollo (rama codigo-app)...
if exist "%DEST_DIR%" (
    echo [ALERTA] La carpeta %DEST_DIR% ya existe. Se eliminará para una reinstalación limpia...
    rmdir /s /q "%DEST_DIR%"
)
git clone -b codigo-app https://github.com/TodoPartesHorizonte/CatalogoOnlineTPH "%DEST_DIR%"

if %errorlevel% neq 0 (
    echo.
    echo [ERROR] No se pudo clonar el repositorio de GitHub. 
    echo Verifica que tengas Git instalado en tu PATH y tengas conexión a internet.
    pause
    exit /b 1
)

cd /d "%DEST_DIR%"

:: 4. Crear entorno virtual de Python
echo.
echo [INFO] Creando entorno virtual de Python (.venv)...
python -m venv .venv
if %errorlevel% neq 0 (
    echo.
    echo [ERROR] No se pudo crear el entorno virtual de Python.
    pause
    exit /b 1
)

:: 5. Activar entorno y actualizar pip
echo [INFO] Activando entorno virtual y actualizando pip...
call .venv\Scripts\activate
python -m pip install --upgrade pip

:: 6. Instalar PyTorch CPU-Only (la versión ligera compatible con servidores)
echo.
echo [INFO] Instalando PyTorch CPU (evita errores de c10.dll en el servidor)...
pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu

if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Ocurrió un error al instalar PyTorch para CPU.
    pause
    exit /b 1
)

:: 7. Instalar el resto de dependencias
echo.
echo [INFO] Instalando dependencias de la aplicación...
pip install easyocr pytesseract customtkinter Pillow

if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Ocurrió un error al instalar las dependencias secundarias.
    pause
    exit /b 1
)

:: 8. Configurar la carpeta 'web' de publicación (rama main)
echo.
echo [INFO] Configurando e inicializando la carpeta 'web' (rama main)...
if not exist "web" mkdir "web"
cd web
git init
git remote add origin https://github.com/TodoPartesHorizonte/CatalogoOnlineTPH
git fetch origin
git checkout -f main
git branch --set-upstream-to=origin/main main
cd ..

:: 9. Configuración de identidad de Git
echo.
echo [INFO] Configurando identidad Git global...
git config --global user.email "contacto@todoparteshorizonte.com"
git config --global user.name "Todo Partes Horizonte"

echo.
echo ===================================================
echo     VERIFICANDO LA CARGA DE EASYOCR
echo ===================================================
python -c "import easyocr; print('[OK] EasyOCR se ha configurado e iniciado correctamente!')"

if %errorlevel% neq 0 (
    echo.
    echo [ERROR] La verificación de EasyOCR falló.
    echo Revisa los mensajes de error arriba.
) else (
    echo.
    echo ===================================================
    echo    ¡INSTALACIÓN DESDE CERO COMPLETADA CON ÉXITO!
    echo    El programa se ha instalado en: %DEST_DIR%
    echo    Puedes ejecutar generar_catalogo.bat para usar la app.
    echo ===================================================
)

echo.
pause
