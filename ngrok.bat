@echo off
:: Check if ngrok is installed
where ngrok >nul 2>&1
if %errorlevel% neq 0 (
    echo ngrok is not installed or not in PATH.
    pause
    exit /b 1
)

:: Start ngrok on port 9090
echo Starting ngrok on http://localhost:9090 ...
start "" ngrok http 9090

:: Optional: pause the script so it doesn't close immediately
pause
