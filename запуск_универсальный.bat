@echo off
chcp 65001 >nul
cls

echo ========================================
echo   Финансовый планировщик v1.1
echo ========================================
echo.

REM Получаем путь к текущей папке
set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"

REM Проверяем Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ОШИБКА] Python не найден!
    echo Установите Python с python.org
    pause
    exit /b 1
)

REM Проверяем venv
if not exist "venv\Scripts\activate.bat" (
    echo [!] Виртуальное окружение не найдено
    echo.
    echo Создаём новое окружение...
    python -m venv venv
    
    if errorlevel 1 (
        echo [ОШИБКА] Не удалось создать venv
        pause
        exit /b 1
    )
    
    echo.
    echo Устанавливаем зависимости...
    call venv\Scripts\activate.bat
    pip install --upgrade pip
    pip install streamlit plotly pandas python-dateutil openpyxl
    
    echo.
    echo ✓ Окружение готово!
    echo.
) else (
    REM Активируем существующее окружение
    call venv\Scripts\activate.bat
)

REM Проверяем streamlit
python -c "import streamlit" >nul 2>&1
if errorlevel 1 (
    echo [!] Streamlit не установлен
    echo Устанавливаем...
    pip install streamlit plotly pandas python-dateutil openpyxl
)

echo.
echo ========================================
echo   Запуск приложения...
echo ========================================
echo.
echo Браузер откроется автоматически на:
echo http://localhost:8501
echo.
echo Для остановки нажмите Ctrl+C
echo.

streamlit run main.py

if errorlevel 1 (
    echo.
    echo [ОШИБКА] Не удалось запустить приложение
    pause
)