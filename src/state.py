from typing import TypedDict, List, Annotated
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langgraph.graph.message import add_messages


class ChatState(TypedDict):
    """
    State schema for the chatbot conversation.
    
    This defines the structure of data that flows through the LangGraph nodes.
    """
    # Messages in the conversation with automatic message addition
    messages: Annotated[List[BaseMessage], add_messages]
    
    # User session identifier
    session_id: str
    
    # Current user input
    user_input: str
    
    # Bot response
    bot_response: str
    
    # Conversation context/memory
    context: str
    
    # Error handling
    error: str
    
    # Metadata for tracking
    turn_count: int
