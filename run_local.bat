@echo off
REM Build and run the chatbot application locally on Windows

echo GreatBuy Customer Support Agent - Local Setup
echo ================================================

REM Check if .env file exists
if not exist .env (
    echo ERROR: .env file not found!
    echo Creating .env from template...
    copy .env.example .env
    echo SUCCESS: Please edit .env file and add your API keys
    echo    - Add OpenAI API key ^(OPENAI_API_KEY^) ^OR^
    echo    - Add Google Gemini API key ^(GOOGLE_API_KEY^)
    echo    Then run this script again.
    pause
    exit /b 1
)

REM Check if at least one API key is set
set "api_key_found=0"
findstr /C:"OPENAI_API_KEY=sk-" .env >nul
if not errorlevel 1 set "api_key_found=1"

findstr /C:"GOOGLE_API_KEY=" .env | findstr /V "your_google_api_key_here" >nul
if not errorlevel 1 set "api_key_found=1"

if "%api_key_found%"=="0" (
    echo ERROR: No valid API key found in .env file!
    echo Please add at least one API key to the .env file:
    echo    - OpenAI: OPENAI_API_KEY=sk-your-api-key-here
    echo    - Google Gemini: GOOGLE_API_KEY=your-google-api-key-here
    pause
    exit /b 1
)

echo Setting up Python environment...

REM Check Python version
python --version 2>nul | findstr "3.11" >nul
if errorlevel 1 (
    echo WARNING: Python 3.11 is recommended ^(matches Docker environment^)
    echo    Current version:
    python --version 2>nul || echo    Python not found in PATH
    echo    Continuing anyway...
    echo.
)

REM Create virtual environment if it doesn't exist
if not exist venv (
    echo Creating virtual environment...
    python -m venv venv
)

REM Activate virtual environment
echo Activating virtual environment...
call venv\Scripts\activate.bat

REM Install dependencies
echo Installing dependencies...
pip install -r requirements.txt

REM Create logs directory
if not exist logs mkdir logs

echo Starting the chatbot application...
echo The app will be available at: http://localhost:8501
echo Press Ctrl+C to stop the application
echo.

REM Set Streamlit configuration
set STREAMLIT_SERVER_PORT=8501
set STREAMLIT_SERVER_ADDRESS=0.0.0.0
set STREAMLIT_SERVER_HEADLESS=true
set STREAMLIT_BROWSER_GATHER_USAGE_STATS=false

REM Run the Streamlit app with explicit configuration
streamlit run app.py --server.port=8501 --server.address=0.0.0.0
