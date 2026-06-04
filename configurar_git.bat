@echo off
echo ===========================================
echo      CONFIGURACION AUTOMATICA DE GITHUB
echo ===========================================
echo.

cd /d "C:\Sistemas\Catalogo Online"

REM 1. Configurar identidad global de Git para evitar el error "Author identity unknown"
echo [INFO] Configurando identidad global de Git...
git config --global user.email "contacto@todoparteshorizonte.com"
git config --global user.name "Todo Partes Horizonte"

REM 2. Inicializar repositorio si no existe
if not exist ".git" (
    echo [INFO] Inicializando repositorio Git local...
    git init
) else (
    echo [INFO] Repositorio Git ya inicializado.
)

REM 3. Configurar o actualizar la URL del repositorio remoto
echo [INFO] Configurando enlace al repositorio remoto...
git remote remove origin >nul 2>&1
git remote add origin https://github.com/TodoPartesHorizonte/CatalogoOnlineTPH

REM 4. Descargar informacion de GitHub y alinear la rama
echo [INFO] Descargando informacion de GitHub...
git fetch origin

echo [INFO] Vinculando rama local con la de GitHub...
git checkout -f codigo-app
git branch --set-upstream-to=origin/codigo-app codigo-app

echo.
echo ===========================================
echo      CONFIGURACION COMPLETADA CON EXITO
echo ===========================================
echo.
pause
