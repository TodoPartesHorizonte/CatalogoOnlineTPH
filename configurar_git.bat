@echo off
echo ===========================================
echo      CONFIGURACION INICIAL DE GITHUB
echo ===========================================
echo.

REM 1. Inicializar repositorio si no existe
if not exist ".git" (
    echo [INFO] Inicializando repositorio Git local...
    git init
) else (
    echo [INFO] Repositorio Git ya inicializado.
)

REM 2. Configurar o actualizar la URL del repositorio remoto
echo [INFO] Configurando enlace al repositorio remoto...
git remote remove origin >nul 2>&1
git remote add origin https://github.com/TodoPartesHorizonte/CatalogoOnlineTPH

REM 3. Descargar informacion de GitHub y alinear la rama
echo [INFO] Descargando informacion de GitHub...
git fetch origin

echo [INFO] Vinculando rama local con la de GitHub...
git checkout -f main
git branch --set-upstream-to=origin/main main

echo.
echo ===========================================
echo      CONFIGURACION COMPLETADA CON EXITO
echo ===========================================
echo Ya puedes ejecutar actualizar_sistema.bat para actualizar la aplicacion.
echo.
pause
