import streamlit as st
import os
import time
from datetime import datetime
from dotenv import load_dotenv
from loguru import logger

# Load environment variables
load_dotenv()

# Import our custom modules
from src.unified_chatbot_service import UnifiedChatbotService


class ChatbotApp:
    """
    Streamlit application for the AI Chatbot.
    
    This class handles the Streamlit UI and integrates with the LangGraph
    conversation management system.
    """
    
    def __init__(self):
        """Initialize the chatbot application."""
        self.setup_page_config()
        self.setup_logging()
        self.initialize_graph()
        self.initialize_session_state()
    
    def setup_page_config(self):
        """Configure the Streamlit page settings."""
        st.set_page_config(
            page_title=os.getenv("APP_TITLE", "GreatBuy Customer Support Agent"),
            page_icon="🛒",
            layout="wide",
            initial_sidebar_state="expanded"
        )
    
    def setup_logging(self):
        """Setup logging configuration."""
        logger.add(
            "logs/chatbot.log",
            rotation="1 MB",
            retention="7 days",
            level="INFO",
            format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}"
        )
    
    def initialize_graph(self):
        """Initialize the unified chatbot service."""
        try:
            self.chatbot_service = UnifiedChatbotService()
            logger.info("Unified chatbot service initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize chatbot service: {str(e)}")
            st.error("Failed to initialize the chatbot. Please check your configuration.")
            st.stop()
    
    def initialize_session_state(self):
        """Initialize Streamlit session state variables."""
        if "messages" not in st.session_state:
            st.session_state.messages = []
        
        if "session_id" not in st.session_state:
            import uuid
            st.session_state.session_id = str(uuid.uuid4())
            logger.info(f"New session started: {st.session_state.session_id}")
        
        if "conversation_started" not in st.session_state:
            st.session_state.conversation_started = False
    
    def display_header(self):
        """Display the application header."""
        # Use the actual GreatBuy logo
        image_path = "assets/GreatBuy_icon.png"
        
        st.image(image_path, width=100)
        st.title("GreatBuy Customer Support Agent")
        st.markdown("✨ How can I assist you today?")
    
    def display_sidebar(self):
        """Display the sidebar with app information and controls."""
        with st.sidebar:
            # GreatBuy logo in sidebar
            image_path = "assets/GreatBuy_icon.png"
            st.sidebar.divider()
            st.sidebar.image(image_path, caption="GreatBuy Customer Support Agent")
            
            st.header("📋 Chat Information")
            st.write(f"**Session ID:** `{st.session_state.session_id[:8]}...`")
            st.write(f"**Messages:** {len(st.session_state.messages)}")
            
            # Fixed status logic - more intuitive
            if st.session_state.conversation_started:
                st.write("**Status:** 🟢 Active")
            else:
                # Check if the system is properly initialized
                try:
                    mcp_status = self.chatbot_service.get_mcp_status()
                    if mcp_status['mcp_available']:
                        st.write("**Status:** 🟢 Ready")
                    else:
                        st.write("**Status:** 🟡 Ready (MCP Issues)")
                except:
                    st.write("**Status:** 🟢 Ready")
            
            st.divider()
            
            st.header("⚙️ Settings")
            
            # Clear chat button
            if st.button("🗑️ Clear Chat", type="secondary"):
                self.clear_chat()
            
            # Reset session button
            if st.button("🔄 New Session", type="secondary"):
                self.reset_session()
            
            st.divider()
            
            st.header("📊 App Info")
            st.write("**Framework:** Streamlit + LangGraph ReAct Agent")
            
            # Show which LLM provider is actually being used
            try:
                provider_info = self.chatbot_service.get_current_provider()
                st.write(f"**LLM:** {provider_info['provider']} {provider_info['model']}")
            except Exception as e:
                # Fallback to environment variable display
                openai_api_key = os.getenv("OPENAI_API_KEY")
                google_api_key = os.getenv("GOOGLE_API_KEY")
                provider_preference = os.getenv("PROVIDER_PREFERENCE", "openai").lower()
                
                if provider_preference == "openai" and openai_api_key:
                    model_name = os.getenv("MODEL", "gpt-4o")
                    st.write(f"**LLM:** OpenAI {model_name}")
                elif google_api_key:
                    fallback_model = os.getenv("FALLBACK_MODEL", "gemini-1.5-flash")
                    st.write(f"**LLM:** Google Gemini {fallback_model}")
                elif openai_api_key:
                    model_name = os.getenv("MODEL", "gpt-4o")
                    st.write(f"**LLM:** OpenAI {model_name} (fallback)")
                else:
                    st.write("**LLM:** ❌ Not configured")
            
            # Show available MCP tools and status
            try:
                mcp_status = self.chatbot_service.get_mcp_status()
                st.write(f"**MCP Status:** {'🟢 Connected' if mcp_status['mcp_available'] else '🔴 Disconnected'}")
                st.write(f"**MCP Tools:** {mcp_status['tool_count']} available")
                
                if mcp_status['tool_names']:
                    with st.expander("🔧 Available Tools"):
                        for tool in mcp_status['tool_names']:
                            st.write(f"• {tool}")
                else:
                    st.write("**Tools:** No MCP tools loaded")
                    
                # Show detailed MCP info in expander
                with st.expander("🔍 MCP Details"):
                    st.json(mcp_status)
                    
            except Exception as e:
                st.write("**MCP Status:** ❌ Error getting status")
                st.write(f"**Error:** {str(e)}")
                logger.error(f"Error displaying MCP status: {str(e)}")
            
            st.write("**Version:** 1.0.0 MVP")
            
            # API key status
            openai_api_key = os.getenv("OPENAI_API_KEY")
            google_api_key = os.getenv("GOOGLE_API_KEY")
            
            if openai_api_key and google_api_key:
                st.write("**API Status:** ✅ Both OpenAI & Google connected")
            elif openai_api_key:
                st.write("**API Status:** ✅ OpenAI connected")
            elif google_api_key:
                st.write("**API Status:** ✅ Google Gemini connected")
            else:
                st.write("**API Status:** ❌ Not connected")
                st.error("Please set either OPENAI_API_KEY or GOOGLE_API_KEY in the .env file")
    
    def display_chat_messages(self):
        """Display the chat message history."""
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])
                
                # Show intermediate steps for assistant messages if available
                if message["role"] == "assistant" and message.get("intermediate_steps"):
                    intermediate_steps = message["intermediate_steps"]
                    tools_used = message.get("tools_used", 0)
                    with st.expander(f"🔍 ReAct Process ({len(intermediate_steps)} steps, {tools_used} tools used)", expanded=False):
                        for i, step in enumerate(intermediate_steps, 1):
                            st.text(f"{i}. {step}")
                
                # Add timestamp for each message
                if "timestamp" in message:
                    st.caption(f"*{message['timestamp']}*")
    
    def process_user_input(self, user_input: str):
        """
        Process user input through the conversation graph.
        
        Args:
            user_input: The user's message
        """
        # Add user message to chat history
        timestamp = datetime.now().strftime("%H:%M:%S")
        st.session_state.messages.append({
            "role": "user",
            "content": user_input,
            "timestamp": timestamp
        })
        
        # Display user message
        with st.chat_message("user"):
            st.markdown(user_input)
            st.caption(f"*{timestamp}*")
        
        # Generate and display assistant response
        with st.chat_message("assistant"):
            with st.spinner("🤖 ReAct Agent is thinking..."):
                try:
                    # Process message through conversation graph
                    response_data = self.chatbot_service.chat(
                        user_input=user_input,
                        session_id=st.session_state.session_id
                    )
                    
                    bot_response = response_data.get("response", "I'm sorry, I couldn't generate a response.")
                    error = response_data.get("error", "")
                    intermediate_steps = response_data.get("intermediate_steps", [])
                    tools_used = response_data.get("tools_used", 0)
                    
                    if error:
                        logger.error(f"Error in chat processing: {error}")
                        st.error("An error occurred while processing your message.")
                    
                    # Display intermediate steps if any
                    if intermediate_steps:
                        with st.expander(f"🔍 ReAct Process ({len(intermediate_steps)} steps, {tools_used} tools used)", expanded=True):
                            for i, step in enumerate(intermediate_steps, 1):
                                st.text(f"{i}. {step}")
                    
                    # Display bot response
                    st.markdown(bot_response)
                    
                    # Add bot message to chat history
                    bot_timestamp = datetime.now().strftime("%H:%M:%S")
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": bot_response,
                        "timestamp": bot_timestamp,
                        "intermediate_steps": intermediate_steps,
                        "tools_used": tools_used
                    })
                    
                    st.caption(f"*{bot_timestamp}*")
                    
                    # Mark conversation as started
                    st.session_state.conversation_started = True
                    
                except Exception as e:
                    error_msg = f"Unexpected error: {str(e)}"
                    logger.error(error_msg)
                    st.error("An unexpected error occurred. Please try again.")
                    
                    # Add error message to history
                    error_timestamp = datetime.now().strftime("%H:%M:%S")
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": "I apologize, but I encountered an error. Please try again.",
                        "timestamp": error_timestamp
                    })
    
    def clear_chat(self):
        """Clear the chat history."""
        st.session_state.messages = []
        st.session_state.conversation_started = False
        logger.info("Chat history cleared")
        st.rerun()
    
    def reset_session(self):
        """Reset the entire session."""
        import uuid
        st.session_state.messages = []
        st.session_state.session_id = str(uuid.uuid4())
        st.session_state.conversation_started = False
        logger.info(f"Session reset: {st.session_state.session_id}")
        st.rerun()
    
    def run(self):
        """Run the Streamlit application."""
        try:
            # Display header
            self.display_header()
            
            # Display sidebar
            self.display_sidebar()
            
            # Check API key
            openai_api_key = os.getenv("OPENAI_API_KEY")
            google_api_key = os.getenv("GOOGLE_API_KEY")
            
            if not openai_api_key and not google_api_key:
                st.error("⚠️ No API key found. Please set either OPENAI_API_KEY or GOOGLE_API_KEY in your .env file.")
                st.info("Copy `.env.example` to `.env` and add your OpenAI API key or Google API key.")
                return
            
            # Display existing chat messages
            self.display_chat_messages()
            
            # Chat input
            if prompt := st.chat_input("Type your message here..."):
                self.process_user_input(prompt)
            
            # Welcome message for new sessions
            if not st.session_state.conversation_started and not st.session_state.messages:
                with st.chat_message("assistant"):
                    welcome_message = """
                    👋 Hello! I'm your GreatBuy customer support assistant. I'm here to help you with any questions about your orders, deliveries, membership benefits, and more.
                    
                    I can help you with:
                    - Order status and tracking
                    - Cancellations and refunds
                    - GreatBuy Premium membership benefits
                    - Shipping policies and fees
                    - Product and seller information
                    - General customer support
                    
                    How can I assist you today?
                    """
                    st.markdown(welcome_message)
                    
                    # Add welcome message to history
                    timestamp = datetime.now().strftime("%H:%M:%S")
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": welcome_message,
                        "timestamp": timestamp
                    })
                    st.caption(f"*{timestamp}*")
        
        except Exception as e:
            logger.error(f"Error running Streamlit app: {str(e)}")
            st.error("An error occurred while running the application. Please refresh the page.")


def main():
    """Main function to run the chatbot application."""
    app = ChatbotApp()
    app.run()


if __name__ == "__main__":
    main()
