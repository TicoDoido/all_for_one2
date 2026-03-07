@echo off
chcp 65001 > nul

echo ==================================================
echo ALL FOR ONE - Build
echo ==================================================
echo.

:: --------------------------------------------------
:: Verifica PyInstaller
:: --------------------------------------------------
python -c "import PyInstaller" 2>nul
if errorlevel 1 (
echo Instalando PyInstaller...
python -m pip install pyinstaller
)

:: --------------------------------------------------
:: Compilar plugins para .pyc
:: --------------------------------------------------
echo.
echo Compilando plugins

python -m compileall -b -f plugins

echo Plugins compilados.

:: --------------------------------------------------
:: Compilar Cython plugins
:: --------------------------------------------------
echo.
echo Compilando plugins Cython...

python tools\build_cython.py build_ext --inplace

:: --------------------------------------------------
:: Build do EXE
:: --------------------------------------------------
echo.
echo Compilando ALL_FOR_ONE.exe...

python -m PyInstaller ALL_FOR_ONE.py --icon=icon.ico --onefile --clean --noconfirm --hidden-import=tkinter --hidden-import=tkinter.filedialog --hidden-import=tkinter.ttk --hidden-import=xml.etree.ElementTree

if errorlevel 1 (
echo.
echo ERRO no build.
pause
exit /b
)

:: --------------------------------------------------
:: Preparar pasta plugins no dist
:: --------------------------------------------------
echo.
echo Preparando dist\plugins...

if not exist dist\plugins mkdir dist\plugins
if not exist dist\plugins\DECOMP_CODE mkdir dist\plugins\DECOMP_CODE

:: Copiar apenas .pyc
xcopy plugins\*.pyc dist\plugins\ /E /I /Y /Q >nul

:: Copiar .pyd (plugins Cython)
xcopy plugins\DECOMP_CODE\*.pyd dist\plugins\DECOMP_CODE\ /E /I /Y /Q >nul

echo Plugins copiados.

echo.
echo ==================================================
echo Build finalizado
echo.
echo Arquivos gerados:
echo dist\ALL_FOR_ONE.exe
echo dist\plugins
echo ==================================================
echo.

pause
