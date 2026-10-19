@echo off
cd /d "%~dp0"
if not exist .venv\Scripts\python.exe (echo Please create the virtual environment first. & pause & exit /b 1)
start "TaskGrid Coordinator" cmd /k ".venv\Scripts\python.exe coordinator.py"
timeout /t 3 /nobreak >nul
start "TaskGrid Worker 1" cmd /k ".venv\Scripts\python.exe worker.py --id worker-1 --port 5001"
start "TaskGrid Worker 2" cmd /k ".venv\Scripts\python.exe worker.py --id worker-2 --port 5002"
start "TaskGrid Worker 3" cmd /k ".venv\Scripts\python.exe worker.py --id worker-3 --port 5003"
timeout /t 3 /nobreak >nul
start http://127.0.0.1:5000
