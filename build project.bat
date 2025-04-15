@echo off
echo Starting build process...

:: Устанавливаем кодировку консоли на UTF-8, чтобы избежать проблем с отображением текста
chcp 65001 >nul

:: Указываем путь к Python
set PYTHON="C:\Users\*****UR USER HERE****\AppData\Local\Programs\Python\Python312\python.exe"

:: Проверяем, существует ли Python
if not exist %PYTHON% (
    echo Python 3.12 not found at %PYTHON%! Please check the path.
    pause
    exit /b 1
)

:: Проверяем наличие необходимых файлов
set "MISSING_FILES="
if not exist "main.py" set "MISSING_FILES=%MISSING_FILES% main.py"
if not exist "kuzhnya.ico" set "MISSING_FILES=%MISSING_FILES% kuzhnya.ico"
if not exist "languages.json" set "MISSING_FILES=%MISSING_FILES% languages.json"
if not exist "settings.json" set "MISSING_FILES=%MISSING_FILES% settings.json"
if not exist "custom_widgets.py" set "MISSING_FILES=%MISSING_FILES% custom_widgets.py"
if not exist "gui_logic.py" set "MISSING_FILES=%MISSING_FILES% gui_logic.py"


if not "%MISSING_FILES%"=="" (
    echo The following required files are missing:%MISSING_FILES%
    echo Please ensure all files are present in the project directory.
    pause
    exit /b 1
)

:: Удаляем старые папки build и dist, если они существуют
if exist build (
    rmdir /s /q build
    echo Removed old build directory.
)

if exist dist (
    rmdir /s /q dist
    echo Removed old dist directory.
)

:: Удаляем старый SPEC-файл, если он существует
if exist ImageAutoclicker.spec (
    del ImageAutoclicker.spec
    echo Removed old spec file.
)

:: Запускаем PyInstaller через python -m PyInstaller, чтобы избежать конфликтов
%PYTHON% -m PyInstaller ^
    --onefile ^
    --windowed ^
    --icon="kuzhnya.ico" ^
    --name ImageAutoclicker ^
    --add-data "languages.json;." ^
    --add-data "settings.json;." ^
    --add-data "kuzhnya.ico;." ^
    --hidden-import tkinterdnd2 ^
    --hidden-import pyautogui ^
    --hidden-import pystray ^
    --hidden-import PIL ^
    --hidden-import mss ^
    --hidden-import numpy ^
    --hidden-import cv2 ^
    --hidden-import keyboard ^
    --hidden-import custom_widgets ^
    --hidden-import gui_logic ^
    main.py

:: Проверяем, успешно ли прошла сборка
if %ERRORLEVEL% neq 0 (
    echo Build failed! Check the error messages above.
    echo PyInstaller exit code: %ERRORLEVEL%
    pause
    exit /b %ERRORLEVEL%
)

echo Build completed successfully!

:: Перемещаем EXE-файл в корневую папку
if exist dist\ImageAutoclicker.exe (
    move dist\ImageAutoclicker.exe .
    if %ERRORLEVEL% neq 0 (
        echo Failed to move ImageAutoclicker.exe to project root!
        pause
        exit /b %ERRORLEVEL%
    )
    echo EXE file moved to project root.
) else (
    echo ImageAutoclicker.exe not found in dist folder! Build may have failed.
    pause
    exit /b 1
)

:: Удаляем временные файлы после перемещения EXE
if exist build (
    rmdir /s /q build
    echo Cleaned up build directory.
)

if exist dist (
    rmdir /s /q dist
    echo Cleaned up dist directory.
)

if exist ImageAutoclicker.spec (
    del ImageAutoclicker.spec
    echo Cleaned up spec file.
)

echo Build process finished!
pause
