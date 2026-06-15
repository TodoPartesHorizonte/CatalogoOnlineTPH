@echo off
chcp 65001 > nul
setlocal enabledelayedexpansion

echo ===================================================
echo      ACTUALIZADOR AUTOMATICO - CATALOGO ONLINE
echo ===================================================
echo.

:: ==========================================
:: 1. ACTUALIZAR CODIGO DESDE GIT (PULL)
:: ==========================================
echo [1/3] Buscando y descargando actualizaciones del sistema...

where git >nul 2>nul
if %errorlevel% neq 0 (
    echo [ERROR] Git no esta instalado o no esta en el PATH.
    pause
    exit /b 1
)

if not exist ".git" (
    echo [ERROR] Este directorio no es un repositorio Git valido.
    echo Ejecuta primero el instalador.bat para inicializar el sistema.
    pause
    exit /b 1
)

echo - Descargando la version mas reciente desde GitHub...
git fetch origin
git pull origin codigo-app

if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Hubo un problema al actualizar el codigo.
    echo Posibles causas:
    echo  - Sin conexion a internet.
    echo  - Conflictos en archivos editados manualmente.
    pause
    exit /b 1
)

:: ==========================================
:: 2. ACTUALIZAR DEPENDENCIAS (PYTHON)
:: ==========================================
echo.
echo [2/3] Verificando e instalando nuevas dependencias...

if exist ".venv\Scripts\activate" (
    call .venv\Scripts\activate

    echo - Actualizando pip...
    python -m pip install --upgrade pip >nul 2>nul

    echo - Instalando / Actualizando paquetes de requirements.txt...
    pip install -r requirements.txt

    if %errorlevel% neq 0 (
        echo [ADVERTENCIA] No se pudieron actualizar algunas dependencias.
    )
) else (
    echo [ALERTA] Entorno virtual .venv no encontrado.
    echo No se actualizaron las dependencias. Te sugerimos correr instalador.bat.
)

:: ==========================================
:: 3. FINALIZACION
:: ==========================================
echo.
echo [3/3] PROCESO DE ACTUALIZACION COMPLETADO
echo ===================================================
echo El sistema cuenta con la version mas reciente.
echo.
echo - Los cambios de la pagina web estaran listos inmediatamente.
echo - Si el Servidor de Produccion estaba apagado, puedes
echo   encenderlo usando iniciar_servidor.bat o su acceso directo.
echo ===================================================
pause
