@echo off
echo Starting build process...

:: Устанавливаем кодировку консоли на UTF-8, чтобы избежать проблем с отображением текста
chcp 65001 >nul

:: Указываем путь к Python 
set PYTHON="C:\Users\User\AppData\Local\Programs\Python\Python312\python.exe"

:: Проверяем, существует ли Python
if not exist %PYTHON% (
    echo Python 3.11 not found at %PYTHON%! Please check the path.
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
    --icon=kuzhnya.ico ^
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
    pause
    exit /b %ERRORLEVEL%
)

echo Build completed successfully!

:: Удаляем временные файлы
rmdir /s /q build
del ImageAutoclicker.spec

echo Cleaned up temporary files.

:: Перемещаем EXE-файл в корневую папку (опционально)
move dist\ImageAutoclicker.exe .
rmdir /s /q dist

echo EXE file moved to project root.

echo Build process finished!
pause