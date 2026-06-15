@echo off
chcp 65001 > nul
setlocal enabledelayedexpansion

echo ===================================================
echo      INSTALADOR AUTOMATICO - CATALOGO ONLINE
echo             SERVIDOR DE PRODUCCION
echo ===================================================
echo.

:: ==========================================
:: 1. CONFIGURACION GIT Y DESCARGA DEL CODIGO
:: ==========================================
echo [1/5] Verificando e instalando el sistema via Git...

where git >nul 2>nul
if %errorlevel% neq 0 (
    echo [ERROR] Git no esta instalado o no esta en el PATH del sistema.
    echo Por favor, instala Git antes de continuar.
    pause
    exit /b 1
)

if not exist ".git" (
    echo - Inicializando repositorio Git local...
    git init
    echo - Configurando repositorio remoto...
    git remote add origin https://github.com/TodoPartesHorizonte/CatalogoOnlineTPH
    echo - Descargando codigo fuente desde produccion...
    git fetch origin
    echo - Vinculando a la rama principal codigo-app...
    git checkout -f codigo-app
    git branch --set-upstream-to=origin/codigo-app codigo-app
) else (
    echo - El repositorio ya esta configurado. Sincronizando ultimos cambios...
    git pull origin codigo-app
)

:: ==========================================
:: 2. ENTORNO VIRTUAL PYTHON
:: ==========================================
echo.
echo [2/5] Configurando el entorno de ejecucion Python...

where python >nul 2>nul
if %errorlevel% neq 0 (
    echo [ERROR] Python no esta instalado o no esta en el PATH del sistema.
    echo Por favor, instala Python 3 y marcalo para agregar al PATH.
    pause
    exit /b 1
)

if not exist ".venv" (
    echo - Creando entorno virtual aislado .venv...
    python -m venv .venv
    if !errorlevel! neq 0 (
        echo [ERROR] Fallo al crear el entorno virtual.
        pause
        exit /b 1
    )
) else (
    echo - Entorno virtual existente detectado.
)

:: ==========================================
:: 3. INSTALACION DE DEPENDENCIAS
:: ==========================================
echo.
echo [3/5] Instalando y actualizando dependencias del sistema...
call .venv\Scripts\activate

echo - Actualizando pip...
python -m pip install --upgrade pip >nul 2>nul

echo - Instalando modulos desde requirements.txt...
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo [ADVERTENCIA] Hubo un problema al instalar algunas dependencias.
    echo Revisa tu conexion a internet.
)

:: ==========================================
:: 4. ENLACE AL SERVIDOR DE PRODUCCION
:: ==========================================
echo.
echo [4/5] Generando enlaces y configurando servidor de produccion...

echo @echo off> iniciar_servidor.bat
echo chcp 65001 ^> nul>> iniciar_servidor.bat
echo title Servidor de Produccion - Catalogo Online>> iniciar_servidor.bat
echo echo ===================================================>> iniciar_servidor.bat
echo echo    SERVIDOR DE PRODUCCION ACTIVO PUERTO 80>> iniciar_servidor.bat
echo echo    Pagina: http://localhost/>> iniciar_servidor.bat
echo echo ===================================================>> iniciar_servidor.bat
echo cd web>> iniciar_servidor.bat
echo ..\.venv\Scripts\python -m http.server 80>> iniciar_servidor.bat

echo - Se ha generado iniciar_servidor.bat para levantar la pagina.

:: ==========================================
:: 5. FINALIZACION
:: ==========================================
echo.
echo [5/5] PROCESO COMPLETADO EXITOSAMENTE
echo ===================================================
echo El sistema ha sido instalado y configurado correctamente.
echo.
echo - Para iniciar el servidor ejecuta: iniciar_servidor.bat
echo - Para gestionar el catalogo ejecuta: generar_catalogo.bat
echo ===================================================
pause
