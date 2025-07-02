@echo off
echo ========================================
echo  Kiddie Color Creations Startup
echo ========================================
echo.

echo Starting backend server...
cd backend
start "Backend" cmd /k "venv\Scripts\python.exe app.py"
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
echo Backend: http://127.0.0.1:5000
echo Frontend: http://localhost:8080/index.html
echo Admin: http://localhost:8080/admin.html
echo.
echo Admin login: admin / admin123
echo.
echo Press any key to exit...
pause >nul
