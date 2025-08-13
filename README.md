# 🛒 GreatBuy Customer Support Agent
<p align="center">
  <img src="assets/GreatBuy_icon.png" alt="GreatBuy Logo" width="100" height="100">
</p>

**GreatBuy** is a modern online marketplace that connects customers with their favorite sellers, offering fast and reliable shipping services across multiple cities. Think of it as a comprehensive e-commerce ecosystem that brings a vast selection of products from diverse categories right to your doorstep with just a few clicks.

A production-ready customer support chatbot built with **Streamlit**, **LangGraph**, and **dual LLM support** (OpenAI/Google Gemini), featuring MCP (Model Context Protocol) tool integration for order management and knowledge base search.
## 🖥️ Live Demo Interface

![GreatBuy Chat Interface Demo](assets\image.png)

*Experience the interactive chat interface with ReAct agent visualization, tool usage tracking, and real-time response streaming*

## ✨ Key Features

- **🎨 Interactive Chat Interface**: Modern Streamlit UI with ReAct agent visualization
- **🔄 Dual LLM Support**: OpenAI GPT + Google Gemini with automatic failover
- **🛠️ MCP Tools Integration**: Order management and knowledge base search via MCP server
- **🐳 Docker Ready**: Containerized deployment with health checks
- **📱 Session Management**: Persistent conversation history with unique session IDs
- **🔍 ReAct Agent**: Visible thinking process with intermediate steps display
- **⚡ Real-time Processing**: Live tool usage tracking and response streaming

## 🚀 Quick Start

### 🐳 Docker Deployment (Recommended)

1. **Clone Repository**
```bash
git clone https://github.com/Riser01/EcomLangGraphMCP.git
cd EcomLangGraphMCP
```

2. **Setup Environment**
```bash
cp .env.example .env
```

3. **Configure API Keys**
Edit `.env` file with your API keys:
```bash
OPENAI_API_KEY=your_openai_api_key_here
GOOGLE_API_KEY=your_google_api_key_here
PROVIDER_PREFERENCE=openai
MODEL=gpt-4o
FALLBACK_MODEL=gemini-1.5-flash
```

**Start Docker**
docker-compose up --build 

access Ui at : http://localhost:8501/


4. **Deploy with Docker**
```bash
# Linux/Mac
./deploy_docker.sh

# Windows
./deploy_docker.bat

# Or manually
docker-compose up -d
```

5. **Access Application**: Open http://localhost:8501

### 💻 Local Development

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows
venv\Scripts\activate
# Linux/Mac  
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Setup environment
cp .env.example .env
# Edit .env with your API keys

# Run application
streamlit run app.py

# For local testing (optional)
# Windows
./run_local.bat
# Linux/Mac
./run_local.sh
```

## 🧪 Testing with Example Scenarios

Once the application is running, try these demo conversations to test the MCP tools:

### **Order Management**
```
User: "Can I get the status of my order ORDZW009?"
```
*Tests: Order lookup tool with MCP server integration*

```
User: "I need to cancel order ORDZW009"
```
*Tests: Order status update functionality*

```
User: "What's the status of ORDZW009 now?"
```
*Tests: Verification of order changes*

### **Knowledge Base Search**
```
User: "Tell me about GreatBuy Gold membership benefits"
```
*Tests: Wiki search for membership information*

```
User: "How do I sell products on GreatBuy?"
```
*Tests: Wiki search for business information*

```
User: "What are your shipping fees?"
```
*Tests: Policy information retrieval*

### **General Conversation**
```
User: "Hi there! How can you help me?"
```
*Tests: Natural conversation flow without tools*

**Expected Behavior:**
- ReAct agent process visualization in expandable sections
- Tool usage counter and step-by-step reasoning display
- Appropriate MCP tool selection for different query types
- Graceful fallback when tools aren't needed
- Real-time response streaming with thinking indicators
## ⚙️ Configuration

### Environment Variables
| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `OPENAI_API_KEY` | OpenAI API key | - | One of OpenAI/Google |
| `GOOGLE_API_KEY` | Google Gemini API key | - | One of OpenAI/Google |
| `PROVIDER_PREFERENCE` | Preferred LLM provider | `openai` | No |
| `MODEL` | Primary model name | `gpt-4o` | No |
| `FALLBACK_MODEL` | Fallback model name | `gemini-1.5-flash` | No |
| `APP_TITLE` | Application title | `GreatBuy Customer Support Agent` | No |

*At least one API key (OpenAI or Google) is required for the application to function*

## 📁 Project Structure

```
EcomLangGraphMCP/
├── app.py                      # Main Streamlit application
├── requirements.txt            # Python dependencies
├── Dockerfile                 # Docker configuration
├── docker-compose.yml         # Docker Compose setup
├── .env.example              # Environment template
├── .gitignore                # Git ignore rules
├── mcp_config.json           # MCP tools configuration
├── mcp_server_remote.py      # MCP server implementation
├── data.py                   # Sample data and mock responses
├── deploy_docker.sh          # Docker deployment script (Linux/Mac)
├── deploy_docker.bat         # Docker deployment script (Windows)
├── run_local.sh             # Local development script (Linux/Mac)
├── run_local.bat            # Local development script (Windows)
├── health_check.sh          # Docker health check script
├── src/                     # Core application modules
│   ├── __init__.py         # Package initialization
│   ├── state.py           # LangGraph state definitions
│   └── unified_chatbot_service.py  # Main chatbot service
└── logs/                   # Application logs directory
    └── chatbot.log        # Main application log file
```

## 🏗️ Architecture

The application follows a modular architecture with clear separation of concerns:

### 🔄 User Interaction Flow

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│                 │    │                  │    │                 │
│      USER       │◄──►│   STREAMLIT UI   │◄──►│  LANGGRAPH      │
│                 │    │                  │    │  REACT AGENT    │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                │                        │
                                │                        ▼
                                │               ┌─────────────────┐
                                │               │                 │
                                │               │   LLM LAYER     │
                                │               │ OpenAI/Gemini   │
                                │               │   + Failover    │
                                │               └─────────────────┘
                                │                        │
                                ▼                        ▼
                       ┌──────────────────┐    ┌─────────────────┐
                       │                  │    │                 │
                       │ SESSION STATE    │    │   MCP TOOLS     │
                       │   Management     │    │   Integration   │
                       │                  │    │                 │
                       └──────────────────┘    └─────────────────┘
                                                         │
                                                         ▼
                                                ┌─────────────────┐
                                                │                 │
                                                │  GreatBuy DATA   │
                                                │ Orders & Wiki   │
                                                │                 │
                                                └─────────────────┘
```

### 📊 Interaction Steps

1. **👤 User Input**: User types message in Streamlit chat interface
2. **🔄 Session Management**: Message added to session state with timestamp
3. **🤖 ReAct Processing**: LangGraph agent analyzes user intent
4. **🧠 LLM Decision**: Primary LLM (OpenAI/Gemini) determines response strategy
5. **🛠️ Tool Selection**: Agent decides if MCP tools are needed:
   - **Order Management**: For order status, cancellations, tracking
   - **Wiki Search**: For policies, membership info, general help
6. **📊 Tool Execution**: MCP server processes tool requests
7. **💭 Response Generation**: LLM synthesizes final response
8. **✨ UI Display**: Response shown with ReAct process visualization
9. **📝 State Update**: Conversation history and session updated

### 🏛️ Component Architecture

- **🎨 Frontend Layer**: 
  - Streamlit web interface with real-time chat
  - Session management and conversation history
  - ReAct process visualization and tool usage tracking

- **🧠 Agent Layer**: 
  - LangGraph ReAct agent for conversation flow
  - Intent recognition and tool selection logic
  - Intermediate step tracking and reasoning display

- **🔧 LLM Integration**: 
  - Dual provider support (OpenAI GPT + Google Gemini)
  - Automatic failover mechanism
  - Dynamic model switching based on availability

- **⚙️ Tool Layer**: 
  - MCP (Model Context Protocol) server integration
  - Order management tools (status, cancellation, tracking)
  - Knowledge base search for policies and information

- **💾 Data Layer**: 
  - Session-based conversation persistence
  - Mock GreatBuy order database
  - Customer support knowledge base (wiki)

- **📊 Infrastructure**: 
  - Docker containerization with health checks
  - Comprehensive logging with rotation
  - Environment-based configuration management
## 🚨 Troubleshooting

### Common Issues

**API Key Problems**
```bash
# Check environment variables
docker-compose exec chatbot env | grep API

# Verify API key format
echo $OPENAI_API_KEY | wc -c  # Should be around 51 characters
```

**Docker Issues**
```bash
# Check container logs
docker-compose logs chatbot

# Check container status
docker-compose ps

# Rebuild container if needed
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

**MCP Connection Problems**
```bash
# Test MCP server separately
python mcp_server_remote.py

# Check MCP configuration
cat mcp_config.json
```

**Streamlit Application Issues**
```bash
# Check application health
curl http://localhost:8501/_stcore/health

# View real-time logs
docker-compose logs -f chatbot

# Restart application
docker-compose restart chatbot
```

### Performance Tips

- Use `gpt-3.5-turbo` for faster responses during development
- Monitor token usage in the sidebar
- Clear chat history periodically for better performance
- Check Docker memory allocation if experiencing slowdowns

## 📊 Features Overview

| Feature | Status | Description |
|---------|--------|-------------|
| ✅ Chat Interface | Ready | Modern Streamlit UI with message history |
| ✅ ReAct Agent | Ready | LangGraph agent with tool integration |
| ✅ Dual LLM Support | Ready | OpenAI + Google Gemini with failover |
| ✅ MCP Tools | Ready | Order management and wiki search |
| ✅ Docker Support | Ready | Full containerization with health checks |
| ✅ Session Management | Ready | Persistent conversation state |
| ✅ Real-time Logging | Ready | Comprehensive logging with rotation |
| ⚠️ Authentication | Planned | User authentication system |
| ⚠️ Database Integration | Planned | Persistent data storage |

## 📝 License

MIT License - see [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **[Streamlit](https://streamlit.io/)** - Web app framework
- **[LangGraph](https://github.com/langchain-ai/langgraph)** - Conversation flow management
- **[OpenAI](https://openai.com/)** & **[Google Gemini](https://ai.google.dev/)** - LLM APIs
- **[Docker](https://www.docker.com/)** - Containerization

---

**🎉 Ready to deploy? Choose your method above and start chatting! 🚀**
