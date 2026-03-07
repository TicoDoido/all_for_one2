@echo off
chcp 65001 > nul
setlocal EnableDelayedExpansion
set "PYTHON="

echo ============================================================
echo ALL FOR ONE - Build Standalone
echo ============================================================
echo.

:: Detecta Python (python ou py -3)
where python >nul 2>nul && set "PYTHON=python"
if not defined PYTHON (
    py -3 --version >nul 2>nul && set "PYTHON=py -3"
)

if not defined PYTHON (
    echo [ERRO] Python 3.10+ nao encontrado neste sistema.
    echo [DICA] Instale em https://www.python.org/downloads/ e marque "Add python.exe to PATH".
    pause
    exit /b 1
)

:: Verifica/instala Flet e PyInstaller
call :ensure_module "flet" "flet==0.28.3" || exit /b 1
call :ensure_module "PyInstaller" "pyinstaller" || exit /b 1

echo [INFO] Compilando plugins para .pyc...
%PYTHON% -m compileall -b -f plugins

if errorlevel 1 (
    echo [ERRO] Falha ao compilar plugins para .pyc.
    pause
    exit /b 1
)

if not exist "plugins\" (
    echo [ERRO] Pasta plugins\ nao encontrada.
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
for /f "usebackq delims=" %%I in (`%PYTHON% tools\collect_plugin_hidden_imports.py`) do (
    set "HIDDEN_IMPORT_ARGS=!HIDDEN_IMPORT_ARGS! --hidden-import %%I"
)

if defined HIDDEN_IMPORT_ARGS (
    echo [INFO] Hidden imports detectados: !HIDDEN_IMPORT_ARGS!
) else (
    echo [INFO] Nenhum hidden import adicional detectado.
)

echo [INFO] Iniciando build PyInstaller...
set "CORE_HIDDEN_IMPORTS=--hidden-import tkinter --hidden-import tkinter.filedialog --hidden-import tkinter.ttk --hidden-import xml.etree.ElementTree --hidden-import xmltree"
%PYTHON% -m PyInstaller ALL_FOR_ONE.py --name all_for_one --onefile --clean --noconfirm !CORE_HIDDEN_IMPORTS! !HIDDEN_IMPORT_ARGS!

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
exit /b 0

:ensure_module
set "MODULE=%~1"
set "PACKAGE=%~2"

%PYTHON% -c "import %MODULE%" 2>nul
if errorlevel 1 (
    echo [INFO] Instalando %PACKAGE%...
    %PYTHON% -m pip install %PACKAGE%
    if errorlevel 1 (
        echo [ERRO] Nao foi possivel instalar %PACKAGE%.
        pause
        exit /b 1
    )

    %PYTHON% -c "import %MODULE%" 2>nul
    if errorlevel 1 (
        echo [ERRO] %MODULE% continua indisponivel apos instalacao.
        pause
        exit /b 1
    )
)
exit /b 0
