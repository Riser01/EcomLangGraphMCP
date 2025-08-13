from mcp.server.fastmcp import FastMCP

# --- Import GreatBuy Mock Data Sources ---
from data import (
    _MOCK_WIKI_DB,
    _MOCK_SELLERS_DB,
    _MOCK_LOGISTICS_PARTNERS_DB
)
# Use persistent order database instead of mock
from persistent_data import persistent_orders_db

# --- MCP Server Setup ---
SERVER_HOST = "0.0.0.0"
SERVER_PORT = 8007

mcp = FastMCP(
    "GreatBuySupportAssistantTools",
    instructions=(
        "You are a GreatBuy customer support assistant. "
        "Use the available tools to help customers with their GreatBuy orders and queries. "
        "If a customer asks about GreatBuy services, policies (like cancellation, returns), or membership (like GreatBuy Premium), use the 'search_wiki' tool. "
        "If a customer asks about their order status, use the 'read_order_status' tool with their order ID (e.g., ORDZW001). "
        "If a customer wants to cancel an order, use the 'update_order_status' tool. For cancellations, set the new_status to 'cancelled'. "
        "Be polite and helpful."
    ),
    host=SERVER_HOST,
    port=SERVER_PORT,
)

# --- MCP Tools ---

@mcp.tool()
async def search_wiki(query: str) -> str:
    """
    Searches the GreatBuy WIKI for information based on a query.
    Use this to answer questions about GreatBuy services, shipping fees, membership, policies, etc.

    Args:
        query (str): The search term or question from the customer.
                     Example: "GreatBuy Premium benefits", "return policy", "shipping fees"

    Returns:
        str: Information found in the WIKI related to the query, or a message if nothing is found.
    """
    print(f"[MCP WIKI Server] Received search_wiki request with query: '{query}'")
    query_lower = query.lower()
    # Prioritize exact or near-exact keyword matches
    for keyword, content in _MOCK_WIKI_DB.items():
        if keyword in query_lower or query_lower in keyword:
            print(f"[MCP WIKI Server] Found direct match for '{keyword}'.")
            return content
    # Fallback to content search
    for keyword, content in _MOCK_WIKI_DB.items():
        if query_lower in content.lower():
            print(f"[MCP WIKI Server] Found partial content match for query '{query}' in content for '{keyword}'.")
            return content
    print(f"[MCP WIKI Server] No information found for query: '{query}'.")
    return f"I couldn't find specific information for '{query}' in our GreatBuy WIKI. Could you rephrase or ask about something else?"

@mcp.tool()
async def read_order_status(order_id: str) -> str:
    """
    Reads the current status and details of a customer's GreatBuy order using the order ID.

    Args:
        order_id (str): The unique identifier for the order. Example: "ORDZW001"

    Returns:
        str: A message indicating the order details and status, or an error if the order is not found.
    """
    print(f"[MCP Order Server] Received read_order_status request for order_id: '{order_id}'")
    order = persistent_orders_db.get(order_id)
    if order:
        seller_name = "Unknown Seller"
        if order.get("seller_id") and order["seller_id"] in _MOCK_SELLERS_DB:
            seller_name = _MOCK_SELLERS_DB[order["seller_id"]]["name"]

        items_str = ", ".join(order.get("items", ["No items listed"]))
        status_message = (
            f"Order '{order_id}': Status is '{order['status']}'. "
            f"Items: {items_str}. "
            f"Seller: {seller_name}. "
            f"Estimated Delivery: {order.get('estimated_delivery_time', 'N/A')}. "
        )
        if order.get("special_instructions"):
            status_message += f"Special Instructions: {order['special_instructions']}"

        print(f"[MCP Order Server] {status_message}")
        return status_message
    else:
        error_message = f"Sorry, I could not find a GreatBuy order with ID '{order_id}'."
        print(f"[MCP Order Server] {error_message}")
        return error_message

@mcp.tool()
async def update_order_status(order_id: str, new_status: str) -> str:
    """
    Updates the status of an existing GreatBuy customer order, primarily for cancellation.
    For cancellations, set new_status to 'cancelled'.

    Args:
        order_id (str): The unique identifier for the order to be updated. Example: "ORDZW001"
        new_status (str): The new status to set. For cancellation, this must be 'cancelled'.

    Returns:
        str: A confirmation message if the update was successful, or an error/reason if not.
    """
    print(f"[MCP Order Server] Received update_order_status request for order_id: '{order_id}', new_status: '{new_status}'")
    order = persistent_orders_db.get(order_id)

    if not order:
        error_message = f"Sorry, I could not find a GreatBuy order with ID '{order_id}' to update."
        print(f"[MCP Order Server] {error_message}")
        return error_message

    normalized_new_status = new_status.lower()

    if normalized_new_status == "cancelled":
        current_status_lower = order["status"].lower()
        cancellable_statuses = ["processing", "awaiting shipment", "preparing for shipment"]

        if current_status_lower in cancellable_statuses:
            update_result = persistent_orders_db.update(order_id, {
                "status": "Cancelled",
                "estimated_delivery_time": None
            })
            
            if update_result:
                message = f"Order '{order_id}' has been successfully cancelled."
                print(f"[MCP Order Server] {message}")
                print(f"[MCP Order Server] Order status persisted to database")
                return message
            else:
                error_message = f"Failed to update order '{order_id}' in database."
                print(f"[MCP Order Server] {error_message}")
                return error_message
        elif current_status_lower == "cancelled":
            message = f"Order '{order_id}' is already cancelled."
            print(f"[MCP Order Server] {message}")
            return message
        else:
            message = f"Order '{order_id}' cannot be cancelled because its current status is '{order['status']}'. Please refer to our cancellation policy or contact support for more help."
            print(f"[MCP Order Server] {message}")
            return message
    else:
        message = f"This tool is primarily for cancelling orders. To change status to '{new_status}' is not supported via this action for order '{order_id}'. Current status remains '{order['status']}'."
        print(f"[MCP Order Server] {message}")
        return message


if __name__ == "__main__":
    print("MCP server for GreatBuy Support Assistant Tools is running...")
    print(f"Access it at http://{SERVER_HOST}:{SERVER_PORT}")
    mcp.run(transport="stdio")