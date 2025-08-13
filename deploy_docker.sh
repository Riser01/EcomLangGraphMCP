#!/bin/bash

# Docker deployment script for the AI Chatbot MVP

echo "🐳 AI Chatbot MVP - Docker Deployment"
echo "====================================="

# Check if .env file exists
if [ ! -f .env ]; then
    echo "❌ .env file not found!"
    echo "📋 Creating .env from template..."
    cp .env.example .env
    echo "✅ Please edit .env file and add your OpenAI API key"
    echo "   Then run this script again."
    exit 1
fi

# Check if OPENAI_API_KEY is set
if ! grep -q "OPENAI_API_KEY=sk-" .env; then
    echo "❌ OpenAI API key not found in .env file!"
    echo "📝 Please add your OpenAI API key to the .env file"
    echo "   Example: OPENAI_API_KEY=sk-your-api-key-here"
    exit 1
fi

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running!"
    echo "🔧 Please start Docker and try again."
    exit 1
fi

echo "🏗️  Building Docker image..."
docker-compose build

if [ $? -eq 0 ]; then
    echo "✅ Docker image built successfully!"
    echo ""
    echo "🚀 Starting the chatbot application..."
    echo "🌐 The app will be available at: http://localhost:8501"
    echo "🛑 Press Ctrl+C to stop the application"
    echo "📊 View logs with: docker-compose logs -f"
    echo ""
    
    # Start the application
    docker-compose up
else
    echo "❌ Docker build failed!"
    echo "🔧 Please check the error messages above and try again."
    exit 1
fi
