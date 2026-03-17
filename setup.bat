@echo off
setlocal enabledelayedexpansion

echo ====================================================
echo   Server Report Generator - One-Click Setup
echo ====================================================
echo.

:: 1. Handle .env file
if not exist .env (
    echo [1/3] Creating .env file from template...
    copy .env.example .env > nul
    echo.
    echo Please paste your ANTHROPIC_API_KEY below:
    set /p API_KEY="Key: "
    
    :: Use a temporary file to perform a simple replacement
    (for /f "tokens=1* delims==" %%a in (.env) do (
        if "%%a"=="ANTHROPIC_API_KEY" (
            echo ANTHROPIC_API_KEY=!API_KEY!
        ) else (
            echo %%a=%%b
        )
    )) > .env.tmp
    move /y .env.tmp .env > nul
    echo Done.
) else (
    echo [1/3] .env file already exists. Skipping.
)

:: 2. Check for Docker
echo.
echo [2/3] Checking for Docker...
where docker >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo WARNING: Docker is not found in your PATH. Please install Docker Desktop.
) else (
    echo Docker found.
)

:: 3. Build and Start
echo.
echo [3/3] Ready to build and start the application? (Y/N)
set /p START_CHOICE="Choice: "
if /i "%START_CHOICE%"=="Y" (
    echo Building...
    docker compose up -d --build
    echo.
    echo Application started at http://localhost:5000
) else (
    echo Setup complete. Run 'docker compose up -d --build' when ready.
)

echo.
echo ====================================================
echo   Setup finished successfully!
echo ====================================================
pause
