@echo off
chcp 65001 > nul
echo ===================================================
echo   CATALOGO AUTOMATIZADO DE REPUESTOS - ADMINISTRADOR
echo ===================================================
echo.

:: Verificar si existe el entorno virtual, si no, crearlo
if not exist .venv (
    echo Creando entorno virtual .venv...
    python -m venv .venv
    if errorlevel 1 (
        echo ERROR: No se pudo crear el entorno virtual. Asegurate de tener Python instalado y en tu PATH.
        pause
        exit /b 1
    )
)

:: Activar entorno virtual
echo Activando entorno virtual...
call .venv\Scripts\activate

:: Instalar/actualizar dependencias
echo Verificando e instalando dependencias (esto puede tardar la primera vez)...
pip install -r requirements.txt
if errorlevel 1 (
    echo ERROR: No se pudieron instalar las dependencias de requirements.txt
    pause
    exit /b 1
)

echo.
echo ===================================================
echo   INICIANDO INTERFAZ DE ADMINISTRACION (GUI)...
echo ===================================================
python gui.py
echo.
echo Administrador cerrado.
echo ===================================================
