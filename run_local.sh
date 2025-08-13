#!/bin/bash

# Build and run the chatbot application locally

echo "GreatBuy Customer Support Agent - Local Setup"
echo "================================================"

# Check if .env file exists
if [ ! -f .env ]; then
    echo "ERROR: .env file not found!"
    echo "Creating .env from template..."
    cp .env.example .env
    echo "SUCCESS: Please edit .env file and add your API keys"
    echo "   - Add OpenAI API key (OPENAI_API_KEY) OR"
    echo "   - Add Google Gemini API key (GOOGLE_API_KEY)"
    echo "   Then run this script again."
    exit 1
fi

# Check if at least one API key is set
api_key_found=0
if grep -q "OPENAI_API_KEY=sk-" .env; then
    api_key_found=1
fi

if grep -q "GOOGLE_API_KEY=" .env && ! grep -q "your_google_api_key_here" .env; then
    api_key_found=1
fi

if [ "$api_key_found" -eq "0" ]; then
    echo "ERROR: No valid API key found in .env file!"
    echo "Please add at least one API key to the .env file:"
    echo "   - OpenAI: OPENAI_API_KEY=sk-your-api-key-here"
    echo "   - Google Gemini: GOOGLE_API_KEY=your-google-api-key-here"
    exit 1
fi

echo "Setting up Python environment..."

# Check Python version
if python --version 2>&1 | grep -q "3.11"; then
    echo "SUCCESS: Python 3.11 detected (matches Docker environment)"
else
    echo "WARNING: Python 3.11 is recommended (matches Docker environment)"
    echo "   Current version: $(python --version 2>&1 || echo 'Python not found in PATH')"
    echo "   Continuing anyway..."
    echo
fi

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python -m venv venv
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

# Create logs directory
mkdir -p logs

echo "Starting the chatbot application..."
echo "The app will be available at: http://localhost:8501"
echo "Press Ctrl+C to stop the application"
echo ""

# Set Streamlit configuration
export STREAMLIT_SERVER_PORT=8501
export STREAMLIT_SERVER_ADDRESS=0.0.0.0
export STREAMLIT_SERVER_HEADLESS=true
export STREAMLIT_BROWSER_GATHER_USAGE_STATS=false

# Run the Streamlit app with explicit configuration
streamlit run app.py --server.port=8501 --server.address=0.0.0.0
