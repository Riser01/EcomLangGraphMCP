import uuid
import os
import warnings
from typing import Dict, Any, List, Union, Optional

# --- NECESSARY IMPORTS FOR MCP ---
import asyncio
import nest_asyncio

from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
from loguru import logger

from .state import ChatState

# Apply nest_asyncio to allow running async code from sync contexts
nest_asyncio.apply()


class ConversationGraph:
    """
    LangGraph ReAct agent implementation for managing conversation flow.
    
    This class creates and manages a ReAct agent that can intelligently
    select and use MCP tools to answer customer support questions.
    """
    
    def __init__(self):
        """Initialize the ReAct agent and MCP Client."""
        self.memory = MemorySaver()  # In-memory state persistence
        
        # Initialize LLM
        self.llm = self._initialize_llm()
        
        # --- INTEGRATED MCP INITIALIZATION ---
        self._mcp_client = None
        self.mcp_tools = []
        self._initialized = False
        
        # Default MCP configuration
        self.mcp_config = {
            "GreatBuy-support": {
                "command": "python",
                "args": ["./mcp_server_remote.py"],
                "transport": "stdio"
            }
        }
        
        # Run the async tool initialization from the sync __init__ method
        try:
            logger.info("Starting MCP client initialization...")
            # This blocks until the async method is complete.
            asyncio.run(self._async_initialize_mcp_tools())
        except Exception as e:
            logger.error(f"❌ Critical error during MCP initialization: {e}")
            # Ensure agent is created even if MCP fails
            self.agent = self._create_react_agent()
            return
            
        # Create the ReAct agent after tools have been initialized
        self.agent = self._create_react_agent()
    
    def _initialize_llm(self) -> Union[ChatOpenAI, ChatGoogleGenerativeAI]:
        """Initialize the LLM with preference for OpenAI, fallback to Google Gemini."""
        openai_api_key = os.getenv("OPENAI_API_KEY")
        google_api_key = os.getenv("GOOGLE_API_KEY")
        provider_preference = os.getenv("PROVIDER_PREFERENCE", "openai").lower()
        
        # Prefer OpenAI if available and preference is set to openai
        if provider_preference == "openai" and openai_api_key:
            try:
                model_name = os.getenv("MODEL", "gpt-3.5-turbo")
                logger.info(f"Initializing OpenAI model: {model_name}")
                return ChatOpenAI(
                    model=model_name,
                    temperature=0.7,
                    api_key=openai_api_key,
                    streaming=True
                )
            except Exception as e:
                logger.warning(f"Failed to initialize OpenAI: {str(e)}")
        
        # Fallback to Google Gemini
        if google_api_key:
            try:
                fallback_model = os.getenv("FALLBACK_MODEL", "gemini-1.5-flash")
                logger.info(f"Initializing Google Gemini model: {fallback_model}")
                return ChatGoogleGenerativeAI(
                    model=fallback_model,
                    temperature=0.7,
                    google_api_key=google_api_key,
                    streaming=True
                )
            except Exception as e:
                logger.warning(f"Failed to initialize Google Gemini: {str(e)}")
        
        # Try OpenAI as last resort if Google Gemini failed
        if openai_api_key:
            try:
                model_name = os.getenv("MODEL", "gpt-3.5-turbo")
                logger.info(f"Using OpenAI as fallback: {model_name}")
                return ChatOpenAI(
                    model=model_name,
                    temperature=0.7,
                    api_key=openai_api_key,
                    streaming=True
                )
            except Exception as e:
                logger.error(f"Failed to initialize OpenAI as fallback: {str(e)}")
        
        # If neither works, raise an error
        raise ValueError(
            "No valid API key found. Please set either OPENAI_API_KEY or GOOGLE_API_KEY environment variable."
        )

    async def _async_initialize_mcp_tools(self):
        """Asynchronously starts the MCP client and loads the tools."""
        try:
            logger.info("🔄 Starting MCP client initialization...")
            
            # Try to import and load MCP tools
            try:
                from langchain_mcp_adapters.client import MultiServerMCPClient
                logger.info("✅ MCP libraries imported successfully")
                
                # Create the MultiServerMCPClient
                self._mcp_client = MultiServerMCPClient(self.mcp_config)
                logger.info("✅ MCP client created successfully")
                
                # Use the new approach: get_tools() instead of context manager
                self.mcp_tools = await self._mcp_client.get_tools()
                logger.info("✅ MCP tools retrieved successfully")
                
                if self.mcp_tools:
                    logger.success(f"✅ Successfully loaded {len(self.mcp_tools)} MCP tools")
                    for i, tool in enumerate(self.mcp_tools, 1):
                        logger.info(f"   {i}. {tool.name} - {getattr(tool, 'description', 'No description')}")
                else:
                    logger.warning("⚠️  MCP tools loaded but list is empty")
                
                self._initialized = True
                
            except ImportError as e:
                logger.warning(f"❌ MCP libraries not available: {str(e)}")
                logger.info("📋 Required packages: langchain-mcp-adapters")
                self.mcp_tools = []
                
        except Exception as e:
            logger.error(f"❌ Critical error in MCP client initialization: {str(e)}")
            logger.exception("Full error details:")
            self.mcp_tools = []
            await self._cleanup_mcp()
            
        # Final status report
        if self.mcp_tools:
            logger.success(f"🎉 MCP Client initialized with {len(self.mcp_tools)} tools")
        else:
            logger.warning("⚠️  MCP Client initialized with NO tools - running in fallback mode")

    def _create_react_agent(self):
        """Create a ReAct agent with MCP tools."""
        # Store system message for later use in chat method
        self.system_message = """<ROLE>
You are a smart GreatBuy customer support agent with an ability to use tools. 
You will be given a question and you will use the tools to answer the question.
Pick the most relevant tool to answer the question. 
If you fail to answer the question, try different tools to get context.
Your answer should be very polite and professional.
</ROLE>
----
<INSTRUCTIONS>
Step 1: Analyze the question
- Analyze user's question and final goal.
- If the user's question consists of multiple sub-questions, split them into smaller sub-questions.

Step 2: Pick the most relevant tool
- Pick the most relevant tool to answer the question.
- **If the query is a simple greeting or does not require a tool, answer directly in a polite and professional manner.**
- If you fail to answer the question, try different tools to get context.

Step 3: Answer the question
- Answer the question in the same language as the question.
- Your answer should be very polite and professional.

Step 4: Provide the source of the answer (if applicable)
- If you've used a tool, provide the source of the answer.
- Valid sources are either a website (URL) or a document (PDF, etc).

Guidelines:
- If you've used a tool, your answer should be based on the tool's output (tool's output is more important than your own knowledge).
- If you've used a tool and the source is a valid URL, provide the source (URL) of the answer.
- Skip providing the source if the source is not a URL.
- Answer in the same language as the question.
- Answer should be concise and to the point.
- Always think step by step and explain your reasoning process.
- Show intermediate steps when using tools.
</INSTRUCTIONS>
----
<OUTPUT_FORMAT>
(concise answer to the question)

Source: (if applicable)
</OUTPUT_FORMAT>"""
        
        # Log agent creation details
        tool_count = len(self.mcp_tools)
        logger.info(f"🤖 Creating ReAct agent with {tool_count} tools")
        
        if self.mcp_tools:
            tool_names = [getattr(tool, 'name', 'Unknown') for tool in self.mcp_tools]
            logger.info(f"🛠️  Agent will use tools: {tool_names}")
        else:
            logger.warning("⚠️  Agent will be created WITHOUT tools (basic responses only)")

        # Create the ReAct agent
        try:
            # This self.agent assignment is correctly placed
            agent = create_react_agent(
                model=self.llm,
                tools=self.mcp_tools,
                checkpointer=self.memory
            )
            
            logger.success(f"✅ ReAct agent created successfully with {tool_count} tools")
            return agent
            
        except Exception as e:
            logger.error(f"❌ Failed to create ReAct agent: {str(e)}")
            logger.exception("Full error details:")
            raise

    async def _cleanup_mcp(self):
        """Cleanup MCP client resources."""
        if self._mcp_client:
            try:
                logger.info("🔌 Shutting down MCP client...")
                # Since we're not using context manager anymore, just reset the reference
                self._mcp_client = None
                self._initialized = False
                logger.info("✅ MCP client shutdown complete")
            except Exception as e:
                logger.error(f"❌ Error during MCP client cleanup: {str(e)}")

    async def cleanup(self):
        """Gracefully shuts down the MCP client and its subprocesses."""
        await self._cleanup_mcp()
    
    def chat(self, user_input: str, session_id: str) -> Dict[str, Any]:
        """
        Process user input through the ReAct agent.
        
        Args:
            user_input: The user's message
            session_id: Session identifier for conversation continuity
            
        Returns:
            Dictionary containing response and metadata
        """
        try:
            logger.info(f"💬 Processing message through ReAct agent: {user_input[:50]}...")
            
            # Log current setup
            tool_count = len(self.mcp_tools)
            logger.info(f"🛠️  Agent has {tool_count} tools available")
            # Fallback to direct LLM if no tools are available
            if tool_count == 0:
                logger.info("⚠️ No tools available, using direct LLM fallback")
                messages = [
                    SystemMessage(content=self.system_message),
                    HumanMessage(content=user_input)
                ]
                llm_result = self.llm.invoke(messages)
                if hasattr(llm_result, "generations"):
                    content = llm_result.generations[0][0].text
                elif hasattr(llm_result, "content"):
                    content = llm_result.content
                else:
                    content = str(llm_result)
                return {
                    "response": content,
                    "intermediate_steps": [],
                    "error": "",
                    "tools_used": 0
                }
            
            # Create the thread config for session management
            config = {"configurable": {"thread_id": session_id}}
            
            # Prepare input messages with system message first
            messages = [
                SystemMessage(content=self.system_message),
                HumanMessage(content=user_input)
            ]
            
            # Track intermediate steps and final response
            intermediate_steps = []
            final_response = ""
            
            # Stream the agent's response to capture intermediate steps
            logger.info("🤖 ReAct Agent: Starting to process query...")
            
            # Add warning suppression for Google Gemini FinishReason enum issue
            import warnings
            warnings.filterwarnings("ignore", message="Unrecognized FinishReason enum value")
            
            for chunk in self.agent.stream({"messages": messages}, config, stream_mode="values"):
                if "messages" in chunk:
                    last_message = chunk["messages"][-1]
                    
                    if hasattr(last_message, 'content') and last_message.content:
                        # Check if this is a tool call or reasoning step
                        if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
                            for tool_call in last_message.tool_calls:
                                tool_step = f"🔧 Using tool: {tool_call['name']} with args: {tool_call['args']}"
                                logger.info(tool_step)
                                intermediate_steps.append(tool_step)
                        
                        # Check if this is the final response
                        elif last_message.type == "ai" and not hasattr(last_message, 'tool_calls'):
                            final_response = last_message.content
                            logger.info(f"✅ Final response generated: {final_response[:100]}...")
                        
                        # Log reasoning steps
                        elif last_message.type == "ai" and "Thought:" in last_message.content:
                            reasoning_step = f"💭 Reasoning: {last_message.content}"
                            logger.info(reasoning_step)
                            intermediate_steps.append(reasoning_step)
            
            # If no final response was captured, get the last AI message
            if not final_response:
                # Get the conversation state to extract the final response
                state = self.agent.get_state(config)
                if state.values.get("messages"):
                    for msg in reversed(state.values["messages"]):
                        if msg.type == "ai" and not hasattr(msg, 'tool_calls'):
                            final_response = msg.content
                            break
            
            # Clean up warnings
            warnings.filterwarnings("default")
            
            if not final_response:
                final_response = "I apologize, but I couldn't generate a proper response. Please try rephrasing your question."
            
            # Calculate tools used
            tools_used_count = len([step for step in intermediate_steps if "Using tool:" in step])
            
            logger.success(f"✅ ReAct agent completed processing (Tools used: {tools_used_count})")
            
            return {
                "response": final_response,
                "intermediate_steps": intermediate_steps,
                "error": "",
                "tools_used": tools_used_count
            }
            
        except Exception as e:
            error_msg = f"Error in ReAct agent processing: {str(e)}"
            logger.error(f"❌ {error_msg}")
            logger.exception("Full error trace:")
            
            # Provide more helpful error message based on error type
            if "'int' object has no attribute 'name'" in str(e):
                error_explanation = "Google Gemini FinishReason enum issue detected. The model completed successfully but there's a minor protocol issue."
                fallback_response = "I'm here to help with your GreatBuy order! Could you please tell me your order ID or what specific information you need?"
            else:
                error_explanation = error_msg
                fallback_response = "I apologize, but I encountered an error while processing your request. Please try again."
            
            logger.info(f"🔧 Error explanation: {error_explanation}")
            
            return {
                "response": fallback_response,
                "intermediate_steps": [f"❌ Error: {error_explanation}"],
                "error": error_msg,
                "tools_used": 0
            }
    
    def get_available_tools(self) -> List[str]:
        """
        Get list of available tool names.
        
        Returns:
            List of tool names
        """
        tool_names = []
        for tool in self.mcp_tools:
            tool_name = getattr(tool, 'name', 'Unknown')
            tool_names.append(tool_name)
        
        logger.info(f"📋 Available tool names: {tool_names}")
        return tool_names

    def get_mcp_status(self) -> Dict[str, Any]:
        """
        Get detailed MCP connection status and tool information.
        
        Returns:
            Dictionary with MCP status details
        """
        try:
            mcp_available = self.is_mcp_available()
            tool_count = len(self.mcp_tools)
            tool_names = self.get_available_tools()
            
            status = {
                "mcp_available": mcp_available,
                "tool_count": tool_count,
                "tool_names": tool_names,
                "mcp_client_tools": len(self.mcp_tools) if self._mcp_client else 0,
                "connection_status": "Connected" if mcp_available else "Disconnected"
            }
            
            logger.info(f"📊 MCP Status: {status}")
            return status
            
        except Exception as e:
            logger.error(f"❌ Error getting MCP status: {str(e)}")
            return {
                "mcp_available": False,
                "tool_count": 0,
                "tool_names": [],
                "mcp_client_tools": 0,
                "connection_status": "Error",
                "error": str(e)
            }

    def is_mcp_available(self) -> bool:
        """
        Check if MCP tools are available.
        
        Returns:
            True if tools are loaded, False otherwise
        """
        available = bool(self.mcp_tools and self._initialized)
        logger.debug(f"🔍 MCP availability check: {available} (tools: {len(self.mcp_tools)}, initialized: {self._initialized})")
        return available

    def get_tool_by_name(self, tool_name: str) -> Optional[object]:
        """
        Get a specific tool by name.
        
        Args:
            tool_name: Name of the tool to retrieve
            
        Returns:
            The tool if found, None otherwise
        """
        for tool in self.mcp_tools:
            if tool.name == tool_name:
                return tool
        return None

    def describe_tools(self) -> str:
        """
        Get a description of all available tools.
        
        Returns:
            String description of tools
        """
        if not self.mcp_tools:
            return "No MCP tools available"
        
        descriptions = []
        for tool in self.mcp_tools:
            descriptions.append(f"- {tool.name}: {getattr(tool, 'description', 'No description available')}")
        
        return "Available MCP Tools:\n" + "\n".join(descriptions)

    def get_conversation_history(self, session_id: str) -> List[Dict[str, Any]]:
        """
        Get conversation history for a session.
        
        Args:
            session_id: Session identifier
            
        Returns:
            List of messages in the conversation
        """
        try:
            config = {"configurable": {"thread_id": session_id}}
            state = self.agent.get_state(config)
            
            messages = []
            for msg in state.values.get("messages", []):
                messages.append({
                    "type": msg.type,
                    "content": msg.content,
                    "timestamp": getattr(msg, "timestamp", None)
                })
            
            return messages
            
        except Exception as e:
            logger.error(f"Error getting conversation history: {str(e)}")
            return []
    
    def get_current_provider(self) -> Dict[str, str]:
        """
        Get information about the current LLM provider being used.
        
        Returns:
            Dict containing provider name and model name
        """
        try:
            if hasattr(self.llm, 'model_name'):
                # OpenAI models
                return {
                    "provider": "OpenAI",
                    "model": self.llm.model_name
                }
            elif hasattr(self.llm, 'model'):
                # Google Gemini models
                return {
                    "provider": "Google Gemini",
                    "model": self.llm.model
                }
            else:
                return {
                    "provider": "Unknown",
                    "model": "Unknown"
                }
        except Exception as e:
            logger.error(f"Error getting provider info: {str(e)}")
            return {
                "provider": "Error",
                "model": "Error"
            }