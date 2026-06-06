@echo off
chcp 65001 > nul
cd /d "C:\Sistemas"

echo ===================================================
echo     INSTALADOR RÁPIDO DEL CATÁLOGO DESDE GIT
echo ===================================================
echo.

echo [INFO] 1/4: Descargando el código desde GitHub...
if exist "Catalogo Online" (
    echo [INFO] Eliminando carpeta anterior...
    rmdir /s /q "Catalogo Online"
)
git clone -b codigo-app https://github.com/TodoPartesHorizonte/CatalogoOnlineTPH "Catalogo Online"

if %errorlevel% neq 0 (
    echo [ERROR] No se pudo clonar el repositorio de GitHub.
    pause
    exit /b 1
)

cd "Catalogo Online"

echo.
echo [INFO] 2/4: Configurando entorno virtual de Python...
python -m venv .venv
call .venv\Scripts\activate
python -m pip install --upgrade pip

echo.
echo [INFO] 3/4: Instalando dependencias (incluyendo EasyOCR para CPU)...
pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
pip install easyocr pytesseract customtkinter Pillow

echo.
echo [INFO] 4/4: Inicializando carpeta de publicación (web)...
if not exist "web" mkdir "web"
cd web
git init
git remote add origin https://github.com/TodoPartesHorizonte/CatalogoOnlineTPH
git fetch origin
git checkout -f main
git branch --set-upstream-to=origin/main main
cd ..

echo.
echo ===================================================
echo     ¡INSTALACIÓN COMPLETADA!
echo     El programa está en C:\Sistemas\Catalogo Online
echo     Usa generar_catalogo.bat para iniciar.
echo ===================================================
echo.
pause
