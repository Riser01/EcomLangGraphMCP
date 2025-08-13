#!/bin/bash

# Health check script for the AI Chatbot MVP

echo "🏥 AI Chatbot MVP - Health Check"
echo "==============================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to check status
check_status() {
    if [ $1 -eq 0 ]; then
        echo -e "${GREEN}✅ $2${NC}"
        return 0
    else
        echo -e "${RED}❌ $2${NC}"
        return 1
    fi
}

# Function to check warning status
check_warning() {
    if [ $1 -eq 0 ]; then
        echo -e "${GREEN}✅ $2${NC}"
        return 0
    else
        echo -e "${YELLOW}⚠️  $2${NC}"
        return 1
    fi
}

echo "🔧 System Requirements Check"
echo "=============================="

# Check Python
python3 --version > /dev/null 2>&1
check_status $? "Python 3 is installed"

# Check pip
pip --version > /dev/null 2>&1
check_status $? "pip is available"

# Check Docker
docker --version > /dev/null 2>&1
check_status $? "Docker is installed"

# Check Docker Compose
docker-compose --version > /dev/null 2>&1
check_status $? "Docker Compose is available"

echo ""
echo "📋 Project Files Check"
echo "======================"

# Check essential files
files=(
    "app.py"
    "requirements.txt"
    "Dockerfile"
    "docker-compose.yml"
    ".env.example"
    "src/state.py"
    "src/chatbot_service.py"
    "src/conversation_graph.py"
)

for file in "${files[@]}"; do
    if [ -f "$file" ]; then
        check_status 0 "$file exists"
    else
        check_status 1 "$file exists"
    fi
done

echo ""
echo "🔐 Environment Check"
echo "===================="

# Check .env file
if [ -f ".env" ]; then
    check_status 0 ".env file exists"
    
    # Check API key
    if grep -q "OPENAI_API_KEY=sk-" .env; then
        check_status 0 "OpenAI API key is configured"
    else
        check_status 1 "OpenAI API key is configured"
    fi
else
    check_status 1 ".env file exists"
fi

echo ""
echo "🐳 Docker Environment Check"
echo "==========================="

# Check if Docker daemon is running
docker info > /dev/null 2>&1
check_status $? "Docker daemon is running"

# Check if any containers are running
running_containers=$(docker ps -q | wc -l)
if [ $running_containers -gt 0 ]; then
    echo -e "${GREEN}📊 $running_containers Docker container(s) currently running${NC}"
else
    echo -e "${YELLOW}📊 No Docker containers currently running${NC}"
fi

echo ""
echo "🌐 Network Check"
echo "================"

# Check if port 8501 is available
if command -v netstat > /dev/null 2>&1; then
    netstat -tuln | grep ":8501 " > /dev/null 2>&1
    if [ $? -eq 0 ]; then
        check_warning 1 "Port 8501 is available (currently in use)"
    else
        check_status 0 "Port 8501 is available"
    fi
else
    echo -e "${YELLOW}⚠️  netstat not available, cannot check port 8501${NC}"
fi

# Check internet connectivity
curl -s --max-time 5 https://api.openai.com > /dev/null 2>&1
check_status $? "Internet connectivity to OpenAI API"

echo ""
echo "🧪 Quick Functionality Test"
echo "==========================="

# Try to run basic import test
if [ -f "test_setup.py" ]; then
    echo "🔄 Running setup validation test..."
    python test_setup.py > /dev/null 2>&1
    check_status $? "Setup validation test passed"
else
    echo -e "${YELLOW}⚠️  test_setup.py not found, skipping validation test${NC}"
fi

echo ""
echo "📊 Summary"
echo "=========="

echo "🎯 Ready to run:"
echo "   Local:  streamlit run app.py"
echo "   Docker: docker-compose up --build"
echo ""
echo "🔗 Useful commands:"
echo "   Test setup:     python test_setup.py"
echo "   Example usage:  python example_usage.py"
echo "   View logs:      docker-compose logs -f"
echo ""
echo "📖 For detailed instructions, see README.md"
