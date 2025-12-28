@echo off
echo ============================================================
echo   FOOD FRESHNESS CLASSIFIER - SETUP AND RUN
echo ============================================================
echo.

echo Installing basic Flask dependencies...
pip install flask flask-login flask-sqlalchemy pillow

echo.
echo Creating necessary directories...
if not exist "static\uploads" mkdir static\uploads

echo.
echo Initializing database...
python init_db.py

echo.
echo ============================================================
echo   STARTING FOOD FRESHNESS CLASSIFIER
echo ============================================================
echo.
echo Demo Credentials:
echo   Username: admin
echo   Password: password
echo.
echo Access the application at: http://localhost:5000
echo.
echo Press Ctrl+C to stop the server
echo ============================================================
echo.

python app.py

pause