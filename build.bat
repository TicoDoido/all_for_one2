@echo off
chcp 65001 > nul
setlocal EnableDelayedExpansion

echo ============================================================
echo ALL FOR ONE - Build Standalone (corrigido para .pyc)
echo ============================================================
echo.

:: Verifica Python e Flet
python -c "import flet" 2>nul
if errorlevel 1 (
    echo [ERRO] Flet nao encontrado. Execute: pip install flet==0.28.3
    pause
    exit /b 1
)

:: Verifica/instala PyInstaller
python -c "import PyInstaller" 2>nul || (
    echo [INFO] Instalando PyInstaller...
    pip install pyinstaller
)

echo [INFO] Compilando plugins para .pyc...
python -m compileall -b -f plugins

if not exist "plugins\" (
    echo [ERRO] Pasta errada criada. Verifique se ha arquivos .py validos em plugins\
    pause
    exit /b 1
)

echo [INFO] Copiando .pyc para pasta temporaria (incluindo subpastas)...
if exist "plugins_pyc" rd /s /q "plugins_pyc" 2>nul
mkdir "plugins_pyc" 2>nul

xcopy /E /I /Y /Q "plugins\*.pyc" "plugins_pyc\" >nul
if errorlevel 1 (
    echo [AVISO] Nenhum .pyc copiado. Verifique a compilacao em plugins\
)

if errorlevel 1 (
    echo [AVISO] Nao ha arquivos .pyc em plugins_pyc. Usando fallback para .py
) else (
    echo [OK] .pyc copiados com sucesso (estrutura preservada).
)

echo [INFO] Coletando dependencias importadas pelos plugins...
set "HIDDEN_IMPORT_ARGS="
for /f "usebackq delims=" %%I in (`python tools\collect_plugin_hidden_imports.py`) do (
    set "HIDDEN_IMPORT_ARGS=!HIDDEN_IMPORT_ARGS! --hidden-import %%I"
)

if defined HIDDEN_IMPORT_ARGS (
    echo [INFO] Hidden imports detectados: !HIDDEN_IMPORT_ARGS!
) else (
    echo [INFO] Nenhum hidden import adicional detectado.
)

echo [INFO] Iniciando build PyInstaller...
set "CORE_HIDDEN_IMPORTS=--hidden-import tkinter --hidden-import tkinter.filedialog --hidden-import tkinter.ttk --hidden-import xml.etree.ElementTree --hidden-import xmltree"
pyinstaller ALL_FOR_ONE.py --onefile --clean --noconfirm !CORE_HIDDEN_IMPORTS! !HIDDEN_IMPORT_ARGS!

if errorlevel 1 (
    echo [ERRO] Build falhou.
    pause
    exit /b 1
)

echo [INFO] Preparando distribuicao...
if not exist "dist\plugins" mkdir "dist\plugins" 2>nul
if not exist "dist\banners" mkdir "dist\banners" 2>nul

:: Copia os .pyc (prioridade) ou fallback para .py
if exist "plugins_pyc" (
    xcopy /E /I /Y /Q "plugins_pyc\*" "dist\plugins\" >nul
    echo [OK] Copiados .pyc para dist\plugins (incluindo subpastas)
) else (
    if exist "plugins" (
        xcopy /E /I /Y /Q "plugins\*.py" "dist\plugins\" >nul
        echo [FALLBACK] Copiados .py (sem .pyc gerados)
    )
)

if exist "banners" xcopy /E /Y /Q "banners" "dist\banners\" >nul

:: Limpeza
rd /s /q "plugins_pyc" 2>nul
rd /s /q build 2>nul
del /q ALL_FOR_ONE.spec 2>nul

echo.
echo ============================================================
echo Build finalizado!
echo Verifique em: dist\
echo - all_for_one.exe
echo - plugins\
echo - banners\
echo ============================================================
pause