@echo off
REM Docker deployment script for the AI Chatbot MVP

echo 🐳 AI Chatbot MVP - Docker Deployment
echo =====================================

REM Check if .env file exists
if not exist .env (
    echo ❌ .env file not found!
    echo 📋 Creating .env from template...
    copy .env.example .env
    echo ✅ Please edit .env file and add your OpenAI API key
    echo    Then run this script again.
    pause
    exit /b 1
)

REM Check if OPENAI_API_KEY is set
findstr /C:"OPENAI_API_KEY=sk-" .env >nul
if errorlevel 1 (
    echo ❌ OpenAI API key not found in .env file!
    echo 📝 Please add your OpenAI API key to the .env file
    echo    Example: OPENAI_API_KEY=sk-your-api-key-here
    pause
    exit /b 1
)

REM Check if Docker is running
docker info >nul 2>&1
if errorlevel 1 (
    echo ❌ Docker is not running!
    echo 🔧 Please start Docker and try again.
    pause
    exit /b 1
)

echo 🏗️ Building Docker image...
docker-compose build

if %errorlevel% equ 0 (
    echo ✅ Docker image built successfully!
    echo.
    echo 🚀 Starting the chatbot application...
    echo 🌐 The app will be available at: http://localhost:8501
    echo 🛑 Press Ctrl+C to stop the application
    echo 📊 View logs with: docker-compose logs -f
    echo.
    
    REM Start the application
    docker-compose up
) else (
    echo ❌ Docker build failed!
    echo 🔧 Please check the error messages above and try again.
    pause
    exit /b 1
)
