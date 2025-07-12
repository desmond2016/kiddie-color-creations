@echo off
echo ========================================
echo  Kiddie Color Creations Startup
echo ========================================
echo.
echo IMPORTANT: Make sure you have a .env file in the 'backend' directory
echo with all required environment variables set (e.g., SECRET_KEY, DATABASE_URL).
echo.

echo Starting backend server...
cd backend
set FLASK_APP=app.py
start "Backend" cmd /k "venv\Scripts\flask.exe run --host=127.0.0.1 --port=5000"
cd ..

echo Waiting 3 seconds...
timeout /t 3 /nobreak >nul

echo Starting frontend server...
start "Frontend" cmd /k "python start_frontend.py"

echo.
echo ========================================
echo  Servers started!
echo ========================================
echo.
echo Backend running at: http://127.0.0.1:5000
echo Frontend running at: http://localhost:8080/index.html
echo Admin Panel at:    http://localhost:8080/admin.html
echo.
echo Please check your .env file for administrator credentials.
echo.
echo Press any key to exit this script window...
pause >nul
