@echo off
echo ========================================
echo Food Freshness Classifier - Starting...
echo ========================================
echo.

echo Checking Python installation...
python --version
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    pause
    exit /b 1
)
echo.

echo Starting Flask application...
echo.
echo Application will be available at: http://localhost:5001
echo.
echo Default Login Credentials:
echo Username: admin
echo Password: password
echo.
echo Press Ctrl+C to stop the server
echo ========================================
echo.

python app.py

pause
