@echo off
setlocal

set "ROOT=%~dp0"
cd /d "%ROOT%"

if not exist ".env" (
  if exist ".env.example" (
    echo [HexMind] Missing .env. Please copy .env.example to .env and fill in your API key.
  ) else (
    echo [HexMind] Missing .env file.
  )
)

set "PYTHON_EXE="

if exist ".venv\Scripts\python.exe" (
  set "PYTHON_EXE=.venv\Scripts\python.exe"
)

if not defined PYTHON_EXE (
  if exist "wheels" if exist "requirements-runtime.txt" (
    where py >nul 2>nul
    if %errorlevel%==0 (
      py -3 -m venv .venv
    ) else (
      python -m venv .venv
    )

    if not exist ".venv\Scripts\python.exe" (
      echo [HexMind] Failed to create local virtual environment.
      exit /b 1
    )

    set "PYTHON_EXE=.venv\Scripts\python.exe"
    "%PYTHON_EXE%" -m pip install --no-index --find-links wheels -r requirements-runtime.txt
    if errorlevel 1 (
      echo [HexMind] Failed to install local runtime dependencies.
      exit /b 1
    )
  )
)

if not defined PYTHON_EXE (
  where py >nul 2>nul
  if %errorlevel%==0 (
    py -3 run_local_web.py %*
    exit /b %errorlevel%
  )

  where python >nul 2>nul
  if %errorlevel%==0 (
    python run_local_web.py %*
    exit /b %errorlevel%
  )

  echo [HexMind] Python 3.11+ not found.
  exit /b 1
)

"%PYTHON_EXE%" run_local_web.py %*
