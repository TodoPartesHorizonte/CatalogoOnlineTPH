@echo off
echo ===========================================
echo      SISTEMA DE ACTUALIZACION AUTOMATICA
echo ===========================================
echo.

REM 1. Crear carpeta de respaldos si no existe
if not exist "respaldos" mkdir "respaldos"

REM 2. Generar nombre de archivo con fecha segura (usando WMIC para formato universal)
for /f "tokens=2 delims==" %%I in ('wmic os get localdatetime /value') do set datetime=%%I
set "FECHA_HORA=%datetime:~0,8%_%datetime:~8,6%"
set "BACKUP_NAME=respaldos\config_backup_%FECHA_HORA%.json"

REM 3. Hacer copia de seguridad de la configuracion (config.json)
if exist "config.json" (
    echo [INFO] Creando respaldo de la configuracion config.json...
    copy "config.json" "%BACKUP_NAME%" >nul
    echo [OK] Configuracion guardada en: %BACKUP_NAME%
) else (
    echo [ALERTA] No se encontro config.json, saltando respaldo.
)

REM 4. Actualizar codigo desde GitHub
echo.
echo [INFO] Descargando actualizaciones de GitHub...
git pull

if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Hubo un problema al actualizar el codigo desde GitHub.
    echo Posibles causas:
    echo  - No hay conexion a internet.
    echo  - No se ha configurado el repositorio remoto git remote.
    echo  - Tienes archivos modificados localmente que entran en conflicto.
    echo.
    pause
    exit /b %errorlevel%
)

REM 5. Activar entorno virtual y actualizar dependencias
echo.
if exist .venv\Scripts\activate (
    echo [INFO] Activando entorno virtual .venv...
    call .venv\Scripts\activate
    
    echo [INFO] Actualizando pip y dependencias de Python...
    python -m pip install --upgrade pip
    pip install -r requirements.txt
    
    if %errorlevel% neq 0 (
        echo.
        echo [ADVERTENCIA] No se pudieron actualizar algunas dependencias de requirements.txt.
        echo Asegurate de tener conexion a internet.
        pause
    )
) else (
    echo [ALERTA] No se encontro la carpeta del entorno virtual .venv.
    echo Se omitio la instalacion de dependencias de Python.
)

echo.
echo ===========================================
echo      ACTUALIZACION COMPLETADA CON EXITO
echo ===========================================
echo.
pause
