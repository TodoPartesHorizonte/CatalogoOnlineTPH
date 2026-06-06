@echo off
chcp 65001 > nul
echo ===================================================
echo    PROCESO AUTOMATICO: GENERAR Y PUBLICAR CATALOGO
echo ===================================================
echo.

:: 1. Ir a la carpeta donde esta este archivo .bat
cd /d "%~dp0"
echo [INFO] Directorio de trabajo: %CD%

:: 2. Activar entorno virtual de Python
if exist .venv\Scripts\activate (
    echo [INFO] Activando entorno virtual de Python...
    call .venv\Scripts\activate
) else (
    echo [ERROR] No se encontro el entorno virtual .venv.
    echo Asegurate de correr generar_catalogo.bat al menos una vez para crearlo.
    pause
    exit /b 1
)

:: 3. Ejecutar el generador (OCR, optimizacion de imagenes y creacion de base de datos)
echo.
echo [INFO] 1/2: Procesando imagenes y ejecutando OCR (esto puede tardar)...
python generator.py

if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Ocurrio un problema al ejecutar generator.py.
    echo Revisa los mensajes de error arriba.
    pause
    exit /b %errorlevel%
)

echo.
echo [OK] Generacion de catalogo local completada con exito.

:: 4. Publicar los cambios en GitHub Pages (Rama main en la carpeta 'web')
echo.
echo [INFO] 2/2: Publicando actualizaciones en GitHub Pages...
if not exist "web\.git" (
    echo [ERROR] No se encontro un repositorio Git inicializado en la carpeta 'web'.
    echo Por favor, asegúrate de correr el administrador (gui.py) al menos una vez para configurarlo.
    pause
    exit /b 1
)

cd web
echo [INFO] Ejecutando: git add .
git add .

echo [INFO] Ejecutando: git commit
:: Se ignora el error si no hay cambios que hacer commit
git commit -m "Actualizacion automatica del catalogo desde el servidor" 2>nul

echo [INFO] Ejecutando: git push origin main
git push origin main

if %errorlevel% neq 0 (
    echo.
    echo [ERROR] No se pudieron subir los cambios a GitHub Pages.
    echo Verifica tu conexion a internet y las credenciales de Git.
    cd ..
    pause
    exit /b %errorlevel%
)

cd ..
echo.
echo ===================================================
echo    ¡PROCESO COMPLETADO CON EXITO!
echo    Tu catalogo web se actualizara en 1-2 minutos.
echo ===================================================
echo.
pause
