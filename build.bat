@echo off
echo ========================================
echo Building Py-IDE Executable
echo ========================================
echo.

REM Activate virtual environment if exists
if exist ".venv\Scripts\activate.bat" (
    echo Activating virtual environment...
    call .venv\Scripts\activate.bat
)

echo Cleaning previous builds...
if exist "build" rmdir /s /q build
if exist "dist" rmdir /s /q dist
if exist "Py-IDE.spec" del /f /q Py-IDE.spec

echo.
echo Preparing icons...
echo.

REM Check for icon files and set flags
set ICON_FLAG=
set PNG_ICON_FLAG=

REM Check for ICO file (for exe icon)
if exist "assets\icon.ico" (
    echo Found ICO icon: assets\icon.ico
    set ICON_FLAG=--icon=assets\icon.ico
) else (
    echo No ICO icon found. Exe will use default Python icon.
    echo Tip: Run 'python convert_icon.py' to create one from PNG
)

REM Check for PNG icon (for splash screen)
if exist "assets\py-ide icon.png" (
    echo Found PNG icon: py-ide icon.png
    set PNG_ICON_FLAG=--add-data "assets\py-ide icon.png;assets"
) else if exist "assets\icon.png" (
    echo Found PNG icon: icon.png  
    set PNG_ICON_FLAG=--add-data "assets\icon.png;assets"
) else (
    echo Warning: No PNG icon found for splash screen
)

echo.
echo Building executable...
echo This may take a few minutes...
echo.

pyinstaller --noconfirm ^
    --onefile ^
    --windowed ^
    --name=Py-IDE ^
    %ICON_FLAG% ^
    --add-data "version.json;." ^
    %PNG_ICON_FLAG% ^
    --hidden-import=PyQt5 ^
    --hidden-import=PyQt5.QtCore ^
    --hidden-import=PyQt5.QtWidgets ^
    --hidden-import=PyQt5.QtGui ^
    --hidden-import=requests ^
    --hidden-import=openai ^
    --hidden-import=anthropic ^
    --hidden-import=google.generativeai ^
    --collect-all PyQt5 ^
    run_ide.py

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ========================================
    echo Build completed successfully!
    echo ========================================
    echo.
    echo Executable location: dist\Py-IDE.exe
    echo.
    echo Cleaning up temporary files...
    rmdir /s /q build
    del /f /q Py-IDE.spec
    echo.
    echo Done! You can now distribute dist\Py-IDE.exe
) else (
    echo.
    echo ========================================
    echo Build FAILED!
    echo ========================================
    echo Please check the error messages above.
)

echo.
pause
